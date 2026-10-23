"""Experimental skin-detail session orchestration; owner CHARACTER_RUNTIME.md section 3.20.

Launch is explicit. Remote operations require this run's pinned node identity.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from launch_local_unreal_editor_v1 import ENGINE, PROJECT, runtime_environment
from ue_remote_exec import load_remote_execution
import cfd_native_pair_ue_target_v1 as target_api

RUN = Path(__file__).resolve().parents[2] / 'outputs/unreal_character_import/skin_detail_optimization_20261012_v1'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('operation', choices=['launch', 'bind', 'exec'])
    p.add_argument('--script', type=Path)
    p.add_argument('--tag', default='operation')
    p.add_argument('--timeout', type=int, default=180)
    args = p.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if args.operation == 'launch':
        report = RUN / 'launch_report.json'
        if report.exists():
            raise RuntimeError('Existing launch receipt: inspect process before another launch')
        env, folders = runtime_environment(RUN / 'runtime')
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        command = [str(ENGINE / 'Engine/Binaries/Win64/UnrealEditor.exe'), str(PROJECT),
                   '/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001',
                   '-nosplash', '-nosound', '-nop4', '-NoLiveCoding', '-unattended',
                   '-DDC-ForceMemoryCache', '-ddc=NoZenLocalFallback',
                   '-ini:Engine:[/Script/Engine.RendererSettings]:r.PathTracing=0',
                   '-abslog=' + str(RUN / 'editor.log')]
        process = subprocess.Popen(command, cwd=PROJECT.parent, env=env, startupinfo=startup)
        data = dict(pid=process.pid, command=command, environment=folders,
                    status='launched_not_yet_verified')
        report.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(json.dumps(data))
    elif args.operation == 'bind':
        module = load_remote_execution(ENGINE)
        session = module.RemoteExecution()
        session.start()
        try:
            deadline = time.monotonic() + 20
            nodes = []
            while time.monotonic() < deadline:
                nodes = [n for n in session.remote_nodes if n.get('project_name') == PROJECT.stem]
                if nodes:
                    break
                time.sleep(.2)
            if len(nodes) != 1:
                raise RuntimeError('Expected exactly one project node, got ' + repr(nodes))
            node = nodes[0]
            data = dict(node_id=node['node_id'], user=node['user'], project=node['project_name'], discovered=node)
            (RUN / 'ue_target.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
            print(json.dumps(data))
        finally:
            session.stop()
    else:
        if not args.script or not args.script.is_file():
            raise ValueError('Existing --script is required')
        target_api.TARGET_FILE = RUN / 'ue_target.json'
        result = target_api.remote(args.script.read_text(encoding='utf-8-sig'), RUN / 'remote',
                                   args.tag, timeout=args.timeout, unattended=True)
        print(json.dumps(result, ensure_ascii=True, default=str))


if __name__ == '__main__':
    main()
