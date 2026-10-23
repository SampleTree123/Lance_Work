"""Root-invoked isolated scene sample adapter. No implicit Unreal connection.

Reuses scene-character duplication, existing validated composites, native section
tracks and bounded MRQ. All editable map assets belong to this new validation run.
"""
from pathlib import Path
import copy
import importlib.util
import json
import shutil
from types import SimpleNamespace

from build_primary_scene_samples_v1 import RUN, ASSETS, sha, read, write

S = Path(__file__).resolve().parent
PLAN_NAME = 'plans/site_v1.json'  # root/runner injects one immutable site plan
INITIAL_ROTATION_POLICY = 'primary_scene_new_revision_initial_rotation_keywords_v3'


def module(name):
    spec = importlib.util.spec_from_file_location('_primary_samples_' + name, S / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def plan(digest):
    path = (Path(RUN) / PLAN_NAME).resolve()
    path.relative_to(Path(RUN).resolve() / 'plans')
    if sha(path) != digest:
        raise ValueError('Frozen scene sample plan changed')
    document = read(path)
    if document.get('schema') != 'primary_scene_sample_trial_v1':
        raise ValueError('Unexpected site sample schema')
    for pin in document['source_pins']:
        if sha(pin['path']) != pin['sha256']:
            raise ValueError('Scene sample source changed: ' + pin['path'])
    return path, document


def exposure(component, compensation):
    """Use the level's saved exposure, including when legacy plans contain EV."""
    from level_exposure_policy_v1 import apply
    return apply(component)


def sample_grass_streaming(u, queue):
    """Keep Landscape grass, using scene distances in this owned MRQ queue.

    UE5.8's transient Game Overrides otherwise flush grass synchronously and
    multiply its cull distance by50. Both can allocate far beyond visible grass.
    No grass density, camera, output, warmup or source-level settings change.
    """
    values = {'flush_grass_streaming': False, 'override_grass_cull_distance_scale': False}
    jobs = queue.get_jobs()
    if not jobs:
        raise ValueError('Sample grass policy requires a populated owned queue')
    verified = []
    for job in jobs:
        setting = job.get_configuration().find_or_add_setting_by_class(u.MoviePipelineGameOverrideSetting)
        for key, value in values.items():
            setting.set_editor_property(key, value)
        if any(setting.get_editor_property(key) is not value for key, value in values.items()):
            raise ValueError('Sample grass streaming policy failed readback')
        verified.append(str(job.job_name))
    return {'policy': 'scene_distance_streamed_grass_v1', **values, 'verified_jobs': verified,
            'grass_enabled_and_density_unchanged': True, 'source_maps_unchanged': True}


def sample_scene_resources(u, queue):
    """Inherit scene resource settings in this private queue, not MRQ maxima.

    UE5.8 defaults disable texture streaming, force LOD0, disable HLODs, and
    override view distance by50. Cinematic quality itself also sets distance10.
    This opts out of those overrides; it never changes source assets or the
    explicit output/camera/AA sampling contract. HLODs already disabled by an
    earlier job are not forcibly re-enabled here.
    """
    values = {'cinematic_quality_settings': False,
              'texture_streaming': u.MoviePipelineTextureStreamingMethod.NONE,
              'use_lod_zero': False, 'disable_hlods': False,
              'override_view_distance_scale': False, 'use_high_quality_shadows': False,
              'flush_streaming_managers': False,
              'override_virtual_texture_feedback_factor': False,
              'flush_grass_streaming': False, 'override_grass_cull_distance_scale': False}
    jobs = queue.get_jobs()
    if not jobs:
        raise ValueError('Scene resource policy requires a populated owned queue')
    encode = lambda data: {key: value if isinstance(value, bool) else str(value) for key, value in data.items()}
    readback = []
    for job in jobs:
        setting = job.get_configuration().find_or_add_setting_by_class(u.MoviePipelineGameOverrideSetting)
        for key, value in values.items():
            setting.set_editor_property(key, value)
        actual = {key: setting.get_editor_property(key) for key in values}
        if any((actual[key] is not value) if isinstance(value, bool) else (actual[key] != value)
               for key, value in values.items()):
            raise ValueError('Scene resource policy failed readback')
        readback.append({'job_name': str(job.job_name), 'settings': encode(actual)})
    return {'policy': 'scene_inherited_resources_v1', 'requested_settings': encode(values),
            'readback_by_job': readback, 'source_maps_and_materials_unchanged': True,
            'output_camera_and_aa_sampling_unchanged': True,
            'scalability': 'inherit current project settings; do not force Cinematic maxima',
            'texture_streaming': 'NONE means do not override existing texture streaming, not disable it',
            'hlod': 'do not force HLOD off; does not repair HLOD state changed by earlier jobs',
            'visual_review': 'scene streaming and LOD may differ from prior forced-max renders; background detail and pop-in remain to review'}


def sample_renderer(renderer):
    """Attach the local policy at the existing pre-submission receipt boundary.

    The private renderer has already initialized its transient MRQ settings here;
    its submitted receipt is persisted before invoking the executor. Restore the
    original writer before returning so callbacks only write their usual receipt.
    """
    original_start = renderer.start_render

    def start(u, *args, **kwargs):
        original_persist = renderer.persist
        configured = False

        def persist(state):
            nonlocal configured
            if not configured and state['receipt']['status'] == 'submitted':
                policy = sample_grass_streaming(u, state['queue'])
                state['receipt']['render_contract']['landscape_grass_streaming'] = policy
                state['receipt']['render_contract']['scene_resource_policy'] = sample_scene_resources(u, state['queue'])
                from mrq_streaming_warmup_v1 import apply as apply_warmup
                warmup = apply_warmup(u, state['queue'])
                contract = state['receipt']['render_contract']
                contract['streaming_warmup'] = warmup
                # Replace the base renderer's 16/8 defaults with the settings
                # actually read back before submission, not just a policy label.
                actual = warmup['readback_by_job'][0]['settings']
                contract['engine_warmup_count'] = actual['engine_warm_up_count']
                contract['render_warmup_count'] = actual['render_warm_up_count']
                configured = True
            return original_persist(state)

        renderer.persist = persist
        try:
            return original_start(u, *args, **kwargs)
        finally:
            renderer.persist = original_persist

    renderer.start_render = start
    return renderer


class _OwnedLevelOperations:
    def __init__(self, unreal, subsystem):
        self.unreal, self.subsystem = unreal, subsystem

    def __getattr__(self, name):
        return getattr(self.subsystem, name)

    def save_current_level(self):
        # The established scene helper calls save_current_level. Save its new
        # owned copy explicitly to avoid an interactive source-control checkout.
        u = self.unreal
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        package = world.get_path_name().split('.')[0]
        if not package.startswith(ASSETS + '/SceneTrials/'):
            raise ValueError('Refusing to save a source scene or unrelated level')
        return u.EditorLoadingAndSavingUtils.save_map(world, package)


class _OwnedUEContext:
    """Local forwarding context; never monkeypatches the shared Unreal module."""
    def __init__(self, unreal):
        self.unreal = unreal

    def __getattr__(self, name):
        return getattr(self.unreal, name)

    def get_editor_subsystem(self, cls):
        result = self.unreal.get_editor_subsystem(cls)
        if cls is self.unreal.LevelEditorSubsystem:
            return _OwnedLevelOperations(self.unreal, result)
        if cls is self.unreal.EditorActorSubsystem:
            return _OwnedActorOperations(result)
        return result


class _OwnedActorOperations:
    def __init__(self, subsystem):
        self.subsystem = subsystem

    def __getattr__(self, name):
        return getattr(self.subsystem, name)

    def destroy_actor(self, actor):
        if not actor.get_path_name().startswith(ASSETS + '/SceneTrials/'):
            raise ValueError('Source-sublevel actor cannot be edited; requires an isolated sublevel copy')
        return self.subsystem.destroy_actor(actor)


def _initial_rotation_target(document, shot):
    # Old assets/receipts remain immutable; this repair requires a new revision.
    site = document.get('site') or {}
    return (document.get('schema') == 'primary_scene_sample_trial_v1'
            and document.get('scene_id') and document['scene_id'] == site.get('site_id')
            and document.get('revision') and document['revision'] != 'v1'
            and document['revision'] == site.get('revision')
            and shot.get('orientation') in ('landscape', 'portrait')
            and any(row.get('shot_id') == shot.get('shot_id') and row == shot
                    for row in document.get('shots', [])))


def _correct_initial_camera_rotation(u, document, shot, camera):
    """Repair the saved initial view only; Sequencer keys/clocks are untouched."""
    if not _initial_rotation_target(document, shot) or not isinstance(camera, u.CameraActor):
        return None
    if not camera.get_path_name().startswith(ASSETS + '/SceneTrials/'):
        raise ValueError('Initial rotation repair requires a new owned trial camera')
    diagnostic = Path(RUN) / 'red_desert_initial_rotation_readback_v1.json'
    diagnostic_pin = {'path': str(diagnostic), 'sha256': sha(diagnostic)}
    components = camera.get_actor_rotation()
    before = {name: float(getattr(components, name)) for name in ('pitch', 'yaw', 'roll')}
    first = shot['frames'][0]['rotation_pitch_yaw_roll']
    expected = dict(zip(('pitch', 'yaw', 'roll'), map(float, first)))
    camera.set_actor_rotation(u.Rotator(**expected), False)
    actual = camera.get_actor_rotation()
    readback = {name: float(getattr(actual, name)) for name in expected}
    if any(abs((readback[name] - value + 180.) % 360. - 180.) > 1e-6
           for name, value in expected.items()):
        raise ValueError('Initial trial camera rotation failed keyword readback')
    return {'policy': INITIAL_ROTATION_POLICY, 'status': 'verified_before_map_save',
            'shot_id': shot['shot_id'], 'revision': document['revision'],
            'camera': camera.get_path_name(), 'before': before,
            'expected': expected, 'readback': readback,
            'adapter_source': {'path': str(Path(__file__).resolve()), 'sha256': sha(__file__)},
            'diagnostic': diagnostic_pin,
            'trajectory_sha256': shot['trajectory_sha256'],
            'scope': 'saved initial CameraActor rotation only; original trajectory keys, animation, frame clock and output unchanged'}


def adapter(document):
    alignment = module('ue_camera_alignment_review_v1')
    alignment.RUN, alignment.ASSETS, alignment.PLAN_NAME = Path(RUN), ASSETS, PLAN_NAME
    base = alignment.adapter()
    original_configured = alignment.configured_module
    exact = {s['shot_id']: s for s in document['shots']}
    rotation_audits = {}
    original_save = base.save

    def save(path, data, *args, **kwargs):
        sid = data.get('job', {}).get('shot_id') if isinstance(data, dict) else None
        if sid in rotation_audits:
            data = dict(data, initial_camera_rotation=rotation_audits[sid])
        return original_save(path, data, *args, **kwargs)

    base.save = save

    def configured(name):
        result = original_configured(name)
        if name == 'ue_motion_scene_sequence_v1':
            original_keys = result.key_rows
            original_build = result.build_sequence

            def keys(shot):
                if shot != exact.get(shot['shot_id']):
                    raise ValueError('Shot differs from frozen placed scene plan')
                # Allowed local cropping remains explicit in the frozen object.
                return original_keys(dict(shot, status='geometry_pass')) if shot.get('status') == 'geometry_review_required' else original_keys(shot)

            def build(u, shot, actor, camera, animation, path, **kwargs):
                audit = _correct_initial_camera_rotation(u, document, shot, camera)
                if audit is not None:
                    rotation_audits[shot['shot_id']] = audit
                exposure(camera.get_component_by_class(u.CameraComponent), shot['exposure_compensation'])
                return original_build(u, shot, actor, camera, animation, path, **kwargs)

            result.key_rows, result.build_sequence = keys, build
        if name == 'ue_motion_scene_render_v1':
            result.LIVE_ATTRIBUTE = '_dm_primary_scene_samples_20261015'
            sample_renderer(result)
        return result

    base.module = configured
    stage = module('ue_scene_character_pilot_v1')
    stage.RUN, stage.A, stage.base = Path(RUN), ASSETS, base
    stage.locations = SimpleNamespace(current_map=lambda scene_id: document['site']['map'].split('.')[0])
    return stage, base, configured


def prepare(u, ids, digest):
    path, document = plan(digest)
    exact = {s['shot_id']: s for s in document['shots']}
    if not ids or len(set(ids)) != len(ids) or not set(ids).issubset(exact):
        raise ValueError('Require nonempty unique shots from this site plan')
    for sid in ids:
        receipt_path = Path(RUN) / 'scene_sequences' / (sid + '.json')
        if _initial_rotation_target(document, exact[sid]) and receipt_path.exists():
            audit = read(receipt_path).get('initial_camera_rotation', {})
            if (audit.get('policy') != INITIAL_ROTATION_POLICY
                    or audit.get('status') != 'verified_before_map_save'
                    or audit.get('shot_id') != sid):
                raise ValueError('Initial rotation repair requires a fresh unprepared revision')
    stage, base, _ = adapter(document)
    if Path(u.Paths.project_dir()).resolve() != base.CONTENT.parent.resolve():
        raise ValueError('Only the verified datatry_02 project is allowed')
    base.clean(u)
    usage = shutil.disk_usage(Path(RUN))
    if usage.free < 5 * 1024 ** 3:
        raise ValueError('Less than5GiB free before bounded sample preparation')
    write(Path(RUN) / 'storage_checks' / (document['scene_id'] + '_' + document['revision'] + '.json'),
          {'disk_free_bytes': usage.free, 'disk_total_bytes': usage.total,
           'selected_shots': ids, 'scope': 'before bounded site copies; raw PNGs retired only after verified encoding'})
    for sid in ids:
        alignment = module('ue_camera_alignment_review_v1')
        alignment.validate_body_contract(exact[sid])
    # Established helper pins source scene and both character templates before
    # duplication, checks them again after, and records complete follower audits.
    result = stage.prepare(_OwnedUEContext(u), path, ids)
    if sha(path) != digest:
        raise ValueError('Site sample plan changed during preparation')
    return result


def render(u, attempt, ids, width, height, digest):
    path, document = plan(digest)
    _, base, configured = adapter(document)
    exact = {s['shot_id']: s for s in document['shots']}
    if not ids or len(set(ids)) != len(ids) or not set(ids).issubset(exact):
        raise ValueError('Unknown sample render selection')
    jobs = []
    for sid in ids:
        shot = exact[sid]
        if (shot['width'], shot['height']) != (width, height):
            raise ValueError('Sample dimensions differ from frozen shot')
        receipt = read(Path(RUN) / 'scene_sequences' / (sid + '.json'))
        if not receipt['success'] or receipt['plan'] != base.pin(path):
            raise ValueError('Sample preparation receipt differs from plan')
        if _initial_rotation_target(document, shot):
            audit = receipt.get('initial_camera_rotation', {})
            if (audit.get('policy') != INITIAL_ROTATION_POLICY
                    or audit.get('status') != 'verified_before_map_save'
                    or audit.get('shot_id') != sid
                    or audit.get('trajectory_sha256') != shot['trajectory_sha256']):
                raise ValueError('New scene sample requires verified initial camera rotation')
        for pin in receipt['asset_files'] + receipt['source_pins']:
            if base.pin(pin['path']) != pin:
                raise ValueError('Sample/source asset changed after preparation')
        jobs.append(receipt['job'])
    result = configured('ue_motion_scene_render_v1').start_render(u, jobs, attempt, width=width, height=height)
    return {'attempt': attempt, 'receipt_path': result.get('receipt_path')}
