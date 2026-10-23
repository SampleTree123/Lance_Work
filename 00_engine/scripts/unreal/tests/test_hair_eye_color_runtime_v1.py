import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("hair_eye_color_runtime_v1", Path(__file__).parents[1] / "hair_eye_color_runtime_v1.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_request_preserves_review_selection_and_rejects_unproven_brightening():
    request = {"sex": "female", "page": 2, "hair_color": "pink"}
    assert m.validate_request(request) == {**request, "eye_color": "original"}
    assert "eye_color" not in request
    for choice in ("brown", "green", "blonde", "gray", "Blue", None, ["pink"]):
        with pytest.raises(ValueError):
            m.validate_request({"hair_color": choice})


def test_only_refractive_iris_shader_is_colored_not_sclera_or_tearline():
    assert m.classify_slot("Eyes", "Std_Cornea_R_Pbr", "/Game/Cornea", [m.EYE_PARENT]) == "eye"
    assert m.classify_slot("Eyes", "Std_Eye_R_Pbr", "/Game/Eye", ["/Game/CC_Shaders/StandardShader/RL_Standard.RL_Standard"]) is None
    assert m.classify_slot("Tearline", "Cornea", "/Game/Cornea", [m.EYE_PARENT]) is None


def test_hair_accessories_and_coverage_never_tinted_even_if_hair_shader():
    for slot in ("Band1_Pbr", "HairRing2", "Flower33", "Pearl1"):
        assert m.classify_slot("HairPart01", slot, "/Game/Accessory", [m.HAIR_PARENT]) is None
    assert m.classify_slot("HairPart01", "Hair19", "/Game/M_Coverage_ZeroMask.M_Coverage_ZeroMask", [m.HAIR_PARENT]) is None
    assert m.classify_slot("HairPart01", "Hair19", "/Game/Hair", [m.HAIR_PARENT]) == "hair"
    assert m.classify_slot("Body", "Hair19", "/Game/Hair", [m.HAIR_PARENT]) is None


def test_deterministic_assets_isolate_actor_source_and_color():
    root = "/Game/DataMake/Validation/HairReview"
    args = (root, 0, "/Game/Hair.Source", "hair", "black")
    a = m._name(*args)
    assert a == m._name(*args)
    assert a != m._name(root, 1, args[2], "hair", "black")
    assert a != m._name(root, 0, "/Game/Other.Source", "hair", "black")
    assert a != m._name(root, 0, args[2], "hair", "brown")
    with pytest.raises(ValueError):
        m._name("/Game/CC_Shaders", 0, args[2], "hair", "black")
    with pytest.raises(ValueError):
        m._name(root, True, args[2], "hair", "black")


def test_missing_or_outside_saved_package_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "PROJECT_CONTENT", tmp_path)
    for path in ("/Engine/Material.Material", "/Game/../Secret.Secret", "/Game/Absent.Absent"):
        with pytest.raises(RuntimeError):
            m.package_file(path)


def test_exact_formal_material_root_is_allowed():
    root = '/Game/DataMake/Appearance/Materials'
    assert m._name(root, 0, '/Game/Hair.Source', 'hair', 'blue').startswith(root + '/ColorExperiments/S00/')


@pytest.mark.parametrize('root', [None, '/Game/DataMake/Appearance',
    '/Game/DataMake/Appearance/Materials/', '/Game/DataMake/Appearance/Materials/Other',
    '/Game/DataMake/Appearance/MaterialsElse', '/Game/DataMake/Appearance//Materials',
    '/Game/DataMake/Appearance/Materials/../Other', '/Game/Scenes/Test',
    '/Game/DataMake/Appearance/Materials.Materials', r'/Game/DataMake/Appearance\Materials'])
def test_formal_material_root_does_not_expand_other_write_roots(root):
    with pytest.raises(ValueError):
        m._name(root, 0, '/Game/Hair.Source', 'hair', 'blue')


class Asset:
    def __init__(self, name, **properties):
        self.name = name
        self.properties = properties

    def get_path_name(self):
        return self.name

    def get_editor_property(self, key):
        return self.properties[key]


class MIC(Asset):
    pass


class Component:
    def __init__(self, mesh, materials, fail=None):
        self.mesh, self.materials, self.fail = mesh, list(materials), fail

    def get_skeletal_mesh_asset(self):
        return self.mesh

    def get_num_materials(self):
        return len(self.materials)

    def get_material(self, i):
        return self.materials[i]

    def set_material(self, i, material):
        if material is self.fail:
            raise RuntimeError("simulated binding failure")
        self.materials[i] = material


def fixture_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "PROJECT_CONTENT", tmp_path)
    parent = Asset(m.HAIR_PARENT)
    source = MIC("/Game/Hair.Source", parent=parent)
    mesh = Asset("/Game/Mesh.Mesh", materials=[SimpleNamespace(material_interface=source, material_slot_name="Hair1")])
    for asset in (parent, source, mesh):
        file = tmp_path / (asset.name.split(".")[0][6:] + ".uasset")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"unchanged source")
    lib = SimpleNamespace(get_vector_parameter_names=lambda _: ["Base Color Tint"],
                          get_material_instance_static_switch_parameter_value=lambda *_: False)
    u = SimpleNamespace(MaterialInstance=MIC, MaterialInstanceConstant=MIC, MaterialEditingLibrary=lib,
        EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: []))
    monkeypatch.setattr(m, "_ue", lambda: u)
    return source, mesh


