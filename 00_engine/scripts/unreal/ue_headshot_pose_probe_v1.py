"""Transient live-editor pose diagnostic confined to the Headshot experiment."""
from array import array
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
import traceback
import unreal

ROOT = Path(r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1')
PROJECT = ROOT / 'ue_normal_probe_project_v1'
RUN = Path(globals().get('DM_HS_NORMAL_RUN', str(ROOT / 'ue_normal_probe_final_female02_v1'))).resolve()
if RUN.parent != ROOT.resolve() or not RUN.name.startswith('ue_normal_probe_'):
    raise ValueError('Pose outputs must remain in a dedicated experiment run')
MANIFEST = json.loads((RUN / 'inputs.json').read_text(encoding='utf-8'))
if 'pose_project' in MANIFEST:
    if MANIFEST['pose_project'] != 'ue_material_probe_project_v1':
        raise ValueError('Only the independent material project override is supported')
    PROJECT = ROOT / MANIFEST['pose_project']
MATERIAL_REPORT = MANIFEST.get('pose_material_report')
MOTION = MANIFEST.get('pose_animation')
IMPORT_ATTEMPT = MANIFEST.get('pose_import_attempt', MOTION['import_attempt'] if MOTION else 'finalv1')
CAPTURE_IMAGES = MANIFEST.get('pose_capture_images', True)
if not isinstance(CAPTURE_IMAGES, bool):
    raise ValueError('pose_capture_images must be boolean')
TAG = globals().get('DM_HS_POSE_TAG', 'poses_v1')
if not TAG.replace('_', '').isalnum():
    raise ValueError('Unsafe tag')
OUT = RUN / TAG
POSES = [('neutral', {}), ('blink', {'CTRL_expressions_eyeBlinkL': 1., 'CTRL_expressions_eyeBlinkR': 1.}),
         ('smile', {'CTRL_expressions_mouthCornerPullL': .65, 'CTRL_expressions_mouthCornerPullR': .65}),
         ('jaw_open', {'CTRL_expressions_jawOpen': .65})]
VIEWS = MANIFEST.get('pose_views', [dict(name='front', yaw_degrees=0, distance_cm=85, target_head_z_cm=7, fov_degrees=32)])
if not VIEWS or len({v['name'] for v in VIEWS}) != len(VIEWS):
    raise ValueError('Diagnostic view names must be unique')
for view in VIEWS:
    if not view['name'].replace('_', '').isalnum():
        raise ValueError('Invalid diagnostic view name')
    for key in ('yaw_degrees', 'distance_cm', 'target_head_z_cm', 'fov_degrees'):
        if not math.isfinite(float(view[key])):
            raise ValueError('Nonfinite camera parameter')
    if not 10 <= float(view['distance_cm']) <= 300 or not 5 <= float(view['fov_degrees']) <= 120:
        raise ValueError('Camera distance/FOV outside diagnostic bounds')
if 'pose_cases' in MANIFEST:
    if MOTION:
        raise ValueError('Individual morph diagnostics cannot also play an animation')
    POSES = [(row['name'], row['weights']) for row in MANIFEST['pose_cases']]
    if not POSES or len({name for name, _ in POSES}) != len(POSES):
        raise ValueError('Diagnostic pose names must be unique')
    for name, weights in POSES:
        if not name.replace('_', '').isalnum() or not isinstance(weights, dict):
            raise ValueError('Invalid diagnostic pose')
        if any(not math.isfinite(float(v)) or abs(float(v)) > 1 for v in weights.values()):
            raise ValueError('Diagnostic morph weights must be finite and within [-1, 1]')


def run():
    if Path(unreal.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Isolated project required')
    OUT.mkdir(exist_ok=False)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    asset_tag = hashlib.sha256(str(RUN).encode('utf-8')).hexdigest()[:12] + '_' + TAG
    if not levels.new_level('/Game/HeadshotNormalProbe/PoseDiagnostic_' + asset_tag):
        raise RuntimeError('Could not create isolated diagnostic level')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    gray = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PoseGray_' + asset_tag,
        '/Game/HeadshotNormalProbe', unreal.Material, unreal.MaterialFactoryNew())
    if gray is None:
        raise RuntimeError('Could not create diagnostic gray material')
    color = unreal.MaterialEditingLibrary.create_material_expression(gray, unreal.MaterialExpressionConstant3Vector, -300, 0)
    color.set_editor_property('constant', unreal.LinearColor(.45,.45,.45,1))
    unreal.MaterialEditingLibrary.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = unreal.MaterialEditingLibrary.create_material_expression(gray, unreal.MaterialExpressionConstant, -300, 160)
    roughness.set_editor_property('r', .7)
    unreal.MaterialEditingLibrary.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.set_material_usage(gray, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    unreal.MaterialEditingLibrary.set_material_usage(gray, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    unreal.MaterialEditingLibrary.recompile_material(gray)
    hidden_scalp = None
    if MANIFEST.get('pose_hide_scalp_overlays', False):
        hidden_scalp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PoseHiddenScalp_' + asset_tag,
            '/Game/HeadshotNormalProbe', unreal.Material, unreal.MaterialFactoryNew())
        hidden_scalp.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        zero = unreal.MaterialEditingLibrary.create_material_expression(hidden_scalp, unreal.MaterialExpressionConstant, -300, 0)
        zero.set_editor_property('r', 0.)
        unreal.MaterialEditingLibrary.connect_material_property(zero, '', unreal.MaterialProperty.MP_OPACITY_MASK)
        unreal.MaterialEditingLibrary.set_material_usage(hidden_scalp, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        unreal.MaterialEditingLibrary.recompile_material(hidden_scalp)
    performance = unreal.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    previous_throttle = performance.get_editor_property('bThrottleCPUWhenNotForeground')
    performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
    # SceneCapture renders explicitly. Removing a nonexistent realtime override
    # on a fresh editor viewport causes a handled UE ensure; leave it untouched.
    for rotation, intensity in [(unreal.Rotator(pitch=-25, yaw=-125), 3.), (unreal.Rotator(pitch=-20, yaw=-55), 1.5)]:
        light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 250), rotation, transient=True)
        light.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', intensity)
    camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -100, 165), unreal.Rotator(yaw=90), transient=True)
    capture = camera.get_component_by_class(unreal.SceneCaptureComponent2D)
    capture.set_editor_properties(dict(capture_every_frame=False, capture_on_movement=False,
        always_persist_rendering_state=True, capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR, fov_angle=32.))
    # Reuse the accepted hair-review capture settings: temporal accumulation
    # is required for the Auto Setup hair shader's dithered transparency.
    capture.set_editor_property('show_flag_settings', [
        unreal.EngineShowFlagsSetting(show_flag_name=name, enabled=True)
        for name in ('AntiAliasing', 'TemporalAA', 'PostProcessing')])
    previous_aa = unreal.SystemLibrary.get_console_variable_int_value('r.AntiAliasingMethod')
    if previous_aa not in (2, 4):
        unreal.SystemLibrary.execute_console_command(world, 'r.AntiAliasingMethod 4')
    target = unreal.RenderingLibrary.create_render_target2d(world, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8,
        unreal.LinearColor(.12, .12, .12, 1))
    capture.set_editor_property('texture_target', target)
    state = dict(index=0, active_case=None, components={}, spawned=[], frames=0, prepared=False, handle=None)
    report = dict(success=False, done=False, scope='Live editor CPU-skinned LOD0 representative morphs and diagnostic gray captures; no production material acceptance',
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), rows=[],
        engine_version=unreal.SystemLibrary.get_engine_version(), sources={})
    report['anti_aliasing'] = dict(previous=previous_aa,
        applied=unreal.SystemLibrary.get_console_variable_int_value('r.AntiAliasingMethod'),
        show_flags=['AntiAliasing','TemporalAA','PostProcessing'], warmup_frames=40)
    material_map = {}
    previous_texture_streaming = None
    if MATERIAL_REPORT:
        material_report_path = Path(MATERIAL_REPORT).resolve()
        if not material_report_path.is_relative_to(ROOT.resolve()):
            raise RuntimeError('Material report must be within isolated experiment')
        material_report = json.loads(material_report_path.read_text(encoding='utf-8'))
        if not material_report['success']:
            raise RuntimeError('Material witness prerequisite failed')
        for item in material_report['assets']:
            for slot in item.get('slots', []):
                for key in (slot['name'], slot['imported_name']):
                    key = key.casefold()
                    if key in material_map and material_map[key] != slot['material']:
                        raise RuntimeError('Ambiguous witness material slot: ' + key)
                    material_map[key] = slot['material']
        report['material_witness'] = dict(path=str(material_report_path), sha256=hashlib.sha256(material_report_path.read_bytes()).hexdigest())
        report['material_assignments'] = []
        report['texture_metadata'] = []
        for item in material_report['assets']:
            if item.get('asset_class') != 'Texture2D':
                continue
            texture = unreal.load_asset(item['path'])
            report['texture_metadata'].append(dict(path=item['path'],
                loaded_size_before_warmup=[texture.blueprint_get_size_x(), texture.blueprint_get_size_y()],
                srgb=texture.get_editor_property('srgb'),
                never_stream=texture.get_editor_property('never_stream'),
                lod_bias=texture.get_editor_property('lod_bias'),
                compression=str(texture.get_editor_property('compression_settings')),
                source_files=list(texture.get_editor_property('asset_import_data').extract_filenames())))
        if MANIFEST.get('pose_disable_texture_streaming', False):
            previous_texture_streaming = unreal.SystemLibrary.get_console_variable_int_value('r.TextureStreaming')
            unreal.SystemLibrary.execute_console_command(world, 'r.TextureStreaming 0')
            report['texture_streaming_contrast'] = dict(previous=previous_texture_streaming,
                applied=unreal.SystemLibrary.get_console_variable_int_value('r.TextureStreaming'),
                scope='Transient process only; original assets and project settings unchanged')
    cases = [s['id'] for s in MANIFEST['sources']]
    steps = [(c, p, w, v) for c in cases for p, w in POSES for v in VIEWS]
    report['camera_views'] = VIEWS
    if MOTION:
        report['scope'] = 'Imported full CC facial animation: CPU-skinned meshes, bone transforms and gray renders; no material acceptance'
        report['motion_settings'] = MOTION
    if MATERIAL_REPORT:
        report['scope'] = 'Full CC facial animation with Auto Setup witness materials; per-image visual acceptance remains separate'

    def flush():
        (OUT / 'result.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def finish(error=None):
        report.update(done=True, success=error is None, error=error)
        if state['handle'] is not None:
            unreal.unregister_slate_post_tick_callback(state['handle'])
        performance.set_editor_property('bThrottleCPUWhenNotForeground', previous_throttle)
        unreal.SystemLibrary.execute_console_command(world, 'r.AntiAliasingMethod ' + str(previous_aa))
        if previous_texture_streaming is not None:
            for item in report['texture_metadata']:
                texture = unreal.load_asset(item['path'])
                item['loaded_size_after_capture'] = [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]
            unreal.SystemLibrary.execute_console_command(world, 'r.TextureStreaming ' + str(previous_texture_streaming))
        flush()
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def read_mesh(name, comp, basename):
        options = unreal.GeometryScriptCopyMeshFromComponentOptions()
        options.set_editor_property('requested_lod', unreal.GeometryScriptMeshReadLOD(lod_type=unreal.GeometryScriptLODType.RENDER_DATA, lod_index=0))
        options.set_editor_property('want_normals', True)
        mesh, transform, outcome = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(comp, unreal.DynamicMesh(), options, False)
        if outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Component geometry failed: ' + name)
        query, lists = unreal.GeometryScript_MeshQueries, unreal.GeometryScript_List
        _, positions, gaps = query.get_all_vertex_positions(mesh, False)
        if gaps:
            raise RuntimeError('Gapped component geometry')
        points = [float(getattr(v, a)) for v in lists.convert_vector_list_to_array(positions) for a in ('x','y','z')]
        _, tids, _ = query.get_all_triangle_i_ds(mesh)
        normals = []
        indices = []
        for tid in lists.convert_index_list_to_array(tids):
            triangle, valid = query.get_triangle_indices(mesh, tid)
            _, n1, n2, n3, valid_normals = query.get_triangle_normals(mesh, tid)
            if not valid or not valid_normals:
                raise RuntimeError('Missing normals or triangle')
            indices.extend(int(getattr(triangle, a)) for a in ('x','y','z'))
            normals.extend(float(getattr(n, a)) for n in (n1,n2,n3) for a in ('x','y','z'))
        row = dict(name=name, vertices=len(points)//3, triangles=len(indices)//3,
            nonfinite_positions=sum(not math.isfinite(v) for v in points),
            nonfinite_normals=sum(not math.isfinite(v) for v in normals))
        for key, values, kind in [('positions', points, 'd'), ('normals', normals, 'd'), ('triangles', indices, 'i')]:
            raw = array(kind, values).tobytes()
            path = OUT / (basename + '_' + name + '_' + key + '.bin.gz')
            path.write_bytes(gzip.compress(raw))
            row[key] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), elements=len(values), type=kind)
        return row

    def tick(delta):
        try:
            if state['index'] == len(steps):
                return finish()
            case, pose, weights, view = steps[state['index']]
            if not state['prepared']:
                if state['active_case'] != case:
                    for actor in state['spawned']:
                        actors.destroy_actor(actor)
                    state['spawned'], state['components'] = [], {}
                    imported = json.loads((RUN / (case + '_' + IMPORT_ATTEMPT + '_import.json')).read_text(encoding='utf-8'))
                    if not imported['success']:
                        raise RuntimeError('Missing import prerequisite')
                    report['sources'][case] = imported['source']
                    animation_imported = imported
                    animation_report = (MOTION.get('source_import_reports', {}).get(case) or MOTION.get('source_import_report')) if MOTION else None
                    if animation_report:
                        animation_report_path = Path(animation_report).resolve()
                        if not animation_report_path.is_relative_to(ROOT.resolve()):
                            raise RuntimeError('Animation report must be within isolated experiment')
                        animation_imported = json.loads(animation_report_path.read_text(encoding='utf-8'))
                        if not animation_imported['success']:
                            raise RuntimeError('Animation import prerequisite failed')
                        report['animation_import_report'] = str(animation_report_path)
                    for item in imported['assets']:
                        if item['class'] != 'SkeletalMesh':
                            continue
                        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(), transient=True)
                        comp = actor.get_component_by_class(unreal.SkeletalMeshComponent)
                        mesh = unreal.load_asset(item['path'])
                        comp.set_skeletal_mesh_asset(mesh)
                        for slot, skeletal_material in enumerate(mesh.get_editor_property('materials')):
                            material = gray
                            if MATERIAL_REPORT:
                                keys = [str(skeletal_material.get_editor_property(k)).casefold() for k in ('material_slot_name','imported_material_slot_name')]
                                paths = {material_map[k] for k in keys if k in material_map}
                                if len(paths) != 1:
                                    raise RuntimeError('No unambiguous witness material: ' + item['name'] + str(keys))
                                material_path = paths.pop()
                                material = unreal.load_asset(material_path)
                                if not isinstance(material, unreal.MaterialInterface):
                                    raise RuntimeError('Witness material did not load: ' + material_path)
                                report['material_assignments'].append(dict(mesh=item['name'], slot=slot, keys=keys, material=material_path))
                            comp.set_material(slot, material)
                            if hidden_scalp is not None and str(skeletal_material.get_editor_property('material_slot_name')).casefold().startswith('scalp'):
                                comp.set_material(slot, hidden_scalp)
                                report.setdefault('hidden_scalp_overlays', []).append(dict(mesh=item['name'], slot=slot, saved=False))
                        comp.set_editor_property('disable_post_process_blueprint', True)
                        comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                        comp.set_update_animation_in_editor(True)
                        comp.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
                        comp.set_editor_property('forced_lod_model', 1)
                        if MOTION:
                            animations = [a for a in animation_imported['assets'] if a['class'] == 'AnimSequence']
                            if len(animations) != 1:
                                raise RuntimeError('Expected one diagnostic animation for ' + item['name'])
                            animation = unreal.load_asset(animations[0]['path'])
                            if animations[0]['skeleton'] != item['skeleton']:
                                if not animation_report:
                                    raise RuntimeError('Unexpected skeleton mismatch')
                                source_meshes = [a for a in animation_imported['assets'] if a['class'] == 'SkeletalMesh' and a['name'] == item['name']]
                                if len(source_meshes) != 1:
                                    raise RuntimeError('Missing comparison mesh for hierarchy check')
                                comparison_actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(), transient=True)
                                comparison = comparison_actor.get_component_by_class(unreal.SkeletalMeshComponent)
                                comparison.set_skeletal_mesh_asset(unreal.load_asset(source_meshes[0]['path']))
                                def hierarchy(component):
                                    return [(str(component.get_bone_name(i)), str(component.get_parent_bone(component.get_bone_name(i)))) for i in range(component.get_num_bones())]
                                left, right = hierarchy(comp), hierarchy(comparison)
                                actors.destroy_actor(comparison_actor)
                                if left != right:
                                    raise RuntimeError('Animation/mesh skeleton hierarchies differ')
                                # In-memory diagnostic only; do not save either skeleton.
                                mesh.get_editor_property('skeleton').add_compatible_skeleton(animation.get_editor_property('skeleton'))
                                report.setdefault('compatible_hierarchy_checks', {})[item['name']] = dict(equal=True, bone_count=len(left), saved=False)
                            comp.set_animation(animation)
                        # Imported hair has no textures in this diagnostic; exclude opaque cards from the face view.
                        visible = MANIFEST.get('pose_visible_meshes', ['cc_base_body','cc_base_eye','cc_base_teeth','cc_base_tongue'])
                        if item['name'] not in visible and not MANIFEST.get('pose_include_hair', False):
                            comp.set_visibility(False)
                        state['components'][item['name']] = comp
                        state['spawned'].append(actor)
                    state['active_case'] = case
                    if any(state['components']['cc_base_body'].get_bone_index(b) < 0 for b in ('head','r_eye','l_eye')):
                        raise RuntimeError('UE5 head/eye bones not found; cannot frame head')
                for comp in state['components'].values():
                    comp.clear_morph_targets()
                    if MOTION:
                        comp.set_position(float(MOTION['seconds'][pose]), False)
                    else:
                        for name, weight in weights.items():
                            comp.set_morph_target(name, weight)
                state.update(prepared=True, frames=0, deadline=time.monotonic()+(20. if state['index'] == 0 else 2.))
                capture.set_editor_property('camera_cut_this_frame', True)
                return
            state['frames'] += 1
            head = state['components']['cc_base_body'].get_socket_location('head')
            if head.z < 50:
                if state['frames'] > 120:
                    raise RuntimeError('Head bone has not evaluated to a plausible world height')
                return
            report.setdefault('head_locations', {})[case] = [head.x,head.y,head.z]
            eyes = [state['components']['cc_base_body'].get_socket_location(b) for b in ('r_eye','l_eye')]
            dx = (eyes[0].x + eyes[1].x)/2 - head.x
            dy = (eyes[0].y + eyes[1].y)/2 - head.y
            length = math.hypot(dx,dy)
            if length < .1:
                raise RuntimeError('Eye-to-head direction cannot define a front view')
            angle = math.radians(float(view['yaw_degrees']))
            forward_x, forward_y = dx/length, dy/length
            direction_x = forward_x*math.cos(angle)-forward_y*math.sin(angle)
            direction_y = forward_x*math.sin(angle)+forward_y*math.cos(angle)
            height = float(view['target_head_z_cm'])
            distance = float(view['distance_cm'])
            target_pos = unreal.Vector(head.x,head.y,head.z + height)
            camera_pos = unreal.Vector(head.x + direction_x*distance,head.y + direction_y*distance,head.z + height)
            capture.set_editor_property('fov_angle', float(view['fov_degrees']))
            camera.set_actor_location(camera_pos, False, False)
            camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera_pos,target_pos), False)
            report.setdefault('camera_front_directions', {})[case] = [dx/length,dy/length]
            if CAPTURE_IMAGES:
                capture.capture_scene()
            if state['frames'] < 40 or time.monotonic() < state['deadline']:
                return
            basename = case + '_' + pose
            if len(VIEWS) > 1 or view['name'] != 'front':
                basename += '_' + view['name']
            if CAPTURE_IMAGES:
                unreal.RenderingLibrary.export_render_target(world, target, str(OUT), basename + '.png')
            row = dict(case=case, pose=pose, view=view['name'], camera=view, requested_weights=weights,
                       image=str(OUT / (basename + '.png')) if CAPTURE_IMAGES else None, meshes=[])
            if MOTION:
                row['requested_weights'] = None
                row['animation_seconds'] = float(MOTION['seconds'][pose])
                body = state['components']['cc_base_body']
                row['bones'] = {str(body.get_bone_name(i)): {
                    'position': [float(getattr(body.get_socket_location(body.get_bone_name(i)), a)) for a in ('x','y','z')],
                    'rotation': [float(getattr(body.get_socket_rotation(body.get_bone_name(i)), a)) for a in ('pitch','yaw','roll')]}
                    for i in range(body.get_num_bones())}
            for name in ('cc_base_body','cc_base_eye','cc_base_teeth','cc_base_tongue'):
                row['meshes'].append(read_mesh(name, state['components'][name], basename))
            if MANIFEST.get('pose_include_hair', False):
                for name, comp in state['components'].items():
                    if not name.startswith('cc_base_'):
                        row['meshes'].append(read_mesh(name, comp, basename))
            report['rows'].append(row)
            flush()
            state.update(index=state['index']+1, prepared=False)
        except Exception:
            finish(traceback.format_exc())

    flush()
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    state['handle'] = unreal.register_slate_post_tick_callback(tick)
    unreal._dm_headshot_pose_probe_state = (state, report, tick)


if __name__ == '__main__':
    run()
