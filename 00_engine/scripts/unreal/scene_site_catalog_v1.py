"""Read-only, live scene/map and saved shooting-point directory. Never imports UE."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTENT = Path('D:/UE/projects/datatry_02/Content')
OUTPUT = ROOT / '00_engine/outputs/camera_follow_compact_scene_20261015_v1'
SOURCE_INDEX = ROOT / '00_engine/outputs/camera_motion_scene_alignment_20261012_v1/scenes/gallery_scene_index_v1.json'
RELOCATION = ROOT / '00_engine/assets/scene_folder_relocation_20261012_v1.json'
SAVED_SITE_ROOTS = (ROOT / '00_engine/outputs/scene_site_review_20261014_v1/sites',)

# Current review choices; the original scene index remains historical evidence.
PRIMARY_MAP_REPLACEMENTS = {
    'FuturisticMetaCity': '/Game/Scenes/FuturisticMetaCity/Maps/VirtualMetaCity',
}
RETIRED_REVIEW_PACKAGES = {'Scifi_building_Bundle', 'Madeline', 'racing_track'}

PACKAGE_NAMES = {
    'CHERRY_TREE': '樱花庭院', 'Kowloon': '九龙巷道', 'KyotoAlley': '京都小巷',
    'Hong_Kong_Street': '香港街道', 'Japanese_Village': '日式村落',
    'TokyoStylizedEnvironment': '风格化东京', 'UrbanJapan': '日本城市街区',
    'AsianArchitecture': '中式建筑', 'Madeline': '教堂', 'VictorianStreet': '维多利亚街道',
    'TheMetro': '地铁站', 'Medieval_Environment': '中世纪城堡',
    'QA_ModularParking': '停车场', 'DesertGasStation': '沙漠加油站',
    'RedDesertPack': '红色沙漠', 'Brushify': '沙丘', 'Seaside_Town': '海滨小镇',
    'Evening_Highway': '傍晚公路', 'racing_track': '赛车场', 'AmusementPark': '游乐园',
    'Cyberpunk_City': '赛博朋克城市', 'Synthwave_city': '合成波城市',
    'FuturisticMetaCity': '未来都市', 'Scifi_building_Bundle': '科幻建筑', 'PostCity': '末日城市',
}
CATEGORY_NAMES = {'primary': '主场景', 'working': '工作地图', 'overview': '资产总览',
                  'sublevel': '灯光子关卡', 'prefab': '建筑组合', 'variant': '其他地图'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def relocated_map(path, relocation):
    for row in relocation.get('mappings', []):
        old = row.get('old_prefix', '')
        if old and (path == old or path.startswith(old + '/')):
            return row['new_prefix'] + path[len(old):]
    return path


def map_category(relative, primary_maps):
    map_path = '/Game/' + relative.with_suffix('').as_posix()
    parts, stem = relative.parts, relative.stem.lower()
    if 'PackedLevelActors' in parts:
        return 'prefab'
    if 'Sublevels' in parts:
        return 'sublevel'
    if 'WorkingMaps' in parts:
        return 'working'
    if map_path in primary_maps:
        return 'primary'
    if any(word in stem for word in ('overview', 'assets', 'materials', 'models')):
        return 'overview'
    return 'variant'


def saved_sites(roots=None):
    """Re-read files every time, so newly saved points appear immediately."""
    rows, warnings = {}, []
    for root in SAVED_SITE_ROOTS if roots is None else roots:
        root = Path(root).resolve()
        for path in sorted(root.glob('*.json')):
            try:
                if path.resolve().parent != root:
                    raise ValueError('点位路径超出目录')
                site = read(path)['site']
                if not isinstance(site.get('map'), str) or not site['map'].startswith('/Game/'):
                    raise ValueError('点位缺少关卡路径')
                sid = site.get('site_id') or path.stem
                if sid != path.stem:
                    raise ValueError('点位 ID 与文件名不一致')
                rows[(site['map'], sid)] = {'id': sid, 'name': site.get('name') or sid,
                                           'map': site['map'], 'source_path': str(path)}
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append({'path': str(path), 'message': str(exc)})
    return sorted(rows.values(), key=lambda row: (row['map'], row['id'])), warnings


def build_catalog(project_content=None, saved_site_roots=None, source_index=None, relocation_path=None):
    content = Path(CONTENT if project_content is None else project_content).resolve()
    index_path = Path(SOURCE_INDEX if source_index is None else source_index)
    overlay_path = Path(RELOCATION if relocation_path is None else relocation_path)
    index = read(index_path) if index_path.is_file() else {'scenes': []}
    relocation = read(overlay_path) if overlay_path.is_file() else {}
    primary_maps = {relocated_map(path, relocation) for row in index.get('scenes', []) for path in row.get('maps', [])}
    for package, replacement in PRIMARY_MAP_REPLACEMENTS.items():
        prefix = '/Game/Scenes/' + package + '/'
        if any(path.startswith(prefix) for path in primary_maps):
            primary_maps = {path for path in primary_maps if not path.startswith(prefix)}
            primary_maps.add(replacement)
    primary_maps = {path for path in primary_maps
                    if not any(path.startswith('/Game/Scenes/' + package + '/')
                               for package in RETIRED_REVIEW_PACKAGES)}
    scenes, warnings = [], []
    scene_root = content / 'Scenes'
    for path in sorted(scene_root.rglob('*.umap')):
        # No external symlink/junction targets become openable maps.
        if not path.resolve().is_relative_to(scene_root.resolve()):
            warnings.append({'path': str(path), 'message': '地图路径超出 Scenes 目录'})
            continue
        relative = path.relative_to(content)
        package = relative.parts[1]
        map_path = '/Game/' + relative.with_suffix('').as_posix()
        category = map_category(relative, primary_maps)
        name = PACKAGE_NAMES.get(package, package)
        scenes.append({'id': map_path, 'map_path': map_path, 'package': package,
                       'name': name, 'label': name + ' / ' + path.stem,
                       'category': category, 'category_label': CATEGORY_NAMES[category],
                       'primary': category == 'primary'})
    scenes.sort(key=lambda row: (list(CATEGORY_NAMES).index(row['category']), row['package'].casefold(), row['map_path']))
    sites, site_warnings = saved_sites(saved_site_roots)
    return {'schema': 'scene_site_catalog_v1', 'scenes': scenes, 'sites': sites,
            'counts': {'packages': len({row['package'] for row in scenes}), 'maps': len(scenes),
                       'primary_maps': sum(row['primary'] for row in scenes), 'saved_sites': len(sites)},
            'sources': {'content': str(content), 'scene_index': str(index_path), 'relocation': str(overlay_path)},
            'warnings': warnings + site_warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT / 'scene_site_catalog_v1.json')
    args = parser.parse_args()
    result = build_catalog()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), **result['counts']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
