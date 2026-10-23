"""Full scene/site panel for all 40 completed user-edited 20261019 identities.

Reuses formal wardrobe, hair, palette, face, motion and camera workflows. Old
saved sites are copied once; their appearance and validation never become new
revision acceptance. Keep the existing run and entry point for user saves.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import traceback
import uuid

SCRIPTS = Path(__file__).resolve().parent
RUN = SCRIPTS.parents[1] / 'outputs/pair_scene_review_20261019_v1'
BASE_RUN = RUN.parent / 'scene_site_review_20261014_v1'
from night_character_review_v1 import DELIVERY, delivery
IDS = tuple(r['character_id'] for r in delivery()['cases'])
CACHE = '_dm_pair_scene_review_20261019_v1'
TEXTURE_PROFILE_CACHE = '_dm_local_texture_profile_20261021_v1'


def ensure_local_texture_budget(u):
    """Apply this machine's review budget once per editor session."""
    if hasattr(u, TEXTURE_PROFILE_CACHE):
        return getattr(u, TEXTURE_PROFILE_CACHE)
    from mrq_streaming_warmup_v1 import pool_profile, POOL_CVAR
    profile = pool_profile()
    if profile['pool_size_mb'] is not None:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        previous = u.SystemLibrary.get_console_variable_int_value(POOL_CVAR)
        u.SystemLibrary.execute_console_command(world, POOL_CVAR + ' ' + str(profile['pool_size_mb']))
        actual = u.SystemLibrary.get_console_variable_int_value(POOL_CVAR)
        if actual != profile['pool_size_mb']:
            raise RuntimeError('当前UE未能应用本机纹理预算。')
        profile = {**profile, 'previous_pool_size_mb': previous, 'applied_pool_size_mb': actual}
    setattr(u, TEXTURE_PROFILE_CACHE, profile)
    return profile


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def restricted_catalog(data):
    data = copy.deepcopy(data)
    data['identities'] = [r for r in data['identities'] if r['id'] in IDS]
    if {r['id'] for r in data['identities']} != set(IDS):
        raise ValueError('新版40人目录不完整。')
    numbers = {'female':0, 'male':0}
    for row in data['identities']:
        numbers[row['sex']] += 1
        row['label'] = ('女' if row['sex'] == 'female' else '男') + str(numbers[row['sex']]) + ' · ' + row['id'] + '（新版）'
    data['sources']['character_revision'] = pin(DELIVERY)
    return data


def prepare():
    """No UE mutation. Preserve originals and never overwrite a user save."""
    imported = read(DELIVERY)
    if (imported['status'] != 'imports_completed'
            or {r['character_id'] for r in imported['cases']} != set(IDS)):
        raise ValueError('请使用昨晚40名新版角色的完成交接。')
    RUN.mkdir(parents=True, exist_ok=True)
    for name in ('site_review_local_geometry_v1.json', 'site_review_catalog_v1.json'):
        dest = RUN / name
        if not dest.exists():
            dest.write_bytes((BASE_RUN / name).read_bytes())
    for source in sorted((BASE_RUN / 'sites').glob('*.json')):
        dest = RUN / 'sites' / source.name
        if dest.exists():
            continue
        old = read(source)
        site = old['site']
        if site.get('site_id') != source.stem:
            raise ValueError('旧点位文件名与编号不一致：' + str(source))
        write(RUN / 'inherited_sites' / source.name, old)
        new = copy.deepcopy(old)
        for key in ('appearance_config_id', 'appearance_selection', 'decisions_stamp'):
            new['site'].pop(key, None)
        new['site']['review_runtime'] = 'inherited_before_pair_revision'
        new['report'] = None
        new['human_acceptance'] = 'pending_new_character_revision'
        new['inherited_source'] = pin(source)
        write(dest, new)
    return RUN


