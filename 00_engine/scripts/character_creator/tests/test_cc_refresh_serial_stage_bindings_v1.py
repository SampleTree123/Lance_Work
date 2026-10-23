"""Offline glue tests; Bridge calls below are explicit in-memory test fixtures only."""
import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_refresh_serial_stage_bindings_v1 as serial
from cc_character_creation_job_state_v1 import BridgeStepDriver,bind,fingerprint,write,ControllerError

ROOT=Path(__file__).resolve().parents[4]
TASK=ROOT/'00_engine/outputs/character_refresh_20261018_v1'
ORDER=TASK/'batch_geometry_command_bindings_v1.json'


def test_offline_prepare_binds38_same_nine_choices_and_creates_no_runtime_state(tmp_path,monkeypatch):
    runtime=tmp_path/'artifacts';runtime.mkdir();backup=runtime/'actual_fixture_backup.ccProject';backup.write_bytes(b'unit backup fixture')
    real_stage=serial.STAGE;staging=tmp_path/'stage';staging.mkdir()
    for name in('visual_LM002_assembled_v1.json','visual_WF003_assembled_v1.json'):(staging/name).write_bytes((real_stage/name).read_bytes())
    monkeypatch.setattr(serial,'RUNTIME',runtime);monkeypatch.setattr(serial,'STAGE',staging)
    path=tmp_path/'serial_order.json';value=serial.prepare(ORDER,backup,path)
    assert len(value['cases'])==38 and not value['actual_application_dispatched']and not value['accepted']
    assert len({r['selected_eyelash']['asset_id']for r in value['cases']})==9
    assert all(not Path(r['state_path']).exists()and not Path(r['stage_dir']).exists()for r in value['cases'])
    assert serial.checked(path)==value
    assert serial.advance(path,value['cases'][0]['character_id'],None)['status']=='preview_only'
    with pytest.raises(ValueError,match='Actual accepted representative gate'):serial.advance(path,value['cases'][0]['character_id'],None,True)
    assert not(runtime/'batch_serial').exists()
    value['cases'][0]['selected_eyelash']['asset_id']='fake_delicate'
    write(path,value)
    with pytest.raises(ValueError,match='Frozen identity'):serial.checked(path)


@pytest.mark.parametrize('gate',[{}, {'passed':True,'status':'accepted'}, {'schema':'cfd40_refresh_batch_representative_gate_v1','status':'accepted','redness_policy':'excluded_by_user','representatives':[]}])
def test_forged_passed_flags_cannot_open_actual_owner_gate(tmp_path,gate):
    path=tmp_path/'fake_gate.json';write(path,gate)
    with pytest.raises((ValueError,KeyError)):serial.representative_evidence(TASK/'batch_preparation_v7.json',path)


def test_existing_compiler_preserves_frozen_subject_choices_no_redness():
    plan=serial.batch.checked_plan(TASK/'batch_preparation_v7.json')
    # Real asset/compiler reads only, no SDK or Bridge.
    for person in [plan['cases'][0],next(r for r in plan['cases']if r['sex']=='female'and r['character_id']not in serial.batch.REPS)]:
        source=person['original_project'];value=serial.original_prelash_library(person,source,source)['refresh_assembly']
        assert value['redness_policy']=='excluded_by_user'and value['include_redness_layers']is False
        assert value['assets']['eyelashes']['asset_id']==person['selected_candidates']['eyelashes']['asset_id']
        assert value['finalize_editor_closed']is True and value['restore_non_skin_materials']is True


def fixture(tmp_path,client):
    run=tmp_path/'runtime';stage=tmp_path/'stage';bridge=tmp_path/'bridge';run.mkdir();stage.mkdir()
    for name in('results','inbox','processing'):(bridge/name).mkdir(parents=True)
    request=dict(appearance_mode='headshot_native')
    state=dict(character_id='FIXTURE_CASE',request=request,request_fingerprint=fingerprint(request),appearance_mode='headshot_native',
        attempt_dir=str(run/'attempt'),stage_dir=str(stage/'attempt'),state_path=str(run/'attempt/state.json'),inputs={},status='prepared',steps={},facts={})
    Path(state['attempt_dir']).mkdir();Path(state['stage_dir']).mkdir();write(state['state_path'],state)
    driver=BridgeStepDriver(run_root=run,stage_root=stage,bridge_root=bridge,client_call=client)
    return state,driver,bridge


