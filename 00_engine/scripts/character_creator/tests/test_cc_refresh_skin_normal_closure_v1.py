"""Bound save-time hook: healthy/missing/protection/source and reload gate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_skin_normal_closure_v1 as hook_module
import cc_probe_refresh_skin_normal_restore_v1 as engine
import cc_repair_headshot_support_materials_v1 as png


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    return dict(path=str(path), sha256=sha(path))


class Image:
    def __init__(self, path):
        self.path = path
    def isNull(self):
        return not Path(self.path).is_file()
    def width(self):
        return 2048
    def height(self):
        return 2048


def setup_case(tmp_path, monkeypatch, healthy=False, unintended_change=False):
    def image(name):
        path = tmp_path / (name + '.png')
        path.write_bytes(('unit pixels ' + name).encode())
        return dict(pin(path), width=2048, height=2048)
    maps = {m: image(m) for m in hook_module.SKINS}
    own = dict(materials=[dict(owner='avatar', mesh='CC_Base_Body', material=m, textures={'bump': maps[m]}) for m in sorted(maps)])
    folder = tmp_path / 'pixels_after_skin'
    folder.mkdir()
    file = folder / 'materials.json'
    file.write_text(json.dumps(own), encoding='utf-8')
    source, skin = tmp_path / 'own.ccProject', tmp_path / 'own.ccSkin'
    source.write_bytes(b'own photo geometry'); skin.write_bytes(b'own selected skin')
    report = dict(config=dict(character_id='CFD40_UNIT_001', source_project=pin(source), assets={'skin': pin(skin)}),
                  pixel_stages={'after_skin': pin(file)})
    current = copy.deepcopy(own)
    current['pixel_capture_complete'] = True
    for row in current['materials']:
        row['textures']['diffuse'] = image(row['material'] + '_diffuse')
        if not healthy:
            row['textures'].pop('bump')
    current['materials'].append(dict(owner='avatar/1:CC_Base_Eye', mesh='CC_Base_Eye', material='Std_Cornea', textures={'opacity': image('eye')}))
    writes = []
    class Component:
        def LoadImageToTexture(self, mesh, material, enum, path):
            assert mesh == 'CC_Base_Body' and enum == 'NormalEnum'
            assert path == maps[material]['path']
            writes.append(material)
            next(r for r in current['materials'] if r['material'] == material)['textures']['bump'] = copy.deepcopy(maps[material])
            if unintended_change:
                current['materials'][-1]['textures']['opacity'] = image('wrong_eye')
            return 'ok'
    api = SimpleNamespace(sha256_file=sha, read_json=lambda p: json.loads(Path(p).read_text()),
                          QtGui=SimpleNamespace(QImage=Image), RLPy=SimpleNamespace(EMaterialTextureChannel_Normal='NormalEnum'),
                          checked=lambda label, raw: raw == 'ok')
    c = SimpleNamespace(report=report, api=api, output_dir=str(tmp_path), pixel_snapshots={'after_skin': own},
                        avatar=lambda: SimpleNamespace(GetMaterialComponent=lambda: Component()), checkpoint=lambda *a: None,
                        probe=SimpleNamespace(status_record=lambda raw: {'raw': raw}))
    monkeypatch.setattr(hook_module, 'private_module', lambda name, api: engine)
    monkeypatch.setattr(png, 'compare_png_images', lambda a, b, api: {'rgba_pixels_equal': Path(a).read_bytes() == Path(b).read_bytes()})
    hook = hook_module.NormalHook(c)
    hook.capture = lambda label: copy.deepcopy(current)
    return c, hook, current, writes


def test_healthy_four_maps_are_verified_without_any_write(tmp_path, monkeypatch):
    _, hook, _, writes = setup_case(tmp_path, monkeypatch, healthy=True)
    hook.before_saved(); hook.gate('first_reload'); hook.gate('same_sha_reload')
    assert writes == [] and hook.report['missing_before'] == [] and hook.report['complete']


def test_missing_four_are_restored_once_using_only_own_four_maps(tmp_path, monkeypatch):
    _, hook, _, writes = setup_case(tmp_path, monkeypatch)
    hook.before_saved(); hook.gate('first_reload'); hook.gate('same_sha_reload')
    assert writes == sorted(hook_module.SKINS)
    assert hook.report['checks']['write_only_four_normal_pairs']['passed']
    assert hook.report['checks']['eight_channels_same_sha_stable']['passed']
    with pytest.raises(ValueError, match='only once'):
        hook.before_saved()


def test_non_skin_material_change_during_normal_write_is_rejected(tmp_path, monkeypatch):
    _, hook, _, _ = setup_case(tmp_path, monkeypatch, unintended_change=True)
    with pytest.raises(ValueError, match='protected material pixels'):
        hook.before_saved()


def test_same_case_source_and_live_after_skin_binding_cannot_be_substituted(tmp_path, monkeypatch):
    c, _, _, _ = setup_case(tmp_path, monkeypatch)
    Path(c.report['config']['source_project']['path']).write_bytes(b'other source')
    with pytest.raises(ValueError, match='Same-case source'):
        hook_module.own_maps(c)
    c.report['config']['source_project']['sha256'] = sha(c.report['config']['source_project']['path'])
    c.pixel_snapshots['after_skin']['materials'][0]['textures']['bump']['sha256'] = 'other-case-map'
    with pytest.raises(ValueError, match='Live and pinned own'):
        hook_module.own_maps(c)


def test_missing_on_reload_is_rejected_even_if_two_missing_snapshots_would_match(tmp_path, monkeypatch):
    _, hook, current, _ = setup_case(tmp_path, monkeypatch)
    hook.before_saved()
    for row in current['materials']:
        if row['material'] in hook_module.SKINS:
            row['textures'].pop('bump')
    assert engine.pixel_compare(current, copy.deepcopy(current), None)['passed']
    with pytest.raises(ValueError, match='no actual decoded'):
        hook.gate('first_reload')


def test_new_entry_private_override_preserves_frozen_runner_and_public_imports(monkeypatch):
    import cc_run_character_refresh_v1 as original
    before = original.importlib
    api = SimpleNamespace(sha256_file=sha)
    private = hook_module.private_module('cc_run_character_refresh_v1', api)
    assert private is not original and private.run.__code__.co_code == original.run.__code__.co_code
    calls = []
    fake = SimpleNamespace(run=lambda *args: calls.append(args) or {'success': False})
    monkeypatch.setattr(hook_module, 'private_module', lambda name, api: fake)
    library = {'refresh_assembly': dict(restore_four_skin_normals_after_editor_close=True, finalize_editor_closed=True, capture_pixel_evidence=True)}
    assert hook_module.run(library, 'unit-output', print, api) == {'success': False}
    assert len(calls) == 1 and original.importlib is before
    assert fake.importlib.import_module('cc_refresh_closed_assembly_v1').finish is hook_module.finish
