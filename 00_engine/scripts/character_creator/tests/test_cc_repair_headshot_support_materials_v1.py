import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

SPEC = importlib.util.spec_from_file_location('support_repair', Path(__file__).parents[1] / 'cc_repair_headshot_support_materials_v1.py')
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Mesh:
    def __init__(self, name):
        self.name = name
        self.vertices = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]
    def GetName(self): return self.name
    def GetVerticesCount(self): return len(self.vertices)
    def GetFacesCount(self): return 1
    def GetFace(self, i): return [0, 1, 2]
    def GetVertices(self, world): return [types.SimpleNamespace(x=v[0], y=v[1], z=v[2]) for v in self.vertices]


class Part:
    def __init__(self, name, kind): self.name, self.kind, self.mesh = name, kind, Mesh(name)
    def GetName(self): return self.name
    def GetAvatarPartType(self): return self.kind
    def GetID(self): return self.name
    def GetMeshes(self, flag): return [self.mesh]


class Avatar:
    def __init__(self, component):
        self.component = component
        self.meshes = [Mesh('CC_Base_Body'), Mesh('CC_Base_Tongue')]
        self.parts = [Part('CC_Base_Eye', 1), Part('CC_Base_Teeth', 2)]
    def GetID(self): return 'avatar'
    def GetMeshes(self, flag): return self.meshes
    def GetAvatarParts(self): return self.parts
    def GetSubdivMeshLevel(self): return 0
    def GetFaceComponent(self): return types.SimpleNamespace(GetExpressionNames=lambda x: list(range(379)))
    def GetMaterialComponent(self): return self.component


class QImage:
    Format_RGBA8888 = 17
    def __init__(self, path): self.data = Path(path).read_bytes()
    def isNull(self): return not self.data
    def width(self): return 2
    def height(self): return 2
    def convertToFormat(self, format): return self
    def __eq__(self, other): return self.data == other.data


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    run = tmp_path / 'run'
    stage = tmp_path / 'stage'
    output = run / 'repair'
    output.mkdir(parents=True)
    stage.mkdir()
    source = stage / 'input.ccProject'
    source.write_bytes(b'protected current average')
    calls, state = [], {'move_eye': False, 'opacity_drift': False, 'reloading': False}
    record = lambda p: {'path': str(p), 'sha256': sha(p)}
    def asset(name):
        p = tmp_path / name
        p.write_bytes(name.encode())
        return record(p)
    selected = {'appearance_support_assets': [asset('Eyes_01.ccEye'), asset('HD_Teeth.ccTeeth')],
                'eyelash_diffuse_repair': asset('lash.png'), 'tongue_diffuse': asset('tongue.png')}
    refs = tmp_path / 'references.json'
    refs.write_text(json.dumps({'sexes': {'male': selected, 'female': selected}}))
    monkeypatch.setattr(REPAIR, 'RUN_ROOT', str(run))
    monkeypatch.setattr(REPAIR, 'STAGE_ROOT', str(stage))
    monkeypatch.setattr(REPAIR, 'REFERENCES_PATH', str(refs))
    textures = {}
    class Image:
        def __init__(self, key): self.key = key
        def GetWidth(self): return 2
        def GetHeight(self): return 2
        def SaveFile(self, path):
            data = textures.get(self.key, b'original-opacity')
            if self.key[2] == 1 and state['opacity_drift'] and textures:
                data = b'drifted-opacity'
            Path(path).write_bytes(data)
            return True
    def apply(mesh, material, channel, path):
        calls.append(('diffuse', mesh, material, channel))
        textures[(mesh, material, channel)] = Path(path).read_bytes()
        return True
    component = types.SimpleNamespace(GetImage=lambda m, n, c: Image((m, n, c)), LoadImageToTexture=apply)
    avatar = Avatar(component)
    def load(path, title):
        calls.append(('load', Path(path).name))
        return {'is_error': False}, []
    def material(path, title):
        calls.append(('material_only', Path(path).name))
        if state['move_eye']:
            avatar.parts[0].mesh.vertices[0][0] += .001
        return {'is_error': False}, [{'button': 'Material Only'}]
    def save(path):
        calls.append(('save',))
        Path(path).write_bytes(b'new material only copy')
        return True
    def checked(title, result):
        if result is False: raise ValueError(title)
    api = types.SimpleNamespace(sha256_file=sha, read_json=lambda p: json.loads(Path(p).read_text()),
        write_json=lambda data, p: Path(p).write_text(json.dumps(data)), checked=checked,
        bodyfit_freeze_file_record=lambda p: {**record(p), 'bytes': Path(p).stat().st_size},
        load_file_with_optional_undo_warning=load, load_file_with_material_only_dialog=material,
        force_avatar_scene_evaluation=lambda a: None,
        RLPy=types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda a: None),
                                  RFileIO=types.SimpleNamespace(SaveProject=save),
                                  EMaterialTextureChannel_Diffuse=0, EMaterialTextureChannel_Opacity=1),
        QtGui=types.SimpleNamespace(QImage=QImage),
        QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(processEvents=lambda: None)))
    source_record = {**record(source), 'bytes': source.stat().st_size}
    library = {'character_creation': {'appearance_mode': 'assembled', 'source_project': source_record},
               'headshot_support_repair': {'sex': 'male', 'source_project': source_record, 'references_file': record(refs)}}
    return types.SimpleNamespace(api=api, avatar=avatar, output=output, source=source,
                                 selected=selected, library=library, calls=calls, state=state)


