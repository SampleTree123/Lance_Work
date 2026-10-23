import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_bind_refresh_geometry_commands_v1 as controller


def fixtures_for(tmp_path,monkeypatch):
    task=tmp_path/'task';task.mkdir();creation=tmp_path/'creation';creation.mkdir()
    monkeypatch.setattr(controller,'TASK',task);monkeypatch.setattr(controller,'CREATION',creation)
    def pin(path):
        p=Path(path);return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    def verified(record,label):
        actual=pin(record['path'])
        if actual['sha256']!=record['sha256']:raise ValueError(label+' hash mismatch')
        return actual
    read=lambda p:json.loads(Path(p).read_text())
    rows=[]
    for identifier in ['CFD40_WF_003','CFD40_LM_002']+['CFD40_AM_%03d'%i for i in range(1,39)]:
        source=tmp_path/(identifier+'.ccProject');source.write_bytes(identifier.encode())
        attempt=creation/identifier/'attempt_001';attempt.mkdir(parents=True)
        result=attempt/'creation_result.json';result.write_text('{}');archive=attempt/'geometry_report.json';archive.write_text('{}')
        rows.append(dict(character_id=identifier,sex='male',creation_result=pin(result),original_project=pin(source),
            archive_inputs=[dict(path=str(archive),available=True,file=pin(archive))],selected_candidates={'eyelashes':{'asset_id':'selected_'+identifier}}))
    operator=task/'offline_WF003_corner_operator_v2';operator.mkdir();(operator/'corner_identity_operator.npz').write_bytes(b'operator');(operator/'corner_operator_evidence.json').write_text('{}')
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(dict(cases=rows)))
    accepted={'passed':True}
    fake=types.SimpleNamespace(REPS={'CFD40_WF_003':'female','CFD40_LM_002':'male'},checked_plan=read,pin=pin,read=read,verified=verified,
        representative_gate=lambda *a:copy.deepcopy(accepted),geometry_fact=lambda record,original:dict(status=read(record['path'])['status'],state=record,result_project=None))
    order=task/'order.json';order.write_text(json.dumps(controller.build(plan,fake)))
    return fake,order,accepted


def test_bind_keeps38_originals_and_selected_assets_without_dispatched_success(tmp_path,monkeypatch):
    batch,path,_=fixtures_for(tmp_path,monkeypatch);order=batch.read(path)
    assert len(order['cases'])==38 and not order['actual_application_dispatched']
    first=order['cases'][0]
    assert first['selected_eyelash']['asset_id']=='selected_CFD40_AM_001'
    assert first['original_project']['path']in first['commands']['geometry_prepare']
    assert '--execute'not in first['commands']['geometry_prepare']
    assert not Path(first['candidate_report']).exists()and not Path(first['geometry_state']).exists()


def test_missing_or_partial_gate_cannot_execute_any_command(tmp_path,monkeypatch):
    batch,path,gate=fixtures_for(tmp_path,monkeypatch);calls=[]
    with pytest.raises(ValueError):controller.advance(path,'CFD40_AM_001',None,execute=True,batch=batch,run=calls.append)
    gate['passed']=False
    with pytest.raises(ValueError):controller.advance(path,'CFD40_AM_001','partial_gate',execute=True,batch=batch,run=calls.append)
    assert calls==[]
    assert controller.advance(path,'CFD40_AM_001',None,batch=batch,run=calls.append)['actual_application_dispatched']is False


def test_one_subject_uses_existing_three_commands_and_pending_blocks_other_subject(tmp_path,monkeypatch):
    batch,path,_=fixtures_for(tmp_path,monkeypatch);order=batch.read(path);person=order['cases'][0];calls=[]
    def run(command):
        calls.append(command)
        if command==person['commands']['candidate']:
            target=Path(person['candidate_report']);target.parent.mkdir(parents=True);target.write_text(json.dumps({'archive_geometry_report':batch.read(order['batch_plan']['path'])['cases'][2]['archive_inputs'][0]['file']}))
        elif command==person['commands']['geometry_prepare']:
            target=Path(person['geometry_state']);target.parent.mkdir(parents=True);target.write_text(json.dumps(dict(character_id=person['candidate_id'],inputs={'original_final_project':person['original_project']},status='prepared',steps={})))
        else:
            target=Path(person['geometry_state']);state=batch.read(target);state.update(status='running',steps={'01_capture':dict(status='pending',job_id='same_job')});target.write_text(json.dumps(state))
    result=controller.advance(path,'CFD40_AM_001','accepted_gate',execute=True,batch=batch,run=run)
    assert len(calls)==3 and result['existing_commands_invoked']==['candidate','geometry_prepare','geometry_advance']
    assert result['geometry']['status']=='running'and not result['full_pipeline_completed']
    with pytest.raises(ValueError):controller.advance(path,'CFD40_AM_002','accepted_gate',execute=True,batch=batch,run=run)
    assert len(calls)==3
    controller.advance(path,'CFD40_AM_001','accepted_gate',execute=True,batch=batch,run=run)
    assert len(calls)==4 and calls[-1]==person['commands']['geometry_advance']


def test_edited_commands_do_not_bypass_frozen_plan(tmp_path,monkeypatch):
    batch,path,_=fixtures_for(tmp_path,monkeypatch);order=batch.read(path);order['cases'][0]['commands']['candidate'].append('--foreign')
    path.write_text(json.dumps(order));calls=[]
    with pytest.raises(ValueError):controller.advance(path,'CFD40_AM_001','accepted_gate',execute=True,batch=batch,run=calls.append)
    assert calls==[]
