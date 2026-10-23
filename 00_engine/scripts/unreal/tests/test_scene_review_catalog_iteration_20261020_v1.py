"""Review-only primary choices preserve maps, saved points and historical index."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1]))
import scene_site_catalog_v1 as catalog
import pair_scene_review_20261019_v1 as panel


CITY = '/Game/Scenes/FuturisticMetaCity/Maps/'
SCIFI = '/Game/Scenes/Scifi_building_Bundle/'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def fixture_catalog(tmp_path):
    content = tmp_path / 'Content'
    unrelated = [f'/Game/Scenes/Unrelated{i:02d}/Maps/Main' for i in range(22)]
    scifi = [SCIFI + f'Scifi_Building_V{i}/Maps/Preview' for i in range(3)]
    historical = unrelated + [CITY + 'ShowcaseMap'] + scifi
    for path in historical + [CITY + 'VirtualMetaCity']:
        file = content / (path.removeprefix('/Game/') + '.umap')
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(('retained:' + path).encode())
    index, overlay, sites = tmp_path / 'index.json', tmp_path / 'overlay.json', tmp_path / 'sites'
    write(index, {'scenes': [{'maps': historical}]})
    write(overlay, {})
    write(sites / 'history_scifi.json', {'site': {'site_id': 'history_scifi', 'map': scifi[0], 'name': '旧科幻点'}})
    files = list(content.rglob('*.umap')) + [index, overlay, sites / 'history_scifi.json']
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return {'project_content': content, 'saved_site_roots': [sites], 'source_index': index,
            'relocation_path': overlay}, unrelated, scifi, pins


def test_church_and_racetrack_retired_without_deleting_maps_or_sites(tmp_path):
    args, _, _, _ = fixture_catalog(tmp_path)
    index = json.loads(args['source_index'].read_text(encoding='utf-8'))
    paths = ['/Game/Scenes/' + p + '/Maps/Main' for p in ['Madeline', 'racing_track']]
    for i, path in enumerate(paths):
        asset = args['project_content'] / (path.removeprefix('/Game/') + '.umap')
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b'keep-source')
        write(args['saved_site_roots'][0] / f'site_retired{i}.json',
              {'site':{'site_id':f'site_retired{i}', 'map':path}})
    index['scenes'].append({'maps':paths})
    write(args['source_index'],index)
    result=catalog.build_catalog(**args)
    rows={r['map_path']:r for r in result['scenes']}
    assert all(not rows[p]['primary'] for p in paths)
    assert all(any(s['map']==p for s in result['sites']) for p in paths)
    assert all((args['project_content']/(p.removeprefix('/Game/')+'.umap')).read_bytes()==b'keep-source'
               for p in paths)


def test_primary_replacement_retirement_preserves_unrelated_files_and_history(tmp_path, monkeypatch):
    args, unrelated, scifi, pins = fixture_catalog(tmp_path)
    result = catalog.build_catalog(**args)
    rows = {row['map_path']: row for row in result['scenes']}
    assert rows[CITY + 'VirtualMetaCity']['primary']
    assert not rows[CITY + 'ShowcaseMap']['primary']
    assert all(not rows[path]['primary'] for path in scifi)
    assert all(path in rows for path in scifi + [CITY + 'ShowcaseMap'])
    assert result['sites'][0]['id'] == 'history_scifi'
    assert result['counts']['primary_maps'] == 23
    # Compare the complete unrelated row, rather than only counts: names,
    # paths, categories and package identity must all survive the override.
    monkeypatch.setattr(catalog, 'PRIMARY_MAP_REPLACEMENTS', {})
    monkeypatch.setattr(catalog, 'RETIRED_REVIEW_PACKAGES', set())
    baseline = {row['map_path']: row for row in catalog.build_catalog(**args)['scenes']}
    assert all(rows[path] == baseline[path] for path in unrelated)
    assert baseline[CITY + 'ShowcaseMap']['primary']
    assert all(baseline[path]['primary'] for path in scifi)
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins} == pins


def test_pair_wrapper_exposes_23_maps_and_packages_with_original_catalog_retained(tmp_path, monkeypatch):
    import motion_library_review_adapter_v1 as adapter
    import pair_review_fast_runtime_v1 as fast
    args, unrelated, scifi, _ = fixture_catalog(tmp_path)
    full = catalog.build_catalog(**args)
    original = copy.deepcopy(full)
    directory = SimpleNamespace(build_catalog=lambda *a, **k: copy.deepcopy(full))
    contract = SimpleNamespace(catalog=lambda: {'identities': [
        {'id': identifier, 'sex': 'female' if index == 0 else 'male'}
        for index, identifier in enumerate(panel.IDS)], 'sources': {}})
    modules = {'scene_site_appearance_v1': contract, 'scene_site_catalog_v1': directory,
               'ue_production_site_runtime_v1': SimpleNamespace(load_mode=lambda *a, **k: None)}
    graph = SimpleNamespace(load=lambda name: modules[name])
    monkeypatch.setattr(adapter, 'PrivateModules', lambda: graph)
    monkeypatch.setattr(fast, 'bind_catalog', lambda module: None)
    delivery = tmp_path / 'delivery.json'
    write(delivery, {})
    monkeypatch.setattr(panel, 'DELIVERY', delivery)
    actual_graph, _ = panel.graph_and_data()
    restricted = actual_graph.load('scene_site_catalog_v1').build_catalog()
    assert restricted['counts']['maps'] == restricted['counts']['packages'] == 23
    assert restricted['counts']['primary_maps'] == 23
    assert {row['map_path'] for row in restricted['scenes']} == set(unrelated + [CITY + 'VirtualMetaCity'])
    assert full == original
    assert len(full['scenes']) == 27  # All three retired maps and old city still present.
    assert all(path in {row['map_path'] for row in full['scenes']} for path in scifi)
