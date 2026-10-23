import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
import scene_site_catalog_v1 as catalog


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_every_scene_map_is_visible_and_primary_is_authoritative(tmp_path):
    content = tmp_path / 'Content'
    paths = ['Scenes/KyotoAlley/Maps/Kyoto.umap', 'Scenes/KyotoAlley/Maps/Sublevels/Night.umap',
             'Scenes/KyotoAlley/Maps/Overview.umap', 'Scenes/KyotoAlley/WorkingMaps/Edited.umap',
             'Scenes/Japanese_Village/Blueprints/PackedLevelActors/House.umap',
             'Other/Secret.umap', 'Scenes/NewPack/Maps/Other.umap']
    for value in paths:
        target = content / value
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    index = tmp_path / 'index.json'
    overlay = tmp_path / 'overlay.json'
    dump(index, {'scenes': [{'maps': ['/Game/KyotoAlley/Maps/Kyoto']}]})
    dump(overlay, {'mappings': [{'old_prefix': '/Game/KyotoAlley', 'new_prefix': '/Game/Scenes/KyotoAlley'}]})
    result = catalog.build_catalog(content, [], index, overlay)
    assert result['counts'] == {'packages': 3, 'maps': 6, 'primary_maps': 1, 'saved_sites': 0}
    assert {row['category'] for row in result['scenes']} == set(catalog.CATEGORY_NAMES)
    assert all(row['map_path'].startswith('/Game/Scenes/') for row in result['scenes'])
    assert result['scenes'][0]['name'] == '京都小巷'


def test_saved_points_are_live_scoped_and_bad_files_do_not_hide_good_points(tmp_path):
    points = tmp_path / 'sites'
    args = dict(project_content=tmp_path / 'Content', saved_site_roots=[points],
                source_index=tmp_path / 'missing-index', relocation_path=tmp_path / 'missing-overlay')
    assert catalog.build_catalog(**args)['sites'] == []
    dump(points / 'one.json', {'site': {'site_id': 'one', 'name': '新点位', 'map': '/Game/Scenes/One/Map'}})
    dump(points / 'bad.json', {'site': {}})
    result = catalog.build_catalog(**args)
    assert [row['id'] for row in result['sites']] == ['one']
    assert result['sites'][0]['map'] == '/Game/Scenes/One/Map'
    assert len(result['warnings']) == 1
    dump(points / 'two.json', {'site': {'site_id': 'two', 'map': '/Game/Scenes/Two/Map'}})
    assert len(catalog.build_catalog(**args)['sites']) == 2
