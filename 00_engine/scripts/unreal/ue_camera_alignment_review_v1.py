"""Isolated camera calibration preparation and render adapter. SCENE_CAMERA_SEQUENCE §12."""
from pathlib import Path
import importlib.util
import hashlib
import json
import math

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_motion_scene_alignment_20261012_v1'
PRIOR = S.parents[1] / 'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1'
ASSETS = '/Game/DataMake/Validation/CameraMotionSceneAlignment20261012'
PLAN_NAME = 'camera_trial_plan_v2.json'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
_SOURCE_SHOTS = None


def approved_source(shot):
    global _SOURCE_SHOTS
    if _SOURCE_SHOTS is None:
        _SOURCE_SHOTS = {s['motion_id']:s for s in read(PRIOR/'camera_trial_plan_v1.json')['shots']
                         if s['group']=='motions'}
    return _SOURCE_SHOTS[shot['motion_id']]


def validate_body_contract(shot):
    source = approved_source(shot)
    cross = shot.get('group') == 'legacy_cross_sex'
    if (shot['sex']==source['sex']) == cross:
        raise ValueError('Unexpected action sex')
    for field in ('source_start_seconds','source_end_seconds','source_body_play_rate',
                  'window_start_seconds','duration_seconds','frame_count','fps'):
        if not math.isclose(shot[field],source[field],rel_tol=0,abs_tol=1e-6):
            raise ValueError('Calibration changed accepted body window: '+field)
    if not cross and shot['source_animation'] != source['source_animation']:
        raise ValueError('Calibration changed accepted animation source')
    return source


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def check(record):
    path = Path(record['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Frozen source changed: ' + str(path))


def module(name):
    spec = importlib.util.spec_from_file_location('_alignment_' + name, S / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def existing_composite(u, shot):
    approved = validate_body_contract(shot)
    if shot.get('group') == 'legacy_cross_sex':
        record = read(RUN / 'legacy_motion' / (shot['motion_id'] + '_' + shot['sex'] + '_v1.json'))
        if (not record['success'] or record['action_id']!=shot['motion_id']
                or record['sex']!=shot['sex'] or record['source_sex']!=approved['sex']
                or record['target']['asset'].split('.')[0] != shot['source_animation'].split('.')[0]):
            raise ValueError('Cross-sex motion has no matching validation')
        check(record['target'])
        for source in record['protected_sources']:
            check(source)
        loop = module('ue_cfd40_full_motion_loop_v1')
        loop.RUN, loop.ASSET_ROOT = RUN, ASSETS
        faces, selection = loop.accepted_faces()
        choice, proof = faces[(shot['sex'], 'smile')]
        return loop.ensure_composite(u, shot['sex'],
            {'path': shot['source_animation'], 'action_id': shot['motion_id']}, choice, proof, selection)
    receipt = read(PRIOR / 'sequences' / (approved['shot_id'] + '.json'))
    if not receipt['success']:
        raise ValueError('Prior composition preparation failed')
    check(receipt['plan'])
    detail = receipt['composition']
    check(detail['cache_receipt'])
    cache = read(detail['cache_receipt']['path'])
    if not cache['success'] or cache['animation_path'] != detail['animation_path']:
        raise ValueError('Composition cache differs from prior receipt')
    check(cache['asset'])
    check(cache['composition_report'])
    for source in cache['spec']['sources']:
        check(source)
    asset = u.load_asset(detail['animation_path'])
    if not isinstance(asset, u.AnimSequence):
        raise ValueError('Current source composition is missing')
    return asset, detail


def configured_module(name):
    result = module(name)
    if name == 'ue_motion_scene_sequence_v1':
        result.ALLOWED_PREFIX = ASSETS + '/'
    if name == 'ue_motion_scene_render_v1':
        result.RUN, result.ASSET_ROOT = RUN, ASSETS
        result.LIVE_ATTRIBUTE = '_dm_camera_alignment_render_v1'
    return result


def adapter():
    result = module('ue_motion_portrait_scene_pilot_v1')
    result.RUN, result.A = RUN, ASSETS
    result.PLAN_NAME = PLAN_NAME
    result.ensure_motion = existing_composite
    result.module = configured_module
    return result


def prepare(u, selected_ids=None):
    preflight(u,RUN/PLAN_NAME,selected_ids)
    return adapter().prepare(u, selected_ids)


def preflight(u, plan_path, selected_ids):
    if Path(u.Paths.project_dir()).resolve()!=CONTENT.parent.resolve():
        raise ValueError('Unexpected UE project')
    adapter().clean(u)
    shots=read(plan_path)['shots']
    wanted=set(selected_ids) if selected_ids is not None else {s['shot_id'] for s in shots}
    selected=[s for s in shots if s['shot_id'] in wanted]
    if not wanted or len(selected)!=len(wanted):
        raise ValueError('Unknown or empty shot selection')
    checked=set()
    for shot in selected:
        validate_body_contract(shot)
        key=(shot['motion_id'],shot['sex'])
        if key not in checked:
            existing_composite(u,shot)
            checked.add(key)


def cross_adapter():
    stage = RUN / 'legacy_stage'
    stage.mkdir(exist_ok=True)
    source = RUN / 'legacy_cross_sex_camera_plan_v1.json'
    target = stage / 'camera_trial_plan_v1.json'
    if target.exists():
        if target.read_bytes() != source.read_bytes():
            raise ValueError('Frozen cross-sex stage plan changed')
    else:
        with target.open('xb') as stream:
            stream.write(source.read_bytes())
    result = adapter()
    result.RUN = stage
    result.PLAN_NAME = 'camera_trial_plan_v1.json'
    return result


def prepare_cross(u, selected_ids=None):
    preflight(u,RUN/'legacy_cross_sex_camera_plan_v1.json',selected_ids)
    return cross_adapter().prepare(u, selected_ids)


def render_cross(u, attempt, ids, width=1280, height=720):
    preflight(u,RUN/'legacy_cross_sex_camera_plan_v1.json',ids)
    return cross_adapter().render(u, attempt, ids, width, height)


def render(u, attempt, ids, width=1280, height=720):
    preflight(u,RUN/PLAN_NAME,ids)
    return adapter().render(u, attempt, ids, width, height)


def status(u):
    return configured_module('ue_motion_scene_render_v1').status(u)