def test_recursive_capture_includes_eyes_and_teeth_and_reports_true_part_motion(fixture):
    before = REPAIR.capture_geometry(fixture.avatar)
    assert {r['name'] for r in before['meshes']} == {'CC_Base_Body', 'CC_Base_Tongue', 'CC_Base_Eye', 'CC_Base_Teeth'}
    fixture.avatar.parts[0].mesh.vertices[0][0] += .0003
    comparison = REPAIR.compare_geometry(before, REPAIR.capture_geometry(fixture.avatar))
    assert comparison['structure_unchanged'] and not comparison['passed']
    assert comparison['maximum_local_delta_mm'] == pytest.approx(.003)


def test_geometry_capture_checks_topology_not_only_positions(fixture):
    before = REPAIR.capture_geometry(fixture.avatar)
    after = copy.deepcopy(before)
    after['meshes'][0]['faces_sha256'] = 'changed-face-order'
    assert not REPAIR.compare_geometry(before, after)['passed']


def test_material_only_repair_keeps_geometry_opacity_and_donor_pixels(fixture):
    result = REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert result['success'] and result['source_unchanged']
    assert result['eyelash_opacity_unchanged']
    assert all(c['passed'] and c['maximum_local_delta_mm'] == 0 for c in result['geometry_checks'])
    assert all(r['rgba_pixels_equal'] for r in result['diffuse_repairs'] + result['reloaded_diffuse'])
    assert [c for c in fixture.calls if c[0] == 'material_only'] == [('material_only', 'Eyes_01.ccEye'), ('material_only', 'HD_Teeth.ccTeeth')]
    assert [c for c in fixture.calls if c[0] == 'diffuse'] == [('diffuse', 'CC_Base_Body', 'Std_Eyelash', 0), ('diffuse', 'CC_Base_Tongue', 'Std_Tongue', 0)]
    assert 'saved_project' in result and fixture.source.read_bytes() == b'protected current average'


def test_eye_part_geometry_change_stops_save(fixture):
    fixture.state['move_eye'] = True
    result = REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert not result['success'] and 'protected local geometry' in result['error']
    assert 'saved_project' not in result and ('save',) not in fixture.calls


def test_eyelash_opacity_drift_stops_save(fixture):
    fixture.state['opacity_drift'] = True
    result = REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert not result['success'] and 'opacity changed' in result['error']
    assert ('save',) not in fixture.calls


def test_support_donor_sha_change_rejected_before_scene_load(fixture):
    Path(fixture.selected['eyelash_diffuse_repair']['path']).write_bytes(b'changed donor')
    with pytest.raises(ValueError, match='Pinned support source SHA'):
        REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert not fixture.calls


def test_existing_project_not_overwritten(fixture):
    output = fixture.output / 'support_materials_repaired_subd0.ccProject'
    output.write_bytes(b'keep prior output')
    with pytest.raises(ValueError, match='overwrite'):
        REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert output.read_bytes() == b'keep prior output' and not fixture.calls


def test_native_original_mode_cannot_silently_apply_repair(fixture):
    fixture.library['character_creation']['appearance_mode'] = 'headshot_native'
    with pytest.raises(ValueError, match='separate from headshot_native'):
        REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert not fixture.calls


def test_available_owner_transform_change_is_not_hidden_by_unchanged_local_mesh(fixture):
    before = REPAIR.capture_geometry(fixture.avatar)
    before['owner_transforms'] = [{'owner': 'avatar/1:CC_Base_Eye', 'space': 'world', 'value': {
        'translation': {'x':0, 'y':0, 'z':0}, 'rotation': {'x':0, 'y':0, 'z':0, 'w':1}}}]
    after = copy.deepcopy(before)
    after['owner_transforms'][0]['value']['translation']['x'] = .001
    result = REPAIR.compare_geometry(before, after)
    assert result['maximum_local_delta_mm'] == 0
    assert not result['passed'] and not result['available_owner_transforms_preserved']


def test_unregistered_references_path_rejected_before_load(fixture):
    fixture.library['headshot_support_repair']['references_file']['path'] = str(fixture.source)
    with pytest.raises(ValueError, match='registered adjacent'):
        REPAIR.run(fixture.library, str(fixture.output), lambda x: None, fixture.api)
    assert not fixture.calls
