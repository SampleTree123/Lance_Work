"""Bounded offline checks; these tests never import or connect to Unreal."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

S = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S))
import build_primary_scene_samples_v1 as samples
import ue_primary_scene_samples_v1 as ue


def _rotation_repair_fake(monkeypatch, tmp_path, orientation='portrait'):
    monkeypatch.setattr(ue, 'RUN', tmp_path)
    (tmp_path / 'red_desert_initial_rotation_readback_v1.json').write_text('{}')

    class Camera:
        def __init__(self):
            self.rotation = SimpleNamespace(pitch=-45., yaw=0., roll=0.)
            self.changed = []

        def get_path_name(self):
            return ue.ASSETS + '/SceneTrials/L_new.L_new:PersistentLevel.CameraActor_0'

        def get_actor_rotation(self):
            return self.rotation

        def set_actor_rotation(self, rotation, sweep):
            self.changed.append(rotation)
            self.rotation = rotation

        def get_component_by_class(self, cls):
            return object()

    fake = SimpleNamespace(CameraActor=Camera, CameraComponent=object(),
                           Rotator=lambda **kwargs: SimpleNamespace(**kwargs))
    shot = source_shot(orientation=orientation)
    shot['frames'][0]['rotation_pitch_yaw_roll'] = [0., -45., 0.]
    shot['exposure_compensation'] = 0.
    document = {'schema': 'primary_scene_sample_trial_v1',
                'scene_id': 'primary_reddesertpack_540b8a32', 'revision': 'v2',
                'site': {'site_id': 'primary_reddesertpack_540b8a32', 'revision': 'v2',
                         'map': '/Game/Scenes/RedDesert/Map'}, 'shots': [shot]}
    return fake, document, shot, Camera


@pytest.mark.parametrize('orientation', ['landscape', 'portrait'])
@pytest.mark.parametrize('revision', ['v2', 'v3'])
@pytest.mark.parametrize('scene_id', ['primary_reddesertpack_540b8a32', 'primary_japanese_village_e67432a1'])
def test_initial_rotation_repair_only_owned_new_scene_camera(monkeypatch, tmp_path, orientation, revision, scene_id):
    fake, document, shot, Camera = _rotation_repair_fake(monkeypatch, tmp_path, orientation)
    document.update(revision=revision, scene_id=scene_id)
    document['site'].update(revision=revision, site_id=scene_id)
    before = copy.deepcopy(shot)
    camera = Camera()
    audit = ue._correct_initial_camera_rotation(fake, document, shot, camera)
    assert audit['readback'] == {'pitch': 0., 'yaw': -45., 'roll': 0.}
    assert audit['status'] == 'verified_before_map_save' and len(camera.changed) == 1
    assert shot == before  # Every trajectory row, animation and clock field remains exact.
    character = SimpleNamespace(untouched=True)
    assert ue._correct_initial_camera_rotation(fake, document, shot, character) is None
    assert vars(character) == {'untouched': True}
    for doc, row in [(dict(document, revision='v1'), shot),
                     (dict(document, schema='another_task_sample_v1'), shot),
                     (dict(document, scene_id='another_task_scene'), shot),
                     (document, dict(shot, orientation='unsupported'))]:
        other = Camera()
        assert ue._correct_initial_camera_rotation(fake, doc, row, other) is None
        assert other.changed == []


def test_initial_rotation_rejects_foreign_camera_and_changed_frozen_shot(monkeypatch, tmp_path):
    fake, document, shot, Camera = _rotation_repair_fake(monkeypatch, tmp_path)
    camera = Camera()
    camera.get_path_name = lambda: '/Game/OtherTask/SceneTrials/L_other.CameraActor_0'
    with pytest.raises(ValueError, match='new owned trial camera'):
        ue._correct_initial_camera_rotation(fake, document, shot, camera)
    assert camera.changed == []
    changed = copy.deepcopy(shot)
    changed['frames'][0]['rotation_pitch_yaw_roll'][0] = 10.
    assert ue._correct_initial_camera_rotation(fake, document, changed, Camera()) is None


@pytest.mark.parametrize('orientation', ['landscape', 'portrait'])
def test_initial_rotation_adapter_records_receipt_before_first_save(monkeypatch, tmp_path, orientation):
    fake, document, shot, Camera = _rotation_repair_fake(monkeypatch, tmp_path, orientation)
    forwarded, saved = [], []
    original = lambda *args, **kwargs: forwarded.append((args, kwargs)) or {'sequence': 'same'}
    builder = SimpleNamespace(key_rows=lambda row: row, build_sequence=original)
    base = SimpleNamespace(save=lambda path, data, *args, **kwargs: saved.append(data))
    alignment = SimpleNamespace(adapter=lambda: base, configured_module=lambda name: builder)
    stage = SimpleNamespace()
    monkeypatch.setattr(ue, 'module', lambda name: alignment if name == 'ue_camera_alignment_review_v1' else stage)
    monkeypatch.setattr(ue, 'exposure', lambda *args: None)
    _, wrapped_base, configured = ue.adapter(document)
    camera, character, animation = Camera(), object(), object()
    result = configured('ue_motion_scene_sequence_v1').build_sequence(
        fake, shot, character, camera, animation, '/owned/sequence')
    assert result == {'sequence': 'same'}
    assert forwarded[0][0] == (fake, shot, character, camera, animation, '/owned/sequence')
    wrapped_base.save('/receipt', {'success': True, 'job': {'shot_id': shot['shot_id']}})
    assert saved[0]['initial_camera_rotation']['expected'] == {'pitch': 0., 'yaw': -45., 'roll': 0.}
    wrapped_base.save('/other', {'success': True, 'job': {'shot_id': 'unrelated'}})
    assert 'initial_camera_rotation' not in saved[1]


def source_shot(motion='MOTION_CAND_008', camera='orbit_360', orientation='landscape'):
    rows = [{'t': i / 30, 'position': [float(i), 300., 100.],
             'look_at': [float(i), 0., 90.], 'rotation_pitch_yaw_roll': [-2., -90., 0.],
             'horizontal_fov_degrees': 64.5} for i in range(4)]
    return {'shot_id': motion.lower() + '_' + camera + '_' + orientation,
            'motion_id': motion, 'motion_label': '向前行走', 'sex': 'female',
            'camera_id': camera, 'camera_label': camera, 'orientation': orientation,
            'width': 1280 if orientation == 'landscape' else 720,
            'height': 720 if orientation == 'landscape' else 1280,
            'aspect_ratio': 16 / 9 if orientation == 'landscape' else 9 / 16,
            'status': 'geometry_pass', 'frames': rows[:-1], 'endpoint_validation_frame': rows[-1],
            'trajectory_sha256': samples.object_sha(rows), 'source_start_seconds': 1.,
            'source_end_seconds': 1.06, 'source_body_play_rate': .6,
            'window_start_seconds': 0., 'duration_seconds': .1, 'frame_count': 3, 'fps': 30,
            'source_animation': '/Game/Body', 'source_clip_id': 'walk',
            'path_metrics': {'min_camera_z_cm': 100.},
            'camera_standard_v2': {'distance_factor': .5, 'derived_trajectory_sha256': samples.object_sha(rows)}}


@pytest.fixture
def setup(tmp_path):
    source = tmp_path / 'source.json'
    source.write_text('{}', encoding='utf-8')
    library = {'sources': [{'path': str(source), 'sha256': samples.sha(source)}],
               'shots': [source_shot(camera=camera, orientation=orientation)
                         for camera in ('orbit_360', 'front_full')
                         for orientation in ('landscape', 'portrait')]}
    sites = [{'site_id': 'scene_a', 'scene_label': '主场景甲', 'map': '/Game/Scenes/A/Main',
              'position': {'x': 100., 'y': 200., 'z': 10.}, 'yaw': 90.,
              'exposure_compensation': 1., 'exclusions': [], 'revision': 'v1'},
             {'site_id': 'scene_b', 'scene_label': '主场景乙', 'map': '/Game/Scenes/B/Main',
              'position': None, 'yaw': 0., 'exposure_compensation': 0., 'exclusions': []}]
    catalog = tmp_path / 'catalog.json'
    samples.write(catalog, {'sites': sites})
    return catalog, sites, library, tmp_path / 'outputs/run'


def test_default_pair_and_pending_scene_are_preserved(setup):
    catalog, _, library, run = setup
    result = samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    assert result['scenes'] == 2 and result['planned_samples'] == 2 and result['points_pending'] == 1
    index = samples.read(run / samples.INDEX)
    assert len(index['sites']) == 2
    assert index['sites'][1]['status'] == 'point_pending'
    plan = samples.read(run / index['sites'][0]['sample_plan']['path'])
    assert [(s['camera_id'], s['orientation']) for s in plan['shots']] == [('orbit_360', 'landscape'), ('front_full', 'portrait')]
    assert all(not s['sample_selection']['fallback_used'] for s in plan['shots'])


def explicit_preferences():
    return [{'motion_id': 'MOTION_CAND_008', 'camera_id': camera,
             'orientation': orientation, 'reason_zh': '展示主建筑与人物构图'}
            for orientation, camera in (('portrait', 'orbit_360'), ('landscape', 'front_full'))]


def test_explicit_sample_preferences_select_exact_pair_without_implying_exclusions(setup):
    _, sites, library, _ = setup
    site = sites[0]
    site['sample_preferences'] = explicit_preferences()
    before = copy.deepcopy(site)
    pair = samples.select_samples(library['shots'], site)
    assert [(s['orientation'], s['camera_id']) for s, _ in pair] == [
        ('landscape', 'front_full'), ('portrait', 'orbit_360')]
    assert all(meta['explicit_preference'] and not meta['fallback_used'] and meta['reason_zh']
               for _, meta in pair)
    assert site == before and site['exclusions'] == []
    assert '默认组合已排除' not in samples.HTML
    assert '代表样片选择：' in samples.HTML


@pytest.mark.parametrize('invalid', ['unknown', 'duplicate_orientation', 'missing_reason', 'excluded'])
def test_invalid_explicit_sample_preferences_fail_without_fallback(setup, invalid):
    _, sites, library, _ = setup
    site = sites[0]
    site['sample_preferences'] = explicit_preferences()
    if invalid == 'unknown':
        site['sample_preferences'][0]['motion_id'] = 'missing_motion'
    elif invalid == 'duplicate_orientation':
        site['sample_preferences'][0]['orientation'] = 'landscape'
    elif invalid == 'missing_reason':
        site['sample_preferences'][0]['reason_zh'] = ' '
    else:
        site['exclusions'] = [{'camera_id': 'orbit_360', 'orientation': 'portrait'}]
    with pytest.raises(ValueError, match='sample_preferences'):
        samples.select_samples(library['shots'], site)


def test_sample_preferences_bind_render_definition_and_require_new_revision(setup):
    catalog, sites, library, run = setup
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    path = run / 'plans/scene_a_v1.json'
    digest = samples.sha(path)
    prior = samples.render_definition(sites[0])
    sites[0]['sample_preferences'] = [
        {'motion_id': 'MOTION_CAND_008', 'camera_id': camera, 'orientation': orientation,
         'reason_zh': '主动保留这组代表构图'}
        for orientation, camera, _ in samples.PREFERENCES]
    assert samples.render_definition(sites[0]) != prior
    samples.write(catalog, {'sites': sites})
    with pytest.raises(ValueError, match='fresh site revision'):
        samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    assert samples.sha(path) == digest


def test_placement_matches_numeric_geometry_and_preserves_entire_body_clock(setup):
    _, sites, library, _ = setup
    source = library['shots'][0]
    before = copy.deepcopy(source)
    shot = samples.place_shot(source, sites[0], {'fallback_used': False})
    assert source == before
    assert {k: shot[k] for k in samples.geo.CLOCK_FIELDS} == {k: source[k] for k in samples.geo.CLOCK_FIELDS}
    old_rows = source['frames'] + [source['endpoint_validation_frame']]
    new_rows = shot['frames'] + [shot['endpoint_validation_frame']]
    for old, new in zip(old_rows, new_rows):
        assert new['position'] == samples.geo.transform_point(old['position'], [100., 200., 10.], 90.)
        assert new['look_at'] == samples.geo.transform_point(old['look_at'], [100., 200., 10.], 90.)
        assert new['rotation_pitch_yaw_roll'] == [-2., 0., 0.]
        assert new['horizontal_fov_degrees'] == old['horizontal_fov_degrees']
    assert shot['trajectory_sha256'] == samples.object_sha(new_rows)
    assert shot['actor_offset_cm'] == [100., 200., 10.]
    assert 'camera_standard_v2' not in shot
    assert shot['source_camera_diagnostics']['camera_standard_v2']['distance_factor'] == .5


@pytest.mark.parametrize('exclusion', ['id', 'combination'])
def test_default_exclusion_selects_compatible_alternative_instead_of_dropping_scene(setup, exclusion):
    _, sites, library, _ = setup
    source = next(s for s in library['shots'] if (s['camera_id'], s['orientation']) == ('orbit_360', 'landscape'))
    sites[0]['exclusions'] = [source['shot_id'] if exclusion == 'id' else
                              {'action_id': source['motion_id'], 'camera_id': 'orbit_360', 'aspect': 'landscape'}]
    pair = samples.select_samples(library['shots'], sites[0])
    assert len(pair) == 2
    assert pair[0][0]['camera_id'] == 'front_full'
    assert pair[0][1]['fallback_used'] is True


def test_one_available_aspect_still_keeps_the_scene_and_compatible_sample(setup):
    catalog, sites, library, run = setup
    sites[0]['exclusions'] = [{'aspect': 'landscape'}]
    samples.write(catalog, {'sites': sites})
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    index = samples.read(run / samples.INDEX)
    assert len(index['sites']) == 2
    assert index['sites'][0]['sample_count'] == 1


def test_updated_point_or_exposure_needs_new_revision_and_preserves_prior_plan(setup):
    catalog, sites, library, run = setup
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    path = run / 'plans/scene_a_v1.json'
    digest = samples.sha(path)
    sites[0]['exposure_compensation'] = 2.
    samples.write(catalog, {'sites': sites})
    with pytest.raises(ValueError, match='fresh site revision'):
        samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    sites[0]['revision'] = 'v2'
    samples.write(catalog, {'sites': sites})
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    assert samples.sha(path) == digest
    assert (run / 'plans/scene_a_v2.json').is_file()
    old_ids = {s['shot_id'] for s in samples.read(path)['shots']}
    new_ids = {s['shot_id'] for s in samples.read(run / 'plans/scene_a_v2.json')['shots']}
    assert old_ids.isdisjoint(new_ids)


def test_non_sample_policy_update_reuses_frozen_plan_bytes_and_displays_current_policy(setup,monkeypatch):
    catalog,sites,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    path=run/'plans/scene_a_v1.json';before=path.read_bytes()
    receipt=run/'existing_media_receipt.json';receipt.write_bytes(b'previous verified receipt')
    sites[0]['exclusions']=[{'motion_id':'MOTION_CAND_008','camera_id':'front_full','orientation':'landscape'}]
    sites[0]['compatibility_policy_revision']='compatibility_v2'
    samples.write(catalog,{'sites':sites})
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    assert path.read_bytes()==before and receipt.read_bytes()==b'previous verified receipt'
    card=samples.read(run/samples.INDEX)['sites'][0]
    policy=card['current_policy_vs_frozen_render_metadata']
    assert policy['current_policy']=={'exclusions':sites[0]['exclusions'],'compatibility_policy_revision':'compatibility_v2'}
    assert policy['frozen_render_metadata']=={'exclusions':[],'compatibility_policy_revision':None}
    assert policy['policy_differs_from_frozen_snapshot']
    import run_all_motion_camera_review_v1 as runner_base
    monkeypatch.setattr(runner_base,'verified_rows',lambda *_:{})
    samples.build_gallery(run)
    delivery=samples.read(run/'scene_samples_delivery_v1.json')['scenes'][0]
    assert delivery['exclusions']==sites[0]['exclusions']
    assert delivery['current_policy_vs_frozen_render_metadata']==policy
    html=(run/'gallery/index.html').read_text(encoding='utf-8')
    assert '当前配置排除' in html and '冻结样片计划历史策略快照' in html
    assert path.read_bytes()==before


def test_policy_excluding_selected_sample_requires_new_revision_even_with_alternative(setup):
    catalog,sites,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    path=run/'plans/scene_a_v1.json';before=path.read_bytes()
    sites[0]['exclusions']=[{'motion_id':'MOTION_CAND_008','camera_id':'orbit_360','orientation':'landscape'}]
    sites[0]['compatibility_policy_revision']='compatibility_v2'
    samples.write(catalog,{'sites':sites})
    with pytest.raises(ValueError,match='fresh site revision'):
        samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    assert path.read_bytes()==before


def test_non_sample_policy_update_does_not_allow_changed_position(setup):
    catalog,sites,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    path=run/'plans/scene_a_v1.json';before=path.read_bytes()
    sites[0]['compatibility_policy_revision']='compatibility_v2'
    sites[0]['position']['x']+=1.
    samples.write(catalog,{'sites':sites})
    with pytest.raises(ValueError,match='fresh site revision'):
        samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    assert path.read_bytes()==before


def test_cli_default_demands_exact_existing26_primary_cards(setup):
    catalog, _, library, run = setup
    with pytest.raises(ValueError, match='existing primary catalog'):
        samples.build_plans(catalog, run=run, library=library)
    assert not run.exists()


@pytest.mark.parametrize('field,value', [('map', '/Game/Unrelated/Map'),
                                       ('position', [0., 0., float('nan')]),
                                       ('exposure_compensation', 11.)])
def test_invalid_placement_and_unowned_scene_namespace_fail(setup, field, value):
    _, sites, _, _ = setup
    site = dict(sites[0], **{field: value})
    with pytest.raises(ValueError):
        samples.validate_site(site)


def test_gallery_keeps_pending_cards_and_does_not_claim_all1260_visual_acceptance(setup, monkeypatch):
    catalog, sites, library, run = setup
    sites[0]['preview_image']='previews/site.png'
    samples.write(catalog,{'sites':sites})
    preview=run/'previews/site.png'
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b'owned screenshot fixture')
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    import run_all_motion_camera_review_v1 as runner_base
    monkeypatch.setattr(runner_base, 'verified_rows', lambda *_: {})
    result = samples.build_gallery(run)
    data = samples.read(run / 'scene_samples_delivery_v1.json')
    assert result['scenes'] == 2 and result['playable'] == 0 and result['samples'] == 2
    assert len(data['scenes']) == 2
    html = (run / 'gallery/index.html').read_text(encoding='utf-8')
    assert '50%移近标准' in html
    assert '不代表全部组合已经视觉通过' in html
    assert data['scenes'][0]['exposure_compensation'] == 1.
    assert data['scenes'][0]['preview_image_ready'] is True
    assert data['scenes'][0]['preview_image_sha256']==samples.sha(preview)
    assert data['scenes'][1]['status'] == 'point_pending'
    assert data['compatibility_review_source'] is None
    assert all('compatibility_review' not in s for s in data['scenes'])


@pytest.mark.parametrize('include_known_site', [False, True])
def test_optional_review_display_maps_exact_site_and_uses_existing_chinese_labels(setup,monkeypatch,include_known_site):
    catalog,sites,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    panel=run.parent/'label_fixture'
    samples.write(panel/'site_review_catalog_v1.json',{
        'actions':[{'motion_id':'MOTION_CAND_008','motion_label':'向前行走'}],
        'cameras':[{'camera_id':'orbit_360','camera_label':'360度环绕'}]})
    monkeypatch.setattr(samples.geo,'RUN',panel)
    review={'site_id':'unknown_site','map':sites[0]['map'],'selected_point':{'position':[100.,200.,10.],'yaw':90.},
        'review_focus_zh':'不应映射未知点位','summary':{'priority_exact_camera_combination_count':2,
            'action_route_review_combination_count':0,'visual_only_combination_count':1},
        'priority_exact_camera_combinations':[{'action_id':'MOTION_CAND_008','aspect':'landscape','camera_ids':['orbit_360']}],
        'action_route_review_combinations':[],'visual_only_combinations':[]}
    rows=[review]
    if include_known_site:
        rows.append(dict(review,site_id='scene_a',review_focus_zh='先核MOTION_CAND_008的环绕镜头。'))
    samples.write(run/'compatibility_review_recommendations_v1.json',{
        'schema':'primary_scene_compatibility_review_recommendations_v1','scenes':rows})
    import run_all_motion_camera_review_v1 as runner_base
    verified=[]
    monkeypatch.setattr(runner_base,'verified_rows',lambda shots,root:verified.append(set(shots)) or {})
    samples.build_gallery(run)
    data=samples.read(run/'scene_samples_delivery_v1.json')
    assert len(verified)==1  # Existing media verification still executes unchanged.
    assert data['planned_samples']==2 and data['playable']==0
    assert '不应映射未知点位' not in json.dumps(data,ensure_ascii=False)
    assert 'compatibility_review' not in data['scenes'][1]
    card=data['scenes'][0]
    assert ('compatibility_review' in card) is include_known_site
    if include_known_site:
        assert card['review_focus_zh']=='先核向前行走的环绕镜头。'
        advice=card['compatibility_review']
        assert advice['camera_entity_count']==2 and advice['visual_only_count']==1
        assert '尚未按这些建议排除组合' in advice['notice_zh']
        assert advice['recommendations_applied'] is False and card['exclusions']==[]
        combo=advice['groups'][0]['combinations'][0]
        assert combo['action_label']=='向前行走' and combo['cameras'][0]['label']=='360度环绕'
        assert combo['action_id']=='MOTION_CAND_008' and combo['orientation']=='landscape'


def test_exposure_always_inherits_level_even_after_nonzero_legacy_point():
    class Properties:
        def __init__(self, values): self.values = dict(values)
        def get_editor_property(self, key): return self.values[key]
        def set_editor_property(self, key, value): self.values[key] = value
    from level_exposure_policy_v1 import OVERRIDES
    settings = Properties({**{k:True for k in OVERRIDES}, 'auto_exposure_bias': -.7,
                           'auto_exposure_method': 'preserved'})
    component = Properties({'post_process_settings': settings, 'post_process_blend_weight': .3,
                            'field_of_view': 35.})
    assert ue.exposure(component, 0.)['camera_override'] is False
    assert settings.values['auto_exposure_bias'] == -.7
    assert ue.exposure(component, 2.)['camera_override'] is False
    assert settings.values['auto_exposure_bias'] == -.7
    assert all(settings.values[k] is False for k in OVERRIDES)
    assert settings.values['auto_exposure_method'] == 'preserved'
    assert component.values['field_of_view'] == 35.
    assert component.values['post_process_blend_weight'] == .3
    import ue_primary_saved_site_review_v1 as preview
    assert preview.apply_camera_exposure(component, -3.) == ue.exposure(component, -3.)


@pytest.mark.parametrize('reject_readback',[None,'grass','resources','warmup'])
def test_sample_resource_and_warmup_policies_apply_before_dispatch(reject_readback, monkeypatch, tmp_path):
    import mrq_streaming_warmup_v1 as warmup_helper
    monkeypatch.setattr(warmup_helper, 'LOCAL_PROFILE', tmp_path/'absent_local_profile.json')
    values={'flush_grass_streaming':True,'override_grass_cull_distance_scale':True,
            'grass_cull_distance_scale':50.,'override_grass_density_scale':False,
            'grass_density_scale':1.,'use_lod_zero':True,'cinematic_quality_settings':True,
            'texture_streaming':'DISABLED','disable_hlods':True,
            'override_view_distance_scale':True,'use_high_quality_shadows':True,
            'flush_streaming_managers':True,'override_virtual_texture_feedback_factor':True}
    before=copy.deepcopy(values)
    def set_property(key,value):
        if reject_readback=='grass' and key=='flush_grass_streaming':return
        if reject_readback=='resources' and key=='use_lod_zero':return
        values[key]=value
    setting=SimpleNamespace(set_editor_property=set_property,get_editor_property=values.__getitem__)
    aa_values={'engine_warm_up_count':16,'render_warm_up_count':8,
               'render_warm_up_frames':True,'use_camera_cut_for_warm_up':False,
               'spatial_sample_count':1,'temporal_sample_count':1}
    def set_aa_property(key,value):
        if reject_readback=='warmup' and key=='engine_warm_up_count':return
        aa_values[key]=value
    aa=SimpleNamespace(set_editor_property=set_aa_property,get_editor_property=aa_values.__getitem__)
    aa_class=object()
    config=SimpleNamespace(find_or_add_setting_by_class=lambda cls:aa if cls is aa_class else setting)
    queue=SimpleNamespace(get_jobs=lambda:[SimpleNamespace(job_name='owned_sample',get_configuration=lambda:config)])
    u=SimpleNamespace(MoviePipelineGameOverrideSetting=object(),
                      MoviePipelineAntiAliasingSetting=aa_class,
                      MoviePipelineTextureStreamingMethod=SimpleNamespace(NONE='NONE'))
    contract={'fps':30,'width':1280,'height':720,'engine_warmup_count':16,'render_warmup_count':8,
              'frame_counts_by_shot':{'owned_sample':300},'spatial_samples':1,'temporal_samples':1}
    persisted=[]; dispatched=[]
    renderer=SimpleNamespace(persist=lambda state:persisted.append(copy.deepcopy(state['receipt'])))
    original_writer=renderer.persist
    def start(fake_u,*args,**kwargs):
        state={'receipt':{'status':'preparing','render_contract':copy.deepcopy(contract)},'queue':None}
        renderer.persist(state)
        state.update(queue=queue)
        state['receipt']['status']='submitted'
        renderer.persist(state)
        assert values['flush_grass_streaming'] is False
        assert values['override_grass_cull_distance_scale'] is False
        assert aa_values['engine_warm_up_count']==120
        assert aa_values['render_warm_up_count']==32
        dispatched.append('executor')
        return state
    renderer.start_render=start
    ue.sample_renderer(renderer)
    if reject_readback:
        with pytest.raises(ValueError,match='failed readback'):
            renderer.start_render(u)
        assert not dispatched
    else:
        result=renderer.start_render(u)
        actual=result['receipt']['render_contract'].copy()
        policy=actual.pop('landscape_grass_streaming')
        resources=actual.pop('scene_resource_policy')
        warmup=actual.pop('streaming_warmup')
        assert actual=={**contract,'engine_warmup_count':120,'render_warmup_count':32}
        assert warmup['readback_by_job']==[{'job_name':'owned_sample','settings':{
            'engine_warm_up_count':120,'render_warm_up_count':32,
            'render_warm_up_frames':True,'use_camera_cut_for_warm_up':False}}]
        assert aa_values['spatial_sample_count']==aa_values['temporal_sample_count']==1
        assert warmup['blocking_streaming_flush'] is False
        assert policy['verified_jobs']==['owned_sample']
        assert dispatched==['executor'] and persisted[-1]['status']=='submitted'
        assert persisted[-1]['render_contract']==result['receipt']['render_contract']
        assert resources['policy']=='scene_inherited_resources_v1'
        observed=resources['readback_by_job'][0]
        assert observed['job_name']=='owned_sample'
        assert observed['settings']==resources['requested_settings']
        assert observed['settings']['texture_streaming']=='NONE'
        assert all(value is False for key,value in observed['settings'].items() if key!='texture_streaming')
        assert {k:v for k,v in values.items() if k not in observed['settings']}=={
            k:v for k,v in before.items() if k not in observed['settings']}
    assert renderer.persist is original_writer


def test_level_save_proxy_rejects_original_and_only_saves_owned_copy():
    state = {'world': '/Game/Scenes/A/Main.Main', 'saved': []}
    world = SimpleNamespace(get_path_name=lambda: state['world'])
    fake = SimpleNamespace(UnrealEditorSubsystem=object(),
        get_editor_subsystem=lambda _: SimpleNamespace(get_editor_world=lambda: world),
        EditorLoadingAndSavingUtils=SimpleNamespace(save_map=lambda w, p: state['saved'].append(p) or True))
    proxy = ue._OwnedLevelOperations(fake, object())
    with pytest.raises(ValueError, match='source scene'):
        proxy.save_current_level()
    assert state['saved'] == []
    state['world'] = ue.ASSETS + '/SceneTrials/L_owned.L_owned'
    assert proxy.save_current_level() is True
    assert state['saved'] == [ue.ASSETS + '/SceneTrials/L_owned']


def test_streamed_original_sublevel_actor_cannot_be_deleted_by_copy_preparation():
    removed=[]
    proxy=ue._OwnedActorOperations(SimpleNamespace(destroy_actor=lambda actor:removed.append(actor) or True))
    original=SimpleNamespace(get_path_name=lambda:'/Game/Scenes/A/Sublevel.Sublevel:PersistentLevel.DemoSequence')
    with pytest.raises(ValueError,match='Source-sublevel actor'):
        proxy.destroy_actor(original)
    assert removed==[]
    owned=SimpleNamespace(get_path_name=lambda:ue.ASSETS+'/SceneTrials/L_owned.L_owned:PersistentLevel.DemoSequence')
    assert proxy.destroy_actor(owned) is True
    assert removed==[owned]


def test_site_plan_hash_and_transitive_inputs_checked_before_ue_work(setup, monkeypatch):
    catalog, _, library, run = setup
    samples.build_plans(catalog, run=run, library=library, require_scene_count=2)
    monkeypatch.setattr(ue, 'RUN', run)
    monkeypatch.setattr(ue, 'PLAN_NAME', 'plans/scene_a_v1.json')
    digest = samples.sha(run / ue.PLAN_NAME)
    assert ue.plan(digest)[1]['scene_id'] == 'scene_a'
    Path(library['sources'][0]['path']).write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='source changed'):
        ue.plan(digest)


def test_exact26_primary_inventory_initializes_pending_catalog_without_rescreening(tmp_path):
    inventory=tmp_path/'inventory.json'
    scenes=[{'id':'existing_'+str(i),'map_path':'/Game/Scenes/Test/Map_'+str(i),
             'package':'Test','primary':True} for i in range(26)]
    samples.write(inventory,{'scenes':scenes})
    run=tmp_path/'run'
    result=samples.initialize_catalog(inventory,run=run)
    assert result['scenes']==26
    path=Path(result['catalog'])
    catalog=samples.read(path)
    assert {s['map'] for s in catalog['sites']}=={s['map_path'] for s in scenes}
    assert all(s['position'] is None for s in catalog['sites'])
    assert len({s['site_id'] for s in catalog['sites']})==26
    catalog['sites'][0]['position']={'x':1.,'y':2.,'z':3.}
    samples.write(path,catalog)
    assert samples.initialize_catalog(inventory,run=run)['existing_preserved'] is True
    assert samples.read(path)['sites'][0]['position']=={'x':1.,'y':2.,'z':3.}


def test_resumable_runner_reuses_completed_media_without_any_ue_dispatch(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    catalog,_,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('Verified media must not dispatch UE'))
    monkeypatch.setattr(runner.base,'RUN',runner.base.RUN)
    monkeypatch.setattr(runner.base,'remote',runner.base.remote)
    monkeypatch.setattr(runner.base,'verified_rows',lambda shots,_:{sid:{'shot_id':sid} for sid in shots})
    monkeypatch.setattr(runner.base,'complete_batch',lambda *args:pytest.fail('Verified groups must not rerun'))
    gallery_calls=[]
    def gallery(_):
        gallery_calls.append('full_validation');return {'reused':True}
    monkeypatch.setattr(runner,'build_gallery',gallery)
    assert runner.execute(run,site_ids=['scene_a'])=={'reused':True}
    assert gallery_calls==['full_validation']
    assert samples.read(run/'scene_sample_progress_v1.json')['verified_site_samples']==2
    assert not (run/'commands').exists()


@pytest.mark.parametrize('landscape_reused',[False,True])
def test_runner_updates_gallery_once_after_both_site_aspects(setup,monkeypatch,landscape_reused):
    import run_primary_scene_samples_v1 as runner
    catalog,_,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner.base,'RUN',runner.base.RUN)
    monkeypatch.setattr(runner.base,'remote',runner.base.remote)
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('Offline test must not dispatch UE'))
    monkeypatch.setattr(runner.base,'verified_rows',lambda shots,_:{
        sid:{'shot_id':sid} for sid,s in shots.items() if landscape_reused and s['orientation']=='landscape'})
    events=[]
    def complete(attempt,group,*args):
        events.append(group[0]['orientation'])
        return {'videos':[{'shot_id':s['shot_id']} for s in group]}
    def gallery(_):
        events.append('full_gallery_validation');return {'updated':True}
    monkeypatch.setattr(runner.base,'complete_batch',complete)
    monkeypatch.setattr(runner,'build_gallery',gallery)
    assert runner.execute(run,site_ids=['scene_a'])=={'updated':True}
    assert events==(['portrait'] if landscape_reused else ['landscape','portrait'])+['full_gallery_validation']
    assert samples.read(run/'scene_sample_progress_v1.json')['verified_site_samples']==2


@pytest.mark.parametrize('cadence,expected',[ (2,[4,6]), (3,[6]) ])
def test_runner_gallery_cadence_batches_new_scenes_and_flushes_final_tail(setup,monkeypatch,cadence,expected):
    import run_primary_scene_samples_v1 as runner
    catalog,sites,library,run=setup
    sites=[dict(sites[0],site_id='scene_'+str(i)) for i in range(3)]
    samples.write(catalog,{'sites':sites})
    samples.build_plans(catalog,run=run,library=library,require_scene_count=3)
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner.base,'RUN',runner.base.RUN)
    monkeypatch.setattr(runner.base,'remote',runner.base.remote)
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('Offline test must not dispatch UE'))
    monkeypatch.setattr(runner.base,'verified_rows',lambda *args:{})
    completed=[];refreshes=[]
    def complete(attempt,group,*args):
        completed.extend(s['shot_id'] for s in group)
        return {'videos':[{'shot_id':s['shot_id']} for s in group]}
    def gallery(_):
        refreshes.append(len(completed));return {'verified':len(completed)}
    monkeypatch.setattr(runner.base,'complete_batch',complete)
    monkeypatch.setattr(runner,'build_gallery',gallery)
    assert runner.execute(run,gallery_every_scenes=cadence)=={'verified':6}
    assert refreshes==expected


def release_context(current,*,dirty=False,rendering=False):
    events=[];state={'map':current}
    classes=[object() for _ in range(3)]
    def load(path):events.append(('load',path));state['map']=path;return True
    subsystems={classes[0]:SimpleNamespace(is_rendering=lambda:rendering,get_active_executor=lambda:None),
        classes[1]:SimpleNamespace(get_editor_world=lambda:SimpleNamespace(get_path_name=lambda:state['map']+'.World')),
        classes[2]:SimpleNamespace(load_level=load)}
    u=SimpleNamespace(Paths=SimpleNamespace(project_dir=lambda:'D:/UE/projects/datatry_02'),
        MoviePipelineQueueSubsystem=classes[0],UnrealEditorSubsystem=classes[1],LevelEditorSubsystem=classes[2],
        get_editor_subsystem=subsystems.__getitem__,
        EditorLoadingAndSavingUtils=SimpleNamespace(
            get_dirty_map_packages=lambda:[SimpleNamespace(get_name=lambda:'unsaved')] if dirty else [],
            get_dirty_content_packages=lambda:[]),
        LevelSequenceEditorBlueprintLibrary=SimpleNamespace(close_level_sequence=lambda:events.append('close_sequence')),
        collect_garbage=lambda:events.append('garbage_collection'))
    return u,events


def test_owned_world_release_changes_only_clean_owned_world_and_preserves_dirty_guard():
    import run_primary_scene_samples_v1 as runner
    owned=runner.ASSETS+'/SceneTrials/L_owned'
    u,events=release_context(owned)
    result=runner.release_owned_world(u)
    assert result['status']=='released_to_entry' and result['after_map']=='/Engine/Maps/Entry'
    assert events==['close_sequence',('load','/Engine/Maps/Entry'),'garbage_collection']
    for current in ('/Engine/Maps/Entry','/Game/Scenes/Cherry/Original'):
        u,events=release_context(current)
        assert runner.release_owned_world(u)['status'].startswith('skipped_')
        assert not events
    for options in ({'dirty':True},{'rendering':True}):
        u,events=release_context(owned,**options)
        with pytest.raises(RuntimeError):runner.release_owned_world(u)
        assert not events


@pytest.mark.parametrize('release_fails',[False,True])
def test_prepare_release_is_a_separate_remote_before_prepare_and_failure_blocks_it(monkeypatch,tmp_path,release_fails):
    import run_primary_scene_samples_v1 as runner
    calls=[]
    def once(code,label,run):
        calls.append((code,label))
        if release_fails:raise RuntimeError('release failed')
    monkeypatch.setattr(runner,'_remote_once',once)
    prepare='print(json.dumps(review.prepare(u,["shot"],"digest")))'
    if release_fails:
        with pytest.raises(RuntimeError,match='release failed'):runner.remote(prepare,'sample_prepare',tmp_path)
        assert len(calls)==1
    else:
        runner.remote(prepare,'sample_prepare',tmp_path)
        assert len(calls)==2 and calls[1]==(prepare,'sample_prepare')
    assert calls[0][1]=='sample_prepare_release'
    assert 'release_owned_world(u)' in calls[0][0] and 'review.prepare(' not in calls[0][0]


def test_runner_stop_marker_prevents_preparation_or_render_dispatch(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    catalog,_,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    (run/'STOP').write_text('stop',encoding='utf-8')
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('STOP must prevent all UE dispatch'))
    monkeypatch.setattr(runner.base,'RUN',runner.base.RUN)
    monkeypatch.setattr(runner.base,'remote',runner.base.remote)
    monkeypatch.setattr(runner.base,'verified_rows',lambda *args:pytest.fail('STOP must precede per-site work'))
    with pytest.raises(RuntimeError,match='STOP marker'):
        runner.execute(run,site_ids=['scene_a'])


@pytest.mark.parametrize('active',['survey','point_checker','mrq'])
def test_remote_idle_guard_blocks_active_shared_ue_work_before_dispatch(active):
    import run_primary_scene_samples_v1 as runner
    fake=SimpleNamespace(MoviePipelineQueueSubsystem=object(),
        get_editor_subsystem=lambda _:SimpleNamespace(is_rendering=lambda:active=='mrq',
                                                      get_active_executor=lambda:None))
    if active=='survey':setattr(fake,'_dm_all_primary_scene_survey_v1',{'status':'running'})
    if active=='point_checker':setattr(fake,'_dm_site_review_v1',{'job':{'status':'running'}})
    context={'u':fake}
    with pytest.raises(AssertionError,match='active'):
        exec(runner.IDLE_GUARD+'dispatched=True',context)
    assert 'dispatched' not in context


def test_idle_guard_allows_idle_editor_and_empty_staged_id_list_never_means_all_sites(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    fake=SimpleNamespace(MoviePipelineQueueSubsystem=object(),
        get_editor_subsystem=lambda _:SimpleNamespace(is_rendering=lambda:False,get_active_executor=lambda:None))
    context={'u':fake}
    exec(runner.IDLE_GUARD+'dispatched=True',context)
    assert context['dispatched'] is True
    catalog,_,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner,'remote',lambda *args:pytest.fail('Empty eligible list must not dispatch'))
    monkeypatch.setattr(runner,'build_gallery',lambda _:{'scenes':2})
    assert runner.execute(run,site_ids=[])['no_site_dispatch_requested'] is True


def test_map_sample_failure_records_stop_and_prevents_blind_retry(setup,monkeypatch):
    import run_primary_scene_samples_v1 as runner
    catalog,_,library,run=setup
    samples.build_plans(catalog,run=run,library=library,require_scene_count=2)
    monkeypatch.setattr(runner,'S',run.parents[1]/'scripts/unreal')
    monkeypatch.setattr(runner.base,'RUN',runner.base.RUN)
    monkeypatch.setattr(runner.base,'remote',runner.base.remote)
    monkeypatch.setattr(runner.base,'verified_rows',lambda *args:{})
    calls=[]
    def fail(*args,**kwargs):
        calls.append(args[0])
        raise RuntimeError('first map failed prepare')
    monkeypatch.setattr(runner.base,'complete_batch',fail)
    with pytest.raises(RuntimeError,match='STOP recorded'):
        runner.execute(run,site_ids=['scene_a'])
    assert (run/'STOP').is_file()
    failures=list((run/'sample_failures').glob('*.json'))
    assert len(failures)==1
    assert samples.read(failures[0])['site_id']=='scene_a'
    with pytest.raises(RuntimeError,match='STOP marker'):
        runner.execute(run,site_ids=['scene_a'])
    assert len(calls)==1


def _visual_review_fixture(tmp_path, ledger='agent_dynamic_exposure_notes_v2.json'):
    clips = [{'shot_id': aspect, 'orientation': aspect, 'playable': True,
              'timeline_contact': 'contacts/' + aspect + '.jpg', 'timeline_contact_sha256': 'contact-' + aspect,
              'video': 'videos/' + aspect + '.mp4', 'video_sha256': 'video-' + aspect}
             for aspect in ('landscape', 'portrait')]
    site = {'site_id': 'current', 'revision': 'v3',
            'sample_plan': {'path': 'plans/current_v3.json', 'sha256': 'current-plan'}, 'clips': clips}
    rows = [{'site_id': site['site_id'], 'shot_id': clip['shot_id'], 'viewed': True,
             'plan': {'path': str(tmp_path / site['sample_plan']['path']), 'sha256': 'current-plan'},
             'contact': {'path': str(tmp_path / clip['timeline_contact']), 'sha256': clip['timeline_contact_sha256']},
             'video': {'path': str(tmp_path / clip['video']), 'sha256': clip['video_sha256']},
             'needs_improvement': False, 'remaining_issues_zh': [], 'recommendation_zh': '保留当前候选，待用户审查。'}
            for clip in clips]
    return site, {ledger: {'items': rows}}, rows


def test_visual_review_data_includes_both_new_ledgers(tmp_path):
    names = ('agent_dynamic_exposure_notes_v2.json', 'agent_new_point_visual_notes_v3.json')
    for name in names:
        samples.write(tmp_path / name, {'items': []})
    records, pins = samples.visual_review_data(tmp_path)
    assert set(records) == set(names)
    assert {pin['path']: pin['sha256'] for pin in pins} == {
        name: samples.sha(tmp_path / name) for name in names}


@pytest.mark.parametrize('ledger', ['agent_dynamic_exposure_notes_v2.json', 'agent_new_point_visual_notes_v3.json'])
def test_visual_review_current_media_pin_match_is_initial_only(tmp_path, ledger):
    site, records, _ = _visual_review_fixture(tmp_path, ledger)
    result = samples.visual_review_card(site, records, tmp_path)
    assert result['status'] == 'sampled_no_obvious_issue'
    assert result['human_acceptance'] == 'pending'
    assert '抽帧' in result['note_zh'] and '未连续观看' in result['note_zh']
    assert '保留当前候选' in result['observations_zh'][0]


def test_visual_review_remaining_framing_choice_is_reminder_not_required_repair(tmp_path):
    site, records, rows = _visual_review_fixture(tmp_path)
    records['scene_visual_retries_v1.json'] = {'items': [{
        'site_id': site['site_id'], 'current_revision': 'v3', 'status': 'queued_review'}]}
    rows[1]['remaining_issues_zh'] = ['竖屏伸臂出画，构图取舍由用户判断。']
    result = samples.visual_review_card(site, records, tmp_path)
    assert result['status'] == 'initial_review_recorded'
    assert '已有初审' in result['label_zh']
    assert any('构图取舍' in text for text in result['observations_zh'])
    rows[1]['needs_improvement'] = True
    assert samples.visual_review_card(site, records, tmp_path)['status'] == 'needs_improvement'


@pytest.mark.parametrize('field', ['plan_path', 'plan_sha', 'contact_path', 'contact_sha',
                                  'video_path', 'video_sha', 'shot_id', 'site_id', 'viewed'])
def test_visual_review_new_ledgers_reject_stale_or_changed_binding(tmp_path, field):
    site, records, rows = _visual_review_fixture(tmp_path)
    for row in rows:
        if field in ('shot_id', 'site_id'):
            row[field] = 'old'
        elif field == 'viewed':
            row[field] = False
        else:
            pin, key = field.split('_')
            row[pin]['sha256' if key == 'sha' else key] = 'old'
    assert samples.visual_review_card(site, records, tmp_path)['status'] == 'unviewed'


def test_visual_review_partial_new_contact_never_claims_scene_clear(tmp_path):
    site, records, rows = _visual_review_fixture(tmp_path)
    rows[1]['viewed'] = False
    result = samples.visual_review_card(site, records, tmp_path)
    assert result['status'] == 'initial_review_recorded'
    assert '部分' in result['label_zh'] and result['human_acceptance'] == 'pending'


@pytest.mark.parametrize('source', ['legacy', 'root'])
def test_visual_review_legacy_and_root_paths_remain_compatible(tmp_path, source):
    site, _, rows = _visual_review_fixture(tmp_path)
    if source == 'legacy':
        records = {'agent_scene_visual_notes_v1.json': {'scenes': [{
            'site_id': site['site_id'], 'plan': rows[0]['plan'], 'contacts': [
                {'shot_id': row['shot_id'], 'viewed': True, 'contact': row['contact']['path'],
                 'visible_issues': [], 'retry_recommended': False} for row in rows]}]}}
    else:
        records = {'root_execution_progress_v1.json': {'sites': [{
            'site_id': site['site_id'], 'visual_status': 'sampled_no_obvious_issue',
            'reviewed_contacts': [row['contact']['path'] for row in rows]}]}}
    assert samples.visual_review_card(site, records, tmp_path)['status'] == 'sampled_no_obvious_issue'
