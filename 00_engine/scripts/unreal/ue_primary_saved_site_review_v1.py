"""Versioned panel adapter; the historical runtime8 worker stays byte-identical.

Root invokes this through the existing panel only after the serial survey/render
work is idle. Existing saved-point files and the normal panel actions are reused.
"""
from pathlib import Path
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import traceback
import uuid

S = Path(__file__).resolve().parent
ORIGINAL = S/'ue_scene_site_review_v1.py'
ORIGINAL_SHA256 = 'ef6fc7e8b1a3b6b93cd9e9d7a555d89e7ae1c5d89c0521f8355ea73bfa30ca29'
LIVE = '_dm_primary_saved_site_review_v1'
CACHE = '_dm_primary_saved_site_review_worker_v1'
ADAPTER_REVISION = 5


def install_scene_switch_behaviors(worker):
    """Keep unloaded UObject wrappers out of state readback; preserve dirty maps."""
    if hasattr(worker, 'restore'):
        original_restore = getattr(worker, '_primary_original_restore', worker.restore)
        worker._primary_original_restore = original_restore
        def restore():
            original_restore()
            state = worker.live()
            for key in ('playback_selection', 'playback_site', 'playback_shot', 'playback_started'):
                state.pop(key, None)
            state['playback'] = {'playing': False, 'time_seconds': 0., 'duration_seconds': 0., 'loop': False}
        worker.restore = restore

    if hasattr(worker, 'start_check'):
        original_check = getattr(worker, '_primary_original_start_check', worker.start_check)
        worker._primary_original_start_check = original_check
        def start_check(request, all_combinations):
            worker.require_site()
            if request.get('excluded_combinations') and request.get('decisions_stamp') != worker.stamp():
                raise ValueError('点位或场景已改变，旧排除清单不能用于本次检查；请刷新状态并重新确认排除项。')
            return original_check(request, all_combinations)
        worker.start_check = start_check

    if hasattr(worker, 'stop_playback'):
        def stop_playback():
            worker.pause_playback()
            state = worker.live()
            selection = state.get('preview') or {}
            if selection and state.get('site') and state['site']['map'] == worker.current_map():
                worker.preview({**selection, 'time_seconds': 0.})
            if state.get('playback'):
                state['playback']['time_seconds'] = 0.
        worker.stop_playback = stop_playback

    def synchronize():
        state = worker.live()
        site, marker = state.get('site'), state.get('marker')
        if not site:
            return state
        valid = False
        if site['map'] == worker.current_map() and marker is not None:
            try:
                valid = bool(worker.u.SystemLibrary.is_valid(marker))
            except (TypeError, RuntimeError):
                pass  # An unloaded UE wrapper can throw instead of returning False.
        if valid:
            state['site']['position'] = dict(zip(('x', 'y', 'z'), worker.xyz(marker.get_actor_location())))
            state['site']['yaw'] = float(marker.get_actor_rotation().yaw)
        else:
            worker.write(worker.RUN/'switch_recovery'/(uuid.uuid4().hex+'_point.json'),
                         {'site': copy.deepcopy(site), 'reason': 'point_actor_unloaded'})
            if site['map'] == worker.current_map():
                worker.restore()
                return state
            worker.pause_playback()
            worker.cancel()
            state.update(site=None, marker=None, character=None, camera=None,
                         job=None, report=None, ranges=False, preview={}, playback={})
            for key in ('playback_selection', 'playback_site', 'playback_shot', 'playback_started'):
                state.pop(key, None)
        return state

    def open_scene(request):
        import scene_site_catalog_v1 as directory
        target = request.get('map_path')
        if target not in {s['map_path'] for s in directory.build_catalog()['scenes']}:
            raise ValueError('目标不在场景目录中。')
        if target == worker.current_map():
            return
        u = worker.u
        if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
            raise ValueError('当前正在渲染，请结束后打开场景。')
        state = synchronize()
        recovery_id = uuid.uuid4().hex
        record = {'source_map': worker.current_map(), 'target_map': target,
                  'site': copy.deepcopy(state.get('site')), 'backup_map': None}
        worker.write(worker.RUN/'switch_recovery'/(recovery_id+'.json'), record)
        # Never retain UPackage wrappers across LoadLevel: they pin the old world in GC.
        dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            # A separate map copy preserves user edits as well as temporary preview dirtiness.
            if any(name != worker.current_map() for name in dirty):
                raise ValueError('其他关卡也有未保存修改，请先在 UE 处理后切换。')
            backup = '/Game/DataMake/Validation/SceneSiteSwitchRecovery/L_'+recovery_id
            if not u.EditorLoadingAndSavingUtils.save_map(worker.world(), backup):
                raise ValueError('未保存现场备份失败，已取消切换。')
            record['backup_map'] = backup
            worker.write(worker.RUN/'switch_recovery'/(recovery_id+'.json'), record)
        worker.restore()
        if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(target):
            raise ValueError('场景打开失败；原点位和未保存现场已有恢复记录。')
        state = worker.live()
        state['original_view'] = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()
        viewport = u.get_editor_subsystem(u.LevelEditorSubsystem)
        state['original_fov'] = viewport.get_level_viewport_fov(viewport.get_active_viewport_config_key())

    worker.synchronize, worker.open_scene = synchronize, open_scene
    worker._primary_adapter_revision = ADAPTER_REVISION
    return worker


