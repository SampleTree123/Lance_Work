"""Offline contract tests for the bounded CC runtime; never import RLPy."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
import types

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('creation_runtime_test', SCRIPTS / 'cc_run_character_creation_v1.py')
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Avatar:
    def __init__(self, calls):
        self.calls = calls
        self.level = 0
        self.count = 379
        self.hair = []
        self.switch_count = 0

    def GetSubdivMeshLevel(self):
        return self.level

    def GetFaceComponent(self):
        return types.SimpleNamespace(GetExpressionNames=lambda name: list(range(self.count)))

    def GetHairs(self):
        return self.hair

    def SwitchSubdivMeshLevel(self, level):
        self.calls.append(('switch', level))
        self.switch_count += 1
        self.level = level
        return True

    def GetMeshes(self, flag):
        self.calls.append(('body_capture', self.switch_count))
        v = types.SimpleNamespace(x=self.switch_count, y=2, z=3)
        return [types.SimpleNamespace(GetName=lambda: 'CC_Base_Body', GetVerticesCount=lambda: 14164,
                                      GetVertices=lambda world: [v] * 14164,
                                      GetFacesCount=lambda: 1, GetFace=lambda i: [0, 1, 2])]

    def GetMaterialComponent(self):
        def load(mesh, material, channel, path):
            self.calls.append(('texture', mesh, material, path))
            return True
        return types.SimpleNamespace(LoadImageToTexture=load)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    run_root = tmp_path / 'authorized'
    stage_root = tmp_path / 'staging'
    output = run_root / 'role' / 'step'
    output.mkdir(parents=True)
    stage_root.mkdir()
    source = stage_root / 'working.ccProject'
    source.write_bytes(b'independent current clean soft input')
    monkeypatch.setattr(RUNTIME, 'RUN_ROOT', str(run_root))
    monkeypatch.setattr(RUNTIME, 'STAGE_ROOT', str(stage_root))
    config = {'source_project': {'path': str(source), 'sha256': sha(source)},
              'operation': 'prepare', 'support_assets': [], 'proportion_preset': {}}
    calls, writes = [], {}
    avatar = Avatar(calls)
    state = {'objects': 0, 'avatars': [avatar], 'dialog_fail': False}

    def write(data, path):
        calls.append(('write', Path(path).name))
        writes[str(path)] = copy.deepcopy(data)
        Path(path).write_text(json.dumps(data), encoding='utf-8')

    def load(path, title):
        calls.append(('load', path))
        return {'is_error': False}, []

    def material_only(path, title):
        calls.append(('material_only', path))
        if state['dialog_fail']:
            raise ValueError('MaterialOnly dialog rejected')
        return {'is_error': False}, [{'button': 'Material Only'}]

    def save(path):
        calls.append(('save', path))
        Path(path).write_bytes(b'new independent project')
        return True

    def checked(title, result):
        if result is False:
            raise ValueError(title)

    api = types.SimpleNamespace(sha256_file=sha, write_json=write,
        read_json=lambda path: json.loads(Path(path).read_text()), checked=checked,
        bodyfit_freeze_file_record=lambda path: {'path': str(path), 'sha256': sha(path)},
        force_avatar_scene_evaluation=lambda avatar: calls.append(('evaluate',)),
        load_file_with_optional_undo_warning=load,
        load_file_with_material_only_dialog=material_only,
        avatar_asset_inventory=lambda avatar: {'object_count': state['objects']},
        avatar_part_inventory=lambda avatar: {'part_count': 0, 'parts': []},
        avatar_material_fingerprint=lambda avatar: {'digest': 'native_material_samples', 'observation_error_count': 0},
        apply_bodyfit_proportion_adjustment=lambda avatar, preset, phase: (avatar, {'success': True}),
        RLPy=types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: state['avatars'],
            SelectObject=lambda avatar: calls.append(('select',))),
            RFileIO=types.SimpleNamespace(SaveProject=save), EMaterialTextureChannel_Diffuse=0),
        QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(processEvents=lambda: None)))
    return types.SimpleNamespace(config=config, api=api, avatar=avatar, calls=calls, writes=writes,
                                 source=source, output=output, state=state, tmp=tmp_path)


def execute(r):
    return RUNTIME.run({'character_creation': r.config}, str(r.output), lambda text: None, r.api)


def test_output_outside_bounded_run_rejected_before_load(runtime):
    with pytest.raises(ValueError, match='authorized run'):
        RUNTIME.run({'character_creation': runtime.config}, str(runtime.tmp / 'elsewhere'), lambda x: None, runtime.api)
    assert runtime.calls == []


def test_original_project_outside_working_roots_rejected(runtime):
    p = runtime.tmp / 'original.ccProject'
    p.write_bytes(b'original protected')
    runtime.config['source_project'] = {'path': str(p), 'sha256': sha(p)}
    with pytest.raises(ValueError, match='independent working'):
        execute(runtime)
    assert p.read_bytes() == b'original protected'
    assert runtime.calls == []


def test_working_input_sha_drift_rejected_before_scene(runtime):
    runtime.source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA changed'):
        execute(runtime)
    assert runtime.calls == []


def test_photo_reads_project_from_backend_report_not_summary(runtime):
    runtime.config['operation'] = 'photo'
    project = runtime.output / 'generated_subd0.ccProject'
    project.write_bytes(b'generated identity')
    report = runtime.output / 'photo_backend.json'
    report.write_text(json.dumps({'success': True, 'project_path': str(project), 'project_sha256': sha(project)}))
    runtime.api.probe_headshot_photo_generation = lambda library, output, log: {'success': True, 'report_path': str(report)}
    result = execute(runtime)
    assert result['success']
    assert result['saved_project'] == {'path': str(project), 'sha256': sha(project)}
    assert not any(c[0] in ('save', 'switch') for c in runtime.calls)


def test_failed_photo_backend_never_promotes_project(runtime):
    runtime.config['operation'] = 'photo'
    runtime.api.probe_headshot_photo_generation = lambda *args: {'success': False, 'error': 'SDK failure'}
    result = execute(runtime)
    assert not result['success']
    assert 'saved_project' not in result
    assert result['phase'] == 'failed'


def test_photo_backend_missing_saved_project_receipt_cannot_promote(runtime):
    runtime.config['operation'] = 'photo'
    report = runtime.output / 'photo_backend.json'
    report.write_text(json.dumps({'success': True}))
    runtime.api.probe_headshot_photo_generation = lambda *args: {'success': True, 'report_path': str(report)}
    result = execute(runtime)
    assert not result['success'] and 'saved_project' not in result


def test_source_drift_during_operation_cannot_promote(runtime):
    runtime.config['operation'] = 'capture'
    def mutate(*args):
        runtime.source.write_bytes(b'accidental input mutation')
        return {'success': True}
    runtime.api.probe_headshot_mesh_replace = mutate
    result = execute(runtime)
    assert not result['success'] and result['source_unchanged'] is False


@pytest.mark.parametrize('field,value,error', [('level', 1, 'SubD 0'), ('count', 378, '379'),
                                              ('hair', [object()], 'no scalp hair')])
def test_prepare_requires_validated_bare_cc5_input(runtime, field, value, error):
    setattr(runtime.avatar, field, value)
    result = execute(runtime)
    assert not result['success'] and error in result['error']
    assert not any(c[0] in ('material_only', 'texture', 'switch', 'save') for c in runtime.calls)


def test_prepare_rejects_attached_wardrobe_or_props(runtime):
    runtime.state['objects'] = 1
    result = execute(runtime)
    assert not result['success'] and 'wardrobe' in result['error']
    assert not any(c[0] == 'save' for c in runtime.calls)


@pytest.mark.parametrize('avatars', [[], [object(), object()]])
def test_prepare_requires_single_avatar(runtime, avatars):
    runtime.state['avatars'] = avatars
    result = execute(runtime)
    assert not result['success'] and 'exactly one' in result['error']


def asset(runtime, suffix='.ccEye'):
    p = runtime.tmp / ('Eyes01' + suffix)
    p.write_bytes(b'support material')
    return {'path': str(p), 'sha256': sha(p)}


@pytest.mark.parametrize('suffix', ['.ccEye', '.ccTeeth'])
def test_support_assets_use_material_only(runtime, suffix):
    selected = asset(runtime, suffix)
    runtime.config['support_assets'] = [selected]
    result = execute(runtime)
    assert result['success']
    assert ('material_only', selected['path']) in runtime.calls
    assert result['support_materials'][0]['source'] == selected
    assert result['expression_count'] == 379
    assert [c for c in runtime.calls if c[0] == 'switch'] == [('switch', 1), ('switch', 0)]
    assert sha(runtime.source) == runtime.config['source_project']['sha256']


def test_support_sha_mismatch_does_not_apply_or_save(runtime):
    selected = asset(runtime)
    selected['sha256'] = '0' * 64
    runtime.config['support_assets'] = [selected]
    result = execute(runtime)
    assert not result['success']
    assert not any(c[0] in ('material_only', 'save') for c in runtime.calls)


def test_non_material_support_type_is_rejected(runtime):
    runtime.config['support_assets'] = [asset(runtime, '.ccAvatar')]
    result = execute(runtime)
    assert not result['success']
    assert not any(c[0] == 'material_only' for c in runtime.calls)


def test_material_only_dialog_failure_stops_before_normalize(runtime):
    runtime.config['support_assets'] = [asset(runtime)]
    runtime.state['dialog_fail'] = True
    result = execute(runtime)
    assert not result['success']
    assert not any(c[0] in ('switch', 'save') for c in runtime.calls)


def test_texture_sha_mismatch_stops_before_apply(runtime):
    selected = asset(runtime, '.png')
    selected['sha256'] = '0' * 64
    runtime.config['tongue_diffuse'] = selected
    result = execute(runtime)
    assert not result['success'] and 'texture SHA' in result['error']
    assert not any(c[0] in ('texture', 'switch', 'save') for c in runtime.calls)


def test_roundtrip_captures_origin_before_and_return_after_switch(runtime):
    runtime.config['operation'] = 'roundtrip'
    result = execute(runtime)
    assert result['success']
    initial = runtime.writes[str(runtime.output / 'initial_0_local_and_bones.json')]
    final = runtime.writes[str(runtime.output / 'return_0_local_and_bones.json')]
    assert len(initial['vertices']) == len(final['vertices']) == 14164
    assert initial['vertices'][0] == [0, 2, 3]
    assert final['vertices'][0] == [2, 2, 3]
    sequence = [c for c in runtime.calls if c[0] in ('body_capture', 'switch')]
    assert sequence == [('body_capture', 0), ('switch', 1), ('switch', 0), ('body_capture', 2)]


def test_existing_project_not_overwritten(runtime):
    output = runtime.output / 'prepared_subd0.ccProject'
    output.write_bytes(b'prior receipt')
    result = execute(runtime)
    assert not result['success'] and 'overwrite' in result['error']
    assert output.read_bytes() == b'prior receipt'


def test_unsupported_export_or_ue_operation_never_runs(runtime):
    runtime.config['operation'] = 'ue_export'
    result = execute(runtime)
    assert not result['success'] and 'Unsupported creation operation' in result['error']
    assert not any(c[0] in ('load', 'save', 'switch') for c in runtime.calls)


def test_native_prepare_preserves_appearance_and_keeps_geometry_normalization(runtime):
    runtime.config['appearance_mode'] = 'headshot_native'
    proportional_calls = []
    def proportion(avatar, preset, phase):
        proportional_calls.append(preset)
        return avatar, {'success': True}
    runtime.api.apply_bodyfit_proportion_adjustment = proportion
    result = execute(runtime)
    assert result['success'] and result['appearance_mode'] == 'headshot_native'
    assert proportional_calls == [runtime.config['proportion_preset']]
    assert [c for c in runtime.calls if c[0] == 'switch'] == [('switch', 1), ('switch', 0)]
    assert not any(c[0] in ('texture', 'material_only') for c in runtime.calls)
    assert result['support_materials'] == []
    metadata = result['native_appearance']
    assert metadata['material_metadata_unchanged'] and metadata['geometry_topology_unchanged']
    after = runtime.writes[str(runtime.output / 'native_appearance_after.json')]
    assert after['geometry_topology'][0]['vertex_count'] == 14164
    assert after['geometry_topology'][0]['face_count'] == 1
    assert after['sampling_scope']['all_texture_pixels_equal_proven'] is False
    assert after['sampling_scope']['texture_file_sha256'] is False


@pytest.mark.parametrize('field', ['support_assets', 'eyelash_diffuse', 'tongue_diffuse', 'facial_components'])
def test_native_rejects_appearance_override_before_scene_load(runtime, field):
    runtime.config.update(appearance_mode='headshot_native')
    runtime.config[field] = [asset(runtime)] if field == 'support_assets' else {'requested': True}
    result = execute(runtime)
    assert not result['success'] and 'prohibits appearance' in result['error']
    assert not any(c[0] in ('load', 'material_only', 'texture', 'switch', 'save') for c in runtime.calls)


def test_native_roundtrip_metadata_change_is_observation_not_false_acceptance(runtime):
    runtime.config.update(operation='roundtrip', appearance_mode='headshot_native')
    runtime.api.avatar_material_fingerprint = lambda avatar: {'digest': str(avatar.switch_count)}
    result = execute(runtime)
    assert result['success']
    assert result['native_appearance']['material_metadata_unchanged'] is False
    assert 'review remains required' in result['native_appearance']['acceptance']


@pytest.mark.parametrize('operation,config_key,backend_mode', [('capture', 'headshot_mesh_replace', 'hair_capture'),
                                                            ('replace', 'headshot_mesh_replace', 'raw_identity'),
                                                            ('late_bake', 'headshot_route_validation', 'tongue_material')])
def test_native_rejects_appearance_capable_backend_modes(runtime, operation, config_key, backend_mode):
    runtime.config.update(operation=operation, appearance_mode='headshot_native')
    nested = {'operation': backend_mode} if operation == 'late_bake' else {'mode': backend_mode}
    result = RUNTIME.run({'character_creation': runtime.config, config_key: nested}, str(runtime.output), lambda x: None, runtime.api)
    assert not result['success'] and 'Native' in result['error']
    assert not any(c[0] in ('load', 'switch', 'save') for c in runtime.calls)


def test_native_cannot_enter_appearance_assembly(runtime):
    runtime.config.update(operation='assemble', appearance_mode='headshot_native')
    result = execute(runtime)
    assert not result['success'] and 'assembly is prohibited' in result['error']


@pytest.mark.parametrize('options', [{'skin_preset': 'Scalp', 'body_type': 'current'},
                                   {'skin_preset': 'Clean Soft', 'body_type': 'female'}])
def test_native_photo_requires_current_clean_soft(runtime, options):
    runtime.config.update(operation='photo', appearance_mode='headshot_native')
    result = RUNTIME.run({'character_creation': runtime.config, 'headshot_photo_probe': options}, str(runtime.output), lambda x: None, runtime.api)
    assert not result['success'] and 'Current + Clean Soft' in result['error']


@pytest.mark.parametrize('operation,mode', [('capture', 'capture_only'), ('replace', 'normalized')])
def test_native_geometry_delegate_keeps_probe_and_captures_after_metadata(runtime, operation, mode):
    runtime.config.update(operation=operation, appearance_mode='headshot_native')
    received = []
    def backend(library, output, log):
        received.append(copy.deepcopy(library['headshot_mesh_replace']))
        return {'success': True}
    runtime.api.probe_headshot_mesh_replace = backend
    result = RUNTIME.run({'character_creation': runtime.config, 'headshot_mesh_replace': {'mode': mode}}, str(runtime.output), lambda x: None, runtime.api)
    assert result['success'] and received == [{'mode': mode}]
    assert result['native_appearance']['after']['sha256'] == sha(runtime.output / 'native_appearance_after.json')


def test_default_assembled_mode_does_not_add_native_observations(runtime):
    result = execute(runtime)
    assert result['success'] and result['appearance_mode'] == 'assembled'
    assert 'native_appearance' not in result


def test_unknown_appearance_mode_rejected_before_scene_load(runtime):
    runtime.config['appearance_mode'] = 'mixed'
    with pytest.raises(ValueError, match='appearance_mode'):
        execute(runtime)
    assert runtime.calls == []


def test_native_photo_success_observes_generated_appearance_without_replacements(runtime):
    runtime.config.update(operation='photo', appearance_mode='headshot_native')
    project = runtime.output / 'generated.ccProject'
    project.write_bytes(b'headshot original appearance')
    backend_report = runtime.output / 'photo_generation_report.json'
    backend_report.write_text(json.dumps({'project_path': str(project), 'project_sha256': sha(project)}))
    runtime.api.probe_headshot_photo_generation = lambda *args: {'success': True, 'report_path': str(backend_report)}
    result = RUNTIME.run({'character_creation': runtime.config, 'headshot_photo_probe': {
        'skin_preset': 'Clean Soft', 'body_type': 'current'}}, str(runtime.output), lambda x: None, runtime.api)
    assert result['success'] and result['saved_project']['path'] == str(project)
    assert result['native_appearance']['appearance_substitution_performed'] is False
    assert not any(c[0] in ('load', 'material_only', 'texture') for c in runtime.calls)


def test_native_late_bake_reloads_only_validated_geometry_control_and_observes_result(runtime, monkeypatch):
    runtime.config.update(operation='late_bake', appearance_mode='headshot_native')
    project = runtime.output / 'late_baked.ccProject'
    project.write_bytes(b'geometry baked with original appearance')
    backend_report = runtime.output / 'route_validation_report.json'
    saved = {'path': str(project), 'sha256': sha(project)}
    backend_report.write_text(json.dumps({'success': True, 'saved_project': saved}))
    calls = []
    def load(name):
        assert name == 'cc_headshot_route_validation_v1'
        calls.append('fresh_local_load')
        return types.SimpleNamespace(run=lambda *args: {'report_path': str(backend_report)})
    monkeypatch.setattr(RUNTIME, '_load_local_dependency', load)
    result = RUNTIME.run({'character_creation': runtime.config, 'headshot_route_validation': {
        'operation': 'late_bake_native_control'}}, str(runtime.output), lambda x: None, runtime.api)
    assert result['success'] and result['saved_project'] == saved
    assert calls == ['fresh_local_load']
    assert 'after' in result['native_appearance']


@pytest.mark.parametrize('operation,module_name', [('assemble', 'cc_run_headshot_base_assembly_v1'),
                                                 ('late_bake', 'cc_headshot_route_validation_v1')])
def test_cached_child_module_reloaded_before_run(runtime, monkeypatch, operation, module_name):
    runtime.config['operation'] = operation
    saved = runtime.output / 'child_result.ccProject'
    saved.write_bytes(b'child saved independent project')
    saved_record = {'path': str(saved), 'sha256': sha(saved)}
    backend_report = runtime.output / 'child_report.json'
    backend_report.write_text(json.dumps({'success': True, 'saved_project': saved_record}))
    order = []
    def load_child(name):
        assert name == module_name
        order.append('fresh_local_load')
        def fresh_run(*args):
            order.append('fresh_run')
            return {'success': True, 'saved_project': saved_record, 'report_path': str(backend_report)}
        return types.SimpleNamespace(run=fresh_run)
    monkeypatch.setattr(RUNTIME, '_load_local_dependency', load_child)
    result = execute(runtime)
    assert result['success']
    assert result['saved_project'] == saved_record
    assert order == ['fresh_local_load', 'fresh_run']


@pytest.mark.parametrize('name', ['cc_headshot_route_validation_v1', 'cc_run_headshot_base_assembly_v1', 'cc_repair_headshot_support_materials_v1'])
def test_dependency_load_uses_exact_adjacent_file_without_sys_path_and_replaces_stale_cache(tmp_path, monkeypatch, name):
    monkeypatch.setattr(RUNTIME, '__file__', str(tmp_path / 'cc_run_character_creation_v1.py'))
    (tmp_path / (name + '.py')).write_text('VALUE = "fresh local implementation"\n', encoding='utf-8')
    monkeypatch.setattr(sys, 'path', [p for p in sys.path if os.path.realpath(p) != str(tmp_path)])
    stale = types.SimpleNamespace(VALUE='stale cached implementation')
    monkeypatch.setitem(sys.modules, name, stale)
    module = RUNTIME._load_local_dependency(name)
    assert module is not stale and module.VALUE == 'fresh local implementation'
    assert Path(module.__file__).resolve() == tmp_path / (name + '.py')
    assert sys.modules[name] is module


def test_failed_local_child_load_restores_prior_cache(tmp_path, monkeypatch):
    name = 'cc_headshot_route_validation_v1'
    monkeypatch.setattr(RUNTIME, '__file__', str(tmp_path / 'cc_run_character_creation_v1.py'))
    (tmp_path / (name + '.py')).write_text('raise RuntimeError("broken child")\n', encoding='utf-8')
    stale = types.SimpleNamespace(VALUE='previous module')
    monkeypatch.setitem(sys.modules, name, stale)
    with pytest.raises(RuntimeError, match='broken child'):
        RUNTIME._load_local_dependency(name)
    assert sys.modules[name] is stale


def test_local_dependency_loader_rejects_unapproved_module():
    with pytest.raises(ValueError, match='Unsupported creation dependency'):
        RUNTIME._load_local_dependency('other_module')


def test_explicit_support_repair_dispatches_only_independent_child(runtime, monkeypatch):
    runtime.config.update(operation='repair_support', appearance_mode='assembled')
    saved = runtime.output / 'support_repaired.ccProject'
    saved.write_bytes(b'separate support repair')
    record = {'path': str(saved), 'sha256': sha(saved)}
    calls = []
    def load(name):
        calls.append(name)
        return types.SimpleNamespace(run=lambda *args: {'success': True, 'saved_project': record})
    monkeypatch.setattr(RUNTIME, '_load_local_dependency', load)
    result = execute(runtime)
    assert result['success'] and result['saved_project'] == record
    assert calls == ['cc_repair_headshot_support_materials_v1']
    assert not any(c[0] in ('load', 'switch', 'texture') for c in runtime.calls)


def test_native_runtime_repair_dispatch_is_prohibited(runtime):
    runtime.config.update(operation='repair_support', appearance_mode='headshot_native')
    result = execute(runtime)
    assert not result['success'] and 'prohibited' in result['error']


SOURCE = ast.parse((SCRIPTS / 'cc_validate_body_reconstruction.py').read_text(encoding='utf-8-sig'))


def original_function(name):
    return next(node for node in SOURCE.body if isinstance(node, ast.FunctionDef) and node.name == name)


def test_transforms_only_original_guard_explicitly_allows_creation_and_rejects_unknown():
    function = original_function('_run_library_without_dialog_guard')
    guards = [node for node in function.body if isinstance(node, ast.If)
              and 'EYE_SNAPSHOT_MODE' in ast.unparse(node.test)]
    assert len(guards) == 2
    compiled = compile(ast.fix_missing_locations(ast.Module(body=guards, type_ignores=[])), '<eye guard>', 'exec')
    for mode in ('cc_character_creation', 'headshot_mesh_replace_probe', 'headshot_route_validation'):
        exec(compiled, {'EYE_SNAPSHOT_MODE': 'transforms_only', 'library': {'diagnostic_mode': mode},
                        'ReconstructionError': ValueError})
    with pytest.raises(ValueError, match='explicit supported mode'):
        exec(compiled, {'EYE_SNAPSHOT_MODE': 'transforms_only', 'library': {'diagnostic_mode': 'unbounded'},
                        'ReconstructionError': ValueError})


def mesh_prefix():
    function = original_function('probe_headshot_mesh_replace')
    prefix = []
    for node in function.body:
        prefix.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'source' for t in node.targets):
            break
    prefix.append(ast.Return(value=ast.Name(id='source', ctx=ast.Load())))
    fn = ast.FunctionDef(name='verify_mesh_source', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='library')],
        kwonlyargs=[], kw_defaults=[], defaults=[]), body=prefix, decorator_list=[])
    namespace = {'os': os, 'SCRIPT_DIR': str(SCRIPTS), 'sha256_file': lambda path: 'locked',
                 'path_is_within': lambda path, roots: any(os.path.commonpath([os.path.realpath(path), os.path.realpath(r)]) == os.path.realpath(r) for r in roots),
                 'ReconstructionError': ValueError}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<mesh path guard>', 'exec'), namespace)
    return namespace['verify_mesh_source']


def test_new_mesh_root_allows_bounded_staging_but_not_original_or_sibling():
    verify = mesh_prefix()
    run = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
    stage = SCRIPTS / 'runtime_staging/headshot_character_creation_20261005_v1'
    for source in (str(stage / 'INPUT.ccProject'), os.path.join(run, 'role', 'prepared.ccProject')):
        result = verify({'headshot_mesh_replace': {'experiment_root': run, 'source_project': {'path': source, 'sha256': 'locked'}}})
        assert result == os.path.realpath(source)
    for source in (str(SCRIPTS / 'runtime_staging/headshot_character_creation_20261005_v1_other/INPUT.ccProject'),
                   r'D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\F02_Average.ccProject'):
        with pytest.raises(ValueError, match='path/hash mismatch'):
            verify({'headshot_mesh_replace': {'experiment_root': run, 'source_project': {'path': source, 'sha256': 'locked'}}})


def test_new_mesh_guard_rejects_arbitrary_experiment_root():
    with pytest.raises(ValueError, match='Unsupported mesh probe experiment root'):
        mesh_prefix()({'headshot_mesh_replace': {'experiment_root': 'D:/UE/unbounded', 'source_project': {'path': 'x', 'sha256': 'locked'}}})


def test_photo_staging_permission_only_for_explicit_creation_mode():
    function = original_function('probe_headshot_photo_generation')
    start = next(i for i, node in enumerate(function.body) if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'photo_roots' for t in node.targets))
    nodes = function.body[start:start + 3]
    assert isinstance(nodes[1], ast.If) and isinstance(nodes[2], ast.If)
    code = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), '<photo staging guard>', 'exec')
    staging = str(SCRIPTS / 'runtime_staging/headshot_character_creation_20261005_v1/face.jpg')
    def evaluate(photo, mode):
        exec(code, {'os': os, 'SCRIPT_DIR': str(SCRIPTS), 'photo': photo,
            'library': {'diagnostic_mode': mode}, 'ReconstructionError': ValueError,
            'path_is_within': lambda path, roots: any(os.path.commonpath([os.path.realpath(path), os.path.realpath(r)]) == os.path.realpath(r) for r in roots)})
    evaluate(staging, 'cc_character_creation')
    with pytest.raises(ValueError, match='bounded creation staging'):
        evaluate(staging, 'headshot_photo_generation_probe')
    with pytest.raises(ValueError, match='bounded creation staging'):
        evaluate(str(SCRIPTS / 'runtime_staging/headshot_character_creation_20261005_v1_other/face.jpg'), 'cc_character_creation')
