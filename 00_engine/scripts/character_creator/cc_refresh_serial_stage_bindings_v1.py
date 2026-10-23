"""Single-case serial glue over existing refresh stage owners. No batch scheduler.

prepare is offline. advance --execute checks actual representative evidence;
pending is read only against the same recorded job; failed work is never rebuilt.
CC completed receipts and source-specific visual/704 approvals are external inputs.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

REPO=Path(__file__).resolve().parents[3]
CC=Path(__file__).resolve().parent
RUN=REPO/'00_engine/outputs/character_refresh_20261018_v1'
RUNTIME=REPO/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1'
STAGE=CC/'runtime_staging/character_refresh_20261018_v1'
SCHEMA='cfd40_refresh_serial_stage_bindings_v1'
sys.path.insert(0,str(RUN))
import cc_bind_refresh_geometry_commands_v1 as geometry
import refresh_batch_prepare_v1 as batch
import cc_refresh_complete_export_v1 as exporter
from cc_character_creation_job_state_v1 import BridgeStepDriver, bind, fingerprint, read, verify, write, controller_lock, bridge_cli


def dependency_paths():
    return [Path(__file__),Path(geometry.__file__),Path(batch.__file__),Path(exporter.__file__),
        RUN/'compile_transfer_manifest_v1.py',RUN/'ue_refresh_representative_import_v1.py',RUN/'ue_refresh_eyelash_followers_v1.py',
        STAGE/'visual_LM002_assembled_v1.json',STAGE/'visual_WF003_assembled_v1.json',RUN/'eyelash_nine_historical_contract_reference.json',
        *(CC/name for name in ('cc_character_creation_job_state_v1.py','run_headshot_base_assembly_v1.py','cc_validate_body_reconstruction.py',
            'cc_compile_character_refresh_v1.py','cc_run_character_refresh_v1.py','cc_refresh_closed_assembly_v1.py',
            'cc_probe_registered_lash_prelash_v1.py','cc_refresh_registered_lash_contract_v1.py','cc_refresh_registered_lash_pixels_v1.py',
            'cc_refresh_generic_prelash_source_chain_v1.py','cc_support_affine_runtime_v1.py','cc_support_topology_runtime_inverse_v1.py',
            'cc_refresh_visual_probe_v1.py'))]


def prepare(order_path,backup_project,output):
    order,_=geometry.checked(order_path);plan=batch.checked_plan(order['batch_plan']['path'])
    backup=bind(backup_project)
    if not Path(backup['path']).is_relative_to(RUNTIME)or Path(backup['path']).suffix.lower()!='.ccproject':raise ValueError('Explicit real immutable session backup under refresh artifacts required')
    rows=[]
    for person in order['cases']:
        identifier=person['character_id'];frozen=next(r for r in plan['cases']if r['character_id']==identifier)
        rows.append(dict(character_id=identifier,sex=frozen['sex'],selected_eyelash=frozen['selected_candidates']['eyelashes'],
            geometry_state=person['geometry_state'],geometry_commands=person['commands'],
            state_path=str(RUNTIME/'batch_serial'/identifier/'attempt_001/serial_state.json'),
            stage_dir=str(STAGE/'batch_serial'/identifier/'attempt_001'),
            commands=dict(advance=[sys.executable,str(Path(__file__)),'--action','advance','--order',str(Path(output).resolve()),
                '--character-id',identifier,'--gate','<REAL_ACCEPTED_REPRESENTATIVE_GATE.json>','--execute']),
            external_handoff='After actual four images: root source-specific visual/704 approval + completed CC receipt and compiled transfer manifest; never inferred.'))
    value=dict(schema=SCHEMA,status='offline_prepared_not_dispatched',geometry_order=bind(order_path),batch_plan=order['batch_plan'],session_backup=backup,
        implementation_pins=[bind(p)for p in dependency_paths()],cases=rows,stage_order=['geometry','normal_prelash','selected_registered_lash','four_image_capture','external_completed_CC_receipt','complete_export'],
        actual_application_dispatched=False,accepted=False,batch40_accepted=False,automatic_next_subject=False,
        gate='Existing representative_gate validates both actual CC/export/import/runtime and visual evidence; no force/skip/accepted override.',
        ownership='Assembly Technical experimental; existing stage owners retain geometry/transfer and acceptance semantics.')
    if Path(output).exists():raise ValueError('Use existing order or a new independent preparation; never overwrite')
    write(output,value);return value


def checked(path):
    value=read(path)
    if value.get('schema')!=SCHEMA or len(value.get('cases',[]))!=38:raise ValueError('Exact offline remaining38 order required')
    for p in value['implementation_pins']+[value['geometry_order'],value['batch_plan'],value['session_backup']]:verify(p,'serial frozen input')
    if {Path(p['path']).resolve()for p in value['implementation_pins']}!={p.resolve()for p in dependency_paths()}:raise ValueError('All thin-stage dependencies must stay pinned')
    old,_=geometry.checked(value['geometry_order']['path'])
    if value['batch_plan']!=old['batch_plan']:raise ValueError('Serial order must retain exact frozen geometry batch plan')
    backup=Path(value['session_backup']['path'])
    if not backup.is_relative_to(RUNTIME)or backup.suffix.lower()!='.ccproject':raise ValueError('Protected session backup root changed')
    if [r['character_id']for r in value['cases']]!=[r['character_id']for r in old['cases']]:raise ValueError('Do not add/remove/reorder frozen38')
    for row,prior in zip(value['cases'],old['cases']):
        if any(row[k]!=prior[k]for k in ('character_id','sex','selected_eyelash','geometry_state'))or row['geometry_commands']!=prior['commands']:raise ValueError('Frozen identity/choice/geometry command changed')
        identifier=row['character_id']
        if Path(row['state_path']).resolve()!=RUNTIME/'batch_serial'/identifier/'attempt_001/serial_state.json'or Path(row['stage_dir']).resolve()!=STAGE/'batch_serial'/identifier/'attempt_001':raise ValueError('Independent fixed serial paths required')
    return value


def representative_evidence(plan_path,gate_path):
    """Call the existing actual CC/export/import/runtime/visual owner, never a flag."""
    if not gate_path:raise ValueError('Actual accepted representative gate required, never a force flag')
    plan=batch.checked_plan(plan_path)
    answer=batch.representative_gate(plan_path,plan,gate_path)
    if answer.get('passed')is not True:raise ValueError('Representative gate still closed')
    return answer


def new_state(order_path,order,row):
    folder=Path(row['state_path']).parent;stage=Path(row['stage_dir'])
    if folder.exists()or stage.exists():raise ValueError('Unbound existing attempt/staging requires inspection, not rebuilding')
    request=dict(character_id=row['character_id'],serial_order=bind(order_path),appearance_mode='headshot_native')
    inputs={str(i):p for i,p in enumerate(order['implementation_pins']+[order['geometry_order'],order['batch_plan'],order['session_backup']])}
    state=dict(character_id=row['character_id'],sex=row['sex'],request=request,request_fingerprint=fingerprint(request),appearance_mode='headshot_native',
        attempt_dir=str(folder),stage_dir=str(stage),state_path=row['state_path'],inputs=inputs,status='prepared',steps={},facts={})
    folder.mkdir(parents=True);stage.mkdir(parents=True);write(row['state_path'],state);return state


def mirror(record,state,label):
    verify(record,'actual stage source');path=Path(state['stage_dir'])/(label+'.ccProject')
    if path.exists():
        if bind(path)['sha256']!=record['sha256']:raise ValueError('Existing staged source changed')
    else:shutil.copyfile(record['path'],path)
    value=bind(path)
    if value['sha256']!=record['sha256']:raise ValueError('Source mirror mismatch')
    return value


def original_prelash_library(person,source,backup):
    import cc_compile_character_refresh_v1 as appearance
    choices=person['selected_candidates']
    request=dict(character_id=person['character_id'],sex=person['sex'],seed=person['seed'],source_project=source,current_scene_backup=backup,
        skin_asset_id=choices['skin']['asset_id'],skin_selection_reason=person['skin_reason'],eye_asset_id=choices['eyes']['asset_id'],eyelash_asset_id=choices['eyelashes']['asset_id'],
        redness_policy='excluded_by_user',include_redness_layers=False,verify_layer_persistence=True,capture_pixel_evidence=True,restore_non_skin_materials=True,finalize_editor_closed=True)
    value=appearance.compile_request(request)
    for slot in ('eyes','eyelashes','makeup_eyebrow'):
        actual=value['refresh_assembly']['assets'][slot];expected=choices[slot]
        if batch.verified(actual,'compiled choice')!=batch.verified(expected,'frozen choice')or actual.get('asset_id')!=expected.get('asset_id'):raise ValueError('Compiler may not redraw frozen assets or seed')
    if batch.verified(value['refresh_assembly']['assets']['skin'],'compiled skin')!=batch.verified(choices['skin']['source'],'frozen photo skin'):raise ValueError('Explicit photo skin changed')
    value.update(schema_version=1,eye_snapshot_mode='transforms_only',presets=[dict(preset_id=('F02'if person['sex']=='female'else'M02')+'_Average',sex=person['sex'],base_avatar=source,source_project=source)])
    return value


def completed_report(state,step_id,filename,driver):
    step=state['steps'][step_id];driver.verify_completed_step(state,step)
    report_pin=step['outputs']['report'];verify(report_pin,'stage report');return read(report_pin['path'])


def stage_tick(state,step_id,library,filename,driver,validate):
    # Reusing submit_step on an existing pending/completed entry never dispatches.
    step=driver.submit_step(state,step_id,library,Path(state['attempt_dir'])/step_id)
    if step['status']=='completed':return completed_report(state,step_id,filename,driver)
    driver.wait_step(state,step_id,0)
    if step['status']=='pending':return None
    if step['status']=='failed':raise ValueError('Actual stage failed; preserve original attempt/evidence and inspect, no automatic rebuilding')
    report_path=Path(step['output_dir'])/filename;report=read(report_path)
    if report.get('success')is not True:raise ValueError('Bridge success without actual stage success')
    validate(report)
    outputs={'report':report_path}
    for key in ('saved_project','candidate'):
        if report.get(key):outputs[key]=report[key]
    driver.mark_step_complete(state,step_id,outputs);state['status']='prepared';driver.persist(state)
    return report


def assert_lash(report,person,source):
    if (report.get('character_id')!=person['character_id']or report.get('sex')!=person['sex']or report.get('source_project')!=source
            or not all(report.get(k)is True for k in ('restored_source','source_unchanged','geometry_restore_completed','material_pixels_verified'))
            or report.get('eyelash_asset',{}).get('asset_id')!=person['selected_candidates']['eyelashes']['asset_id']):raise ValueError('Own selected lash/source complete protected stage required')
    if any(not x['original_protection_passed']for x in report['steps']if not x['pending_restoration_supports']):raise ValueError('Final geometry protection failed')
    for check in report['pixel_checks']:
        if not check['passed']:raise ValueError('Protected pixels failed')
    verify(report['eyelash_parts_evidence']['capture'],'actual added parts');verify(report['saved_project'],'actual saved selected-lash product')


def assert_visual(report,source):
    from cc_refresh_visual_probe_v1 import png_dimensions
    if report['source_project']!=source or not report.get('source_unchanged')or not report.get('restoration',{}).get('success'):raise ValueError('Actual same-source visual/restoration required')
    if {(x['pose'],x['view'])for x in report['captures']}!={('neutral','front'),('neutral','side'),('blink','front'),('blink','side')}:raise ValueError('Four actual required images')
    for row in report['captures']:verify(row['image'],'actual captured image');png_dimensions(row['image']['path'])


def other_pending(order,current):
    for row in order['cases']:
        if row['character_id']==current:continue
        for path in (Path(row['state_path']),Path(row['geometry_state'])):
            if path.exists():
                state=read(path)
                if state.get('facts',{}).get('export_submission_recorded')and not state['facts'].get('export_inventory'):raise ValueError('Query same pending other-subject export before new work: '+row['character_id'])
                if any(s.get('status')in('pending','succeeded')for s in state.get('steps',{}).values()):raise ValueError('Query same pending other-subject job before new work: '+row['character_id'])


def bind_external_completed(state,person,manifest_path):
    if not manifest_path:return None
    # Existing compiler/export contract remains owner. This adds exact local
    # products and real root review links; never writes an accepted receipt.
    record=exporter.character_from_plan(manifest_path,person['character_id']);receipt=read(record['assembly_result']['path'])
    lash=read(state['facts']['lash_report']['path']);prelash=read(state['facts']['prelash_report']['path'])
    batch.same(receipt['source_project'],person['original_project'],'completed original')
    batch.same(receipt['geometry_project'],state['facts']['geometry']['result_project'],'completed geometry')
    batch.same(receipt['prelash_project'],prelash['candidate'],'completed PRELASH');batch.selected_lash_fact(receipt,person)
    if batch.verified(receipt['result_project'],'completed staged final')['sha256']!=lash['saved_project']['sha256']:raise ValueError('Completed receipt must use actual selected-lash final bytes')
    if receipt['eyelash_parts_evidence']!=lash['eyelash_parts_evidence']:raise ValueError('Completed receipt must retain exact actual added-parts capture')
    batch.same(receipt['visual_report'],state['facts']['visual_report'],'completed actual four images')
    approval=read(batch.verified(receipt['root_visual_approval'],'external root source review')['path'])
    if (approval.get('schema')!='cfd40_refresh_root_export_source_review_v1'or approval.get('character_id')!=person['character_id']
            or approval.get('reviewer')!='root_agent'or not str(approval.get('decision','')).startswith('approved_for_')
            or batch.verified(approval['source_project'],'reviewed exact final')['sha256']!=lash['saved_project']['sha256']):raise ValueError('Explicit real root source-specific review required; no automatic visual acceptance')
    batch.same(approval['visual_report'],state['facts']['visual_report'],'reviewed actual image report')
    images=read(state['facts']['visual_report']['path'])['captures']
    if {(r['pose'],r['view'],batch.verified(r['image'],'root actual image')['sha256'])for r in approval['reviewed_images']}!={(r['pose'],r['view'],r['image']['sha256'])for r in images}:raise ValueError('Root must bind all four actual same-source images')
    exception=read(batch.verified(receipt['body_geometry_exception'],'source-specific named native704 approval')['path'])
    if (exception.get('schema')!='cfd40_refresh_source_asset_native704_exception_v1'or exception.get('character_id')!=person['character_id']or not exception.get('name')):raise ValueError('Named source-specific native704 exception required')
    batch.same(exception['basis_report'],state['facts']['lash_report'],'704 actual basis');batch.same(exception['source_project'],prelash['candidate'],'704 source')
    batch.same(exception['eyelash_asset'],person['selected_candidates']['eyelashes'],'704 selected asset')
    batch.same(exception['authorization'],receipt['root_visual_approval'],'704 actual source approval')
    batch.same(exception['geometry_project'],state['facts']['geometry']['result_project'],'704 actual geometry')
    if batch.verified(exception['result_project'],'704 actual result')['sha256']!=lash['saved_project']['sha256']:raise ValueError('704 approval names different result bytes')
    measurement=next(r['body']['lash_measurement']for r in lash['steps']if r['phase']=='reloaded_native_export')
    if (exception.get('magnitude_bound_registered')is not True or exception.get('native_lash_count')!=704
            or exception.get('indices')!=lash['native_lash_partition']['native_lash_indices']
            or exception.get('protected_nonlash_body_count')!=13460 or exception.get('protected_nonlash_maximum_mm')!=.002
            or exception.get('measured_local_max_mm')!=measurement['local_max_mm']or exception.get('measured_world_max_mm')!=measurement['world_max_mm']
            or not isinstance(exception.get('bounded_upper_limit_mm'),(float,int))
            or not max(measurement['local_max_mm'],measurement['world_max_mm'])<=exception['bounded_upper_limit_mm']<float('inf')):raise ValueError('704 named approval must bind actual measured native partition and explicit finite source-specific bound')
    state['facts']['completed_transfer_manifest']=bind(manifest_path);state['facts']['completed_CC_receipt']=record['assembly_result']
    return record


def export_tick(state,person,manifest_path,driver):
    existing=state['facts'].get('export_preparation')
    if not existing:
        if not bind_external_completed(state,person,manifest_path):return dict(status='awaiting_external_completed_CC_receipt',accepted=False)
        job='BATCH_'+person['character_id'].removeprefix('CFD40_')+'_V1'
        prep=exporter.prepare(manifest_path,person['character_id'],job)
        path=RUN/'representative_exports'/job/'preparation.json';state['facts']['export_preparation']=bind(path);driver.persist(state)
    else:path=Path(existing['path']);verify(existing,'existing export preparation')
    prep,export_state,export_driver=exporter.checked_preparation(path)
    if not state['facts'].get('export_submission_recorded'):
        if exporter.STEP in export_state['steps']:raise ValueError('Unbound existing export step requires inspection')
        # Exact prepared library/job are adopted BEFORE the existing Bridge CLI;
        # an uncertain return remains pending and can only be queried.
        health=export_driver.client_call(['health'])
        if not health.get('healthy')or(health.get('heartbeat')or{}).get('active_job_id'):raise ValueError('CC unavailable or busy')
        if any(list((export_driver.bridge_root/a).glob('*.json'))for a in('inbox','processing')):raise ValueError('Other queued CC work exists')
        state['facts']['export_submission_recorded']=True;driver.persist(state)
        export_state['steps'][exporter.STEP]=dict(step_id=exporter.STEP,status='pending',job_id=prep['job_id'],library=prep['library'],output_dir=prep['output_dir'])
        export_state['status']='pending';export_driver.persist(export_state)
        export_driver.client_call(['validate-bodies','--library-file',prep['library']['path'],'--output-dir',prep['output_dir'],'--job-id',prep['job_id'],'--confirm-scene-replace','--auto-dismiss-undo-warning','--no-wait'])
    answer=exporter.status(path)
    if answer.get('status')=='failed':
        state['status']='failed';driver.persist(state);raise ValueError('Actual complete export failed; no new job/attempt automatically')
    if answer.get('complete_export_verified'):
        state['facts']['export_inventory']=answer['export_inventory'];state['status']='completed';driver.persist(state)
    return answer


def verify_stage_facts(state,driver):
    for step_id,fact in (('01_prelash','prelash_report'),('02_lash','lash_report'),('03_visual','visual_report')):
        if fact in state['facts']:
            step=state['steps'].get(step_id)
            if not step or step.get('status')!='completed'or step.get('outputs',{}).get('report')!=state['facts'][fact]:raise ValueError('Stage fact is not its actual completed Bridge output')
            driver.verify_completed_step(state,step)


def advance(order_path,identifier,gate_path,execute=False,completed_manifest=None):
    order=checked(order_path);matches=[r for r in order['cases']if r['character_id']==identifier]
    if len(matches)!=1:raise ValueError('Explicit remaining38 identity required')
    row=matches[0]
    if not execute:return dict(character_id=identifier,status='preview_only',state_path=row['state_path'],application_dispatched=False,stage_order=order['stage_order'])
    gate=representative_evidence(order['batch_plan']['path'],gate_path)
    with controller_lock(RUNTIME/'batch_serial'):
        other_pending(order,identifier)
        state=read(row['state_path'])if Path(row['state_path']).exists()else new_state(order_path,order,row)
        driver=BridgeStepDriver(run_root=RUNTIME,stage_root=STAGE);driver.verify_state_inputs(state)
        if state['request']['serial_order']!=bind(order_path)or state['character_id']!=identifier:raise ValueError('Existing state belongs to different immutable order')
        if state['status']=='failed':raise ValueError('Failed attempt retained; no automatic rebuilding')
        verify_stage_facts(state,driver)
        if state['status']=='completed':
            if not state['facts'].get('export_preparation'):raise ValueError('Completed flag without actual export preparation')
            verify(state['facts']['export_preparation'],'actual completed export input')
            actual=exporter.status(state['facts']['export_preparation']['path'])
            if actual.get('complete_export_verified')is not True or actual.get('export_inventory')!=state['facts'].get('export_inventory'):raise ValueError('Completed flag without actual verified same export')
            return dict(status='complete_CC_export_not_UE_accepted',facts=state['facts'])
        person=next(r for r in batch.checked_plan(order['batch_plan']['path'])['cases']if r['character_id']==identifier)
        if state['facts'].get('geometry'):
            actual=batch.geometry_fact(bind(row['geometry_state']),person['original_project'])
            if actual!=state['facts']['geometry']or not actual.get('result_project'):raise ValueError('Geometry fact differs from actual completed same-source state')
        try:
            if 'geometry'not in state['facts']:
                gpath=Path(row['geometry_state'])
                if gpath.exists()and read(gpath).get('status')=='failed':raise ValueError('Existing geometry failed; do not recreate')
                result=geometry.advance(order['geometry_order']['path'],identifier,gate_path,execute=True)
                if not result['geometry'].get('result_project'):return dict(status='geometry_same_state_pending',geometry=result['geometry'])
                state['facts']['geometry']=result['geometry'];driver.persist(state);return dict(status='geometry_numeric_complete',next='normal_prelash')
            source=mirror(state['facts']['geometry']['result_project'],state,'GEOMETRY_INPUT')
            if 'prelash_report'not in state['facts']:
                existing=state['steps'].get('01_prelash')
                library=read(existing['library']['path'])if existing else original_prelash_library(person,source,order['session_backup'])
                def valid(r):
                    if r.get('status')!='prelash_checkpoint_validated_not_final'or not r.get('stage_validated')or r['config']['character_id']!=identifier:raise ValueError('Actual same-case normal PRELASH required')
                r=stage_tick(state,'01_prelash',library,'refresh_partial_report.json',driver,valid)
                if r is not None:state['facts']['prelash_report']=state['steps']['01_prelash']['outputs']['report'];driver.persist(state)
                return dict(status='normal_prelash_complete'if r else'same_prelash_job_pending')
            if 'lash_report'not in state['facts']:
                import cc_probe_registered_lash_prelash_v1 as registered
                path=Path(state['stage_dir'])/'selected_lash_prepared.json'
                if not path.exists():registered.prepare(state['facts']['prelash_report']['path'],'BATCH_'+identifier+'_LASH_V1',str(Path(state['attempt_dir'])/'02_lash'),str(path))
                library=read(path);expected=read(state['facts']['prelash_report']['path'])['candidate']
                r=stage_tick(state,'02_lash',library,'registered_lash_support_restore_report.json',driver,lambda r:assert_lash(r,person,expected))
                if r is not None:state['facts']['lash_report']=state['steps']['02_lash']['outputs']['report'];driver.persist(state)
                return dict(status='selected_lash_complete'if r else'same_selected_lash_job_pending')
            product=read(state['facts']['lash_report']['path'])['saved_project']
            if 'visual_report'not in state['facts']:
                existing=state['steps'].get('03_visual')
                if existing:template=read(existing['library']['path'])
                else:
                    template=read(STAGE/('visual_'+('LM002'if person['sex']=='male'else'WF003')+'_assembled_v1.json'))
                    template['presets']=[dict(preset_id=('M02'if person['sex']=='male'else'F02')+'_Average',sex=person['sex'],base_avatar=source,source_project=source)]
                    template['refresh_visual_probe'].update(case_id='BATCH_'+identifier+'_VISUAL_V1',sex=person['sex'],source_project=product)
                r=stage_tick(state,'03_visual',template,'refresh_visual_report.json',driver,lambda r:assert_visual(r,product))
                if r is not None:state['facts']['visual_report']=state['steps']['03_visual']['outputs']['report'];state['facts']['review_ready_staged_final']=mirror(product,state,'ASSEMBLED_EXPORT_INPUT');driver.persist(state)
                return dict(status='four_images_ready_external_root_review_required'if r else'same_visual_job_pending',visual_accepted=False)
            result=export_tick(state,person,completed_manifest,driver)
            return dict(character_id=identifier,gate=gate,export=result,full_CC_complete=state['status']=='completed',UE_accepted=False,published=False)
        except Exception as error:
            # Uncertain submissions remain pending; never turn transport doubt
            # into a reset/new attempt. Actual failed or invalid receipts halt.
            gpath=Path(row['geometry_state']);gpending=gpath.exists()and any(s.get('status')=='pending'for s in read(gpath).get('steps',{}).values())
            pending=gpending or any(s.get('status')=='pending'for s in state['steps'].values())or state['facts'].get('export_submission_recorded')and not state['facts'].get('export_inventory')
            state['last_error']=str(error)
            if not pending:state['status']='failed'
            driver.persist(state);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--action',choices=('prepare','advance'),required=True)
    parser.add_argument('--geometry-order');parser.add_argument('--session-backup');parser.add_argument('--output');parser.add_argument('--order');parser.add_argument('--character-id');parser.add_argument('--gate');parser.add_argument('--execute',action='store_true');parser.add_argument('--completed-transfer-manifest')
    args=parser.parse_args()
    if args.action=='prepare':
        if not all((args.geometry_order,args.session_backup,args.output))or args.execute:parser.error('Offline prepare requires geometry-order/session-backup/output, never execute')
        value=prepare(args.geometry_order,args.session_backup,args.output);value=dict(status=value['status'],people=len(value['cases']),output=args.output,application_dispatched=False)
    else:
        if not args.order or not args.character_id:parser.error('Advance requires existing order and explicit character-id')
        value=advance(args.order,args.character_id,args.gate,args.execute,args.completed_transfer_manifest)
    print(json.dumps(value,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