@pytest.mark.parametrize('terminal',['failed','succeeded'])
def test_pending_same_job_query_then_actual_terminal_no_duplicate_dispatch(tmp_path,terminal):
    calls=[]
    def client(arguments):calls.append(arguments);return dict(healthy=True,heartbeat={})if arguments==['health']else dict(queued=True)
    state,driver,bridge=fixture(tmp_path,client)
    library={'diagnostic_mode':'explicit_unit_fixture_only'}
    assert serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)is None
    job=state['steps']['01_prelash']['job_id'];count=len(calls)
    assert serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)is None
    assert len(calls)==count and state['steps']['01_prelash']['job_id']==job
    step=state['steps']['01_prelash']
    if terminal=='succeeded':write(Path(step['output_dir'])/'report.json',dict(success=True,fixture=True))
    write(bridge/'results'/(job+'.json'),dict(job_id=job,command='validate_bodyfit_library',status=terminal,
        result=dict(library_file=step['library']['path'],output_dir=step['output_dir'])))
    if terminal=='failed':
        with pytest.raises(ValueError,match='Actual stage failed'):serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)
        with pytest.raises(ControllerError):serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)
    else:
        assert serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)['fixture']
        state['facts']['prelash_report']=state['steps']['01_prelash']['outputs']['report'];serial.verify_stage_facts(state,driver)
        write(Path(step['output_dir'])/'report.json',dict(success=True,fixture='changed'))
        with pytest.raises(ControllerError):serial.verify_stage_facts(state,driver)
    assert len(calls)==count


def test_uncertain_transport_is_persisted_pending_never_resubmitted(tmp_path):
    calls=[]
    def client(arguments):
        calls.append(arguments)
        if arguments==['health']:return dict(healthy=True,heartbeat={})
        raise OSError('Unit fixture uncertain submission')
    state,driver,bridge=fixture(tmp_path,client)
    library={'diagnostic_mode':'explicit_unit_fixture_only'}
    with pytest.raises(ControllerError,match='uncertain'):serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)
    pending=state['steps']['01_prelash'];job=pending['job_id']
    assert pending['status']=='pending'
    assert serial.stage_tick(state,'01_prelash',library,'report.json',driver,lambda r:None)is None
    assert state['steps']['01_prelash']['job_id']==job and len(calls)==2


def test_other_pending_export_blocks_new_person_without_querying_or_dispatching(tmp_path):
    path=tmp_path/'serial.json';write(path,dict(facts=dict(export_submission_recorded=True),steps={}))
    order=dict(cases=[dict(character_id='OTHER',state_path=str(path),geometry_state=str(tmp_path/'missing'))])
    with pytest.raises(ValueError,match='same pending other-subject export'):serial.other_pending(order,'CURRENT')


def test_capture_success_or_missing_completed_receipt_never_becomes_accepted(tmp_path):
    assert serial.bind_external_completed({'facts':{}},{},None)is None
    with pytest.raises(ValueError,match='actual completed Bridge output'):
        serial.verify_stage_facts(dict(facts=dict(prelash_report={'path':'arbitrary_success.json'}),steps={}),None)


def test_existing_real_male_completed_chain_consumed_without_generating_approval():
    plan=serial.batch.read(TASK/'batch_preparation_v7.json');person=next(r for r in plan['cases']if r['character_id']=='CFD40_LM_002')
    run=serial.RUNTIME
    facts=dict(geometry=person['known_geometry'],prelash_report=bind(run/'LM002_assembly_v1/refresh_partial_report.json'),
        lash_report=bind(run/'delicate_LM002_prelash_combined_v1/delicate_support_restore_report.json'),visual_report=bind(run/'visual_LM002_assembled_v1/refresh_visual_report.json'))
    manifest=TASK/'transfer_manifest_pair_staged_v1.json'
    if not manifest.exists():pytest.skip('Actual completed representative evidence unavailable')
    state=dict(facts=facts)
    result=serial.bind_external_completed(state,person,manifest)
    assert result['character_id']=='CFD40_LM_002'and state['facts']['completed_CC_receipt']
    assert 'accepted'not in state and 'export_preparation'not in state['facts']


def test_export_uncertain_submission_only_queries_existing_prepared_job(tmp_path,monkeypatch):
    calls=[]
    def client(arguments):
        calls.append(arguments)
        if arguments==['health']:return dict(healthy=True,heartbeat={})
        raise OSError('Unit fixture export transport uncertain')
    state,driver,bridge=fixture(tmp_path,lambda a:(_ for _ in()).throw(AssertionError('No primary client expected')))
    other=tmp_path/'export_fixture';other.mkdir();export_state,export_driver,_=fixture(other,client)
    prep_path=tmp_path/'preparation.json';write(prep_path,dict(explicit_unit_fixture=True))
    library=Path(export_state['stage_dir'])/'01_complete_export_library.json';write(library,dict(explicit_unit_fixture=True))
    prep=dict(job_id='UNIT_EXPORT_JOB',library=bind(library),output_dir=str(Path(export_state['attempt_dir'])/'export'))
    state['facts']['export_preparation']=bind(prep_path)
    monkeypatch.setattr(serial.exporter,'checked_preparation',lambda path:(prep,export_state,export_driver))
    monkeypatch.setattr(serial.exporter,'status',lambda path:dict(status='pending',complete_export_verified=False))
    with pytest.raises(OSError,match='uncertain'):serial.export_tick(state,{},None,driver)
    assert state['facts']['export_submission_recorded']is True
    assert export_state['steps'][serial.exporter.STEP]['job_id']=='UNIT_EXPORT_JOB'
    assert serial.export_tick(state,{},None,driver)['status']=='pending'
    assert len(calls)==2 and calls[-1][0]=='validate-bodies'
