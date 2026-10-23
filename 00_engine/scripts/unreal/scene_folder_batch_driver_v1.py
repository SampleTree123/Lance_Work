"""Explicitly invoked, serial scene migration host. Default is offline planning only.

Never retries a move, kills an editor, renders, deletes assets or edits frozen runs.
UE remains the sole writer of assets; this host writes only receipts and saved view cache.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

SCRIPTS = Path(__file__).resolve().parent
ENGINE = SCRIPTS.parents[1]
RUN = ENGINE / 'outputs/scene_folder_organization_20261012_v1'
TEMP = ENGINE / 'temp/scene_folder_organization_20261012_v1/driver'
PROJECT = Path('D:/UE/projects/datatry_02/datatry_02.uproject')
EDITOR = Path('D:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
ENTRY = '/Game/DataMake/Validation/CameraMotionPilot20261009/MapsV2/L_cam_01_static_front_v003'
REGISTRY = ENGINE / 'assets/scene_folder_relocation_20261012_v1.json'
PROTECTED = {'StarterContent', 'Scenes', 'DataMake', 'CC_Rigs', 'CC_Shaders'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def slug(root):
    if not re.fullmatch(r'/Game/[A-Za-z0-9_]+', root) or root[6:] in PROTECTED:
        raise ValueError('Only explicitly selected, unprotected top-level scene roots allowed: ' + root)
    return root[6:]


def receipt(root, kind, run=RUN):
    return Path(run) / f'{kind}_{slug(root)}_v1.json'


def successful_verification(root, baseline_sha, run=RUN):
    """A later failed verification invalidates an earlier success until investigated."""
    paths = sorted(Path(run).glob(f'verified_{slug(root)}_v*.json'), key=lambda p: p.stat().st_mtime_ns)
    if not paths:
        return None
    path = paths[-1]
    data = read(path)
    if data.get('root') != root or data.get('destination') != '/Game/Scenes/' + slug(root):
        raise RuntimeError('Verification root mismatch: ' + str(path))
    if data.get('baseline_sha256') != baseline_sha:
        raise RuntimeError('Verification baseline SHA mismatch: ' + str(path))
    return path if data.get('success') is True else None


def route(root, entry, run=RUN):
    """Uncertain writes are an inspection stop, never an automatic retry."""
    base = receipt(root, 'baseline', run)
    move = receipt(root, 'move', run)
    if base.exists():
        data = read(base)
        if data.get('success') is not True or data.get('root') != root or not data.get('assets'):
            raise RuntimeError('Invalid/empty baseline')
        if entry.get('baseline_sha256') not in (None, sha(base)):
            raise RuntimeError('Frozen baseline changed')
        proof = successful_verification(root, sha(base), run)
        if proof:
            if entry.get('verification_sha256') not in (None, sha(proof)):
                raise RuntimeError('Frozen verification changed')
            return 'verified', proof
    elif move.exists() or entry.get('move_intent'):
        raise RuntimeError('Move without original baseline')
    else:
        return 'baseline', None
    if move.exists():
        data = read(move)
        if data.get('root') != root or data.get('baseline_sha256') != sha(base):
            raise RuntimeError('Move receipt provenance mismatch')
        if data.get('rename_returned') is True:
            return 'verify', None
        raise RuntimeError('Failed/uncertain move requires manual inspection; will not retry')
    if entry.get('move_intent'):
        raise RuntimeError('Move dispatched without conclusive receipt; will not retry')
    return 'move', None


def reset_view_bytes(raw):
    """Replace exactly the one setting value; retain BOM, line endings and all else."""
    matches = list(re.finditer(rb'(?m)^EditorViews=[^\r\n]*', raw))
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one EditorViews setting')
    m = matches[0]
    return raw[:m.start()] + b'EditorViews=()' + raw[m.end():]


def assert_identity(process, expected_pid=None):
    if expected_pid is not None and process.pid != expected_pid:
        raise RuntimeError('Wrong editor PID')
    if not process.is_running():
        raise RuntimeError('Editor process exited')
    norm = lambda x: os.path.normcase(os.path.abspath(x))
    if norm(process.exe()) != norm(EDITOR):
        raise RuntimeError('PID is not the configured UnrealEditor')
    args = process.cmdline()
    if not any(norm(arg.strip('"')) == norm(PROJECT) for arg in args[1:]):
        raise RuntimeError('PID is not the configured project')
    return {'pid': process.pid, 'create_time': process.create_time(), 'exe': process.exe(), 'cmdline': args}


def payload_code(payload_path):
    # repr is Python string escaping, never shell escaping. JSON is read from disk.
    return '''import json, os, sys, inspect
from pathlib import Path
payload = json.loads(Path(%r).read_text(encoding='utf-8'))
sys.path.insert(0, payload['scripts'])
import unreal as u
import ue_scene_folder_organization_v1 as migration
if os.getpid() != payload['pid']:
    raise RuntimeError('Remote editor PID mismatch')
migration.guard(u)
action = payload['action']
if action == 'guard':
    print('SCENE_DRIVER_GUARD_OK')
elif action == 'quit':
    u.SystemLibrary.quit_editor()
elif action == 'verify':
    if 'receipt_filename' in inspect.signature(migration.verify).parameters:
        migration.verify(u, payload['root'], receipt_filename=payload['receipt_filename'])
    else:
        old = migration.RUN / ('verified_' + payload['root'][6:] + '_v1.json')
        if old.exists():
            raise RuntimeError('Versioned verify API required to preserve previous evidence')
        migration.verify(u, payload['root'])
elif action in ('baseline', 'move'):
    getattr(migration, action)(u, payload['root'])
else:
    raise RuntimeError('Unsupported driver action')
''' % str(payload_path)


class Driver:
    def __init__(self, roots, batch_size, editor_pid, timeout=7200):
        if not roots or len(set(roots)) != len(roots) or batch_size not in (1, 2, 3):
            raise ValueError('Unique roots and batch size 1-3 required')
        for root in roots:
            slug(root)
        self.roots, self.batch_size, self.timeout = roots, batch_size, timeout
        import psutil
        self.process = psutil.Process(editor_pid)
        assert_identity(self.process, editor_pid)
        self.state_path = RUN / 'batch_driver_state_v1.json'
        self.state = read(self.state_path) if self.state_path.exists() else {'schema': 'scene_batch_driver_v1', 'roots': {}, 'pins': {}}
        self.session = stamp()
        self.code_pins = {str(p): sha(p) for p in (Path(__file__), SCRIPTS / 'ue_scene_folder_organization_v1.py', SCRIPTS / 'ue_remote_exec.py')}
        atomic(RUN / ('driver_session_' + self.session + '.json'), {
            'session': self.session, 'roots': roots, 'batch_size': batch_size,
            'editor': assert_identity(self.process), 'source_pins': self.code_pins,
            'source_pin_scope': 'This invocation only; later audited code revisions use a new session.'})

    def progress(self, message):
        print(stamp() + ' ' + message, flush=True)

    def save(self):
        atomic(self.state_path, self.state)

    def pin(self, path):
        key, value = str(path), sha(path)
        if self.state['pins'].get(key, value) != value:
            raise RuntimeError('Frozen driver input changed: ' + key)
        self.state['pins'][key] = value
        self.save()

    def preflight(self):
        for path in (RUN / 'backup_manifest_v1.json', RUN / 'external_referencer_backup_v1.json', RUN / 'editor_view_history_before_v1.ini'):
            self.pin(path)
        backup = read(RUN / 'backup_manifest_v1.json')
        external = read(RUN / 'external_referencer_backup_v1.json')
        if backup.get('success') is not True or external.get('success') is not True:
            raise RuntimeError('Successful original and external backup required')
        if not set(self.roots).issubset(backup.get('completed_roots', [])):
            raise RuntimeError('Requested scene lacks completed original backup')
        pilot = '/Game/Synthwave_city'
        base = receipt(pilot, 'baseline')
        if not base.exists() or not successful_verification(pilot, sha(base)):
            raise RuntimeError('Pilot structural verification unresolved: driver execution prohibited')
        self.dispatch('guard')

    def dispatch(self, action, root=None):
        self.progress('Starting ' + action + (' ' + root if root else '') + f' (UE PID {self.process.pid})')
        assert_identity(self.process)
        for key, value in {**self.state['pins'], **self.code_pins}.items():
            if sha(key) != value:
                raise RuntimeError('Frozen input changed: ' + key)
        token = stamp() + '_' + action + ('_' + slug(root) if root else '')
        TEMP.mkdir(parents=True, exist_ok=True)
        data = {'scripts': str(SCRIPTS), 'pid': self.process.pid, 'action': action, 'root': root,
                'receipt_filename': f'verified_{slug(root)}_vdriver_{token}.json' if root else None}
        payload, script = TEMP / (token + '.json'), TEMP / (token + '.py')
        atomic(payload, data)
        script.write_text(payload_code(payload), encoding='utf-8')
        log = RUN / ('driver_' + token + '.log')
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([sys.executable, str(SCRIPTS / 'ue_remote_exec.py'), '--project', 'datatry_02', '--discovery-timeout', '90', '--script', str(script)],
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=self.timeout, shell=False)
        if result.returncode and action != 'quit':
            raise RuntimeError('Remote action failed; see ' + str(log))
        self.progress('Finished ' + action + '; log=' + str(log))
        return data

    def restart(self):
        self.dispatch('guard')
        identity = assert_identity(self.process)
        atomic(RUN / ('driver_quit_' + stamp() + '.json'), identity)
        self.dispatch('quit')
        try:
            self.process.wait(timeout=180)
        except Exception as exc:
            raise RuntimeError('Editor did not exit; cache unchanged, no forced kill') from exc
        if self.process.is_running():
            raise RuntimeError('Editor still live; cache unchanged')
        # Refuse if another editor for this project appeared while waiting.
        import psutil
        for p in psutil.process_iter(['name']):
            if (p.info['name'] or '').lower() == 'unrealeditor.exe':
                try:
                    assert_identity(p)
                except (RuntimeError, psutil.NoSuchProcess):
                    continue
                raise RuntimeError('Another configured-project editor exists; cache unchanged')
        ini = PROJECT.parent / 'Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini'
        original = ini.read_bytes()
        updated = reset_view_bytes(original)
        token = stamp()
        before = RUN / ('editor_view_history_before_driver_' + token + '.ini')
        before.write_bytes(original)
        ini.write_bytes(updated)
        atomic(RUN / ('editor_view_history_reset_' + token + '.json'), {'before': str(before), 'before_sha256': sha(before), 'after_sha256': sha(ini), 'exited_editor': identity})
        args = [str(EDITOR), str(PROJECT), ENTRY, '-nosplash', '-nosound', '-nop4', '-NoLiveCoding', '-unattended',
                '-asyncTexturecompilationmaxconcurrency=2', '-asyncStaticMeshcompilationmaxconcurrency=2',
                '-abslog=' + str(RUN / ('editor_driver_' + token + '.log'))]
        child = subprocess.Popen(args, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        self.process = psutil.Process(child.pid)
        self.progress(f'Launched UE PID {child.pid}; waiting for remote discovery')
        atomic(RUN / ('editor_driver_launch_' + token + '.json'), {'pid': child.pid, 'command': args})
        from ue_remote_exec import load_remote_execution
        remote = load_remote_execution(EDITOR.parents[3])
        session = remote.RemoteExecution()
        session.start()
        try:
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                assert_identity(self.process)
                nodes = [n for n in session.remote_nodes if n.get('project_name') == 'datatry_02']
                if len(nodes) > 1:
                    raise RuntimeError('Ambiguous remote project nodes')
                if len(nodes) == 1:
                    break
                time.sleep(2)
            else:
                raise RuntimeError('Editor discovery timeout')
        finally:
            session.stop()
        self.dispatch('guard')

    def run(self):
        self.preflight()
        for offset in range(0, len(self.roots), self.batch_size):
            batch = self.roots[offset:offset + self.batch_size]
            self.progress('Batch ' + str(offset // self.batch_size + 1) + ': ' + ', '.join(batch))
            pending = []
            for root in batch:
                entry = self.state['roots'].setdefault(root, {})
                action, proof = route(root, entry)
                if action == 'baseline':
                    self.dispatch('baseline', root)
                    action, proof = route(root, entry)
                base = receipt(root, 'baseline')
                self.pin(base)
                entry['baseline_sha256'] = sha(base)
                self.save()
                if action == 'verified':
                    entry.update(status='verified', verification_path=str(proof), verification_sha256=sha(proof))
                    self.pin(proof)
                    self.save()
                else:
                    pending.append(root)
            if pending:
                self.restart()
            for root in pending:
                entry = self.state['roots'][root]
                action, proof = route(root, entry)
                if action == 'move':
                    self.dispatch('guard')
                    entry['move_intent'] = stamp()
                    self.save()  # Persist before any potentially ambiguous remote mutation.
                    self.dispatch('move', root)
                    action, proof = route(root, entry)
                if action == 'verify':
                    self.dispatch('verify', root)
                    action, proof = route(root, entry)
                if action != 'verified':
                    raise RuntimeError('Verification did not succeed; stopped')
                entry.update(status='verified', verification_path=str(proof), verification_sha256=sha(proof))
                self.pin(proof)
                self.save()
            self.publish(batch)

    def publish(self, roots=None):
        from scene_path_relocation_v1 import read_overlay, validate_overlay
        roots = self.roots if roots is None else list(roots)
        if not roots or not set(roots).issubset(self.roots):
            raise ValueError('Publication must select a nonempty subset of requested roots')
        overlay = read_overlay(REGISTRY)
        registry_sha = sha(REGISTRY)
        rows = {row['old_prefix']: row for row in overlay['mappings']}
        for root in roots:
            entry = self.state['roots'][root]
            action, proof = route(root, entry)
            if action != 'verified':
                raise RuntimeError('All requested roots must verify before publication')
            rows[root] = {'old_prefix': root, 'new_prefix': '/Game/Scenes/' + slug(root), 'status': 'verified',
                          'verification_receipt': {'path': str(proof), 'sha256': sha(proof)}}
        overlay['mappings'] = list(rows.values())
        overlay['status'] = 'in_progress'  # A selected batch does not claim the whole task complete.
        validate_overlay(overlay)
        if sha(REGISTRY) != registry_sha:
            raise RuntimeError('Overlay concurrently changed')
        atomic(RUN / ('overlay_before_driver_' + stamp() + '.json'), read(REGISTRY))
        atomic(REGISTRY, overlay)
        self.state['last_publication'] = {'roots': roots, 'overlay_sha256': sha(REGISTRY)}
        self.save()
        self.progress('Published verified batch: ' + ', '.join(roots))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roots', nargs='+', required=True)
    parser.add_argument('--batch-size', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--editor-pid', type=int)
    parser.add_argument('--execute', action='store_true', help='Actually operate UE. Omit for offline routing only.')
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps([{'root': root, 'next_action': route(root, {})[0]} for root in args.roots], ensure_ascii=False, indent=2))
        return
    if not args.editor_pid:
        parser.error('--execute requires --editor-pid of the current owned editor')
    # A stale lock is deliberately a manual inspection, not automatic takeover.
    lock = RUN / 'batch_driver.lock'
    with lock.open('x', encoding='utf-8') as stream:
        json.dump({'host_pid': os.getpid(), 'started_at': stamp()}, stream)
    try:
        driver = Driver(args.roots, args.batch_size, args.editor_pid)
        driver.run()
    except Exception as exc:
        atomic(RUN / ('driver_stopped_' + stamp() + '.json'), {'success': False, 'error': str(exc), 'roots': args.roots, 'editor_pid': driver.process.pid if 'driver' in locals() else args.editor_pid, 'automatic_retry': False})
        raise
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
