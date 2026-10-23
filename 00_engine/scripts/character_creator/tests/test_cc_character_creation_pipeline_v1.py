"""End-to-end request/graph/recovery tests with synthetic local Bridge output.

These tests perform no CC calls. Real SDK geometry is tested separately; this
suite checks orchestration, source lineage, configuration and resume behavior.
"""
import ast
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_character_creation_pipeline_v1 as pipeline
import cc_character_creation_job_state_v1 as jobs
from cc_compile_headshot_base_assembly_v1 import COMPONENT_FIELDS


@pytest.fixture
def environment(tmp_path, monkeypatch):
    run, stage, bridge = (tmp_path / key for key in ('run', 'stage', 'bridge'))
    def record(name, content=b'reference'):
        path = tmp_path / name
        path.write_bytes(content)
        return jobs.bind(path)
    selected = {
        'starter_project': record('START.ccProject'),
        'proportion_preset': {'bodyfit_proportion_adjustment': {'targets': []}},
        'appearance_support_assets': [record('Eyes.ccEye'), record('Teeth.ccTeeth')],
        'eyelash_diffuse_repair': record('eyelash.png'),
        'tongue_diffuse': record('tongue.png'),
        'regions': record('regions.json', b'{}'),
    }
    refs = {'schema_version':1, 'sexes':{'female':selected, 'male':selected}}
    references = tmp_path / 'references.json'
    jobs.write(references, refs)
    policy = tmp_path / 'policy.json'
    jobs.write(policy, {'schema_version':1, 'policies':{}})
    monkeypatch.setattr(pipeline, 'RUN_ROOT', run)
    monkeypatch.setattr(pipeline, 'STAGE_ROOT', stage)
    monkeypatch.setattr(pipeline, 'REFERENCES', references)
    monkeypatch.setattr(pipeline, 'POLICY', policy)
    # Model the eight implementation bindings using a small immutable fixture;
    # this exercises drift checks without repeatedly hashing the large legacy SDK
    # module for every synthetic graph step.
    implementation = record('implementation.py', b'fixture implementation')
    monkeypatch.setattr(pipeline, 'bind', lambda path: dict(implementation)
        if Path(path).suffix == '.py' else jobs.bind(path))
    monkeypatch.setattr(pipeline, 'load_references', lambda sex, path: (
        refs, dict(selected, requires_final_neutral_morph_bake=(sex == 'female'))))
    photo = tmp_path / 'face.jpg'
    photo.write_bytes(b'original photo')
    project = tmp_path / 'RAW.ccProject'
    project.write_bytes(b'original raw project')
    calls, compiled = [], []
    def fake_compile(request):
        assert set(request['facial_components']) <= COMPONENT_FIELDS
        assert isinstance(request['source_project'], str)
        assert isinstance(request['output_project'], str)
        assert isinstance(request['regions_path'], str)
        assert type(request['seed']) is int
        compiled.append(copy.deepcopy(request))
        return dict(request, assets=[])
    monkeypatch.setattr(pipeline, 'compile_base_assembly', fake_compile)
    def world_obj(template, vertices, output):
        Path(output).write_text(json.dumps(np.asarray(vertices).tolist()))
    monkeypatch.setattr(pipeline, 'write_world_obj', world_obj)
    def solver(capture, calibration, identity, sex, output, references):
        output.mkdir(parents=True, exist_ok=False)
        jobs.write(output / 'geometry_report.json', {'passed':True})
        np.savez(output / 'target_geometry.npz', points=np.zeros((4,3)))
        (output / 'target_world.obj').write_bytes(b'target')
    monkeypatch.setattr(pipeline, 'build_geometry_targets', solver)
    def final_check(state, driver, target_dir, capture_dir):
        path = Path(state['attempt_dir']) / 'final_geometry_review.json'
        if not path.exists():
            jobs.write(path, {'passed':True})
        state['offline_outputs']['final_geometry_review'] = jobs.bind(path)
        driver.persist(state)
    monkeypatch.setattr(pipeline, 'verify_final_geometry', final_check)
    def bridge_call(arguments):
        if arguments == ['health']:
            return {'healthy':True}
        calls.append(arguments)
        library_path = Path(arguments[arguments.index('--library-file') + 1])
        library = jobs.read(library_path)
        output = Path(arguments[arguments.index('--output-dir') + 1])
        job_id = arguments[arguments.index('--job-id') + 1]
        operation = library['character_creation']['operation']
        if operation == 'assemble':
            project_path = Path(library['base_assembly']['output_project'])
        else:
            project_path = output / 'RESULT.ccProject'
        project_path.write_bytes((operation + ' project').encode())
        report = {'success':True, 'source_unchanged':True, 'saved_project':jobs.bind(project_path)}
        if library['character_creation'].get('appearance_mode') == 'headshot_native':
            snapshot = native_snapshot()
            # Scene reload IDs may legitimately differ without part replacement.
            snapshot['parts']['parts'][0]['id'] = str(output)
            report['native_appearance'] = {'material_metadata_unchanged':True,
                'geometry_topology_unchanged':True,'appearance_substitution_performed':False,
                'acceptance':'observations only; not visual acceptance'}
            for label in ('before','after'):
                path = output / ('native_appearance_' + label + '.json')
                jobs.write(path, snapshot)
                report['native_appearance'][label] = jobs.bind(path)
        jobs.write(output / 'creation_report.json', report)
        if operation == 'capture':
            jobs.write(output / 'before_world_mesh.json', {'vertices':np.zeros((4,3)).tolist()})
            (output / 'before_body.obj').write_text('v 0 0 0\nvt 0.5 0.5\nusemtl Skin\nf 1/1 2/1 3/1\n')
        if operation == 'roundtrip':
            jobs.write(output / 'return_0_local_and_bones.json', {'vertices':np.zeros((4,3)).tolist()})
        jobs.write(bridge / 'results' / (job_id + '.json'), {
            'job_id':job_id, 'command':'validate_bodyfit_library', 'status':'succeeded',
            'result':{'library_file':str(library_path), 'output_dir':str(output)}, 'error':None,
        })
        return {'queued':True}
    driver = jobs.BridgeStepDriver(run_root=run, stage_root=stage, bridge_root=bridge, client_call=bridge_call)
    return {'run':run, 'stage':stage, 'photo':photo, 'project':project, 'driver':driver,
            'calls':calls, 'compiled':compiled, 'selected':selected, 'references':references,
            'bridge_call':bridge_call}


