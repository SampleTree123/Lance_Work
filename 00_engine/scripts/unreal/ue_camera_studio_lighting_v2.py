"""Scoped studio v2 helper. Owner: SCENE_CAMERA_SEQUENCE.md section 7.

Caller must clone + explicitly load MapsV2 before apply(unreal, world), and owns
the map save/receipt. This helper saves only its newly created StudioV2 material.
No Unreal connection or edits occur merely by importing this file.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re

ASSET_ROOT = '/Game/DataMake/Validation/CameraMotionPilot20261009'
MAP_ROOT = ASSET_ROOT + '/MapsV2/'
MATERIAL_PATH = ASSET_ROOT + '/StudioV2/M_WorldChecker_1m_v002'
PROJECT = Path('D:/UE/projects/datatry_02')
OWNER_TAG = 'DM_Camera_StudioV2_Spec'
EXPOSURE_BIAS = .2
LIGHTS = [
    {'label': 'DM_StudioV2_Key', 'lux': 1.8, 'pitch': -45., 'yaw': -45., 'shadows': True},
    {'label': 'DM_StudioV2_Fill', 'lux': 1.2, 'pitch': -45., 'yaw': 135., 'shadows': False},
    {'label': 'DM_StudioV2_SideA', 'lux': .6, 'pitch': -45., 'yaw': 45., 'shadows': False},
    {'label': 'DM_StudioV2_SideB', 'lux': .6, 'pitch': -45., 'yaw': 225., 'shadows': False},
]
FLOOR_SPEC = {'schema': 'camera_studio_v2_checker_material', 'coordinate': 'absolute_world_xy_cm',
              'cell_size_cm': 100., 'formula': 'fmod(abs(floor(world_x/100)+floor(world_y/100)),2)',
              'base_color_linear': [.18, .24], 'roughness': 1., 'metallic': 0., 'specular': 0.,
              'shading': 'default_lit', 'visual_acceptance': 'pending'}


def validate_world_path(path):
    if not isinstance(path, str) or not re.fullmatch(r'/[A-Za-z0-9_/]+(?:\.[A-Za-z0-9_]+)?', path):
        raise ValueError('Expected a saved MapsV2 world')
    package = path.split('.')[0]
    if not package.startswith(MAP_ROOT) or not package[len(MAP_ROOT):]:
        raise ValueError('Only owned CameraMotionPilot20261009/MapsV2 worlds may be changed')
    return package


def checker_alpha(x_cm, y_cm):
    """CPU description of the shader integer parity, for signed-coordinate tests."""
    return math.fmod(abs(math.floor(x_cm / 100.) + math.floor(y_cm / 100.)), 2.)


def material_pin():
    file = PROJECT / 'Content' / (MATERIAL_PATH.removeprefix('/Game/') + '.uasset')
    return {'path': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}


def _material(u):
    spec = json.dumps(FLOOR_SPEC, sort_keys=True, separators=(',', ':'))
    material = u.load_asset(MATERIAL_PATH)
    if material is not None:
        if not isinstance(material, u.Material) or u.EditorAssetLibrary.get_metadata_tag(material, OWNER_TAG) != spec:
            raise RuntimeError('Existing StudioV2 material has another specification; refusing to edit')
        if any(p.get_path_name() == MATERIAL_PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Existing StudioV2 material is dirty; inspect before reuse')
        return material, {'created': False, 'asset': material.get_path_name(), 'specification': FLOOR_SPEC,
                          'package': material_pin(), 'compile_errors': []}
    lib = u.MaterialEditingLibrary
    folder, name = MATERIAL_PATH.rsplit('/', 1)
    u.EditorAssetLibrary.make_directory(folder)
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not isinstance(material, u.Material):
        raise RuntimeError('Could not create owned floor material')
    material.set_editor_properties({'blend_mode': u.BlendMode.BLEND_OPAQUE,
                                   'shading_model': u.MaterialShadingModel.MSM_DEFAULT_LIT})
    nodes = []

    def node(cls, props=None):
        result = lib.create_material_expression(material, cls, len(nodes) * 160, 0)
        if result is None:
            raise RuntimeError('Could not create expression ' + str(cls))
        if props:
            result.set_editor_properties(props)
        nodes.append(result)
        return result

    def wire(source, target, name):
        names = [str(n) for n in lib.get_material_expression_input_names(target)]
        if name not in names and len(names) == 1:
            name = names[0]
        if not lib.connect_material_expressions(source, '', target, name):
            raise RuntimeError('Cannot wire material input ' + name + '; available=' + repr(names))

    world = node(u.MaterialExpressionWorldPosition)
    # The local UE5.8 default enum is WPT_Default = absolute world, not camera-relative.
    world_mode = str(world.get_editor_property('world_position_shader_offset'))
    mask = node(u.MaterialExpressionComponentMask, {'r': True, 'g': True, 'b': False, 'a': False})
    divide = node(u.MaterialExpressionDivide, {'const_b': 100.})
    floor = node(u.MaterialExpressionFloor)
    x = node(u.MaterialExpressionComponentMask, {'r': True, 'g': False, 'b': False, 'a': False})
    y = node(u.MaterialExpressionComponentMask, {'r': False, 'g': True, 'b': False, 'a': False})
    add = node(u.MaterialExpressionAdd)
    absolute = node(u.MaterialExpressionAbs)
    modulo = node(u.MaterialExpressionFmod)
    two = node(u.MaterialExpressionConstant, {'r': 2.})
    dark = node(u.MaterialExpressionConstant3Vector, {'constant': u.LinearColor(.18, .18, .18, 1.)})
    light = node(u.MaterialExpressionConstant3Vector, {'constant': u.LinearColor(.24, .24, .24, 1.)})
    blend = node(u.MaterialExpressionLinearInterpolate)
    roughness = node(u.MaterialExpressionConstant, {'r': 1.})
    zero = node(u.MaterialExpressionConstant, {'r': 0.})
    for source, target, name in [(world, mask, 'Input'), (mask, divide, 'A'), (divide, floor, 'Input'),
                                 (floor, x, 'Input'), (floor, y, 'Input'), (x, add, 'A'), (y, add, 'B'),
                                 (add, absolute, 'Input'), (absolute, modulo, 'A'), (two, modulo, 'B'),
                                 (dark, blend, 'A'), (light, blend, 'B'), (modulo, blend, 'Alpha')]:
        wire(source, target, name)
    for source, prop in [(blend, u.MaterialProperty.MP_BASE_COLOR), (roughness, u.MaterialProperty.MP_ROUGHNESS),
                         (zero, u.MaterialProperty.MP_METALLIC), (zero, u.MaterialProperty.MP_SPECULAR)]:
        if not lib.connect_material_property(source, '', prop):
            raise RuntimeError('Cannot connect floor property ' + str(prop))
    errors = [str(e) for e in lib.recompile_material(material)]
    if errors:
        raise RuntimeError('Floor material compilation failed: ' + repr(errors))
    u.EditorAssetLibrary.set_metadata_tag(material, OWNER_TAG, spec)
    if not u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Cannot save new owned StudioV2 material')
    return material, {'created': True, 'asset': material.get_path_name(), 'specification': FLOOR_SPEC,
                      'package': material_pin(), 'compile_errors': errors, 'expression_count': len(nodes),
                      'world_position_mode_readback': world_mode}


def apply(u, world):
    """Apply studio lighting to current cloned MapsV2 only; return metadata, do not save map."""
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong Unreal project')
    package = validate_world_path(world.get_path_name())
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_editor_world() != world:
        raise RuntimeError('Caller world is not the current explicitly loaded MapsV2 world')
    queue = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if queue.is_rendering() or queue.get_active_executor() is not None:
        raise RuntimeError('Cannot change studio while any render is active')
    dirty_maps = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if any(p != package for p in dirty_maps):
        raise RuntimeError('Unrelated dirty map exists; no save/discard attempted')
    actorsub = u.get_editor_subsystem(u.EditorActorSubsystem)
    actors = list(actorsub.get_all_level_actors())

    def unique(label, cls):
        found = [a for a in actors if a.get_actor_label() == label]
        if len(found) != 1 or not isinstance(found[0], cls):
            raise RuntimeError('Expected exactly one owned ' + label + ' of class ' + str(cls))
        if not found[0].get_path_name().startswith(world.get_path_name() + ':'):
            raise RuntimeError('Actor does not belong to current world')
        return found[0]

    floor_actor = unique('DM_CCWH_Floor', u.StaticMeshActor)
    exposure = unique('DM_CCWH_Exposure', u.PostProcessVolume)
    old_lights = [unique('DM_CCWH_' + name, u.Light) for name in ('Key', 'Fill', 'Back')]
    if any(a.get_actor_label() in {s['label'] for s in LIGHTS} for a in actors):
        raise RuntimeError('StudioV2 lights already exist; refusing a partial/repeated apply')
    floor_component = floor_actor.get_component_by_class(u.StaticMeshComponent)
    if floor_component is None:
        raise RuntimeError('Floor has no static mesh component')
    before_materials = [m.get_path_name() if m else None for m in floor_component.get_materials()]
    material, material_report = _material(u)
    report = {'schema': 'camera_studio_lighting_v2', 'world': world.get_path_name(),
              'status': 'applied_pending_caller_save_and_visual_probe', 'visual_acceptance': 'pending',
              'removed_owned_lights': [a.get_path_name() for a in old_lights], 'lights': [],
              'floor': {'actor': floor_actor.get_path_name(), 'prior_materials': before_materials,
                        'material': material_report, 'world_cell_size_cm': 100.},
              'manual_exposure_bias': EXPOSURE_BIAS, 'map_saved_by_helper': False}
    for actor in old_lights:
        if not actorsub.destroy_actor(actor):
            raise RuntimeError('Could not remove owned legacy light')
    for settings in LIGHTS:
        actor = actorsub.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 300),
            u.Rotator(pitch=settings['pitch'], yaw=settings['yaw'], roll=0.), transient=False)
        if actor is None:
            raise RuntimeError('Could not create owned directional light')
        actor.set_actor_label(settings['label'])
        actor.set_editor_property('tags', [u.Name('DM_Camera_StudioV2')])
        component = actor.get_component_by_class(u.DirectionalLightComponent)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_intensity(settings['lux'])
        component.set_light_color(u.LinearColor(1., 1., 1., 1.), False)
        component.set_cast_shadows(settings['shadows'])
        component.set_visibility(True, True)
        intensity = float(component.get_editor_property('intensity'))
        shadows = bool(component.get_editor_property('cast_shadows'))
        if abs(intensity - settings['lux']) > 1e-6 or shadows != settings['shadows']:
            raise RuntimeError('Directional light readback failed')
        report['lights'].append(dict(settings, actor=actor.get_path_name(), intensity_readback=intensity,
                                     cast_shadows_readback=shadows, range='directional_infinite'))
    for index in range(max(1, floor_component.get_num_materials())):
        floor_component.set_material(index, material)
        if floor_component.get_material(index) != material:
            raise RuntimeError('Floor material override readback failed')
    exposure.set_editor_property('unbound', True)
    settings = exposure.get_editor_property('settings')
    settings.set_editor_properties({'override_auto_exposure_method': True, 'auto_exposure_method': u.AutoExposureMethod.AEM_MANUAL,
        'override_auto_exposure_apply_physical_camera_exposure': True, 'auto_exposure_apply_physical_camera_exposure': False,
        'override_auto_exposure_bias': True, 'auto_exposure_bias': EXPOSURE_BIAS})
    exposure.set_editor_property('settings', settings)
    report['exposure_bias_readback'] = float(exposure.get_editor_property('settings').get_editor_property('auto_exposure_bias'))
    if abs(report['exposure_bias_readback'] - EXPOSURE_BIAS) > 1e-6:
        raise RuntimeError('Exposure readback failed')
    return report
