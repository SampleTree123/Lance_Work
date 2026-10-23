"""Launch a frozen render bundle against an already running UE editor.

Default is a read-only command preview. Use --execute to render; never retries
or forces completed jobs. One editor and output root per worker.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bundle_file(bundle, relative):
    path = (bundle / relative).resolve()
    if not path.is_relative_to(bundle.resolve()):
        raise ValueError('Bundle path escapes root: ' + relative)
    return path


def build_command(bundle, machine, queue_name, limit=None, job_ids=()):
    config = read(bundle / 'RENDER_CONFIG.json')
    if queue_name not in config['queues']:
        raise ValueError('Unknown queue: ' + queue_name)
    if limit is not None and limit < 1:
        raise ValueError('limit must be positive')
    for key in ('workspace_root', 'project_root', 'engine_root', 'output_root'):
        if not machine.get(key) or not Path(machine[key]).is_absolute():
            raise ValueError('Fill absolute machine path: ' + key)
    pool = machine.get('texture_pool_mb')
    if not isinstance(pool, int) or isinstance(pool, bool) or pool <= 0:
        raise ValueError('Fill positive server texture_pool_mb; do not inherit local GPU budget')
    queue = config['queues'][queue_name]
    jobs_path = bundle_file(bundle, queue['jobs'])
    jobs = read(jobs_path)['jobs']
    unknown = set(job_ids) - {j['job_id'] for j in jobs}
    if unknown:
        raise ValueError('Unknown job IDs: ' + ', '.join(sorted(unknown)))
    run = Path(machine['output_root']) / queue['output_subdir']
    cmd = [machine.get('python_executable') or sys.executable,
           str(Path(machine['workspace_root']) / '00_engine/scripts/unreal/run_dataset_render_v11.py'),
           '--workspace', machine['workspace_root'], '--project-root', machine['project_root'],
           '--engine-root', machine['engine_root'], '--run-root', str(run),
           '--jobs', str(jobs_path), '--worker-module', queue['worker_module'],
           '--pool-mb', str(pool)]
    runtime = config['runtime']
    if runtime.get('portable_runtime', True):
        cmd.append('--portable-runtime')
    for key in ('command_timeout', 'render_timeout', 'discovery_timeout'):
        cmd += ['--' + key.replace('_', '-'), str(runtime[key])]
    for key in ('ffmpeg', 'node_id'):
        if machine.get(key):
            cmd += ['--' + key.replace('_', '-'), machine[key]]
    if limit is not None:
        cmd += ['--limit', str(limit)]
    for jid in job_ids:
        cmd += ['--job-id', jid]
    return cmd, run, queue


def seed_output(bundle, run, queue):
    for name, source in queue.get('seed_files', {}).items():
        if Path(name).name != name:
            raise ValueError('Seed destination must be a file name')
        src, dest = bundle_file(bundle, source), run / name
        if dest.exists() and dest.read_bytes() != src.read_bytes():
            raise ValueError('Existing output has different carrier definitions: ' + str(dest))
    run.mkdir(parents=True, exist_ok=True)
    for name, source in queue.get('seed_files', {}).items():
        dest = run / name
        if not dest.exists():
            shutil.copyfile(bundle_file(bundle, source), dest)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--machine', type=Path, required=True)
    p.add_argument('--queue', required=True)
    p.add_argument('--limit', type=int)
    p.add_argument('--job-id', action='append', default=[])
    p.add_argument('--execute', action='store_true')
    args = p.parse_args(argv)
    try:
        bundle = args.bundle.resolve()
        machine = read(args.machine)
        command, run, queue = build_command(bundle, machine, args.queue, args.limit, args.job_id)
        print(json.dumps({'mode': 'execute' if args.execute else 'preview_only',
                          'command': command, 'output': str(run)}, ensure_ascii=False), flush=True)
        if not args.execute:
            return 0
        for key in ('workspace_root', 'project_root', 'engine_root'):
            if not Path(machine[key]).is_dir():
                raise ValueError('Machine directory missing: ' + key)
        seed_output(bundle, run, queue)
        return subprocess.run(command, check=False).returncode
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
