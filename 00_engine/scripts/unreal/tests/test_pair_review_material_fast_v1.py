"""Pair preview acceleration preserves the actual shared palette/coverage rules."""
import copy
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pair_material_fast_tests', SCRIPTS / 'pair_review_material_fast_v1.py')
fast = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fast)
ROOT = '/Game/DataMake/Validation/PairFast'


class Asset:
    def __init__(self, path, parent=None, parameters=None):
        self.path, self.parent = path, parent
        self.parameters = parameters or {'scalar': {}, 'vector': {}, 'texture': {}, 'static': {}}
        self.metadata = {}
        self.properties = SimpleNamespace()

    def get_path_name(self):
        return self.path

    def get_name(self):
        return self.path.rsplit('/', 1)[-1].split('.')[0]

    def get_editor_property(self, name):
        if name == 'parent':
            return self.parent
        if name == 'base_property_overrides':
            return self.properties
        raise KeyError(name)

    def set_editor_property(self, name, value):
        if name != 'base_property_overrides':
            raise KeyError(name)
        self.properties = value


class MIC(Asset):
    pass


def effective(asset, kind):
    values = effective(asset.parent, kind) if asset.parent else {}
    values.update(asset.parameters[kind])
    return values


class MID(Asset):
    def set_vector_parameter_value(self, name, value):
        self.parameters['vector'][name] = value

    def set_scalar_parameter_value(self, name, value):
        self.parameters['scalar'][name] = value

    def get_vector_parameter_value(self, name):
        return effective(self, 'vector')[name]

    def get_scalar_parameter_value(self, name):
        return effective(self, 'scalar')[name]


# Do not accidentally permit fake MID objects through MIC-only library calls.
class Dynamic(MID):
    pass


class Component:
    def __init__(self, source, material):
        self.source, self.material = source, material

    def get_skeletal_mesh_asset(self):
        return self

    def get_path_name(self):
        return '/Game/HairMesh'

    def get_editor_property(self, key):
        assert key == 'materials'
        return [SimpleNamespace(material_interface=self.source, material_slot_name='Hair1')]

    def get_material(self, index):
        return self.material

    def set_material(self, index, material):
        self.material = material

    def get_num_materials(self):
        return 1


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    from motion_library_review_adapter_v1 import PrivateModules
    graph = PrivateModules()
    neutral = graph.load('hair_color_neutral_trial_runtime_v1')
    original = graph.load('hair_eye_color_runtime_v1')
    coverage = graph.load('ue_hair_coverage_runtime_v1')
    assets, calls = {}, []

    def color(*values):
        return SimpleNamespace(**dict(zip(('r', 'g', 'b', 'a'), values)))

    parameters = {'scalar': {'Compensate Color Power': 1., 'Specular Multiplier': 1., 'Roughness Multiplier': .3},
        'vector': {'Base Color Tint': color(1., 1., 1., 1.)},
        'texture': {'Opacity Map': Asset('/Game/SourceOpacity')},
        'static': {'Activate Hair Color': False, 'Use Normal': True}}
    original_shader = Asset(original.HAIR_PARENT, parameters=copy.deepcopy(parameters))
    shader = Asset(neutral.SHADER, parameters=copy.deepcopy(parameters))
    shader.metadata['DM_NeutralHairTrial'] = 'v1'
    source = MIC('/Game/HB1_01/Materials/MI_Hair134_Test', original_shader)
    assets.update({a.path: a for a in (source, shader, original_shader)})
    opacity_path = '/Game/HB1_01/Textures/T_Hair134_Transparency_Pbr_Opacity'
    assets[opacity_path] = Asset(opacity_path)

    def mic_only(asset):
        assert isinstance(asset, MIC) and not isinstance(asset, Dynamic), 'MIC library called on MID'

    def getter(kind, asset, name):
        if isinstance(asset, Dynamic):
            pytest.fail('MIC getter called on MID')
        return effective(asset, kind)[str(name)]

    def setter(kind, asset, name, value):
        mic_only(asset)
        calls.append((kind, str(name)))
        asset.parameters[kind][str(name)] = value

    lib = SimpleNamespace()
    for kind, plural in (('scalar', 'scalar'), ('vector', 'vector'), ('texture', 'texture'), ('static', 'static_switch')):
        setattr(lib, 'get_' + plural + '_parameter_names', lambda asset, kind=kind: list(effective(asset, kind)))
        setattr(lib, 'get_material_instance_' + plural + '_parameter_value', lambda asset, name, kind=kind: getter(kind, asset, name))
        setattr(lib, 'set_material_instance_' + plural + '_parameter_value', lambda asset, name, value, kind=kind: setter(kind, asset, name, value))

    def parent(instance, value):
        mic_only(instance)
        instance.parent = value

    def duplicate(source_path, target):
        calls.append(('duplicate', target))
        src = assets[source_path]
        result = MIC(target, src.parent, copy.deepcopy(src.parameters))
        assets[target] = result
        return result

    def props():
        result = SimpleNamespace()
        result.set_editor_property = lambda name, value: setattr(result, name, value)
        return result

    def create_asset(name, directory, *_):
        target = directory + '/' + name
        result = MIC(target)
        result.properties = props()
        assets[target] = result
        calls.append(('coverage_create', target))
        return result

    def create_mid(context, parent):
        result = Dynamic('/Engine/Transient/MID_' + str(len(calls)), parent)
        calls.append(('mid', parent.path))
        return result

    def save(instance, *_):
        mic_only(instance)
        calls.append(('save', instance.path))
        return True

    lib.set_material_instance_parent = parent
    lib.update_material_instance = lambda instance: (mic_only(instance), calls.append(('update', instance.path)))
    u = SimpleNamespace(MaterialInstanceConstant=MIC, MaterialInstance=MIC, MaterialInstanceDynamic=Dynamic,
        MaterialEditingLibrary=lib, LinearColor=color, load_asset=lambda path: assets.get(path),
        MaterialLibrary=SimpleNamespace(create_dynamic_material_instance=create_mid),
        EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda path: path in assets,
            duplicate_asset=duplicate, get_metadata_tag=lambda a, k: a.metadata.get(k, ''),
            set_metadata_tag=lambda a, k, v: a.metadata.__setitem__(k, v), save_loaded_asset=save),
        AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda: SimpleNamespace(create_asset=create_asset)),
        MaterialInstanceConstantFactoryNew=lambda: None,
        EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: []))
    monkeypatch.setattr(original, '_ue', lambda: u)
    monkeypatch.setattr(original, 'package_file', lambda path: tmp_path / (hashlib.sha256(path.encode()).hexdigest() + '.uasset'))
    def sha(file):
        calls.append(('sha', str(file)))
        return hashlib.sha256(str(file).encode()).hexdigest()
    monkeypatch.setattr(original, '_sha', sha)
    session = fast.install(graph, u)
    return SimpleNamespace(graph=graph, u=u, session=session, original=original, neutral=neutral,
        coverage=coverage, source=source, shader=shader, assets=assets, calls=calls,
        row={'source': source, 'source_sha256': 'source_hash', 'kind': 'hair', 'preset': 'blue'})


