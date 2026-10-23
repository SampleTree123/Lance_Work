"""Bounded first-view MRQ warmup while retaining the scene's texture streaming.

UE5.8 MoviePipelineTiming.cpp submits each engine warmup tick to the GPU when
bRenderWarmUpFrames is true. MoviePipelineRendering.cpp performs render warmup
samples on the final warmup tick. The sequence stays at its first output frame
when bUseCameraCutForWarmUp is false; no output frames or asset tracks are added.

This gives normal streaming time and rendered-view feedback, not a residency
guarantee. Game Overrides' flush has no exposed timeout and calls the C++
BlockTillAllRequestsFinished() with its unbounded default, so it remains off.
"""
import hashlib
import json
from pathlib import Path
import platform

POLICY = 'streamed_first_view_warmup_v1'
SETTINGS = {'engine_warm_up_count': 120, 'render_warm_up_count': 32,
            'render_warm_up_frames': True, 'use_camera_cut_for_warm_up': False}
LOCAL_PROFILE = Path(__file__).resolve().parents[2] / 'outputs/local_render_profile_v1/profile.json'
POOL_CVAR = 'r.Streaming.PoolSize'


def pool_profile(pool_size_mb=None, profile_path=None, *, for_render=False):
    """An explicit budget or this machine's local profile; never a universal size."""
    if pool_size_mb is not None:
        result = {'source': 'explicit_parameter', 'pool_size_mb': pool_size_mb}
    else:
        path = Path(profile_path) if profile_path is not None else LOCAL_PROFILE
        if not path.is_file():
            return {'source': 'profile_missing_inherit_session', 'path': str(path), 'pool_size_mb': None}
        raw = path.read_bytes()
        profile = json.loads(raw.decode('utf-8-sig'))
        if (not isinstance(profile, dict) or profile.get('schema') != 'local_texture_streaming_profile_v1'
                or not isinstance(profile.get('machine_name'), str)
                or profile['machine_name'].casefold() != platform.node().casefold()):
            raise ValueError('Texture pool profile must belong to this machine')
        key = 'mrq_pool_size_mb' if for_render and 'mrq_pool_size_mb' in profile else 'pool_size_mb'
        result = {'source': 'local_machine_profile', 'path': str(path),
                  'sha256': hashlib.sha256(raw).hexdigest(), 'machine_name': profile['machine_name'],
                  'pool_size_mb': profile.get(key), 'profile_budget_key': key}
    if type(result['pool_size_mb']) is not int or not 0 < result['pool_size_mb'] <= 131072:
        raise ValueError('Texture pool budget must be an integer 1..131072 MiB')
    return result


def apply(u, queue, *, pool_size_mb=None, profile_path=None):
    """Configure and verify every owned job before the executor is submitted."""
    jobs = queue.get_jobs()
    if not jobs:
        raise ValueError('Streaming warmup requires a populated owned queue')
    profile = pool_profile(pool_size_mb, profile_path, for_render=True)
    readback = []
    for job in jobs:
        setting = job.get_configuration().find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
        if setting.get_editor_property('use_camera_cut_for_warm_up'):
            raise ValueError('Streaming warmup cannot replace explicit camera-cut preroll')
        for key, value in SETTINGS.items():
            setting.set_editor_property(key, value)
        actual = {key: setting.get_editor_property(key) for key in SETTINGS}
        if any(type(actual[key]) is not type(value) or actual[key] != value
               for key, value in SETTINGS.items()):
            raise ValueError('Streaming warmup policy failed readback')
        observed = {'job_name': str(job.job_name), 'settings': actual}
        if profile['pool_size_mb'] is not None:
            cvars = job.get_configuration().find_or_add_setting_by_class(u.MoviePipelineConsoleVariableSetting)
            if (not cvars.add_or_update_console_variable(POOL_CVAR, float(profile['pool_size_mb']))
                    or not cvars.update_console_variable_enable_state(POOL_CVAR, True)):
                raise ValueError('Could not configure reversible MRQ texture pool budget')
            matches = [entry for entry in cvars.get_console_variables() if str(entry.name) == POOL_CVAR]
            if not matches or not matches[-1].is_enabled or matches[-1].value != profile['pool_size_mb']:
                raise ValueError('MRQ texture pool budget failed readback')
            observed['texture_pool_cvar'] = {'name': POOL_CVAR, 'value': float(matches[-1].value),
                                             'is_enabled': bool(matches[-1].is_enabled)}
        readback.append(observed)
    return {'policy': POLICY, 'requested_settings': dict(SETTINGS), 'readback_by_job': readback,
            'sequence_time': 'hold first output frame; no camera-cut preroll or output-range changes',
            'streaming_policy': 'inherit scene texture streaming; optional local pool budget; no forced full residency',
            'texture_pool': {**profile, 'restore_policy': 'MRQ ConsoleVariableSetting restores prior values on pipeline teardown'},
            'streaming_completion': 'not measured; bounded warmup frames do not guarantee complete texture residency',
            'blocking_streaming_flush': False,
            'boundary': 'first-view warmup only; later camera reveals and insufficient pool budget still require visual review'}
