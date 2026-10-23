"""Two targeted in-memory corruption probes; immutable v6 is never written."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import audit_dual_aspect as audit


def probe(kind):
    original_read, original_sessions = audit.read, audit.sessions
    calls = {}

    def altered_read(path):
        value = original_read(path)
        path = Path(path)
        calls[path] = calls.get(path, 0) + 1
        if kind == 'mixed_aspect' and path == audit.BASELINE/'train/nodes.json' and calls[path] == 2:
            value[0]['state']['aspect'] = 'portrait'
        return value

    def altered_sessions(path):
        value = original_sessions(path)
        path = Path(path)
        calls[path] = calls.get(path, 0) + 1
        if kind == 'history_parent' and path == audit.BASELINE/'train/sessions.jsonl' and calls[path] == 2:
            value[0]['steps'][1]['source_position'] = 1
        return value

    audit.read, audit.sessions = altered_read, altered_sessions
    try:
        result = audit.audit(audit.BASELINE)
    finally:
        audit.read, audit.sessions = original_read, original_sessions
    expected = 'mixed_aspect_session' if kind == 'mixed_aspect' else 'original_steps_changed'
    assert not result['passed'] and expected in result['error_counts'], result['error_counts']
    return {'probe': kind, 'rejected': True, 'error_counts': result['error_counts']}


if __name__ == '__main__':
    result = {'schema': 'dual_aspect_audit_targeted_rejection_probes_v1',
              'scope': 'Two in-memory corruptions of candidate reads; all source files immutable',
              'probes': [probe('mixed_aspect'), probe('history_parent')]}
    path = audit.HERE/'audit_rejection_probes.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