def test_first_source_skips_unchanged_static_and_other_parameter_writes(runtime):
    r = runtime
    material, rgba, _ = r.session.material(r.row, ROOT, 1)
    assert isinstance(material, Dynamic)
    assert not any(c[0] in {'static', 'scalar'} for c in r.calls)
    assert [c for c in r.calls if c[0] == 'vector'] == [('vector', 'Base Color Tint')]
    assert len([c for c in r.calls if c[0] == 'duplicate']) == 1
    assert rgba == [fast._f32(x) for x in r.session.palette.NEUTRAL_TINTS['blue']]
    assert material.parent.properties.opacity_mask_clip_value == .49
    assert effective(material, 'texture')['Opacity Map'].path.endswith('T_Hair134_Transparency_Pbr_Opacity')


def test_reparenting_restores_only_actual_inherited_differences(runtime):
    r = runtime
    r.source.parent.parameters['scalar']['Roughness Multiplier'] = .7
    r.source.parent.parameters['static']['Use Normal'] = False
    result, _, _ = r.session.material(r.row, ROOT, 1)
    assert effective(result, 'scalar')['Roughness Multiplier'] == .7
    assert effective(result, 'static')['Use Normal'] is False
    assert [c for c in r.calls if c[0] == 'static'] == [('static', 'Use Normal')]
    assert [c for c in r.calls if c[0] == 'scalar'] == [('scalar', 'Roughness Multiplier')]


def test_all_nine_dyes_reuse_one_source_parent_and_keep_standard_reflection(runtime):
    r = runtime
    for preset in r.session.palette.NEUTRAL_TINTS:
        material, _, _ = r.session.material(dict(r.row, preset=preset), ROOT, 1)
        assert effective(material, 'scalar')['Specular Multiplier'] == 1.
        assert effective(material, 'scalar')['Roughness Multiplier'] == .3
        assert effective(material, 'static') == {'Activate Hair Color': False, 'Use Normal': True}
        expected = fast._f32(.4) if preset == 'silver_white' else 1.
        assert effective(material, 'scalar')['Compensate Color Power'] == expected
    assert len([c for c in r.calls if c[0] == 'duplicate']) == 1
    assert len([c for c in r.calls if c[0] == 'coverage_create']) == 2
    assert len([c for c in r.calls if c[0] == 'save']) == 3


def test_existing_formal_neutral_instance_reused_at_same_spec_key(runtime):
    r = runtime
    expected, spec, suffix = r.session.specification(r.row, 'blue')
    instance = r.session.create_base(dict(r.row, preset='black'), fast.FORMAL_ROOT)
    target = fast.FORMAL_ROOT + suffix
    r.assets.pop(instance.path)
    instance.path = target
    instance.parameters['vector']['Base Color Tint'] = r.u.LinearColor(*expected['vector']['Base Color Tint'])
    instance.metadata[r.neutral.OWNER] = spec
    r.assets[target] = instance
    r.calls.clear()
    actual, rgba, created = r.session.material(r.row, ROOT, 1)
    assert actual is instance and not created and rgba == expected['vector']['Base Color Tint']
    assert not any(c[0] in {'duplicate', 'save', 'mid', 'static'} for c in r.calls)


