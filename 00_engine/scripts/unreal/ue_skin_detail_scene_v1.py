"""Copy accepted camera scenes for skin A/B/C comparison; no automatic UE access.

The root caller injects Unreal and owns execution. Configuration contains
characters {female: id, male: id}, variants {sex: {B: clone_receipt, C: ...}},
optional variant_names (default A,B,C), framings (default head,upper), revision.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path

S = Path(__file__).resolve().parent
RUN = S.parents[1]/'outputs/unreal_character_import/skin_detail_optimization_20261012_v1'
SOURCE = RUN.parent/'camera_complete_angles_20261010_v1'
ROOT = '/Game/DataMake/Validation/SkinDetailOptimization20261012'
PROJECT = Path('D:/UE/projects/datatry_02')
SOURCES = {
    'female': {'head': 'cam_211_angles_stand_front_head', 'upper': 'cam_206_angles_stand_front_upper'},
    'male': {'head': 'cam_316_angles_thinking_front_head', 'upper': 'cam_311_angles_thinking_front_upper'}}
CHARACTERS = {'female': 'CFD40_AF_005', 'male': 'CFD40_LM_002'}


def module(name):
    spec = importlib.util.spec_from_file_location('_skin_detail_'+name, S/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def asset_file(value, extension='.uasset'):
    package = value.split('.')[0]
    if not package.startswith('/Game/'):
        raise ValueError('Expected project asset')
    return PROJECT/'Content'/(package[6:]+extension)


def check(record):
    if pin(record['path']) != record:
        raise ValueError('Source changed: '+record['path'])


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def find_actors(u, sex):
    actors = list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    people = [a for a in actors if a.get_actor_label() == 'DM_CCWH_'+sex+'_Character']
    cameras = [a for a in actors if a.get_actor_label() == 'DM_CCWH_Camera']
    if len(people) != 1 or len(cameras) != 1:
        raise RuntimeError('Expected one character and one camera')
    return people[0], cameras[0]


def component_meshes(u, actor):
    return {c.get_name(): c.get_editor_property('skeletal_mesh_asset').get_path_name()
            for c in actor.get_components_by_class(u.SkeletalMeshComponent)
            if c.get_editor_property('skeletal_mesh_asset') is not None}


def stage(u, config):
    """Prepare independent maps/sequences. A leaves all source materials intact."""
    materials = module('ue_skin_detail_materials_v1')
    helper = module('ue_camera_prepare_studio_v2')
    builder = module('ue_camera_sequence_builder_v1')
    library = module('ue_camera_library_prepare_v1')
    builder.ALLOWED_PREFIX = ROOT+'/'
    materials.assert_project(u)
    library.clean(u)
    subsystem = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if subsystem.is_rendering() or subsystem.get_active_executor() is not None:
        raise RuntimeError('MRQ already active')
    if config.get('characters', CHARACTERS) != CHARACTERS:
        raise ValueError('This adapter preserves accepted-scene AF005/LM002 meshes')
    revision = config.get('revision', 'v1')
    if not re.fullmatch(r'[A-Za-z0-9_]+', revision):
        raise ValueError('Unsafe revision')
    variants = config.get('variant_names', ['A', 'B', 'C'])
    framings = config.get('framings', ['head', 'upper'])
    if not variants or set(variants)-{'A', 'B', 'C'} or len(set(variants)) != len(variants):
        raise ValueError('Invalid variants')
    if not framings or set(framings)-{'head', 'upper'} or len(set(framings)) != len(framings):
        raise ValueError('Invalid framings')
    manifest = read(SOURCE/'prepared_jobs_v1.json')
    plan = read(SOURCE/'expansion_plan_v1.json')
    if manifest.get('success') is not True:
        raise ValueError('Accepted source preparation failed')
    plan_pin = pin(SOURCE/'expansion_plan_v1.json')
    jobs = {r['shot_id']: r for r in manifest['jobs']}
    shots = {r['shot_id']: r for r in plan['shots']}
    receipt_pins = {Path(r['path']).stem: r for r in manifest['sequence_receipts']}
    entry = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name()
    if not asset_file(entry, '.umap').is_file():
        raise ValueError('Entry world must be saved')
    outputs = []
    for sex in ('female', 'male'):
        for framing in framings:
            source_id = SOURCES[sex][framing]
            check(receipt_pins[source_id])
            receipt = read(receipt_pins[source_id]['path'])
            for p in receipt['asset_files']:
                check(p)
            source_job = jobs[source_id]
            animation_path = receipt['sequence_report']['animation_path']
            animation = u.load_asset(animation_path)
            for variant_name in variants:
                identifier = 'skin_'+sex+'_'+framing+'_'+variant_name+'_'+revision
                new_map, new_seq = ROOT+'/Maps/L_'+identifier, ROOT+'/Sequences/LS_'+identifier
                receipt_path = RUN/'staged'/(identifier+'.json')
                if receipt_path.exists() or u.EditorAssetLibrary.does_asset_exist(new_map) or u.EditorAssetLibrary.does_asset_exist(new_seq):
                    raise ValueError('Existing stage needs inspection; choose new revision: '+identifier)
                library.clean(u)
                source_world = helper._load(u, source_job['map'])
                actor, _ = find_actors(u, sex)
                before_meshes = component_meshes(u, actor)
                expected = '/'+CHARACTERS[sex]+'/Meshes/'
                if not all(expected in before_meshes[n] for n in helper.FACE_COMPONENTS):
                    raise RuntimeError('Accepted scene identity differs')
                before_materials = {n: [c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
                    for n in helper.FACE_COMPONENTS for c in [helper.fresh_component(u, actor, n)]}
                library.clean(u)
                if not u.EditorLoadingAndSavingUtils.save_map(source_world, new_map):
                    raise RuntimeError('Map copy failed')
                world = helper._load(u, new_map)  # SaveMap does not switch worlds.
                actor, camera = find_actors(u, sex)
                if component_meshes(u, actor) != before_meshes:
                    raise RuntimeError('Copied scene changed meshes')
                if variant_name != 'A':
                    variant = config['variants'][sex][variant_name]
                    if variant['character_id'] != CHARACTERS[sex]:
                        raise ValueError('Wrong skin identity')
                    materials.apply_to_copied_component(u, helper.fresh_component(u, actor, 'Body'), variant)
                shot = copy.deepcopy(shots[source_id])
                shot['shot_id'] = identifier
                # Use the saved face/body composite, not the plan BodyOnly asset.
                shot['window_start_seconds'] = receipt['sequence_report']['source_start_seconds']
                built = builder.build_sequence(u, shot, actor, camera, animation, new_seq)
                for name in sorted(helper.FACE_COMPONENTS-{'Body'}):
                    builder.add_animation_component_track(u, built['sequence'], built['actor_binding'],
                        helper.fresh_component(u, actor, name), animation,
                        source_start_seconds=shot['window_start_seconds'])
                if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'], False):
                    raise RuntimeError('Sequence save failed')
                u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
                if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
                    raise RuntimeError('Map save failed')
                library.clean(u)
                world = helper._load(u, new_map)
                actor, _ = find_actors(u, sex)
                if component_meshes(u, actor) != before_meshes:
                    raise RuntimeError('Reload changed meshes')
                after_materials = {n: [c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
                    for n in helper.FACE_COMPONENTS for c in [helper.fresh_component(u, actor, n)]}
                expected_materials = copy.deepcopy(before_materials)
                if variant_name != 'A':
                    for row in config['variants'][sex][variant_name]['overrides']:
                        expected_materials['Body'][row['slot_index']] = row['material']
                if after_materials != expected_materials:
                    raise RuntimeError('Saved material overrides differ')
                sequence = u.load_asset(new_seq)
                bindings = helper.binding_readback(u, sequence, world)
                face = helper.audit_face_animation(u, actor, animation_path)
                library.sequence_animation_audit(u, sequence, animation_path, shot['window_start_seconds'])
                for p in receipt['asset_files']:
                    check(p)
                check(plan_pin)
                result = {'success': True, 'character_id': CHARACTERS[sex], 'variant': variant_name, 'framing': framing,
                    'job': {'shot_id': identifier, 'map': world.get_path_name(), 'sequence': sequence.get_path_name()},
                    'source_receipt': receipt_pins[source_id], 'source_plan': plan_pin,
                    'source_trajectory_sha256': shot['trajectory_sha256'], 'sequence_report': built['report'],
                    'mesh_paths_unchanged': before_meshes, 'material_readback': after_materials,
                    'face_audit': face, 'binding_readback': bindings,
                    'asset_files': [pin(asset_file(new_map, '.umap')), pin(asset_file(new_seq))]}
                write_new(receipt_path, result)
                outputs.append(result['job'])
    library.clean(u)
    helper._load(u, entry)
    result = {'success': True, 'config': config, 'jobs': outputs, 'source_preserved': True,
              'entry_world_restored': entry, 'human_visual_acceptance': 'pending'}
    write_new(RUN/('prepared_'+revision+'.json'), result)
    return result


def renderer():
    result = module('ue_camera_pilot_render_v1')
    result.RUN, result.ASSET_ROOT = RUN, ROOT
    result.LIVE_ATTRIBUTE = '_dm_skin_detail_render_v1'
    return result


def render(u, jobs, attempt_id, width=1920, height=1080, spatial_samples=4):
    # Same settings for A/B/C: no streaming quality advantage for newly imported
    # C textures. Warmup is a bounded settling budget, not proof of compilation.
    # Caller still checks final texture dimensions and actual output.
    return renderer().start_render(u, jobs, attempt_id, width=width, height=height,
        spatial_samples=spatial_samples, disable_texture_streaming=True,
        engine_warmup_count=64, render_warmup_count=32)


def status(u):
    return renderer().status(u)