def native_snapshot():
    return {'appearance_mode':'headshot_native', 'working_subdivision':0,
        'geometry_topology':[{'name':'Body','vertex_count':4,'face_count':1,'face_indices_sha256':'faces'}],
        'parts':{'parts':[{'avatar_part_type':'Eye','name':'Eye','python_type':'Part','id':'temporary'}]},
        'assets':{'objects':[]},
        'materials':{'digest':'material','mesh_digests':{'Body':'skin'},'material_count':1,
                     'texture_count':2,'observation_error_count':0,'observation_errors':[]}}


def request(environment, mode='photo', sex='female', **values):
    result = {'character_id':'test_' + sex + '_' + mode, 'seed':123, 'sex':sex,
              'photo' if mode == 'photo' else 'source_project':str(environment['photo' if mode == 'photo' else 'project'])}
    result.update(values)
    return result


@pytest.mark.parametrize('mode', ['photo', 'project'])
def test_prepare_preserves_original_and_copies_to_stage(environment, mode):
    config = request(environment, mode)
    state = pipeline.prepare_request(config)
    assert state['status'] == 'prepared' and state['steps'] == {}
    assert state['inputs']['original']['sha256'] == state['inputs']['working_input']['sha256']
    assert Path(state['inputs']['working_input']['path']).is_relative_to(environment['stage'])
    assert Path(state['preset_source']['path']).suffix.lower() == '.ccproject'
    assert environment['calls'] == []
    assert pipeline.prepare_request(config)['attempt_id'] == 'attempt_001'


