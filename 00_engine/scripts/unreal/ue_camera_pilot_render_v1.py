"""Isolated camera-pilot MRQ queue. Owner: SCENE_CAMERA_SEQUENCE.md section 7.

start_render returns immediately. Callbacks only persist receipts; they never
load/change a map, rebuild actors, restore a scene, or submit another queue.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
PROJECT = Path('D:/UE/projects/datatry_02')
ASSET_ROOT = '/Game/DataMake/Validation/CameraMotionPilot20261009'
LIVE_ATTRIBUTE = '_dm_camera_pilot_render_v1'


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', value):
        raise ValueError('Expected a short filename-safe attempt/shot identifier')
    if value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        raise ValueError('Reserved Windows identifier')
    return value


def asset_path(value):
    if not isinstance(value, str):
        raise ValueError('Asset path must be a string')
    package, *objects = value.split('.')
    if (not package.startswith(ASSET_ROOT + '/') or len(objects) > 1
            or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', package)
            or '//' in package or package.endswith('/')):
        raise ValueError('Only CameraMotionPilot20261009 assets are allowed')
    leaf = package.rsplit('/', 1)[1]
    if objects and objects[0] != leaf:
        raise ValueError('Object path must match its package leaf')
    return package + '.' + leaf


def validate_request(jobs, attempt_id, width, height, run_root=None, spatial_samples=1):
    identifier(attempt_id)
    if type(spatial_samples) is not int or spatial_samples not in (1, 4):
        raise ValueError('Spatial samples must be the integer 1 or 4')
    if (type(width) is not int or type(height) is not int
            or not 64 <= width <= 4096 or not 64 <= height <= 4096):
        raise ValueError('Resolution must be integer 64..4096 pixels')
    if not isinstance(jobs, (list, tuple)) or not 1 <= len(jobs) <= 64:
        raise ValueError('Expected 1..64 explicitly selected jobs')
    selected, ids = [], set()
    for job in jobs:
        if not isinstance(job, dict) or set(job) != {'shot_id', 'map', 'sequence'}:
            raise ValueError('Each job must contain only shot_id, map, sequence')
        shot_id = identifier(job['shot_id'])
        if shot_id.casefold() in ids:
            raise ValueError('Duplicate shot identifiers would share an output folder')
        ids.add(shot_id.casefold())
        selected.append({'shot_id': shot_id, 'map': asset_path(job['map']),
                         'sequence': asset_path(job['sequence'])})
    root = Path(run_root or RUN).resolve()
    output = (root / 'renders' / attempt_id).resolve()
    receipt = (root / 'render_receipts' / (attempt_id + '.json')).resolve()
    if not output.is_relative_to(root / 'renders') or not receipt.is_relative_to(root / 'render_receipts'):
        raise ValueError('Output path escapes the owned Run Root')
    if output.exists() or receipt.exists():
        raise ValueError('Attempt already exists; inspect it and choose a fresh attempt_id')
    return selected, output, receipt


def file_pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def queue_snapshot(subsystem):
    queue = subsystem.get_queue()  # Read only. Never clear, copy, load or allocate here.
    return {'queue_path': queue.get_path_name(), 'dirty': bool(subsystem.is_queue_dirty()),
            'jobs': [{'path': job.get_path_name(), 'name': str(job.job_name),
                      'map': str(job.map), 'sequence': str(job.sequence),
                      'enabled': bool(job.is_enabled()),
                      'configuration_path': job.get_configuration().get_path_name()}
                     for job in queue.get_jobs()],
            'scope': 'queue identity, dirty state and job identity/references; not a serialization of every configuration field'}


def persist(state):
    path = state['receipt_path']
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state['receipt'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def status(u):
    """Read current executor plus the latest owned in-memory receipt; no mutation."""
    subsystem = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    state = getattr(u, LIVE_ATTRIBUTE, None)
    active = subsystem.get_active_executor()
    return {'subsystem_rendering': bool(subsystem.is_rendering()),
            'active_executor_path': active.get_path_name() if active else None,
            'owned_attempt_id': state['receipt']['attempt_id'] if state else None,
            'owned_executor_active': bool(state and active == state['executor']),
            'receipt_path': str(state['receipt_path']) if state else None,
            'receipt': copy.deepcopy(state['receipt']) if state else None}


def start_render(u, jobs, attempt_id, width=1280, height=720, spatial_samples=1, *,
                 disable_texture_streaming=False, engine_warmup_count=16,
                 render_warmup_count=8):
    """Submit a fresh isolated 30fps / 300-frame PNG queue and return live status."""
    if type(disable_texture_streaming) is not bool:
        raise ValueError('disable_texture_streaming must be boolean')
    for value in (engine_warmup_count, render_warmup_count):
        if type(value) is not int or not 0 <= value <= 256:
            raise ValueError('Warmup counts must be integers in 0..256')
    selected, output_root, receipt_path = validate_request(
        jobs, attempt_id, width, height, spatial_samples=spatial_samples)
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Only the verified datatry_02 project is allowed')
    subsystem = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if subsystem.is_rendering() or subsystem.get_active_executor() is not None:
        raise RuntimeError('Another MRQ executor is active')
    prior = getattr(u, LIVE_ATTRIBUTE, None)
    if prior and prior['receipt']['status'] not in {'completed', 'failed', 'setup_failed'}:
        raise RuntimeError('Prior owned attempt is not terminal; reconcile before another render')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    dirty.update(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    pins = []
    for row in selected:
        for field, extension in [('map', '.umap'), ('sequence', '.uasset')]:
            package = row[field].split('.')[0]
            if package in dirty or not u.EditorAssetLibrary.does_asset_exist(package):
                raise RuntimeError('Job map/sequence must exist and be saved: ' + package)
            pins.append(file_pin(PROJECT / 'Content' / (package.removeprefix('/Game/') + extension)))
        sequence = u.load_asset(row['sequence'])
        if not isinstance(sequence, u.LevelSequence):
            raise ValueError('Job sequence has another asset type')
        rate = sequence.get_display_rate()
        if rate.numerator != 30 or rate.denominator != 1:
            raise ValueError('Sequence must use the frozen 30fps display rate')
        if sequence.get_playback_start() != 0 or sequence.get_playback_end() != 300:
            raise ValueError('Sequence must use the frozen [0,300) playback range')
    global_before = queue_snapshot(subsystem)
    output_root.mkdir(parents=True, exist_ok=False)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 'camera_pilot_render_receipt_v1', 'attempt_id': attempt_id,
               'created_at': now(), 'status': 'preparing', 'success': False,
               'jobs': selected, 'inputs': pins, 'global_queue_before': global_before,
               'output_root': str(output_root), 'media_validation': 'pending_external_frame_count_decode_and_visual_checks',
               'render_contract': {'fps': 30, 'duration_seconds': 10, 'frame_count': 300,
                   'range_start_inclusive': 0, 'range_end_exclusive': 300,
                   'width': width, 'height': height, 'format': 'PNG',
                   'spatial_samples': spatial_samples, 'temporal_samples': 1,
                   'engine_warmup_count': engine_warmup_count, 'render_warmup_count': render_warmup_count,
                   'motion_blur_cvars': {'r.MotionBlurQuality': 0.0, 'r.MotionBlur.Amount': 0.0},
                   'profile_scope': 'prototype_camera_pilot'},
               'errors': [], 'job_results': []}
    if disable_texture_streaming:
        # Match UE 5.8 MoviePipelineGameOverrideSetting Disabled exactly without
        # adding its unrelated default quality/LOD/shadow/GameMode overrides.
        # MoviePipelineConsoleVariableSetting stores/restores prior values.
        receipt['render_contract']['texture_streaming_cvars'] = {'r.TextureStreaming': 0.0}
    state = {'receipt': receipt, 'receipt_path': receipt_path, 'executor': None, 'queue': None}
    persist(state)
    submitted = False
    try:
        queue = u.MoviePipelineQueue()
        state['queue'] = queue
        for row in selected:
            destination = output_root / row['shot_id']
            destination.mkdir(exist_ok=False)
            job = queue.allocate_new_job(u.MoviePipelineExecutorJob)
            job.job_name = row['shot_id']
            job.map = u.SoftObjectPath(row['map'])
            job.sequence = u.SoftObjectPath(row['sequence'])
            config = job.get_configuration()
            output = config.find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
            directory = u.DirectoryPath()
            directory.set_editor_property('path', str(destination))
            output.set_editor_property('output_directory', directory)
            output.output_resolution = u.IntPoint(width, height)
            output.use_custom_frame_rate = True
            output.output_frame_rate = u.FrameRate(30, 1)
            output.use_custom_playback_range = True
            output.custom_start_frame, output.custom_end_frame = 0, 300
            output.output_frame_step, output.handle_frame_count = 1, 0
            output.file_name_format, output.zero_pad_frame_numbers = 'frame_{frame_number_rel}', 4
            output.override_existing_output = False
            output.flush_disk_writes_per_shot = True
            config.find_or_add_setting_by_class(u.MoviePipelineDeferredPassBase).set_is_enabled(True)
            png = config.find_or_add_setting_by_class(u.MoviePipelineImageSequenceOutput_PNG)
            png.set_is_enabled(True)
            png.write_alpha = False
            aa = config.find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
            aa.spatial_sample_count = spatial_samples
            aa.temporal_sample_count = 1
            aa.engine_warm_up_count = engine_warmup_count
            aa.render_warm_up_count = render_warmup_count
            aa.render_warm_up_frames = True
            aa.use_camera_cut_for_warm_up = False
            cvars = config.find_or_add_setting_by_class(u.MoviePipelineConsoleVariableSetting)
            for key, value in receipt['render_contract']['motion_blur_cvars'].items():
                if not cvars.add_or_update_console_variable(key, value):
                    raise RuntimeError('Could not configure reversible render cvar: ' + key)
            for key, value in receipt['render_contract'].get('texture_streaming_cvars', {}).items():
                if not cvars.add_or_update_console_variable(key, value):
                    raise RuntimeError('Could not configure reversible texture cvar: ' + key)
            config.initialize_transient_settings()
        executor = u.MoviePipelinePIEExecutor(subsystem)
        state['executor'] = executor
        executor.set_is_rendering_offscreen(True)

        def on_error(executor_arg, pipeline_arg, fatal, error_text):
            receipt['errors'].append({'at': now(), 'fatal': bool(fatal), 'text': str(error_text)})
            persist(state)  # No scene/application mutation in callbacks.

        def on_job(output_data):
            receipt['job_results'].append({'at': now(), 'shot_id': str(output_data.job.job_name),
                                           'success': bool(output_data.success)})
            persist(state)

        def on_finished(executor_arg, success):
            receipt['executor_success'] = bool(success)
            receipt['finished_at'] = now()
            try:
                receipt['global_queue_after'] = queue_snapshot(subsystem)
                receipt['global_queue_unchanged'] = receipt['global_queue_after'] == global_before
                expected = {r['shot_id'] for r in selected}
                results = receipt['job_results']
                jobs_ok = (len(results) == len(expected) and {r['shot_id'] for r in results} == expected
                           and all(r['success'] for r in results))
                receipt['all_job_callbacks_success'] = jobs_ok
                receipt['input_files_unchanged'] = all(file_pin(p['path']) == p for p in pins)
                receipt['success'] = bool(success and jobs_ok and receipt['global_queue_unchanged']
                    and receipt['input_files_unchanged'] and not any(e['fatal'] for e in receipt['errors']))
                receipt['status'] = 'completed' if receipt['success'] else 'failed'
            except Exception as exc:
                receipt['status'], receipt['success'] = 'failed', False
                receipt['errors'].append({'at': now(), 'fatal': True, 'text': 'Terminal inspection: ' + str(exc)})
            persist(state)

        state['callbacks'] = (on_error, on_job, on_finished)
        executor.on_executor_errored_delegate.add_callable_unique(on_error)
        executor.on_individual_job_work_finished_delegate.add_callable_unique(on_job)
        executor.on_executor_finished_delegate.add_callable_unique(on_finished)
        setattr(u, LIVE_ATTRIBUTE, state)  # Pin queue, executor and callable wrappers.
        receipt['status'], receipt['submitted_at'] = 'submitted', now()
        persist(state)
        submitted = True
        subsystem.render_queue_instance_with_executor_instance(queue, executor)
    except Exception as exc:
        receipt['errors'].append({'at': now(), 'fatal': True, 'text': str(exc)})
        receipt['success'] = False
        receipt['status'] = 'submission_outcome_unknown' if submitted else 'setup_failed'
        persist(state)
        raise
    return status(u)
