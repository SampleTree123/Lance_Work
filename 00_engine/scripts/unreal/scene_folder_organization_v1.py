"""Offline rollback snapshots for authorized UE scene-folder reorganization.

Owned by SCENE_CAMERA_SEQUENCE section 13. Never directly moves UE assets.
"""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/scene_folder_organization_20261012_v1')
CONTENT = Path('D:/UE/projects/datatry_02/Content')
BACKUP = Path('D:/UE/Lance_Work/00_engine/temp/scene_folder_organization_20261012_v1/rollback/Content')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def backup_roots(roots):
    if shutil.disk_usage('D:/').free < 80 * 1024**3:
        raise RuntimeError('Insufficient rollback headroom')
    manifest_path = RUN / 'backup_manifest_v1.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.exists() else {
        'schema': 'scene_relocation_backup_v1', 'success': False, 'completed_roots': [], 'files': []}
    for root in roots:
        if root in manifest['completed_roots']:
            continue
        if not root.startswith('/Game/') or root.startswith('/Game/Scenes/') or '..' in root.split('/'):
            raise ValueError('Unsafe source root')
        source = CONTENT / root.removeprefix('/Game/')
        target = BACKUP / root.removeprefix('/Game/')
        if not source.resolve().is_relative_to(CONTENT.resolve()) or not target.resolve().is_relative_to(BACKUP.resolve()):
            raise ValueError('Path boundary violation')
        for file in sorted(source.rglob('*')):
            if file.is_symlink():
                raise ValueError('Reparse/symlink source preserved, inspect')
            if not file.is_file():
                continue
            destination = target / file.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = sha(file)
            if not destination.exists():
                shutil.copy2(file, destination)
            if sha(destination) != digest:
                raise RuntimeError('Rollback bytes differ')
            manifest['files'].append({'source': str(file), 'backup': str(destination),
                                      'bytes': file.stat().st_size, 'sha256': digest})
        manifest['completed_roots'].append(root)
        manifest['success'] = True
        manifest['observed_at'] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Rollback verified:', root, flush=True)
    return manifest

def backup_external_referencers():
    inventory = json.loads((RUN / 'ue_inventory_v1.json').read_text(encoding='utf-8-sig'))
    selected = {r['root'] for r in inventory['roots']}
    packages = sorted({p for r in inventory['roots'] for p in r['external_referencers']
                       if p.startswith('/Game/') and not any(p == x or p.startswith(x + '/') for x in selected)})
    evidence = {'schema': 'scene_relocation_external_backup_v1', 'success': True, 'files': []}
    for package in packages:
        stem = CONTENT / package.removeprefix('/Game/')
        for extension in ('.uasset', '.umap', '.uexp', '.ubulk'):
            file = stem.with_suffix(extension)
            if not file.exists():
                continue
            destination = BACKUP / file.relative_to(CONTENT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = sha(file)
            if not destination.exists():
                shutil.copy2(file, destination)
            if sha(destination) != digest:
                raise RuntimeError('External referencer rollback differs')
            evidence['files'].append({'source': str(file), 'backup': str(destination), 'sha256': digest,
                                      'package': package, 'bytes': file.stat().st_size})
    (RUN / 'external_referencer_backup_v1.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print('External referencer rollback verified:', len(evidence['files']), flush=True)
    return evidence

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('roots', nargs='+')
    args = parser.parse_args()
    backup_roots(args.roots)
    backup_external_referencers()