def test_prepare_fingerprint_change_rejected(environment):
    config = request(environment)
    pipeline.prepare_request(config)
    with pytest.raises(jobs.ControllerError, match='different'):
        pipeline.prepare_request(dict(config, seed=124))


def test_reference_and_original_drift_rejected(environment):
    config = request(environment)
    state = pipeline.prepare_request(config)
    Path(state['inputs']['original']['path']).write_bytes(b'drift')
    with pytest.raises(jobs.ControllerError, match='SHA'):
        pipeline.prepare_request(config)


def test_terminal_failed_attempt_starts_fresh_copy(environment):
    config = request(environment)
    first = pipeline.prepare_request(config)
    first['status'] = 'failed'
    jobs.write(first['state_path'], first)
    second = pipeline.prepare_request(config)
    assert second['attempt_id'] == 'attempt_002'
    assert second['steps'] == {}
    assert second['inputs']['original'] == first['inputs']['original']
    assert Path(first['state_path']).exists()


@pytest.mark.parametrize('mode,sex', [('photo','female'), ('project','female'), ('photo','male'), ('project','male')])
def test_entry_graph_common_tail_and_compiler_mapping(environment, mode, sex):
    state = pipeline.prepare_request(request(environment, mode, sex))
    state = pipeline.advance(state, environment['driver'], 0)
    assert state['status'] == 'completed'
    names = list(state['steps'])
    assert ('01_photo' in names) == (mode == 'photo')
    assert ('09_late_bake' in names) == (sex == 'female')
    assert names[-2:] == ['11_final_capture', '12_assemble']
    assert names.count('02_prepare') == 1
    assert set(['04_calibrate_zero','04_calibrate_x','04_calibrate_y','04_calibrate_z']) <= set(names)
    assert environment['compiled'][0]['facial_components']['eyelash_asset_id'] == 'CCAPP_EYELASHES_284c3a142668'
    assert environment['compiled'][0]['regions_path'] == environment['selected']['regions']['path']
    assert state['visual_acceptance'] == 'representative_review_pending'
    assert state['scope'].startswith('CC-only')
    libraries = [jobs.read(step['library']['path']) for step in state['steps'].values()]
    prepare = next(item for item in libraries if item['character_creation']['operation'] == 'prepare')
    assert prepare['character_creation']['support_assets'] == environment['selected']['appearance_support_assets']
    assert prepare['character_creation']['eyelash_diffuse'] == environment['selected']['eyelash_diffuse_repair']
    if mode == 'photo':
        generation = libraries[0]['headshot_photo_probe']
        assert generation['skin_preset'] == 'Clean Soft' and generation['body_type'] == 'current'
        assert generation['pre_generation_subdiv_level'] == 0
    original_bytes = environment['photo' if mode == 'photo' else 'project'].read_bytes()
    assert original_bytes == (b'original photo' if mode == 'photo' else b'original raw project')


def test_explicit_facial_component_override_is_retained(environment):
    state = pipeline.prepare_request(request(environment, 'project', 'male',
        facial_components={'eyelash_asset_id':'custom_lash', 'hair_color_id':'black'}))
    pipeline.advance(state, environment['driver'], 0)
    assert environment['compiled'][0]['facial_components']['eyelash_asset_id'] == 'custom_lash'
    assert environment['compiled'][0]['facial_components']['hair_color_id'] == 'black'


def test_completed_resume_never_submits_and_rejects_receipt_drift(environment):
    config = request(environment, 'project', 'male')
    state = pipeline.advance(pipeline.prepare_request(config), environment['driver'], 0)
    count = len(environment['calls'])
    assert pipeline.advance(pipeline.prepare_request(config), environment['driver'], 0)['status'] == 'completed'
    assert len(environment['calls']) == count
    Path(state['result_project']['path']).write_bytes(b'drift')
    with pytest.raises(jobs.ControllerError, match='SHA'):
        pipeline.advance(pipeline.prepare_request(config), environment['driver'], 0)
    assert len(environment['calls']) == count