def test_white_parent_resets_scalar_for_other_dye_without_saved_material_write(runtime):
    r = runtime
    expected, spec, suffix = r.session.specification(r.row, 'silver_white')
    instance = r.session.create_base(r.row, fast.FORMAL_ROOT)
    r.assets.pop(instance.path)
    instance.path = fast.FORMAL_ROOT + suffix
    instance.parameters['scalar'].update(expected['scalar'])
    instance.parameters['vector']['Base Color Tint'] = r.u.LinearColor(*expected['vector']['Base Color Tint'])
    instance.metadata[r.neutral.OWNER] = spec
    r.assets[instance.path] = instance
    r.calls.clear()
    result, _, _ = r.session.material(r.row, ROOT, 1)
    assert effective(result, 'scalar')['Compensate Color Power'] == 1.
    assert not any(c[0] == 'duplicate' for c in r.calls)
    assert len([c for c in r.calls if c[0] == 'save']) == 2  # coverage + Hair134 border protection


def test_existing_mismatched_metadata_raises_instead_of_falling_back(runtime):
    r = runtime
    _, _, suffix = r.session.specification(r.row, 'blue')
    target = fast.FORMAL_ROOT + suffix
    r.assets[target] = MIC(target, r.shader)
    with pytest.raises(RuntimeError, match='mismatched'):
        r.session.material(r.row, ROOT, 1)
    assert not any(c[0] == 'duplicate' for c in r.calls)


def test_coverage_receipt_handles_known_dynamic_and_rejects_unowned_dynamic(runtime):
    r = runtime
    material, _, _ = r.session.material(r.row, ROOT, 1)
    component = Component(r.source, material)
    receipt = r.coverage.apply(r.u, {'HairPart01': component})
    assert receipt['bindings'][0]['opacity_repaired'].endswith('T_Hair134_Transparency_Pbr_Opacity')
    assert receipt['bindings'][0]['material'] == material.path
    assert component.material is material
    assert material.get_scalar_parameter_value('Alpha Multiplier') == 1.5
    assert .49 > (25 / 255) * 1.5 + 1 / 3
    component.material = Dynamic('/Engine/Transient/Unknown', material.parent)
    with pytest.raises(RuntimeError, match='Unrecognized dynamic'):
        r.coverage.apply(r.u, {'HairPart01': component})


def test_interrupted_coverage_parent_is_reported_instead_of_reused(runtime):
    r = runtime
    r.session.material(r.row, ROOT, 1)
    parent, _ = next(iter(r.session.parents.values()))
    parent.parent.metadata.pop('DM_HairCoverage')
    r.session.parents.clear()
    r.session.materials.pop((r.source.path, 'source_hash', 'blue', ROOT, False))
    with pytest.raises(RuntimeError, match='Incomplete or mismatched hair coverage'):
        r.session.material(r.row, ROOT, 1)


def test_binding_failure_keeps_original_apply_rollback_and_error_feedback(runtime):
    r = runtime
    first = Component(r.source, r.source)
    second = Component(r.source, r.source)
    original_set = second.set_material

    def fail_dynamic(index, material):
        if isinstance(material, Dynamic):
            raise RuntimeError('simulated preview binding failure')
        original_set(index, material)

    second.set_material = fail_dynamic
    with pytest.raises(RuntimeError, match='simulated preview binding failure'):
        r.neutral.apply({'hair_color': 'blue', 'eye_color': 'original'},
                        {'HairPart01': first, 'HairPart02': second}, 1, ROOT)
    assert first.material is r.source and second.material is r.source


def test_other_source_keeps_standard_coverage_cutoff(runtime):
    r = runtime
    source = MIC('/Game/HB1_02/Materials/MI_Other', r.source.parent)
    r.assets[source.path] = source
    result, _, _ = r.session.material(dict(r.row, source=source), ROOT, 1)
    assert result.parent.properties.opacity_mask_clip_value == .34
    assert effective(result, 'texture')['Opacity Map'].path == '/Game/SourceOpacity'


def test_install_is_private_idempotent_and_hashes_only_once_per_session_path(runtime):
    r = runtime
    assert fast.install(r.graph, r.u) is r.session
    file = r.original.package_file('/Game/Source')
    assert r.session.sha(file) == r.session.sha(file)
    assert len([c for c in r.calls if c == ('sha', str(file))]) == 1
    assert r.graph.modules['hair_color_neutral_trial_runtime_v1'].material == r.session.material
    with pytest.raises(TypeError, match='private'):
        fast.install(SimpleNamespace(), r.u)

