"""Survey merge stays observational for root-chosen/rendered sites; no UE calls."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_primary_scene_samples_v1 as builder
import merge_primary_scene_surveys_v1 as merge


@pytest.fixture
def setup(tmp_path):
    run=tmp_path/'run'
    inventory=tmp_path/'inventory.json'
    scenes=[{'id':'existing_'+str(i),'map_path':'/Game/Scenes/Test/Map_'+str(i),
             'package':'Test','primary':True} for i in range(26)]
    builder.write(inventory,{'scenes':scenes})
    path=Path(builder.initialize_catalog(inventory,run=run)['catalog'])
    source=tmp_path/'source.json'
    source.write_text('{}',encoding='utf-8')
    return run,path,source


def report(setup,name,count,position=(1.,2.,3.),*,site_index=0,yaw=0.,partial=False):
    run,path,source=setup
    site=builder.read(path)['sites'][site_index]
    clear='no_conflict_detected_at_sampled_proxies'
    document={'schema':'all_primary_scene_site_survey_v1','status':'complete','map':site['map'],
        'source_pins':[{'path':str(source),'sha256':builder.sha(source)}],
        'site':{'position':{'x':99.,'y':99.,'z':99.}},
        'full_attempts':[{'candidate':{'position':list(position),'yaw':yaw,'score':0.},
            'summary':{'matrix_combinations':1260,'sample_items_completed':1 if partial else 27907,
                'total_sample_items':27907,'full_matrix_sampled':True,
                'no_proxy_conflict_combinations':count,'suspected_conflict_combinations':1260-count,
                'unmeasured_visibility_samples':0},
            'combinations':[{'assessment':clear if i<count else 'suspected_conflict'} for i in range(1260)],
            'confirmed_exclusions':[{'not':'automatically adopted'}]}],
        'confirmed_exclusions':[{'not':'automatically adopted'}]}
    output=run/'surveys'/(name+'.json')
    builder.write(output,document)
    return output


def select_root(setup,position=(9.,8.,7.),yaw=90.):
    _,path,_=setup
    catalog=builder.read(path)
    site=catalog['sites'][0]
    site.update(position=dict(zip(('x','y','z'),position)),yaw=yaw,exposure_compensation=2.,
                exclusions=[{'camera_id':'front_full'}],revision='root_v7',location_label='root chosen')
    catalog['source_pins']=[{'root_metadata':'must remain untouched'}]
    builder.write(path,catalog)
    return copy.deepcopy(site),catalog['source_inventory']


def test_best_full_count_populates_only_unselected_and_never_creates_exclusions(setup):
    run,path,_=setup
    report(setup,'first',1240,(1.,2.,3.))
    best=report(setup,'best',1258,(4.,5.,6.))
    report(setup,'latest_but_worse',1249,(7.,8.,9.))
    result=merge.merge_surveys(path,run=run)
    catalog=builder.read(path)
    assert result['new_points']==1 and len(catalog['sites'])==26
    site=catalog['sites'][0]
    assert site['position']=={'x':4.,'y':5.,'z':6.}
    assert site['exclusions']==[]
    metadata=catalog['survey_metadata'][site['site_id']]
    assert metadata['survey_summary']['no_proxy_conflict_combinations']==1258
    assert metadata['survey_report']['path']==best.relative_to(run).as_posix()
    assert '尚未自动排除' in metadata['survey_warning_zh']
    assert not (run/'plans').exists()  # Root chooses exposure before freezing media plans.


def test_rendered_root_choices_revision_and_plan_bytes_are_preserved(setup):
    run,path,_=setup
    original,inventory_pin=select_root(setup)
    plan_path=run/'plans/root_v7.json'
    builder.write(plan_path,{'site':original,'shots':[]})
    digest=builder.sha(plan_path)
    catalog=builder.read(path)
    cards=[dict(s,sample_plan=None,sample_count=0,status='point_pending') for s in catalog['sites']]
    cards[0].update(sample_plan={'path':'plans/root_v7.json','sha256':digest},sample_count=2,status='planned')
    builder.write(run/builder.INDEX,{'sites':cards,'sample_count':2})
    report(setup,'other',1260,(100.,200.,300.))
    merge.merge_surveys(path,run=run)
    after=builder.read(path)
    assert after['sites'][0]==original
    assert after['source_inventory']==inventory_pin
    assert after['source_pins']==catalog['source_pins']
    assert builder.sha(plan_path)==digest
    card=builder.read(run/builder.INDEX)['sites'][0]
    assert card['sample_plan']['sha256']==digest and card['sample_count']==2
    assert card['survey_summary']['applies_to_current_site'] is False
    assert '不能沿用其他点位' in card['survey_warning_zh']


def test_existing_point_uses_matching_candidate_report_not_higher_other_point(setup):
    run,path,_=setup
    original,_=select_root(setup,position=(1.,2.,3.),yaw=0.)
    matching=report(setup,'matching',1249,(1.,2.,3.))
    report(setup,'other_better',1260,(20.,30.,40.))
    merge.merge_surveys(path,run=run)
    catalog=builder.read(path)
    metadata=catalog['survey_metadata'][original['site_id']]
    assert catalog['sites'][0]==original
    assert metadata['survey_summary']['applies_to_current_site'] is True
    assert metadata['survey_summary']['no_proxy_conflict_combinations']==1249
    assert metadata['survey_report']['path']==matching.relative_to(run).as_posix()


def test_partial_matrix_cannot_select_a_point_or_claim_full_pass(setup):
    run,path,_=setup
    report(setup,'partial',1260,partial=True)
    assert merge.merge_surveys(path,run=run)['new_points']==0
    catalog=builder.read(path)
    assert all(s['position'] is None for s in catalog['sites'])
    assert not catalog['survey_metadata'][catalog['sites'][0]['site_id']]['survey_summary']['full_matrix_sampled']


def test_changed_survey_source_is_rejected_without_changing_root_choices(setup):
    run,path,source=setup
    original,_=select_root(setup)
    report(setup,'valid_then_stale',1260)
    source.write_text('changed',encoding='utf-8')
    result=merge.merge_surveys(path,run=run)
    assert result['rejected_reports']==1 and result['new_points']==0
    assert builder.read(path)['sites'][0]==original


def test_current_gallery_marks_changed_numeric_source_stale(setup):
    run,path,source=setup
    report(setup,'valid',1260)
    merge.merge_surveys(path,run=run)
    source.write_text('changed after merge',encoding='utf-8')
    builder.build_gallery(run)
    card=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert card['survey_status']=='stale_requires_recheck'
    assert card['survey_summary']['applies_to_current_site'] is False
    assert '需要重新核对' in card['survey_warning_zh']


def test_merge_aborts_if_root_edits_catalog_during_source_verification(setup,monkeypatch):
    run,path,_=setup
    report(setup,'valid',1260)
    original=merge._verify_pins
    def concurrent_edit(pins,cache):
        original(pins,cache)
        catalog=builder.read(path)
        catalog['root_concurrent_choice']='preserve me'
        builder.write(path,catalog)
    monkeypatch.setattr(merge,'_verify_pins',concurrent_edit)
    with pytest.raises(ValueError,match='changed during merge'):
        merge.merge_surveys(path,run=run)
    after=builder.read(path)
    assert after['root_concurrent_choice']=='preserve me'
    assert all(s['position'] is None for s in after['sites'])


def test_same_selected_yaw_can_wrap_without_losing_matching_report(setup):
    run,path,_=setup
    original,_=select_root(setup,position=(1.,2.,3.),yaw=360.)
    report(setup,'matching_zero',1260,(1.,2.,3.),yaw=0.)
    merge.merge_surveys(path,run=run)
    assert builder.read(path)['survey_metadata'][original['site_id']]['survey_summary']['applies_to_current_site'] is True


def sample_library(setup):
    _,_,source=setup
    shots=[]
    for orientation,camera in [('landscape','orbit_360'),('portrait','front_full')]:
        rows=[{'t':i/30,'position':[0.,300.,100.],'look_at':[0.,0.,90.],
               'rotation_pitch_yaw_roll':[-2.,-90.,0.],'horizontal_fov_degrees':64.5} for i in range(2)]
        shots.append({'shot_id':'walk_'+orientation,'motion_id':'MOTION_CAND_008','motion_label':'向前行走',
            'sex':'female','camera_id':camera,'camera_label':camera,'orientation':orientation,
            'width':1280 if orientation=='landscape' else 720,'height':720 if orientation=='landscape' else 1280,
            'aspect_ratio':16/9 if orientation=='landscape' else 9/16,'status':'geometry_pass',
            'frames':rows[:-1],'endpoint_validation_frame':rows[-1],'trajectory_sha256':builder.object_sha(rows),
            'frame_count':1,'fps':30,'duration_seconds':1/30,'source_start_seconds':0.,
            'source_end_seconds':.02,'source_body_play_rate':.6,'window_start_seconds':0.,
            'source_animation':'/Game/Body','source_clip_id':'walk'})
    return {'sources':[{'path':str(source),'sha256':builder.sha(source)}],'shots':shots}


def test_stage_only_matching1260_clear_sites_and_preserve_metadata_and_frozen_v1(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    run,path,_=setup
    catalog=builder.read(path)
    catalog['sites'][0].update(position={'x':1.,'y':2.,'z':3.},yaw=0.,location_label='待完整复查')
    builder.write(path,catalog)
    library=sample_library(setup)
    sid=catalog['sites'][0]['site_id']
    builder.build_plans(path,run=run,library=library,site_ids=[sid])
    frozen=run/'plans'/(sid+'_v1.json')
    digest=builder.sha(frozen)
    catalog=builder.read(path)
    catalog['sites'][0]['location_label']='root updated label，待完整复查'
    builder.write(path,catalog)
    report(setup,'current_clear',1260,(1.,2.,3.))
    report(setup,'conflicted',1250,(4.,5.,6.),site_index=1)
    report(setup,'new_clear',1260,(7.,8.,9.),site_index=2)
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('Staging must never dispatch UE'))
    result=runner.stage_clear_sites(run,path,library=library)
    after=builder.read(run/builder.INDEX)
    assert result['eligible_site_ids']==[catalog['sites'][0]['site_id'],catalog['sites'][2]['site_id']]
    assert len(result['pending_site_ids'])==24 and result['ue_dispatched'] is False
    assert builder.sha(frozen)==digest
    assert after['sites'][0]['survey_summary']['no_proxy_conflict_combinations']==1260
    assert after['sites'][1]['survey_summary']['no_proxy_conflict_combinations']==1250
    assert after['sites'][1]['sample_plan'] is None
    assert len(after['survey_metadata'])==len(after['sites'])==26
    assert not (run/'plans'/(catalog['sites'][1]['site_id']+'_v1.json')).exists()
    merge.merge_surveys(path,run=run)
    assert builder.sha(frozen)==digest
    assert builder.read(run/builder.INDEX)['sites'][0]['survey_summary']['applies_to_current_site'] is True
    delivered=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert '完整数字采样已完成' in delivered['display_location_label']
    assert builder.read(frozen)['site']['location_label']=='待完整复查'


def test_stage_with_no_clear_sites_does_not_accidentally_build_all_selected_points(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    run,path,_=setup
    report(setup,'conflicted',1259)
    monkeypatch.setattr(runner,'build_plans',lambda *args,**kwargs:pytest.fail('No clear sites means no plan creation'))
    result=runner.stage_clear_sites(run,path)
    assert result['eligible_site_ids']==[] and len(result['pending_site_ids'])==26
    assert not (run/'plans').exists()


def dual_report(setup, *, changed=True, fault=None):
    run, _, source = setup
    attempt = 'fresh_dual_v3'
    entry = source.parent/'ue_primary_scene_survey_dual_v3.py'
    entry.write_text('# frozen wrapper fixture', encoding='utf-8')
    pin = lambda p: {'path': str(p), 'sha256': builder.sha(p)}
    binding_path = run/'dual_signature_bindings'/f'{attempt}.json'
    binding = {'schema':'survey_dual_signature_binding_v3','attempt_id':attempt,
        'geometry_signature_policy':merge.DUAL_POLICY,'private_worker_only':True,
        'original_global_worker_functions_modified':False,
        'entry_source':pin(entry),'original_worker_source':pin(source),'diff_source':pin(source)}
    builder.write(binding_path,binding)
    raw = {'actors':[{'path':'landscape','location':[0,0,0],'components':[]}], 'dirty_packages':[]}
    component = {'path':'landscape.grass','get_collision_enabled':merge.DUAL_POLICY['required_collision'],
                 'visibility_response':merge.DUAL_POLICY['required_visibility_response']}
    grass = {'actor':'landscape','actual_class':'GrassInstancedStaticMeshComponent','component':component}
    snapshots=[]
    for i in range(2):
        payload=copy.deepcopy(raw)
        excluded=[]
        if i and changed:
            payload['actors'][0]['components'].append(component)
            excluded=[grass]
        capture={'schema':'survey_dual_signature_snapshot_v3','attempt_id':attempt,
            'binding':pin(binding_path),'geometry_signature_policy':merge.DUAL_POLICY,
            'captured_at_original_scene_signature_call':True,'raw_payload':payload,
            'collision_proxy_payload':raw,'raw_scene_signature':merge._canonical_sha(payload),
            'collision_proxy_signature':merge._canonical_sha(raw),'excluded_grass_components':excluded}
        if fault=='snapshot_call' and i: capture['captured_at_original_scene_signature_call']=False
        if fault=='wrong_class' and i: capture['excluded_grass_components'][0]['actual_class']='OtherComponent'
        if fault=='proxy_weakened' and i: capture['collision_proxy_payload']=dict(raw,dirty_packages=['changed'])
        snapshot_path=run/'dual_signature_snapshots'/f'{attempt}_{i}.json'
        builder.write(snapshot_path,capture)
        snapshots.append(pin(snapshot_path))
    base_path=report(setup,'fresh_proxy',1260)
    base=builder.read(base_path)
    base.update(attempt_id=attempt,selected_full_attempt_index=0,scene_signature=merge._canonical_sha(raw))
    base['source_pins'] += [pin(entry),pin(binding_path),*snapshots]
    if fault=='stale_base':base['status']='stale'
    if fault=='base_signature':base['scene_signature']='incorrect'
    builder.write(base_path,base)
    first,last=[builder.read(p['path']) for p in snapshots]
    document={'schema':'primary_scene_survey_dual_evidence_v3',
        'status':'collision_proxy_stable_visual_grass_pending' if changed else 'collision_proxy_stable_visual_review_pending',
        'attempt_id':attempt,'map':base['map'],'base_report':pin(base_path),'base_report_status':'complete',
        'geometry_signature_policy':merge.DUAL_POLICY,'geometry_proxy_stable':True,'collision_proxy_qualified':True,
        'full_matrix_sampled':True,'summary':base['full_attempts'][0]['summary'],
        'raw_scene_changed':changed,'raw_before_signature':first['raw_scene_signature'],
        'raw_after_signature':last['raw_scene_signature'],'raw_before_after_changes':[{'grass':'added'}] if changed else [],
        'collision_proxy_changes':[],'excluded_grass_before':first['excluded_grass_components'],
        'excluded_grass_after':last['excluded_grass_components'],'snapshots':snapshots,'binding':pin(binding_path),
        'source_pins':base['source_pins'],'raw_scene_unchanged_certified':False,
        'rendered_visibility_or_exposure_passed':False,'visual_warning':'自动草层变化仍须渲染检查。'}
    if fault=='policy':document['geometry_signature_policy']=dict(merge.DUAL_POLICY,excluded_actual_class='AnyComponent')
    output=run/'dual_signature_reports'/f'{attempt}.json'
    builder.write(output,document)
    return output,base_path,snapshots


@pytest.mark.parametrize('changed',[True,False])
def test_fresh_dual_evidence_keeps1260_coverage_warning_and_raw_receipt(setup,changed):
    run,path,_=setup
    dual,base,_=dual_report(setup,changed=changed)
    assert merge.merge_surveys(path,run=run)['new_points']==1
    card=builder.read(run/builder.INDEX)['sites'][0]
    assert card['survey_summary']['no_proxy_conflict_combinations']==1260
    assert card['survey_summary']['raw_scene_changed'] is changed
    assert card['survey_summary']['raw_scene_unchanged_certified'] is False
    assert card['survey_summary']['rendered_visibility_or_exposure_passed'] is False
    assert card['exclusions']==[] and len(builder.read(run/builder.INDEX)['sites'])==26
    assert card['survey_report']['path']==base.relative_to(run).as_posix()
    assert card['survey_dual_evidence']['path']==dual.relative_to(run).as_posix()
    builder.build_gallery(run)
    delivery=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert '草层变化仍须渲染检查' in delivery['survey_warning_zh']
    assert delivery['survey_qualification_status'].startswith('collision_proxy_stable_visual_')
    assert '查看原始场景变化与草层证据' in (run/'gallery/index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('fault',['stale_base','base_signature','snapshot_call','wrong_class','proxy_weakened','policy'])
def test_unqualified_dual_never_falls_back_to_plain_complete_base(setup,fault):
    run,path,_=setup
    dual_report(setup,fault=fault)
    result=merge.merge_surveys(path,run=run)
    assert result['new_points']==0 and result['rejected_reports']==1
    assert all(s['position'] is None for s in builder.read(path)['sites'])


def test_missing_dual_and_changed_capture_cannot_claim_current_proxy_pass(setup):
    run,path,_=setup
    dual,base,snapshots=dual_report(setup)
    assert merge.merge_surveys(path,run=run,report_paths=[base])['new_points']==0
    merge.merge_surveys(path,run=run)
    Path(snapshots[-1]['path']).write_text('changed after merge',encoding='utf-8')
    builder.build_gallery(run)
    card=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert card['survey_status']=='stale_requires_recheck'
    assert card['survey_summary']['collision_proxy_qualified'] is False
    assert card['survey_summary']['applies_to_current_site'] is False


def panel_sync_fixture(setup,monkeypatch):
    import camera_standard_v3 as standard
    import scene_site_review_geometry_v1 as geo
    run,path,source=setup
    panel=run.parent/'panel'
    config=run.parent/'standard.json'
    builder.write(config,{'standard_id':'nonface_landscape_distance050_fov_compensated_v3'})
    monkeypatch.setattr(geo,'CAMERA_STANDARD',config)
    monkeypatch.setattr(standard,'load_config',lambda path:builder.read(path))
    rows=[{'shot_id':'s'+str(i),'motion_id':'m'+str(i//42), 'camera_id':'c'+str((i%42)//2),
           'orientation':'landscape' if i%2==0 else 'portrait'} for i in range(1260)]
    builder.write(panel/'site_review_local_geometry_v1.json',{
        'sources':[{'path':str(config),'sha256':builder.sha(config)}],'shots':rows})
    original,_=select_root(setup,position=(1.,2.,3.),yaw=90.)
    catalog=builder.read(path)
    catalog['sites'][0]['exclusions']=[{'motion_id':'m0','orientation':'landscape'},'s43']
    builder.write(path,catalog)
    builder.write(panel/'sites/gas_pilot.json',{'site':{'site_id':'gas_pilot','map':'/Game/Scenes/Gas/Main',
        'position':'user owned'},'report':'retain'})
    builder.write(panel/'selection.json',{'site_id':'gas_pilot','camera_id':'front_head'})
    return panel,catalog['sites'][0]


def test_saved_point_sync_defaults_to_preview_and_preserves_user_points_selection_and_semantics(setup,monkeypatch):
    import scene_site_catalog_v1 as directory
    run,path,_=setup
    panel,source=panel_sync_fixture(setup,monkeypatch)
    protected={p:builder.sha(p) for p in panel.rglob('*.json')}
    plan=run/'plans/unchanged_v1.json'
    builder.write(plan,{'frozen':'untouched'})
    digest=builder.sha(plan)
    result=merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel)
    target=panel/'sites'/(source['site_id']+'.json')
    assert not result['applied'] and not target.exists()
    assert len(result['unselected_site_ids_skipped'])==25
    assert all(builder.sha(p)==value for p,value in protected.items())
    merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel,apply=True)
    record=builder.read(target)
    assert record['site']['position']==source['position']
    assert record['site']['yaw']==90. and record['site']['exposure_compensation']==2.
    assert record['site']['exclusions']==source['exclusions']
    assert len(record['site']['imported_excluded_combinations'])==22
    assert {d['decision'] for d in record['site']['imported_excluded_combinations']}=={'excluded'}
    assert record['site']['allowed_combinations']==[] and 'decisions_stamp' not in record['site']
    assert record['human_acceptance']=='pending' and record['report'] is None
    assert record['input_fingerprint'] is None and record['scene_signature'] is None
    assert record['site']['imported_camera_standard']['distance_factor']==.5
    assert builder.sha(plan)==digest and all(builder.sha(p)==value for p,value in protected.items())
    rows,warnings=directory.saved_sites([panel/'sites'])
    assert not warnings and {r['id'] for r in rows}=={'gas_pilot',source['site_id']}
    merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel,apply=True)
    assert builder.read(target)==record


def test_saved_point_sync_updates_own_records_but_never_overwrites_user_edits(setup,monkeypatch):
    run,path,_=setup
    panel,source=panel_sync_fixture(setup,monkeypatch)
    merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel,apply=True)
    target=panel/'sites'/(source['site_id']+'.json')
    catalog=builder.read(path)
    catalog['sites'][0]['exposure_compensation']=1.25
    builder.write(path,catalog)
    merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel,apply=True)
    assert builder.read(target)['site']['exposure_compensation']==1.25
    edited=builder.read(target)
    edited['site']['position']['x']=900.
    builder.write(target,edited)
    digest=builder.sha(target)
    with pytest.raises(ValueError,match='user-owned or edited'):
        merge.sync_catalog_to_saved_points(path,run=run,panel_run=panel,apply=True)
    assert builder.sha(target)==digest


def object_ground_report(setup, fault=None, *, simple=False):
    run,_,source=setup
    dual_path,base_path,_=dual_report(setup)
    base,dual=builder.read(base_path),builder.read(dual_path)
    pin=lambda p:{'path':str(p),'sha256':builder.sha(p)}
    base_adapter=source.parent/'ue_primary_scene_ground_objects_v1.py'
    base_adapter.write_text('# unchanged complex adapter fixture',encoding='utf-8')
    adapter=source.parent/('ue_primary_scene_ground_simple_v2.py' if simple else 'ue_primary_scene_ground_objects_v1.py')
    adapter.write_text('# ground-only adapter fixture',encoding='utf-8')
    target={'component_path':base['map']+'.Map:PersistentLevel.road.mesh', 'is_world_dynamic':False,
            'static_mesh':'/Game/Road.Mesh'}
    policy={'id':'targeted_object_type_ground_v1','object_types':['WorldStatic'],
        'dynamic_enabled_only_from_named_actual_target_type':False,'target_component_paths':[target['component_path']],
        'ground_domains':['anchor_and_nine_probes','screen_ground_probes','full_action_ground_probes'],
        'trace_complex':True,'body_standing_camera_occlusion':'original Visibility logic unchanged',
        'flat_region_tolerance_cm':3.,'standing_probe_radius_cm':80.,'ground_probe_count':9,
        'full_action_ground_height_tolerance_cm':5.,'full_matrix_combinations':1260}
    if simple:
        position=base['full_attempts'][0]['candidate']['position']
        diagnostic={'component':target['component_path'],'mesh':target['static_mesh'],
            'traces':[{'complex':True,'start':[1.,2.,300.],'end':[1.,2.,-500.],'parsed':None},
                      {'complex':False,'start':[1.,2.,300.],'end':[1.,2.,-500.],
                       'parsed':{'point':position,'normal':[0.,0.,1.]},'hit':target['component_path']}]}
        if fault=='diagnostic_xy':diagnostic['traces'][1]['start'][0]=99.
        elif fault=='diagnostic_target':diagnostic['component']='another_actual_component'
        diagnostic_path=run/'simple_ground_diagnostic.json'
        builder.write(diagnostic_path,diagnostic)
        policy.update(id='targeted_object_type_ground_simple_v2',trace_complex=False,
            diagnostic_evidence=pin(diagnostic_path),base_adapter_source=pin(base_adapter),
            simple_collision_surface_limitation='Simple collision proxy ground only; rendered contact needs visual review.')
    elif fault=='complex_trace_false':
        policy['trace_complex']=False
    binding={'schema':'primary_scene_object_ground_binding_v1','attempt_id':base['attempt_id'],'map':base['map'],
        'ground_query_policy':policy,'target_components':[target],'adapter_source':pin(adapter),
        'frozen_sources':[pin(source)],'local_api_sources':[pin(source)]}
    binding_path=run/'ground_object_bindings/attempt.json'
    builder.write(binding_path,binding)
    base['source_pins'] += [pin(adapter),pin(binding_path)]
    if simple:base['source_pins'] += [pin(base_adapter),pin(diagnostic_path)]
    base['ground_candidates']=[{'eligible':True,'position':base['full_attempts'][0]['candidate']['position'],
        'support_hit':{'component_path':target['component_path']}}]
    builder.write(base_path,base)
    counts={'anchor':1,'nine_probes':9,'screen_ground':40,'full_ground':3245}
    receipt={'schema':'primary_scene_object_ground_evidence_v1','attempt_id':base['attempt_id'],'map':base['map'],
        'status':'complete','ground_query_policy':policy,'binding':pin(binding_path),'adapter_source':pin(adapter),
        'base_report':pin(base_path),'target_components':[target],
        'query_statistics':dict(counts,body_camera_visibility_unchanged=True,standing_visibility_unchanged=True),
        'queries':{'trace_count_by_domain':counts},'ground_candidates':base['ground_candidates'],
        'body_camera_occlusion_and_standing_changed':False,'original_thresholds_and_full1260_changed':False,
        'old_reports_requalified':False}
    if fault=='attempt':receipt['attempt_id']='another_attempt'
    elif fault=='map':receipt['map']='/Game/Scenes/Other/Map'
    elif fault=='targets':receipt['target_components']=[]
    elif fault=='policy':receipt['ground_query_policy']=dict(policy,full_matrix_combinations=12)
    elif fault=='coverage':receipt['query_statistics']=dict(receipt['query_statistics'],full_ground=0)
    receipt_path=run/'ground_object_reports/attempt.json'
    builder.write(receipt_path,receipt)
    dual.update(base_report=pin(base_path),ground_query_policy=policy,
                ground_query_evidence=pin(receipt_path),ground_adapter_source=pin(adapter))
    dual['source_pins'] += [pin(adapter),pin(binding_path),pin(receipt_path)]
    if simple:dual['source_pins'] += [pin(base_adapter),pin(diagnostic_path)]
    builder.write(dual_path,dual)
    return dual_path,receipt_path


def test_object_ground_receipt_keeps_distinct_policy_and_gallery_warning(setup):
    run,path,_=setup
    _,receipt=object_ground_report(setup)
    assert merge.merge_surveys(path,run=run)['new_points']==1
    builder.build_gallery(run)
    card=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert card['survey_summary']['no_proxy_conflict_combinations']==1260
    assert card['survey_ground_query_policy']['id']=='targeted_object_type_ground_v1'
    assert card['survey_ground_evidence']['path']==receipt.relative_to(run).as_posix()
    assert '身体、站立、相机及遮挡仍用原Visibility检查' in card['survey_warning_zh']
    assert '查看地面对象查询记录' in (run/'gallery/index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('fault',['attempt','map','targets','policy','coverage'])
def test_object_ground_receipt_mismatch_cannot_fall_back_to_plain_survey(setup,fault):
    run,path,_=setup
    object_ground_report(setup,fault)
    result=merge.merge_surveys(path,run=run)
    assert result['new_points']==0 and result['rejected_reports']==1


def test_object_ground_simple_branch_requires_diagnostic_and_displays_proxy_contact_warning(setup):
    run,path,_=setup
    object_ground_report(setup,simple=True)
    assert merge.merge_surveys(path,run=run)['new_points']==1
    builder.build_gallery(run)
    card=builder.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert card['survey_ground_query_policy']['trace_complex'] is False
    assert card['survey_ground_query_policy']['id']=='targeted_object_type_ground_simple_v2'
    assert card['survey_ground_diagnostic']['path']=='simple_ground_diagnostic.json'
    assert '简单碰撞代理' in card['survey_warning_zh'] and '不保证与画面网格精确接地' in card['survey_warning_zh']
    assert '查看同位置复杂未命中／简单命中诊断' in (run/'gallery/index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('fault',['diagnostic_xy','diagnostic_target','complex_trace_false'])
def test_object_ground_simple_gate_does_not_relax_original_complex_policy(setup,fault):
    run,path,_=setup
    object_ground_report(setup,fault,simple=fault!='complex_trace_false')
    result=merge.merge_surveys(path,run=run)
    assert result['new_points']==0 and result['rejected_reports']==1