def test_library_presets_satisfy_real_bridge_path_contract(environment):
    state = pipeline.advance(pipeline.prepare_request(request(environment, 'project', 'male')), environment['driver'], 0)
    plugin = Path(__file__).resolve().parents[3] / 'character_creator_bridge/plugin/main.py'
    tree = ast.parse(plugin.read_text(encoding='utf-8-sig'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'bodyfit_preset_input_paths')
    namespace = {'SOURCE_PROJECT_ONLY_BODYFIT_MODES':frozenset()}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(plugin), 'exec'), namespace)
    for step in state['steps'].values():
        library = jobs.read(step['library']['path'])
        paths = namespace['bodyfit_preset_input_paths'](library, library['presets'][0])
        assert len(paths) == 2
        assert all(Path(path).is_relative_to(environment['stage']) for path in paths)


def test_pending_resume_queries_same_job_and_continues(environment):
    config = request(environment, 'project', 'male')
    driver = environment['driver']
    pending_calls = []
    def uncertain(arguments):
        if arguments == ['health']:
            return {'healthy':True}
        pending_calls.append(arguments)
        return {'queued':True}
    driver.client_call = uncertain
    state = pipeline.advance(pipeline.prepare_request(config), driver, 0)
    assert state['status'] == 'pending'
    first_id = state['steps']['02_prepare']['job_id']
    assert len(pending_calls) == 1
    # Complete the already submitted same job, then resume; this invocation must
    # query its result instead of issuing a second prepare request.
    environment['bridge_call'](pending_calls[0])
    driver.client_call = environment['bridge_call']
    state = pipeline.advance(pipeline.prepare_request(config), driver, 0)
    assert state['status'] == 'completed'
    assert state['steps']['02_prepare']['job_id'] == first_id
    ids = [args[args.index('--job-id')+1] for args in environment['calls']]
    assert ids.count(first_id) == 1


def test_reference_drift_blocks_prepared_resume(environment):
    config = request(environment)
    state = pipeline.prepare_request(config)
    Path(state['inputs']['references']['path']).write_bytes(b'changed references')
    with pytest.raises(jobs.ControllerError, match='SHA'):
        pipeline.prepare_request(config)
    assert environment['calls'] == []


def test_implementation_drift_blocks_prepared_resume(environment):
    config = request(environment)
    state = pipeline.prepare_request(config)
    item = next(record for name, record in state['inputs'].items() if name.startswith('implementation_'))
    Path(item['path']).write_bytes(b'changed code')
    with pytest.raises(jobs.ControllerError, match='SHA'):
        pipeline.advance(state, environment['driver'], 0)
    assert environment['calls'] == []


@pytest.mark.parametrize('changes', [
    {'facial_components':{'eyelashes':'wrong_field'}}, {'facial_components':[]},
    {'character_id':12}, {'photo':None}, {'seed':True},
])
def test_invalid_configs_fail_before_cc_preparation(environment, changes):
    config = request(environment, **changes)
    with pytest.raises(jobs.ControllerError):
        pipeline.prepare_request(config)
    assert environment['calls'] == []


@pytest.mark.parametrize('mode,sex', [('photo','female'), ('project','female'), ('photo','male'), ('project','male')])
def test_native_mode_runs_same_geometry_without_any_assembly(environment, mode, sex):
    config = request(environment,mode,sex,appearance_mode='headshot_native')
    state = pipeline.advance(pipeline.prepare_request(config),environment['driver'],0)
    assert state['status']=='completed' and state['appearance_mode']=='headshot_native'
    assert '12_assemble' not in state['steps']
    assert 'assembly_manifest' not in state['offline_outputs']
    assert 'assembly_geometry_policy' not in state['inputs']
    assert not any(key.startswith('assembly_policy_evidence') for key in state['inputs'])
    assert environment['compiled']==[]
    assert ('09_late_bake' in state['steps']) == (sex=='female')
    expected_final = '10_post_bake_roundtrip' if sex=='female' else '08_normalize_geometry'
    report = jobs.read(Path(state['attempt_dir'])/expected_final/'creation_report.json')
    assert state['result_project']==report['saved_project']
    assert 'assembly_manifest' not in jobs.read(Path(state['attempt_dir'])/'creation_result.json')
    review = jobs.read(state['native_appearance_review']['path'])
    assert review['passed'] and review['checks']['body_obj_uv_material_index_layout']
    assert review['baseline_step']==('01_photo' if mode=='photo' else '02_prepare')
    assert jobs.read(Path(state['attempt_dir'])/'creation_result.json')['native_appearance_review']==state['native_appearance_review']
    assert 'native_appearance_after' in state['steps']['11_final_capture']['outputs']
    assert 'no assembly' in state['scope']
    for step in state['steps'].values():
        library = jobs.read(step['library']['path'])
        config = library['character_creation']
        assert config['appearance_mode']=='headshot_native'
        assert not set(config)&{'support_assets','eyelash_diffuse','tongue_diffuse'}
        assert 'base_assembly' not in library