def test_failed_binding_rolls_back_previous_actor_components(tmp_path, monkeypatch):
    source, mesh = fixture_runtime(tmp_path, monkeypatch)
    derived = MIC("/Game/DataMake/Validation/Hair/Derived.Derived")
    monkeypatch.setattr(m, "_material", lambda *args: (derived, [.1, .1, .1, 1.], True))
    components = {"HairPart01": Component(mesh, [source]), "HairPart02": Component(mesh, [source], fail=derived)}
    with pytest.raises(RuntimeError, match="simulated binding failure"):
        m.apply({"hair_color": "black"}, components, 0, "/Game/DataMake/Validation/Hair")
    assert all(c.get_material(0) is source for c in components.values())


def test_source_change_detection_rolls_back_bindings(tmp_path, monkeypatch):
    source, mesh = fixture_runtime(tmp_path, monkeypatch)
    derived = MIC("/Game/DataMake/Validation/Hair/Derived.Derived")
    def mutate_source(*args):
        m.package_file(source.name).write_bytes(b"external unexpected change")
        return derived, [.1, .1, .1, 1.], True
    monkeypatch.setattr(m, "_material", mutate_source)
    components = {"HairPart01": Component(mesh, [source])}
    with pytest.raises(RuntimeError, match="Protected source package changed"):
        m.apply({"hair_color": "black"}, components, 0, "/Game/DataMake/Validation/Hair")
    assert components["HairPart01"].get_material(0) is source


def test_original_restores_source_without_generating_material(tmp_path, monkeypatch):
    source, mesh = fixture_runtime(tmp_path, monkeypatch)
    derived = MIC("/Game/DataMake/Validation/Hair/Derived.Derived")
    components = {"HairPart01": Component(mesh, [derived])}
    monkeypatch.setattr(m, "_material", lambda *_: pytest.fail("original must not create material"))
    receipt = m.apply({}, components, 0, "/Game/DataMake/Validation/Hair")
    assert components["HairPart01"].get_material(0) is source
    assert receipt["source_unchanged"] is True
    assert receipt["bindings"][0]["rgba_readback"] is None


def test_unrecognized_existing_asset_never_overwritten(monkeypatch):
    instance = MIC("/Game/DataMake/Validation/Hair/Existing.Existing")
    source = MIC("/Game/Hair.Source")
    u = SimpleNamespace(MaterialInstanceConstant=MIC, MaterialEditingLibrary=SimpleNamespace(),
        EditorAssetLibrary=SimpleNamespace(get_metadata_tag=lambda *_: "not ours"))
    monkeypatch.setattr(m, "_ue", lambda: u)
    with pytest.raises(RuntimeError, match="Unrecognized"):
        m._verify_instance(instance, source, "spec", "hair", "black")


def test_request_nonoriginal_requires_supported_materials(tmp_path, monkeypatch):
    fixture_runtime(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="No supported eye"):
        m.apply({"eye_color": "blue"}, {}, 0, "/Game/DataMake/Validation/Hair")


def test_plugin_accessory_material_is_protected_but_not_tinted(tmp_path, monkeypatch):
    source, mesh = fixture_runtime(tmp_path, monkeypatch)
    plugin_root = tmp_path / 'plugin_content'
    monkeypatch.setattr(m, 'INTERCHANGE_CONTENT', plugin_root)
    parent = Asset('/InterchangeAssets/Materials/FBXLegacyPhongSurfaceMaterial.FBXLegacyPhongSurfaceMaterial')
    file = plugin_root / 'Materials/FBXLegacyPhongSurfaceMaterial.uasset'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'plugin material')
    accessory = MIC('/Game/Band.Band', parent=parent)
    (tmp_path / 'Band.uasset').write_bytes(b'accessory')
    mesh.properties['materials'].append(SimpleNamespace(material_interface=accessory, material_slot_name='Band1_Pbr'))
    derived = MIC('/Game/DataMake/Validation/Hair/Derived.Derived')
    monkeypatch.setattr(m, '_material', lambda *args: (derived, [.1, .1, .1, 1.], True))
    component = Component(mesh, [source, accessory])
    receipt = m.apply({'hair_color': 'black'}, {'HairPart01': component}, 1, '/Game/DataMake/Validation/Hair')
    assert component.get_material(0) is derived
    assert component.get_material(1) is accessory
    assert str(file.resolve()) in receipt['protected_package_hashes']
    assert len(receipt['bindings']) == 1
    assert file.read_bytes() == b'plugin material'
    # The read-only plugin is still guarded by its own mount name. A dirty
    # plugin parent must roll back just like a dirty project source.
    component.materials = [source, accessory]
    dirty = []
    u = m._ue()
    u.EditorLoadingAndSavingUtils.get_dirty_content_packages = lambda: dirty
    def mark_dirty(*args):
        dirty.append(Asset(parent.name.split('.')[0]))
        return derived, [.1, .1, .1, 1.], False
    monkeypatch.setattr(m, '_material', mark_dirty)
    with pytest.raises(RuntimeError, match='Protected source became dirty'):
        m.apply({'hair_color': 'black'}, {'HairPart01': component}, 1, '/Game/DataMake/Validation/Hair')
    assert component.get_material(0) is source
    assert component.get_material(1) is accessory


def test_external_content_roots_still_reject_unknown_mounts_and_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'INTERCHANGE_CONTENT', tmp_path)
    for path in ('/Unknown/Materials/A.A', '/InterchangeAssets/../Secret.Secret',
                 '/InterchangeAssets/Materials/../../../Secret.Secret'):
        with pytest.raises(RuntimeError):
            m.package_file(path)


def test_engine_source_resolves_to_engine_not_project(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    monkeypatch.setattr(m, 'ENGINE_CONTENT', engine)
    file = engine / 'EngineMaterials/DefaultMaterial.uasset'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'engine material')
    assert m.package_file('/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial') == file.resolve()