def graph_and_data():
    from motion_library_review_adapter_v1 import PrivateModules
    graph = PrivateModules()
    contract = graph.load('scene_site_appearance_v1')
    import pair_review_fast_runtime_v1 as fast_runtime
    fast_runtime.bind_catalog(contract)
    data = restricted_catalog(contract.catalog())
    contract.catalog = lambda: copy.deepcopy(data)
    from night_character_review_v1 import bind_saved_selections
    bind_saved_selections(contract, data)
    directory = graph.load('scene_site_catalog_v1')
    original_catalog = directory.build_catalog

    def scenes(*args, **kwargs):
        kwargs['saved_site_roots'] = (RUN / 'sites',)
        result = original_catalog(*args, **kwargs)
        result['scenes'] = [r for r in result['scenes'] if r['primary']]
        for row in result['scenes']:
            if row['map_path'] == '/Game/Scenes/FuturisticMetaCity/Maps/VirtualMetaCity':
                reviewed = any(s['map'] == row['map_path'] and s['id'].startswith('site_')
                               for s in result['sites'])
                row['shooting_point_status'] = 'saved_user_point' if reviewed else 'pending_user_selection'
                if not reviewed:
                    row['label'] += '（待选拍摄点）'
        result['counts'].update(maps=len(result['scenes']),
            packages=len({r['package'] for r in result['scenes']}))
        return result

    directory.build_catalog = scenes
    import scene_review_selection_policy_v1 as selection_policy
    selection_policy.install(graph.load('ue_production_site_runtime_v1'))
    return graph, data


def install_camera_checks(current):
    """Keep fast browsing; make explicit camera checks cover simple collision."""
    import ue_camera_collision_proxy_review_v1 as proxy
    w = current['worker']
    proxy.install(w)
    if current.get('camera_check_method') == proxy.METHOD:
        return current
    old_stamp, old_state, old_stale = w.stamp, w.state, w.job_stale_reason

    def stamp():
        return hashlib.sha256((old_stamp() + ':' + proxy.METHOD).encode('utf-8')).hexdigest()

    def job_stale_reason(job, force=False):
        # Start already refreshes in fast_runtime.dispatch. End must not reuse
        # that same cached snapshot when checking for intervening scene edits.
        if force:
            current['fast_caches']['scene'].clear()
        return old_stale(job, force=force)

    def state():
        result = old_state()
        result['camera_check_method'] = proxy.METHOD
        result['scene_freshness_policy'] = 'explicit_check_snapshot_not_continuous'
        report = (result.get('check') or {}).get('report') or {}
        if report and report.get('camera_check_method') != proxy.METHOD:
            result.update(current_result_fresh=False, full_matrix_fresh=False,
                          needs_recheck=True,
                          recheck_reason='遮挡检测已更新，旧报告未做简化碰撞补查，请重新检查。')
        return result

    w.stamp, w.state, w.job_stale_reason = stamp, state, job_stale_reason
    current['camera_check_method'] = proxy.METHOD
    return current


def worker(u):
    ensure_local_texture_budget(u)
    import ue_pair_revision_runtime_20261019_v1 as revision
    import pair_review_fast_runtime_v1 as fast_runtime
    import pair_review_site_intent_v1 as site_intent
    import scene_review_selection_policy_v1 as selection_policy
    cached = getattr(u, CACHE, None)
    if cached is not None:
        return selection_policy.install_worker(site_intent.install(install_camera_checks(fast_runtime.install(cached))))
    prepare()
    graph, data = graph_and_data()
    assembly = graph.load('ue_scene_site_appearance_v1')
    import night_character_review_v1 as night
    configuration = night.configuration(revision)
    revision.install(assembly, u=u, expected_pid=os.getpid(), configuration=configuration)
    w = graph.load('ue_scene_site_review_v1')
    w.RUN, w.LIVE, w.PREFIX = RUN, CACHE + '_live', 'DM_SiteReview_Pair19_'
    graph.load('ue_primary_saved_site_review_v1').install_private_behaviors(w)
    fast_runtime.disable_startup_asset_audits(graph)
    graph.load('ue_production_site_runtime_v1').install(w)
    revision.install_worker(w, assembly)
    original_live = w.live
    extra = configuration['inputs'] + [pin(__file__), pin(revision.__file__)]

    def live():
        state = original_live()
        present = {r['path'] for r in state['runtime_inputs']}
        additions = [r for r in extra if r['path'] not in present]
        if additions:
            state['runtime_inputs'] += additions
            state['input_stats'], state['input_result'] = {}, None
        return state

    w.live = live
    cached = {'worker': w, 'assembly': assembly, 'graph': graph, 'data': data,
              'configuration': configuration, 'revision': revision}
    setattr(u, CACHE, cached)
    return selection_policy.install_worker(site_intent.install(install_camera_checks(fast_runtime.install(cached))))


