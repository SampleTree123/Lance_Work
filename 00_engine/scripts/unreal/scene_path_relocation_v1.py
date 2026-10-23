"""Verified scene-path overlay. Never rewrites historical plans or receipts."""
from pathlib import Path
import copy
import hashlib
import json

ENGINE = Path(__file__).resolve().parents[2]
REGISTRY = ENGINE / 'assets/scene_folder_relocation_20261012_v1.json'
RUN = ENGINE / 'outputs/scene_folder_organization_20261012_v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_overlay(data):
    if data.get('schema') != 'scene_folder_relocation_v1' or data.get('status') not in {'in_progress', 'complete'}:
        raise ValueError('Unknown scene relocation registry')
    seen = []
    for row in data['mappings']:
        old, new = row['old_prefix'], row['new_prefix']
        for value in (old, new):
            if (not isinstance(value, str) or not value.startswith('/Game/')
                    or any(not s or s in {'.', '..'} for s in value[1:].split('/'))
                    or any(c.isspace() or c in '.:\\' for c in value)):
                raise ValueError('Invalid package prefix')
        if old.startswith('/Game/Scenes/') or old == '/Game/Scenes' or new != '/Game/Scenes/' + old[6:]:
            raise ValueError('Relocation must preserve original scene suffix')
        if any(old == p or old.startswith(p + '/') or p.startswith(old + '/') for p in seen):
            raise ValueError('Duplicate or overlapping relocation prefixes')
        seen.append(old)
    return data


def read_overlay(path=REGISTRY):
    path = Path(path)
    data = validate_overlay(json.loads(path.read_text(encoding='utf-8-sig')))
    for row in data['mappings']:
        if row.get('status') != 'verified':
            continue
        proof = row['verification_receipt']
        receipt = Path(proof['path'])
        if not receipt.is_absolute():
            receipt = path.parent / receipt
        if sha(receipt) != proof['sha256']:
            raise ValueError('Relocation verification receipt changed')
        evidence = json.loads(receipt.read_text(encoding='utf-8-sig'))
        if evidence.get('success') is not True:
            raise ValueError('Relocation has no successful verification')
    return data


def resolve_path(value, overlay):
    """Pure boundary-aware mapping; preserves object/subobject suffix verbatim."""
    validate_overlay(overlay)
    package, dot, suffix = value.partition('.')
    for row in overlay['mappings']:
        old = row['old_prefix']
        if package == old or package.startswith(old + '/'):
            if row.get('status') != 'verified':
                raise ValueError('Scene relocation is not verified: ' + old)
            return row['new_prefix'] + package[len(old):] + (dot + suffix if dot else '')
    return value


def resolve_current_path(value):
    return resolve_path(value, read_overlay())


def relocate_index(source, overlay):
    """Return a new display/index document; preserve historical provenance."""
    result = copy.deepcopy(source)
    for row in result['scenes']:
        original = {k: copy.deepcopy(row[k]) for k in ('content_root', 'content_roots', 'maps', 'all_maps') if k in row}
        for key in ('content_root', 'content_roots', 'maps', 'all_maps'):
            if key not in row:
                continue
            row[key] = ([resolve_path(p, overlay) for p in row[key]] if isinstance(row[key], list)
                        else resolve_path(row[key], overlay))
        changed = any(row[k] != v for k, v in original.items())
        row['original_locations'] = original
        row['relocation_status'] = 'verified' if changed else 'unchanged'
        row['import_status_scope'] = 'Original import checks; relocation proof is separate.'
    return result


def build_current_index(source_path, *, registry_path=REGISTRY, output_path=None):
    source_path, registry_path = Path(source_path).resolve(), Path(registry_path).resolve()
    output_path = Path(output_path or RUN / 'gallery_scene_index_relocated_v1.json').resolve()
    if not output_path.is_relative_to(RUN.resolve()) or output_path in {source_path, registry_path}:
        raise ValueError('Relocated index must stay in the new relocation run')
    source_pin = {'path': str(source_path), 'sha256': sha(source_path)}
    registry_pin = {'path': str(registry_path), 'sha256': sha(registry_path)}
    result = relocate_index(json.loads(source_path.read_text(encoding='utf-8-sig')), read_overlay(registry_path))
    result['source_index'] = source_pin
    result['relocation_registry'] = registry_pin
    if sha(source_path) != source_pin['sha256'] or sha(registry_path) != registry_pin['sha256']:
        raise ValueError('Relocation inputs changed while resolving index')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output_path)
    return result
