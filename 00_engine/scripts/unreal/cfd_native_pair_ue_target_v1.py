"""Explicit UE instance binding for this CFD run only; no launch or fallback."""
import json
from pathlib import Path
import time

from ue_remote_exec import DEFAULT_ENGINE_ROOT, load_remote_execution

RUN = Path(__file__).resolve().parents[2] / 'outputs/unreal_character_import/cfd_native_pair_20261006_v1'
TARGET_FILE = RUN / 'ue_target.json'


def load_target(node_id=None):
    target = json.loads(TARGET_FILE.read_text(encoding='utf-8-sig'))
    if any(not isinstance(target.get(key), str) or not target[key].strip()
           for key in ('node_id', 'user', 'project')):
        raise ValueError('ue_target.json requires nonempty node_id, user and project')
    if node_id and node_id != target['node_id']:
        raise RuntimeError('--node-id differs from this run target; verify and update ue_target.json first')
    return {key: target[key] for key in ('node_id', 'user', 'project')}


def select_exact(nodes, target):
    matches = [node for node in nodes
               if node.get('node_id') == target['node_id']
               and node.get('user') == target['user']
               and node.get('project_name') == target['project']]
    if len(matches) != 1:
        raise RuntimeError('Expected exactly the configured CFD UE node/user/project; no other instance is allowed')
    return matches[0]


def select_panel_node(nodes, node_id=None, pinned=None):
    # The run-scoped target is authoritative; a historical panel session never
    # silently overrides it or permits a project-only fallback.
    return select_exact(nodes, load_target(node_id))


def remote(command, run, tag, discovery=12, timeout=1200, node_id=None, unattended=True):
    target = load_target(node_id)
    module = load_remote_execution(DEFAULT_ENGINE_ROOT.resolve())
    session = module.RemoteExecution()
    envelope = {'target': target, 'success': False, 'unattended': bool(unattended)}
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    try:
        session.start()
        deadline = time.monotonic() + discovery
        while True:
            try:
                node = select_exact(list(session.remote_nodes), target)
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.2)
        # Re-check immediately before connection; never retarget on failure.
        node = select_exact(list(session.remote_nodes), target)
        envelope['node'] = node
        session.open_command_connection(node['node_id'])
        session._command_connection._command_channel_socket.settimeout(timeout)
        reply = session.run_command(command, unattended=bool(unattended),
                                   exec_mode=module.MODE_EXEC_FILE, raise_on_failure=False)
        envelope['command_result'] = reply
        envelope['success'] = reply.get('success') is True
        if not envelope['success']:
            raise RuntimeError('Selected UE operation failed; inspect ' + str(run / (tag + '_remote.json')))
        return envelope
    except Exception as exc:
        envelope['error'] = str(exc)
        raise
    finally:
        try:
            session.stop()
        finally:
            (run / (tag + '_remote.json')).write_text(
                json.dumps(envelope, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
