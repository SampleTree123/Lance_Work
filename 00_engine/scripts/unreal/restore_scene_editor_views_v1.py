"""Restore only saved EditorViews after verified scene migration; dry run by default."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import datetime

from scene_path_relocation_v1 import read_overlay, resolve_path

ENGINE = Path(__file__).resolve().parents[2]
RUN = ENGINE / 'outputs/scene_folder_organization_20261012_v1'
REGISTRY = ENGINE / 'assets/scene_folder_relocation_20261012_v1.json'
PROJECT = Path('D:/UE/projects/datatry_02/datatry_02.uproject')
INI = PROJECT.parent / 'Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini'
ORIGINAL = RUN / 'editor_view_history_before_v1.ini'
INVENTORY = RUN / 'ue_inventory_v1.json'


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def setting(raw):
    matches = list(re.finditer(rb'(?m)^(?:\xef\xbb\xbf)?EditorViews=([^\r\n]*)', raw))
    if len(matches) != 1:
        raise ValueError('Expected exactly one EditorViews value')
    return matches[0]


def restore_bytes(original, current, overlay):
    source, target = setting(original), setting(current)
    value = source.group(1)
    mappings, keys = [], set()

    def replace(match):
        old = match.group(1).decode('utf-8')
        new = resolve_path(old, overlay)
        key = new.casefold()
        if key in keys:
            raise ValueError('EditorViews FName path collision: ' + new)
        keys.add(key)
        if old != new:
            mappings.append({'old': old, 'new': new})
        return b'"' + new.encode('utf-8') + b'"'

    value = re.sub(rb'"(/Game/[^"\r\n]+)"', replace, value)
    result = current[:target.start(1)] + value + current[target.end(1):]
    # Structural check avoids changing any unrelated current INI bytes.
    assert result[:target.start(1)] == current[:target.start(1)]
    assert result[target.start(1) + len(value):] == current[target.end(1):]
    return result, mappings


def require_complete(overlay, inventory):
    roots = {r['root'] for r in inventory['roots']} - {'/Game/StarterContent'}
    if inventory.get('success') is not True or len(roots) != 24:
        raise ValueError('Expected successful 24-scene inventory, excluding StarterContent')
    rows = {r['old_prefix']: r for r in overlay['mappings']}
    for root in roots:
        row = rows.get(root)
        if not row or row.get('status') != 'verified':
            raise ValueError('Scene root is not verified: ' + root)
        proof = Path(row['verification_receipt']['path'])
        if not proof.is_absolute():
            proof = REGISTRY.parent / proof
        # read_overlay checks hash/success; bind that proof to the mapped root too.
        data = read_json(proof)
        if data.get('root') != root or data.get('destination') != row['new_prefix']:
            raise ValueError('Verification receipt does not prove this scene mapping')


def assert_no_editor(processes=None, lock=RUN / 'batch_driver.lock'):
    if Path(lock).exists():
        raise RuntimeError('Migration driver lock exists; restoration prohibited')
    import psutil
    if processes is None:
        processes = psutil.process_iter(['name'])
    norm = lambda value: os.path.normcase(os.path.abspath(value.strip('"')))
    for process in processes:
        try:
            name = process.name().lower()
            if name not in {'unrealeditor.exe', 'unrealeditor-cmd.exe'}:
                continue
            if any(norm(arg) == norm(str(PROJECT)) for arg in process.cmdline()[1:]):
                raise RuntimeError(f'Configured project editor still running: PID {process.pid}')
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            raise RuntimeError('Cannot establish editor identity; restoration prohibited') from exc


def plan():
    paths = [ORIGINAL, INI, REGISTRY, INVENTORY]
    contents = {str(p): p.read_bytes() for p in paths}
    overlay = read_overlay(REGISTRY)
    require_complete(overlay, read_json(INVENTORY))
    result, mappings = restore_bytes(contents[str(ORIGINAL)], contents[str(INI)], overlay)
    # Include all proof files in commit-time check, not merely the registry.
    for row in overlay['mappings']:
        if row.get('status') == 'verified':
            p = Path(row['verification_receipt']['path'])
            if not p.is_absolute():
                p = REGISTRY.parent / p
            contents[str(p)] = p.read_bytes()
            if sha_bytes(contents[str(p)]) != row['verification_receipt']['sha256']:
                raise RuntimeError('Verification proof changed while preparing restoration')
    pins = {p: sha_bytes(raw) for p, raw in contents.items()}
    check_pins(pins)
    return result, mappings, pins, contents[str(INI)]


def check_pins(pins):
    for path, expected in pins.items():
        if sha_bytes(Path(path).read_bytes()) != expected:
            raise RuntimeError('Input changed before restoration: ' + path)


def exclusive_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result, mappings, pins, current = plan()
    summary = {'dry_run': not args.apply, 'changed_paths': len(mappings), 'output_sha256': sha_bytes(result), 'input_pins': pins}
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    # No editor shutdown or launch here. Root owns that separately.
    assert_no_editor()
    token = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = RUN / ('editor_views_current_before_restore_' + token + '.ini')
    pending = INI.with_name(INI.name + '.restore_' + token + '.tmp')
    intent = RUN / ('editor_views_restore_intent_' + token + '.json')
    with backup.open('xb') as stream:
        stream.write(current)
    with pending.open('xb') as stream:
        stream.write(result)
    exclusive_json(intent, dict(summary, applied=False, backup=str(backup), mappings=mappings))
    assert_no_editor()
    check_pins(pins)
    os.replace(pending, INI)
    if INI.read_bytes() != result:
        raise RuntimeError('Restored INI readback mismatch; inspect preserved backup and intent')
    receipt = RUN / ('editor_views_restored_' + token + '.json')
    exclusive_json(receipt, dict(summary, applied=True, success=True, backup=str(backup), backup_sha256=sha_bytes(current), mappings=mappings))
    print(str(receipt))


if __name__ == '__main__':
    main()
