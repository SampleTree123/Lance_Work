"""Thin fixed-plan bindings to existing per-person candidate/geometry CLIs.

No batch status/next implementation, scheduler, receipt promotion or CC API.
Bind is offline. Explicit advance requires the existing real representative
CC/export/import/runtime gate, then prepares missing offline inputs and advances
exactly one existing serial geometry step. Pending jobs are never resubmitted.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REPO=Path(__file__).resolve().parents[3]
CC=Path(__file__).resolve().parent
TASK=REPO/'00_engine/outputs/character_refresh_20261018_v1'
CREATION=REPO/'00_engine/outputs/character_creator_bridge/artifacts/headshot_character_creation_20261005_v1'
OWNER=TASK/'refresh_batch_prepare_v1.py'
SCHEMA='cfd40_refresh_geometry_command_bindings_v1'


def owner():
    spec=importlib.util.spec_from_file_location('refresh_batch_existing_owner_v1',OWNER)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def case_binding(person,python=sys.executable):
    identifier=person['character_id']
    if not identifier.startswith('CFD40_')or not all(c.isalnum()or c=='_'for c in identifier):raise ValueError('Safe frozen CFD identity required')
    candidate_id='REFRESH_'+identifier+'_20261018_BATCH_V1'
    attempt=Path(person['creation_result']['path']).parent
    output=TASK/'batch_geometry'/identifier/'offline_candidate_v1'
    report=output/'candidate_report.json';state=CREATION/candidate_id/'attempt_001/repair_state.json'
    operator=TASK/'offline_WF003_corner_operator_v2/corner_identity_operator.npz'
    evidence=TASK/'offline_WF003_corner_operator_v2/corner_operator_evidence.json'
    candidate=[python,str(CC/'cc_native_geometry_repair_candidate_v1.py'),'--source-attempt',str(attempt),'--output',str(output),'--rings','6']
    prepare=[python,str(CC/'run_cc_explicit_corner_fresh_geometry_repair_v3.py'),'--candidate-id',candidate_id,'--sex',person['sex'],
        '--source-project',person['original_project']['path'],'--candidate-report',str(report),'--operator',str(operator),'--operator-evidence',str(evidence)]
    advance=[python,str(CC/'run_cc_explicit_corner_fresh_geometry_repair_v3.py'),'--state',str(state),'--execute','--max-steps','1','--wait-seconds','0']
    return {'character_id':identifier,'sex':person['sex'],'original_project':person['original_project'],'archive_attempt':str(attempt),
        'candidate_id':candidate_id,'candidate_report':str(report),'geometry_state':str(state),
        'commands':{'candidate':candidate,'geometry_prepare':prepare,'geometry_advance':advance},
        'calibration_strategy':'existing_fresh_controller_no_unproven_archive_affine_reuse',
        'selected_eyelash':person['selected_candidates']['eyelashes'],
        'post_geometry_handoff':'existing batch status/next and normal PRELASH runner; generic selected-nine-lash adapter still required; no Delicate substitution',
        'full_pipeline_execution_supported':False}


def verify_subject(person,batch):
    batch.verified(person['original_project'],'per-person original final')
    batch.verified(person['creation_result'],'per-person archive result')
    for row in person['archive_inputs']:
        if not row.get('available'):raise ValueError('Required subject photo/target/topology archive absent')
        batch.verified(row['file'],'per-person archive target input')


def build(plan_path,batch=None,verify_subjects=True):
    batch=batch or owner();plan=batch.checked_plan(plan_path)
    rows=[case_binding(p)for p in plan['cases']if p['character_id']not in batch.REPS]
    if len(rows)!=38:raise ValueError('Exactly remaining38 declared subjects required')
    if verify_subjects:
        for person in plan['cases']:
            if person['character_id']not in batch.REPS:verify_subject(person,batch)
    dependencies={name:batch.pin(CC/name)for name in('cc_bind_refresh_geometry_commands_v1.py','cc_native_geometry_repair_candidate_v1.py',
        'run_cc_explicit_corner_fresh_geometry_repair_v3.py','run_cc_fresh_final_geometry_repair_v1.py','run_cc_fresh_final_corner_repair_v2.py',
        'cc_lash_corner_operator_v2.py','cc_headshot_geometry_solver_v1.py','cc_character_creation_job_state_v1.py')}
    dependencies['batch_owner']=batch.pin(OWNER)
    operator=TASK/'offline_WF003_corner_operator_v2/corner_identity_operator.npz';evidence=operator.with_name('corner_operator_evidence.json')
    return {'schema':SCHEMA,'status':'offline_bound_not_dispatched','batch_plan':batch.pin(plan_path),'python_executable':sys.executable,
        'implementation_pins':dependencies,'operator':batch.pin(operator),'operator_evidence':batch.pin(evidence),'cases':rows,
        'execution_gate':'Reuse existing representative_gate: both full CC/export/sharedSkeleton import/runtime accepted; missing/partial gate forbids advance',
        'actual_application_dispatched':False,'full_pipeline_execution_supported':False,
        'calibration_reuse':'WF/LM sample prepared-source SHA differs from retained-final; no strict equivalence proven, existing fresh mode selected',
        'notes':['No prepare/bake or female proportion double-bake is introduced.','Existing batch prepare/status/next remains authority.',
            'Nine-preset inventory/style/sourcechain runner remains separate work; do not substitute all choices with Delicate.',
            'The existing geometry prepare pins then-current Bridge dispatcher dependencies. This offline order is not a completed repair state.']}


def checked(order_path,batch=None):
    batch=batch or owner();value=batch.read(order_path)
    if value.get('schema')!=SCHEMA or value.get('python_executable')!=sys.executable:raise ValueError('Exact local geometry work order required')
    batch.verified(value['batch_plan'],'frozen batch plan')
    for pin in list(value['implementation_pins'].values())+[value['operator'],value['operator_evidence']]:batch.verified(pin,'bound existing implementation/operator')
    expected=build(value['batch_plan']['path'],batch,verify_subjects=False)
    if value!=expected:raise ValueError('Command bindings differ from current exact frozen plan')
    return value,batch


def pending_other_case(order,current,batch):
    pending=[]
    for person in order['cases']:
        path=Path(person['geometry_state'])
        if person['character_id']==current or not path.is_file():continue
        state=batch.read(path)
        for name,step in state.get('steps',{}).items():
            if step.get('status')=='pending':pending.append(dict(character_id=person['character_id'],step=name,job_id=step.get('job_id')))
    return pending


def run_command(command):
    result=subprocess.run(command,check=True,capture_output=True,text=True,encoding='utf-8')
    return result.stdout


def advance(order_path,identifier,gate_path,*,execute=False,batch=None,run=run_command):
    order,batch=checked(order_path,batch)
    matches=[r for r in order['cases']if r['character_id']==identifier]
    if len(matches)!=1:raise ValueError('Exactly one remaining frozen identity required')
    person=matches[0]
    if not execute:return {'character_id':identifier,'actual_application_dispatched':False,'commands':person['commands'],'scope':'command preview only'}
    if not gate_path:raise ValueError('Existing actual accepted representative gate is required before executing any bound commands')
    plan=batch.checked_plan(order['batch_plan']['path']);gate=batch.representative_gate(order['batch_plan']['path'],plan,gate_path)
    if not gate.get('passed'):raise ValueError('Representative gate is not accepted')
    original=next(p for p in plan['cases']if p['character_id']==identifier)
    verify_subject(original,batch)
    from cc_character_creation_job_state_v1 import controller_lock
    with controller_lock(TASK/'batch_geometry'):
        active=pending_other_case(order,identifier,batch)
        if active:raise ValueError('Query existing other-subject pending job before new subject: '+str(active))
        calls=[]
        report=Path(person['candidate_report']);state=Path(person['geometry_state'])
        if not report.is_file():run(person['commands']['candidate']);calls.append('candidate')
        else:
            candidate=batch.read(report)
            expected=next(p for p in plan['cases']if p['character_id']==identifier)
            archive=next(r['file']for r in expected['archive_inputs']if Path(r['path']).name=='geometry_report.json')
            if batch.verified(candidate['archive_geometry_report'],'candidate subject archive')!=batch.verified(archive,'frozen subject archive'):
                raise ValueError('Existing candidate belongs to another source')
        if not state.is_file():run(person['commands']['geometry_prepare']);calls.append('geometry_prepare')
        actual=batch.read(state)
        if actual['character_id']!=person['candidate_id']or batch.verified(actual['inputs']['original_final_project'],'state original')!=batch.verified(person['original_project'],'frozen original'):
            raise ValueError('Existing geometry state belongs to another source')
        if actual['status']!='completed':run(person['commands']['geometry_advance']);calls.append('geometry_advance')
        result=batch.geometry_fact(batch.pin(state),person['original_project'])
        return {'character_id':identifier,'gate':gate,'existing_commands_invoked':calls,'geometry':result,
            'full_pipeline_completed':False,'scope':'Only existing candidate/fresh geometry pipeline; pending same job is queried, never retried. Existing batch receipts/status owns next stage.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--action',choices=('bind','advance'),required=True)
    parser.add_argument('--plan');parser.add_argument('--output');parser.add_argument('--order');parser.add_argument('--character-id');parser.add_argument('--gate');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.action=='bind':
        if not args.plan or not args.output or args.execute:parser.error('Offline bind requires plan/output, never --execute')
        path=Path(args.output)
        if path.exists():raise ValueError('Refuse to replace existing work order')
        value=build(args.plan);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(status=value['status'],cases=len(value['cases']),output=str(path.resolve())),indent=2))
    else:
        if not args.order or not args.character_id:parser.error('Advance requires order and explicit character-id')
        print(json.dumps(advance(args.order,args.character_id,args.gate,execute=args.execute),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