def apply_camera_exposure(component, value):
    """Retain the call shape; saved point EV no longer overrides level exposure."""
    from level_exposure_policy_v1 import apply
    return apply(component)


def activate_imported_exclusions(worker):
    """Bind explicit catalog exclusions to the actual loaded point, never a pass."""
    state = worker.live()
    site = state['site']
    if not site.get('imported_camera_standard'):
        return  # Existing user points retain the original decision semantics.
    standard = site['imported_camera_standard']
    if (standard.get('configuration') != worker.geo.pin(worker.geo.CAMERA_STANDARD)
            or standard.get('standard_id') != 'nonface_landscape_distance050_fov_compensated_v3'
            or standard.get('distance_factor') != .5 or standard.get('scope') != 'nonface_landscape'
            or standard.get('portrait_and_face_unchanged') is not True):
        raise ValueError('Saved point does not match the current50% nonface landscape standard')
    if site.get('imported_preview_semantics') == 'active_private_version_adapter_v1':
        return  # Never replace a user's later panel decisions with old imports.
    rows = copy.deepcopy(site.get('imported_excluded_combinations', []))
    combinations = {(s['motion_id'], s['camera_id'], s['orientation']) for s in state['local']['shots']}
    if any(r.get('decision') != 'excluded' or
           tuple(r.get(k) for k in ('action_id', 'camera_id', 'aspect')) not in combinations for r in rows):
        raise ValueError('Imported exclusions must be explicit existing combinations, without allowed decisions')
    site.update(allowed_combinations=rows, issue_reviews={},
                imported_preview_semantics='active_private_version_adapter_v1', human_acceptance='pending')
    state['report'] = None
    site['decisions_stamp'] = worker.stamp()


def install_private_behaviors(worker):
    original_live, original_stamp = worker.live, worker.stamp
    original_load, original_preview = worker.load_site, worker.preview
    adapter_pin = worker.geo.pin(__file__)
    worker._primary_adapter_pin = adapter_pin

    def live():
        state = original_live()
        pin = worker._primary_adapter_pin
        if pin not in state['runtime_inputs']:
            state['runtime_inputs'].append(pin)
            state['input_stats'], state['input_result'] = {}, None
        return state

    def stamp():
        state = worker.live()
        site = state.get('site') or {}
        return worker.geo.canonical_sha({'original_stamp': original_stamp(),
            'exposure_compensation': site.get('exposure_compensation', 0.),
            'catalog_exclusions': site.get('exclusions', [])})

    def load_site(request):
        result = original_load(request)
        activate_imported_exclusions(worker)
        return result

    def preview(request):
        state = worker.require_site()
        value = state['site'].get('exposure_compensation', 0.)
        result = original_preview(request)
        component = state['camera'].get_component_by_class(worker.u.CameraComponent)
        apply_camera_exposure(component, value)
        return result

    worker.live, worker.stamp = live, stamp
    worker.load_site, worker.preview = load_site, preview
    return install_scene_switch_behaviors(worker)


