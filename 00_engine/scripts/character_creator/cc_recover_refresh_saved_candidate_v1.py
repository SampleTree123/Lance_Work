"""Narrow recovery of v9's saved candidate, not success of its failed report."""
import importlib
import os
import sys

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'character_refresh_20261018_v1')
WARNING_SHA = '38eb6ecb3423431ffae01afeff4ad43b14260fb47874a2f10677a2ffba298385'
FAILURE_TEXT = 'Scoped real texture pixel capture incomplete: saved'


def validate(config, output_dir, api, probe, core):
    if config.get('recipe_complete') is not False or config.get('recovery_kind') != 'recover_v9_saved_candidate':
        raise ValueError('Explicit recover_v9/recipe-incomplete contract required')
    if not probe.inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Independent new recovery output child required')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refuse existing recovery output')
    path = probe.reference(config['failed_report'], api, '.json', (RUN_ROOT,))
    prior = core.read_json(path)
    if (prior.get('diagnostic_mode') != 'character_refresh' or prior.get('success') is not False
        or prior.get('phase') != 'failed_partial_candidate' or prior.get('error', {}).get('message') != FAILURE_TEXT
        or prior.get('recipe_complete') is not False or prior.get('pixel_capture_enabled') is not True
        or prior.get('layers_after_reload') is not None or prior.get('layer_persistence_passed') is not False):
        raise ValueError('Only the exact failed saved-pixel candidate case is eligible')
    recipe = prior['config']
    if recipe.get('include_redness_layers') is not False or recipe.get('redness_policy') != 'excluded_by_user':
        raise ValueError('Current recipe must exclude redness by user')
    signature = prior.get('layers_before_save')
    if not isinstance(signature, dict) or set(signature) != {'makeup'} or set(signature['makeup']) != {'eyebrow'}:
        raise ValueError('Actual before-save unique Eyebrow signature required')
    body_step_count = 0
    for step in prior.get('steps', []):
        if step.get('measured_working_subdivision_level') != 0:
            raise ValueError('Historical actual SubD0 geometry evidence missing')
        for label in ('geometry_against_source', 'geometry_against_previous_phase'):
            gate = step.get(label, {})
            if gate.get('passed') is not True or gate.get('vertex_count') != 14164 or gate.get('threshold_mm') != .002 or gate.get('allowances') != []:
                raise ValueError('Historical strict all14164 Body gate failed')
        body_step_count += 1
    if not body_step_count or prior['steps'][-1]['phase'] != 'post_save':
        raise ValueError('Candidate must have a successful actual post-save Body check')
    if prior.get('pixel_checks', {}).get('source_to_restored_protected_support', {}).get('passed') is not True:
        raise ValueError('Original support restoration must already have real pixel proof')
    parent = os.path.dirname(path)
    candidate = probe.reference(config['candidate'], api, '.ccproject', (parent,))
    if config['candidate'] != prior['saved_candidate']:
        raise ValueError('Explicit candidate must equal actual saved reference')
    source = probe.reference(recipe['source_project'], api, '.ccproject', (RUN_ROOT, STAGE_ROOT))
    if os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(candidate)):
        raise ValueError('Recovery cannot overwrite its original source')
    for asset in recipe.get('assets', {}).values():
        if api.sha256_file(asset['path']) != asset['sha256']:
            raise ValueError('Selected historical asset SHA changed')
    body_path = probe.reference(config['source_body_snapshot'], api, '.json', (parent,))
    if os.path.normcase(os.path.realpath(body_path)) != os.path.normcase(os.path.realpath(os.path.join(parent, 'source_geometry.json'))):
        raise ValueError('Source Body reference belongs to another run')
    manifests = {}
    for label in ('source', 'after_eyes', 'saved'):
        entry = prior['pixel_stages'][label]
        manifest_path = probe.reference(entry, api, '.json', (parent,))
        observed = core.read_json(manifest_path)
        if observed.get('checkpoint') != label:
            raise ValueError('Pixel manifest checkpoint mismatch')
        if label != 'saved' and (entry.get('pixel_capture_complete') is not True or observed.get('pixel_capture_complete') is not True):
            raise ValueError('Source/selected eye baseline is incomplete')
        for row in observed['materials']:
            records = list(row['textures'].values()) + [value['evidence'] for value in row.get('missing_textures', {}).values() if value.get('evidence')]
            for record in records:
                probe.reference(record, api, '.png', (parent,))
        manifests[label] = observed
    bad = manifests.pop('saved')
    if (bad.get('pixel_capture_complete') is not False or bad.get('skin_diffuse_coverage') != []
        or bad.get('texture_observation_errors') or bad.get('decode_errors')):
        raise ValueError('Saved capture differs from measured warning-only failure')
    expected = {'Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg', 'Std_Eyelash'}
    rows = [row for row in bad['materials'] if row['mesh'] == 'CC_Base_Body' and row['material'] in expected]
    if len(rows) != 5 or {row['material'] for row in rows} != expected:
        raise ValueError('Exact original Body material inventory required')
    for row in rows:
        if row['textures'] or set(row.get('missing_textures', {})) != {'diffuse', 'bump', 'roughness', 'opacity', 'metallic', 'ambient_occlusion'}:
            raise ValueError('Body channels are not the measured warning-only pattern')
        if any(item.get('reason') != 'sdk_known_warning_image' or item.get('evidence', {}).get('sha256') != WARNING_SHA for item in row['missing_textures'].values()):
            raise ValueError('Unrecognized missing map must not receive recovery assumptions')
    return prior, source, candidate, core.read_json(body_path), manifests


def run(library, output_dir, log, api):
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    probe = importlib.reload(importlib.import_module('cc_makeup_probe_v1'))
    core = importlib.reload(importlib.import_module('cc_finalize_refresh_partial_v1'))
    config = library['recover_saved_candidate']
    inputs = validate(config, output_dir, api, probe, core)
    return core._execute(library, output_dir, log, api, validated_recovery=inputs)
