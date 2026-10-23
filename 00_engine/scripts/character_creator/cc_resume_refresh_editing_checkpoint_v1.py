"""Narrow AF005 timing recovery; resume saved editing checkpoint, never reapply assets.

Experimental owner: Assembly Technical §10.4.2. New recovery child outputs only.
Frozen failed report, source, checkpoint and earlier PNGs remain immutable.
"""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
RUNNER_SHA = '80c6c4c479dbdbb158a24dd830f76859b4e3d6727b13e7125c848ea2bfb02a72'
FAILURE = 'Actual Appearance/editor did not become ready within bounded10seconds'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(record, api):
    if api.sha256_file(record['path']) != record['sha256']:
        raise ValueError('Recovery input changed: ' + record['path'])
    return record['path']


def validate(config, recipe, api):
    prior = read(verify(config['failed_report'], api))
    if (prior.get('success') is not False or prior.get('error', {}).get('message') != FAILURE
            or prior.get('phase') != 'failed_partial_candidate' or prior.get('layer_persistence_passed') is not False
            or prior.get('layers_after_reload') is not None or prior.get('config') != recipe
            or recipe.get('character_id') != 'CFD40_AF_005' or prior.get('recipe_complete') is not False):
        raise ValueError('Only exact AF005 saved-editing readiness failure may resume')
    if prior['editing_checkpoint'] != config['editing_checkpoint'] or not prior.get('layers_before_save'):
        raise ValueError('Actual own editing checkpoint and pre-save layers required')
    verify(prior['editing_checkpoint'], api)
    verify(recipe['source_project'], api)
    if not prior.get('steps'):
        raise ValueError('Prior measured geometry is required')
    for step in prior['steps']:
        for key in ('geometry_against_source', 'geometry_against_previous_phase'):
            gate = step[key]
            if (gate.get('passed') is not True or gate.get('threshold_mm') != .002
                    or gate.get('vertex_count') != 14164 or gate.get('allowances') != []):
                raise ValueError('Prior strict all14164 .002 gate failed')
    if [r['phase'] for r in prior['applications']] != ['skin', 'remove_legacy_brow_parts', 'eyes', 'makeup_eyebrow']:
        raise ValueError('Original selected appearance applications incomplete')
    for record in recipe['assets'].values():
        verify(record, api)
    verify(prior['source_native_geometry'], api)
    for pin in prior['pixel_stages'].values():
        snapshot = read(verify(pin, api))
        if pin.get('pixel_capture_complete') is not True or snapshot.get('pixel_capture_complete') is not True:
            raise ValueError('Original real pixel baseline incomplete')
        for row in snapshot['materials']:
            for image in row['textures'].values():
                verify(image, api)
    return prior


def transformed_runner(source):
    """Keep the frozen runner's callbacks/closure, replace only already-completed work."""
    first = '    previous_snapshot = None\n    try:\n'
    last = "            avatar_id = str(avatar().GetID())\n            activate_target_editor('activate_editor_after_editing_reload', wait_ready=True)"
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError('Frozen runner resume anchors changed')
    start, end = source.index(first), source.index(last)
    replacement = '''    previous_snapshot = None
    try:
        report, baseline, original_support, inherited_pixels, target = _resume_initial(library, output_dir, api)
        pixel_snapshots.update(inherited_pixels)
        previous_snapshot = baseline
        if close_editor:
            checkpoint('resume_own_saved_editing_checkpoint_no_asset_application')
            probe.guarded_load(target, 'Resume own immutable editing checkpoint', api, report['loads'], checkpoint)
'''
    return source[:start] + replacement + source[end:]


def initial(library, output_dir, api):
    prior = validate(library['saved_editing_resume'], library['refresh_assembly'], api)
    parent, output = Path(library['saved_editing_resume']['failed_report']['path']).parent, Path(output_dir)
    report = json.loads(json.dumps(prior))
    report.pop('error', None)
    report.update(summary_path=str(output / 'refresh_partial_report.json'), success=False,
                  phase='resuming_saved_editing_checkpoint', loads=[],
                  saved_editing_recovery=dict(failed_report=library['saved_editing_resume']['failed_report'],
                      editing_checkpoint=prior['editing_checkpoint'], implementation_sha256=api.sha256_file(__file__),
                      assets_reapplied=False, editor_readiness_max_seconds=60))
    for name in ('source_geometry.json', 'source_native_geometry.json'):
        shutil.copyfile(str(parent / name), str(output / name))
    report['source_native_geometry'] = dict(path=str(output / 'source_native_geometry.json'),
                                          sha256=api.sha256_file(str(output / 'source_native_geometry.json')))
    snapshots = {}
    for label, pin in prior['pixel_stages'].items():
        destination = output / ('pixels_' + label) / 'materials.json'
        destination.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(pin['path'], str(destination))
        report['pixel_stages'][label] = dict(pin, path=str(destination))
        snapshots[label] = read(destination)
    return report, read(output / 'source_geometry.json'), read(output / 'source_native_geometry.json'), snapshots, prior['editing_checkpoint']['path']


def run(library, output_dir, log, api):
    validate(library['saved_editing_resume'], library['refresh_assembly'], api)
    normal = importlib.import_module('cc_refresh_skin_normal_closure_v1')
    runner_path = DIRECTORY / 'cc_run_character_refresh_v1.py'
    if api.sha256_file(str(runner_path)) != RUNNER_SHA:
        raise ValueError('Frozen runner changed')
    namespace = dict(__file__=str(runner_path), __name__='_saved_editing_private_runner', _resume_initial=initial)
    exec(compile(transformed_runner(runner_path.read_text(encoding='utf-8-sig')), str(runner_path), 'exec'), namespace)
    finalizer = importlib.import_module('cc_finalize_refresh_partial_v1')
    wait_source = Path(finalizer.__file__).read_text(encoding='utf-8-sig')
    wait_source = wait_source.replace('timeout_seconds=10.):', 'timeout_seconds=60.):', 1).replace('timeout_seconds <= 10:', 'timeout_seconds <= 60:', 1)
    wait_namespace = dict(__file__=finalizer.__file__, __name__='_saved_editing_private_finalizer')
    exec(compile(wait_source, finalizer.__file__, 'exec'), wait_namespace)
    class Imports:
        def __getattr__(self, name):
            return getattr(importlib, name)
        def import_module(self, name):
            if name == 'cc_refresh_closed_assembly_v1':
                return SimpleNamespace(finish=normal.finish, __file__=normal.__file__)
            if name == 'cc_finalize_refresh_partial_v1':
                return SimpleNamespace(**wait_namespace)
            return importlib.import_module(name)
    namespace['importlib'] = Imports()
    report = namespace['run'](library, output_dir, log, api)
    verify(library['saved_editing_resume']['failed_report'], api)
    verify(library['saved_editing_resume']['editing_checkpoint'], api)
    return report