def install_production_runtime(worker):
    """Refresh cached code only at command boundaries, then install privately."""
    names = ('hair_eye_color_runtime_v1', 'ue_hair_coverage_runtime_v1', 'scene_site_hair_color_trials_v1',
             'hair_color_neutral_trial_runtime_v1', 'scene_site_appearance_v1',
             'ue_scene_site_appearance_v1', 'ue_production_site_runtime_v1')
    refreshed = False
    for name in names:
        source = S / (name + '.py')
        if name == 'hair_color_neutral_trial_runtime_v1' and not source.is_file():
            continue  # The optional trial implementation may be published later.
        current = hashlib.sha256(source.read_bytes()).hexdigest()
        module = importlib.import_module(name)
        if getattr(module, '_primary_loaded_source_sha256', None) != current:
            state = getattr(worker.u, worker.LIVE, {})
            if (state.get('job') or {}).get('status') == 'running':
                raise ValueError('检查期间工具代码已更新，请先停止检查再加载新版工具。')
            module = importlib.reload(module)
            module._primary_loaded_source_sha256 = current
            refreshed = True
    if refreshed:
        worker._production_site_context = None
        importlib.import_module('scene_site_appearance_v1')._formal_cache = None
        cache = getattr(worker.u, '_dm_scene_site_appearance_cache_v1', None)
        if cache is not None:
            cache.clear()
    return importlib.import_module('ue_production_site_runtime_v1').install(worker)


def refresh_adapter_pin(worker):
    """Upgrade a cached revision4 live closure without wrapping it a second time."""
    pin = worker.geo.pin(__file__)
    worker._primary_adapter_pin = pin
    function = getattr(worker, '_production_site_originals', {}).get('live', worker.live)
    # Revision4 captured the file pin in a closure; revision5 reads the worker
    # attribute. Updating that one captured value prevents perpetual stale pins.
    for name, cell in zip(getattr(function, '__code__', SimpleCode()).co_freevars,
                          getattr(function, '__closure__', None) or ()):
        if name == 'adapter_pin':
            cell.cell_contents = pin


class SimpleCode:
    co_freevars = ()


def private_worker():
    import unreal as u
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('Historical pinned runtime8 worker changed; do not overwrite its evidence')
    cached = getattr(u, CACHE, None)
    if cached is not None:
        if getattr(cached, '_primary_adapter_revision', None) != ADAPTER_REVISION:
            # The production installer owns its wrappers. Detach them before
            # refreshing scene-switch fixes so restore cannot lose cache cleanup.
            for name, original in getattr(cached, '_production_site_originals', {}).items():
                setattr(cached, name, original)
            if hasattr(cached, '_production_site_installed'):
                delattr(cached, '_production_site_installed')
            install_scene_switch_behaviors(cached)
        refresh_adapter_pin(cached)
        return install_production_runtime(cached)
    spec = importlib.util.spec_from_file_location('_dm_primary_saved_site_worker_private', ORIGINAL)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    old = getattr(u, worker.LIVE, None)
    if old:
        if (old.get('job') or {}).get('status') == 'running':
            raise ValueError('Finish the original panel check before switching review adapters')
        # Use the original namespace for this one handoff cleanup; no source or
        # saved-point file is changed, and no duplicate preview actors remain.
        worker.restore()
    worker.LIVE = LIVE
    worker.PREFIX = 'DM_SiteReview_Primary_'
    install_private_behaviors(worker)
    install_production_runtime(worker)
    setattr(u, CACHE, worker)
    return worker


def dispatch(request):
    return private_worker().dispatch(request)


if __name__ == '__main__':
    request = globals().get('DM_SCENE_SITE_REVIEW_REQUEST', {'action': 'status'})
    try:
        worker = private_worker()
        result = worker.dispatch(request)
    except Exception as exc:
        result = {'success': False, 'action': request.get('action'), 'request_id': request.get('request_id'),
                  'error': str(exc), 'traceback': traceback.format_exc()}
    run = S.parents[1]/'outputs/scene_site_review_20261014_v1'
    path = run/'replies'/((request.get('request_id') or uuid.uuid4().hex)+'.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('DM_SCENE_SITE_REVIEW='+json.dumps({'success': True, 'result_file': str(path)}))