def dispatch(request):
    import unreal as u
    # Cleanup must remain available after an input changes. Calling the normal
    # dispatcher here would rebuild state/stamps and reject the stale inputs
    # before the existing exact-owner restore hooks can release their actors.
    cached = getattr(u, CACHE, None)
    if request.get('action') == 'restore' and cached is not None:
        if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
            raise ValueError('正在渲染，请结束后操作审查面板。')
        w = cached['worker']
        w.restore()
        return {'success': True, 'action': 'restore', 'request_id': request.get('request_id'),
                'cleanup_only': True, 'message': '临时人物和预览已释放。',
                'state': {'current_map': w.current_map(), 'preview': {}, 'show_ranges': False,
                          'check': {'status': 'idle', 'completed': 0, 'total': 0},
                          'playback': {'playing': False, 'time_seconds': 0.,
                                       'duration_seconds': 0., 'loop': False}}}
    current = worker(u)
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
        raise ValueError('正在渲染，请结束后操作审查面板。')
    result = current['worker'].dispatch(request)
    result['character_revision'] = {'ids': list(IDS), 'source': pin(DELIVERY),
                                    'additional_characters_integrated_in_panel': True}
    return result


def endpoint(request):
    try:
        result = dispatch(request)
    except Exception as exc:
        result = {'success': False, 'action': request.get('action'),
                  'request_id': request.get('request_id'), 'error': str(exc),
                  'traceback': traceback.format_exc()}
    rid = request.get('request_id') or uuid.uuid4().hex
    if not rid.isalnum():
        raise ValueError('Invalid request ID')
    output = RUN / 'replies' / (rid + '.json')
    write(output, result)
    print('DM_SCENE_SITE_REVIEW=' + json.dumps({'success': True, 'result_file': str(output)}))


def controller():
    prepare()
    graph, _ = graph_and_data()
    app = graph.load('scene_site_review_panel_v1')
    app.RUN, app.WORKER = RUN, Path(__file__).resolve()
    import pair_review_transport_fast_v1 as fast_transport
    fast_transport.install(app)
    import pair_review_site_drafts_v1 as site_drafts
    site_drafts.install(app)
    original_panel = app.Panel

    class PairPanel(original_panel):
        def refresh_remaining(self):
            super().refresh_remaining()
            if self.state.get('scene_freshness_policy') == 'explicit_check_snapshot_not_continuous':
                text = self.dirty.get()
                text = text.replace('全量检查有效', '全量采样已完成')
                text = text.replace('剩余组合检查有效', '剩余组合采样已完成')
                text = text.replace('局部检查有效', '局部采样已完成')
                self.dirty.set(text + ' 结果为检查时快照；在UE中改动场景后请重新检查。')

        def __init__(self, root, *args, **kwargs):
            self._pair_initial_synced = False
            self._pair_count_labels = []
            super().__init__(root, *args, **kwargs)
            root.title('新版40人 · 完整场景拍摄点审查')
            pending = [root]
            while pending:
                widget = pending.pop()
                pending.extend(widget.winfo_children())
                try:
                    text = widget.cget('text')
                except Exception:
                    continue
                if text == '沿用现用 30 动作、21 镜头与横竖画幅；不修改镜头参数。':
                    self._pair_count_labels.append(widget)
                    widget.configure(text='正在读取当前动作与镜头目录…')

        def apply(self, reply, action):
            super().apply(reply, action)
            motions, cameras = self.catalog.get('motions', []), self.catalog.get('cameras', [])
            if motions and cameras:
                for label in self._pair_count_labels:
                    label.configure(text=f'当前目录 {len(motions)} 动作、{len(cameras)} 镜头，支持横竖画幅。')
            if (self._pair_initial_synced or action not in {'status', 'catalog'}
                    or reply.get('success') is not True or not isinstance(reply.get('state'), dict)):
                return
            preview = self.state.get('preview') or {}
            motion = next((r for r in motions if r['id'] == preview.get('action_id')), None)
            camera = next((r for r in cameras if r['id'] == preview.get('camera_id')), None)
            if (motion is None or camera is None or preview.get('aspect') not in {'landscape', 'portrait'}
                    or type(preview.get('time_seconds')) not in (int, float)):
                return
            self.motion.set(self.row_label(motion))
            self.camera.set(self.row_label(camera))
            self.aspect.set('竖屏' if preview['aspect'] == 'portrait' else '横屏')
            self.seconds.set(str(preview['time_seconds']))
            current_map = self.state.get('current_map') or self.state.get('map')
            site = next((r for r in self.catalog.get('sites', [])
                         if r['id'] == self.state.get('site_id') and r.get('map') == current_map), None)
            if site is not None:
                self.saved_site.set(self.row_label(site))
            self._pair_initial_synced = True

    app.Panel = PairPanel
    return app


if __name__ == '__main__':
    if 'DM_SCENE_SITE_REVIEW_REQUEST' in globals():
        endpoint(globals()['DM_SCENE_SITE_REVIEW_REQUEST'])
    else:
        controller().main()