def test_native_preparation_has_no_policy_or_assembly_implementation_dependency(environment, monkeypatch):
    monkeypatch.setattr(pipeline,'POLICY',environment['run']/'absent_policy.json')
    state = pipeline.prepare_request(request(environment,appearance_mode='headshot_native'))
    assert state['appearance_mode']=='headshot_native'
    assert not any('compile_headshot_base_assembly' in key or 'run_headshot_base_assembly' in key for key in state['inputs'])


@pytest.mark.parametrize('components',[{}, {'eye_asset_id':'override'}])
def test_native_rejects_facial_components_before_preparation(environment,components):
    with pytest.raises(jobs.ControllerError,match='cannot select facial_components'):
        pipeline.prepare_request(request(environment,appearance_mode='headshot_native',facial_components=components))
    assert environment['calls']==[]


def test_default_assembled_request_keeps_legacy_fingerprint_and_graph(environment):
    config = request(environment,'project','male')
    normalized = pipeline.normalize_request(config)
    assert 'appearance_mode' not in normalized
    assert pipeline.fingerprint(normalized)==pipeline.fingerprint(config)
    state = pipeline.advance(pipeline.prepare_request(config),environment['driver'],0)
    assert state['appearance_mode']=='assembled'
    assert '12_assemble' in state['steps'] and environment['compiled']


def test_mode_change_cannot_reuse_previous_character_attempt(environment):
    config = request(environment,appearance_mode='headshot_native')
    state = pipeline.prepare_request(config)
    with pytest.raises(jobs.ControllerError,match='different input/config'):
        pipeline.prepare_request(dict(config,appearance_mode='assembled'))
    state['appearance_mode']='assembled'
    with pytest.raises(jobs.ControllerError,match='appearance_mode'):
        environment['driver'].verify_state_inputs(state)


@pytest.mark.parametrize('field', ['material','part','topology'])
def test_native_appearance_rejects_observed_changes(field):
    before, after = native_snapshot(), native_snapshot()
    if field=='material':
        after['materials']['digest']='changed_skin'
    elif field=='part':
        after['parts']['parts'][0]['name']='replacement_eye'
    else:
        after['geometry_topology'][0]['face_indices_sha256']='new_topology'
    review=pipeline.native_appearance_comparison(before,after)
    assert review['passed'] is False and review['mismatches']


def test_native_appearance_ignores_ids_but_discloses_incomplete_observations():
    before, after = native_snapshot(), native_snapshot()
    after['parts']['parts'][0]['id']='reloaded-id'
    after['materials'].update(observation_error_count=1,observation_errors=[{'stage':'opacity','error':'getter failed'}])
    review=pipeline.native_appearance_comparison(before,after)
    assert review['passed'] is True
    assert review['observation_errors']['after']
    assert any('observation errors' in item for item in review['limitations'])
    assert any('not every texture pixel' in item for item in review['limitations'])
    assert review['checks']['body_obj_uv_material_index_layout'] is None


def test_native_appearance_rejects_uv_or_material_layout_changes(tmp_path):
    before, after = tmp_path/'before.obj', tmp_path/'after.obj'
    before.write_text('v 0 0 0\nvt 0.5 0.5\nusemtl Skin\nf 1/1 2/1 3/1\n')
    after.write_text('v 9 9 9\nvt 0.5 0.5\nusemtl Skin\nf 1/1 2/1 3/1\n')
    assert pipeline.native_appearance_comparison(native_snapshot(),native_snapshot(),before,after)['passed']
    after.write_text('v 9 9 9\nvt 0.8 0.5\nusemtl Skin\nf 1/1 2/1 3/1\n')
    assert not pipeline.native_appearance_comparison(native_snapshot(),native_snapshot(),before,after)['passed']


def test_native_mismatch_never_marks_character_completed(environment,monkeypatch):
    compare=pipeline.native_appearance_comparison
    def mismatch(before,after,*args):
        after['materials']['digest']='different'
        return compare(before,after,*args)
    monkeypatch.setattr(pipeline,'native_appearance_comparison',mismatch)
    state=pipeline.prepare_request(request(environment,'project','male',appearance_mode='headshot_native'))
    with pytest.raises(jobs.ControllerError,match='Native appearance changed'):
        pipeline.advance(state,environment['driver'],0)
    assert jobs.read(state['state_path'])['status']=='failed'
    assert jobs.read(state['offline_outputs']['native_appearance_review']['path'])['passed'] is False
    assert not (Path(state['attempt_dir'])/'creation_result.json').exists()


def test_native_completed_resume_verifies_snapshot_without_submission(environment):
    config=request(environment,'photo','male',appearance_mode='headshot_native')
    state=pipeline.advance(pipeline.prepare_request(config),environment['driver'],0)
    count=len(environment['calls'])
    pipeline.advance(pipeline.prepare_request(config),environment['driver'],0)
    assert len(environment['calls'])==count
    Path(state['steps']['01_photo']['outputs']['native_appearance_after']['path']).write_bytes(b'changed')
    with pytest.raises(jobs.ControllerError,match='SHA'):
        pipeline.advance(pipeline.prepare_request(config),environment['driver'],0)


def test_native_photo_selects_optional_repaired_starter_only(environment):
    repaired=environment['photo'].parent/'NATIVE_START.ccProject'
    repaired.write_bytes(b'repaired native support')
    environment['selected']['native_starter_project']=jobs.bind(repaired)
    photo_state=pipeline.prepare_request(request(environment,'photo','female',appearance_mode='headshot_native'))
    assert photo_state['inputs']['selected_starter']==jobs.bind(repaired)
    assert Path(photo_state['inputs']['working_starter']['path']).read_bytes()==b'repaired native support'
    raw_state=pipeline.prepare_request(request(environment,'project','female',appearance_mode='headshot_native'))
    assert 'working_starter' not in raw_state['inputs']
    assert 'selected_starter' not in raw_state['inputs']


def test_assembled_photo_uses_original_starter_when_native_one_exists(environment):
    repaired=environment['photo'].parent/'NATIVE_START.ccProject'
    repaired.write_bytes(b'native support')
    environment['selected']['native_starter_project']=jobs.bind(repaired)
    state=pipeline.prepare_request(request(environment,'photo','male'))
    assert state['inputs']['selected_starter']==environment['selected']['starter_project']
    assert Path(state['inputs']['working_starter']['path']).read_bytes()==b'reference'


def test_native_starter_reference_sha_and_resume_drift_are_rejected(environment):
    repaired=environment['photo'].parent/'NATIVE_START.ccProject'
    repaired.write_bytes(b'native support')
    reference=jobs.bind(repaired)
    environment['selected']['native_starter_project']=reference
    config=request(environment,'photo','male',appearance_mode='headshot_native')
    state=pipeline.prepare_request(config)
    repaired.write_bytes(b'changed source')
    with pytest.raises(jobs.ControllerError,match='SHA'):
        pipeline.prepare_request(config)
    with pytest.raises(jobs.ControllerError,match='SHA'):
        pipeline.prepare_request(dict(config,character_id='bad_starter_sha'))
    assert state['inputs']['selected_starter']['sha256']==reference['sha256']
