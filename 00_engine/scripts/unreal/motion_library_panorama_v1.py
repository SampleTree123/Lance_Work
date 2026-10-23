"""Optional fixed panorama; original motion, light rig and floor untouched.

Initial parameters require root's actual viewport check. No automatic tracking,
root locking or guarantee for an arbitrary full-length travelling clip.
Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
"""
from __future__ import annotations
import copy
import math

FRAMING = 'motion_panorama'
LABEL = 'DM_MotionExtension_PanoramaFill_v1'
OWNER = 'DM_MotionExtension_PanoramaFill_Owned_v1'
FLOOR_LABEL = 'DM_MotionExtension_PanoramaFloor_v1'
FLOOR_OWNER = 'DM_MotionExtension_PanoramaFloor_Owned_v1'
PROFILE = {'camera_x_cm': 1600., 'camera_z_cm': 100., 'camera_fov_degrees': 35.,
           'fill_x_cm': 1400., 'fill_z_cm': 400., 'fill_pitch_degrees': -25.,
           'fill_yaw_degrees': 180., 'fill_intensity': 10.,
           'floor_half_extent_cm': 2000., 'floor_top_offset_cm': .25}


def profile():
    value = copy.deepcopy(PROFILE)
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in value.values())
            or value['camera_x_cm'] <= 0 or not 5 <= value['camera_fov_degrees'] <= 120
            or value['fill_intensity'] < 0 or value['floor_half_extent_cm'] <= 0
            or not 0 < value['floor_top_offset_cm'] <= 2.):
        raise ValueError('Invalid panorama camera/light profile')
    return value


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def floor_geometry(minimum, maximum, location, scale, angles):
    """Axis-aligned root StaticMeshComponent bounds; no assumed Cube dimensions."""
    p = profile()
    values = [*minimum, *maximum, *location, *scale, *angles]
    if (any(not math.isfinite(v) for v in values) or any(v <= 0 for v in scale)
            or any(hi <= lo for lo, hi in zip(minimum, maximum))
            or any(abs(v) > 1e-4 for v in angles)):
        raise ValueError('Panorama floor needs finite, positive, axis-aligned source geometry')
    center = [location[i] + (minimum[i]+maximum[i])*.5*scale[i] for i in range(2)]
    target_scale = [2*p['floor_half_extent_cm']/(maximum[i]-minimum[i]) for i in range(2)] + [scale[2]]
    top = location[2] + maximum[2]*scale[2]
    target_location = [center[i]-(minimum[i]+maximum[i])*.5*target_scale[i] for i in range(2)]
    target_location.append(top-p['floor_top_offset_cm']-maximum[2]*target_scale[2])
    return {'source_local_min': minimum, 'source_local_max': maximum,
        'source_location': location, 'source_scale': scale, 'source_top_z_cm': top,
        'location': target_location, 'scale': target_scale, 'top_z_cm': top-p['floor_top_offset_cm'],
        'world_min_xy': [v-p['floor_half_extent_cm'] for v in center],
        'world_max_xy': [v+p['floor_half_extent_cm'] for v in center],
        'top_offset_below_source_cm': p['floor_top_offset_cm']}


def legacy_request(request):
    result = copy.deepcopy(request)
    if result.get('framing') == FRAMING:
        result['framing'] = 'full'
    return result


def extend_parser(parser):
    for action in parser._actions:
        if action.dest == 'framing' and FRAMING not in action.choices:
            action.choices = tuple(action.choices) + (FRAMING,)
    return parser


def install_button(app):
    previous = app.install_face_controls
    def install(frame, data):
        previous(frame, data)
        from tkinter import ttk
        def find(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == 'TButton' and str(child.cget('text')) == '全身':
                    return child
                found = find(child)
                if found is not None:
                    return found
        anchor = find(frame)
        if anchor is None:
            raise ValueError('Existing framing toolbar not found')
        def click():
            manager = app._active_manager
            if manager is None or manager.busy or manager.closing:
                return
            try:
                request = app.ui_request(data, 'view', framing=FRAMING)
                if manager.loaded_request is None or request['choices'] != manager.loaded_request['choices']:
                    raise ValueError('请先显示当前搭配。')
                manager.submit(request)
                for editor in app._active_editors.values():
                    editor.enable(False)
                app.action_box().configure(state='disabled')
                app._config_status.set('正在切换动作全景；原动作位移保持不变。')
            except Exception as exc:
                app._config_status.set('未执行：' + str(exc))
        button = ttk.Button(anchor.master, text='动作全景', command=click)
        button.pack(side='left', padx=(0, 6), pady=2)
    app.install_face_controls = install


class PanoramaView:
    def __init__(self, app):
        self.app, self.u = app, app.unreal

    def actors(self):
        return self.u.get_editor_subsystem(self.u.EditorActorSubsystem)

    def world_actors(self):
        # UE5.8 EditorActorSubsystem.GetAllLevelActors explicitly excludes
        # RF_Transient. Owned helpers must remain transient yet be discoverable
        # by later worker instances, readback, hide and transaction rollback.
        world = self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_editor_world()
        if world is None:
            raise RuntimeError('Current editor world is unavailable')
        return self.u.GameplayStatics.get_all_actors_of_class(world, self.u.Actor)

    def light(self):
        rows = [a for a in self.world_actors() if a.get_actor_label() == LABEL]
        if len(rows) > 1:
            raise ValueError('Duplicate panorama fill actors')
        if not rows:
            return None
        actor = rows[0]
        if (not isinstance(actor, self.u.DirectionalLight)
                or OWNER not in {str(t) for t in actor.get_editor_property('tags')}):
            raise ValueError('Refusing a foreign light with the panorama label')
        return actor

    def component(self, actor):
        return actor.get_component_by_class(self.u.DirectionalLightComponent)

    def floor(self):
        rows = [a for a in self.world_actors() if a.get_actor_label() == FLOOR_LABEL]
        if len(rows) > 1:
            raise ValueError('Duplicate panorama floor actors')
        if not rows:
            return None
        actor = rows[0]
        if (not isinstance(actor, self.u.StaticMeshActor)
                or FLOOR_OWNER not in {str(t) for t in actor.get_editor_property('tags')}):
            raise ValueError('Refusing a foreign floor with the panorama label')
        return actor

    def floor_component(self, actor):
        return actor.get_component_by_class(self.u.StaticMeshComponent)

    def source_floor(self):
        actor = self.app.legacy.find(self.app.legacy.PREFIX + 'Floor')
        if not isinstance(actor, self.u.StaticMeshActor):
            raise ValueError('Existing source review floor is missing or is not a StaticMeshActor')
        c = self.floor_component(actor)
        if c != actor.get_editor_property('root_component'):
            raise ValueError('Source floor mesh must be the actor root for audited bounds')
        mesh = c.get_editor_property('static_mesh')
        if mesh is None:
            raise ValueError('Existing source floor mesh is not loaded')
        low, high = c.get_local_bounds()
        rot = actor.get_actor_rotation()
        geometry = floor_geometry(xyz(low), xyz(high), xyz(actor.get_actor_location()),
            xyz(actor.get_actor_scale3d()), [rot.pitch, rot.yaw, rot.roll])
        materials = [c.get_material(i) for i in range(c.get_num_materials())]
        if not materials:
            raise ValueError('Existing source floor has no material slots')
        return actor, mesh, materials, geometry

    def ensure_floor(self):
        u = self.u
        _, mesh, materials, geometry = self.source_floor()
        actor = self.floor()
        location, rotation = u.Vector(*geometry['location']), u.Rotator()
        if actor is None:
            actor = self.actors().spawn_actor_from_class(u.StaticMeshActor, location, rotation, transient=True)
            if actor is None:
                raise RuntimeError('Cannot create transient panorama floor')
            actor.set_actor_label(FLOOR_LABEL)
            actor.set_editor_property('tags', [u.Name(FLOOR_OWNER)])
        c = self.floor_component(actor)
        c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        c.set_editor_property('override_materials', [])
        for index, material in enumerate(materials):
            c.set_material(index, material)
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, False)
        actor.set_actor_scale3d(u.Vector(*geometry['scale']))
        c.set_cast_shadow(False)
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_visibility(True, True)
        return actor

    def center_y(self, request):
        sexes = ('female', 'male') if request['focus'] == 'both' else (request['focus'],)
        return sum(self.app.fixed.actor_for(sex).get_actor_location().y for sex in sexes) / len(sexes)

    def ensure_fill(self, request):
        u, p = self.u, profile()
        actor = self.light()
        location = u.Vector(p['fill_x_cm'], self.center_y(request), p['fill_z_cm'])
        rotation = u.Rotator(pitch=p['fill_pitch_degrees'], yaw=p['fill_yaw_degrees'])
        if actor is None:
            actor = self.actors().spawn_actor_from_class(u.DirectionalLight, location, rotation, transient=True)
            if actor is None:
                raise RuntimeError('Cannot create transient panorama fill')
            actor.set_actor_label(LABEL)
            actor.set_editor_property('tags', [u.Name(OWNER)])
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(rotation, False)
        component = self.component(actor)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_intensity(p['fill_intensity'])
        component.set_light_color(u.LinearColor(1., 1., 1., 1.), False)
        component.set_cast_shadows(False)
        component.set_visibility(True, True)
        return actor

    def hide(self):
        actor = self.light()
        if actor is not None:
            self.component(actor).set_visibility(False, True)
        floor = self.floor()
        if floor is not None:
            self.floor_component(floor).set_visibility(False, True)

    def apply(self, request, original_view):
        # Original view owns actor orientation, camera pilot and normal framing.
        original_view(legacy_request(request))
        if request['framing'] != FRAMING:
            self.hide()
            return
        u, p = self.u, profile()
        self.ensure_fill(request)
        self.ensure_floor()
        camera = self.app.legacy.find(self.app.legacy.PREFIX + 'Camera')
        if camera is None:
            raise RuntimeError('Existing review camera is missing')
        location, rotation = u.Vector(p['camera_x_cm'], self.center_y(request), p['camera_z_cm']), u.Rotator(yaw=180.)
        camera.set_actor_location(location, False, False)
        camera.set_actor_rotation(rotation, False)
        camera.get_component_by_class(u.CameraComponent).set_editor_property('field_of_view', p['camera_fov_degrees'])
        u.EditorLevelLibrary.set_level_viewport_camera_info(location, rotation)
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_invalidate_viewports()

    def snapshot(self):
        floor = self.floor()
        ground = {'existed': False}
        if floor is not None:
            c = self.floor_component(floor)
            ground = {'existed': True, 'actor': floor, 'location': floor.get_actor_location(),
                'rotation': floor.get_actor_rotation(), 'scale': floor.get_actor_scale3d(),
                'visible': c.is_visible(), 'mesh': c.get_editor_property('static_mesh'),
                'override_materials': list(c.get_editor_property('override_materials')),
                'cast_shadow': c.get_editor_property('cast_shadow'), 'collision': c.get_collision_enabled()}
        actor = self.light()
        if actor is None:
            return {'existed': False, 'floor': ground}
        c = self.component(actor)
        return {'existed': True, 'actor': actor, 'location': actor.get_actor_location(),
            'rotation': actor.get_actor_rotation(), 'visible': c.is_visible(),
            'intensity': c.get_editor_property('intensity'), 'color': c.get_light_color(),
            'cast_shadows': c.get_editor_property('cast_shadows'), 'floor': ground}

    def restore(self, snapshot):
        errors = []
        for operation in (lambda: self.restore_light(snapshot), lambda: self.restore_floor(snapshot['floor'])):
            try:
                operation()
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError('; '.join(errors))

    def restore_light(self, snapshot):
        if not snapshot['existed']:
            actor = self.light()
            if actor is not None and not self.actors().destroy_actor(actor):
                raise RuntimeError('Could not remove newly created panorama fill during rollback')
            return
        actor = self.light()
        if actor is None or actor != snapshot['actor']:
            raise RuntimeError('Previous panorama fill disappeared during transaction')
        c = self.component(actor)
        actor.set_actor_location(snapshot['location'], False, False)
        actor.set_actor_rotation(snapshot['rotation'], False)
        c.set_intensity(snapshot['intensity'])
        c.set_light_color(snapshot['color'], False)
        c.set_cast_shadows(snapshot['cast_shadows'])
        c.set_visibility(snapshot['visible'], True)

    def restore_floor(self, snapshot):
        actor = self.floor()
        if not snapshot['existed']:
            if actor is not None and not self.actors().destroy_actor(actor):
                raise RuntimeError('Could not remove newly created panorama floor during rollback')
            return
        if actor is None or actor != snapshot['actor']:
            raise RuntimeError('Previous panorama floor disappeared during transaction')
        c = self.floor_component(actor)
        c.set_static_mesh(snapshot['mesh'])
        c.set_editor_property('override_materials', snapshot['override_materials'])
        actor.set_actor_location(snapshot['location'], False, False)
        actor.set_actor_rotation(snapshot['rotation'], False)
        actor.set_actor_scale3d(snapshot['scale'])
        c.set_cast_shadow(snapshot['cast_shadow'])
        c.set_collision_enabled(snapshot['collision'])
        c.set_visibility(snapshot['visible'], True)

    def floor_readback(self, active):
        floor = self.floor()
        c = self.floor_component(floor) if floor is not None else None
        visible = bool(c and c.is_visible())
        errors = []
        row = {'exists': floor is not None, 'visible': visible,
            'source_floor_untouched_by_helper': True, 'mesh_and_material_assets_modified': False}
        if visible != active:
            errors.append('panorama_floor_visibility_mismatch')
        if active and c:
            source_actor, mesh, materials, geometry = self.source_floor()
            path = lambda asset: asset.get_path_name() if asset is not None else None
            actual_materials = [c.get_material(i) for i in range(c.get_num_materials())]
            row.update(source_actor=source_actor.get_actor_label(), source_mesh=path(mesh),
                actual_mesh=path(c.get_editor_property('static_mesh')), source_materials=[path(m) for m in materials],
                actual_materials=[path(m) for m in actual_materials], source_geometry=geometry,
                location=xyz(floor.get_actor_location()), scale=xyz(floor.get_actor_scale3d()),
                collision_disabled=c.get_collision_enabled() == self.u.CollisionEnabled.NO_COLLISION,
                cast_shadow=c.get_editor_property('cast_shadow'))
            rot = floor.get_actor_rotation()
            if (c.get_editor_property('static_mesh') != mesh or actual_materials != materials
                    or any(abs(a-b) > 1e-4 for a, b in zip(row['location'], geometry['location']))
                    or any(abs(a-b) > 1e-4 for a, b in zip(row['scale'], geometry['scale']))
                    or any(abs(v) > 1e-4 for v in (rot.pitch, rot.yaw, rot.roll))
                    or not row['collision_disabled'] or row['cast_shadow']):
                errors.append('panorama_floor_geometry_or_material_mismatch')
        row['errors'], row['success'] = errors, not errors
        return row

    def readback(self, request):
        actor = self.light()
        c = self.component(actor) if actor is not None else None
        enabled = bool(c and c.is_visible())
        active = request['framing'] == FRAMING
        p = profile()
        errors = []
        if enabled != active:
            errors.append('panorama_fill_visibility_mismatch')
        floor = self.floor_readback(active)
        errors.extend(floor['errors'])
        row = {'framing': request['framing'], 'fill_exists': actor is not None, 'fill_visible': enabled,
               'fixed_camera_no_tracking': True, 'original_lights_unchanged': True,
               'original_motion_unchanged': True, 'visual_acceptance': 'pending_root_viewport_check', 'floor': floor}
        if active:
            camera = self.app.legacy.find(self.app.legacy.PREFIX + 'Camera')
            if camera is None:
                errors.append('missing_review_camera')
            else:
                pos, rot = camera.get_actor_location(), camera.get_actor_rotation()
                fov = camera.get_component_by_class(self.u.CameraComponent).get_editor_property('field_of_view')
                row['camera'] = {'x': pos.x, 'y': pos.y, 'z': pos.z, 'yaw': rot.yaw, 'fov': fov}
                if (abs(pos.x-p['camera_x_cm']) > 1e-3 or abs(pos.y-self.center_y(request)) > 1e-3
                        or abs(pos.z-p['camera_z_cm']) > 1e-3 or abs(abs(rot.yaw)-180.) > 1e-3
                        or abs(fov-p['camera_fov_degrees']) > 1e-3):
                    errors.append('panorama_camera_mismatch')
            if c:
                row['fill_intensity'] = c.get_editor_property('intensity')
                row['fill_cast_shadows'] = c.get_editor_property('cast_shadows')
                if abs(row['fill_intensity']-p['fill_intensity']) > 1e-5 or row['fill_cast_shadows']:
                    errors.append('panorama_fill_profile_mismatch')
            row['profile'] = p
        row['errors'], row['success'] = errors, not errors
        return row


def install_worker(app):
    view = PanoramaView(app)
    review = app.review
    original_view, original_state = review.set_view, review.state
    original_snapshot, original_restore = review.snapshot_scene, review.restore_scene
    original_run = app.run
    reload_fill_checked = False
    review.set_view = lambda request: view.apply(request, original_view)
    def snapshot():
        result = original_snapshot()
        result['motion_panorama'] = view.snapshot()
        return result
    def restore(snapshot):
        errors = original_restore(snapshot)
        try:
            view.restore(snapshot['motion_panorama'])
        except Exception as exc:
            errors.append('panorama_fill: ' + str(exc))
        return errors
    def state(request, data, plan, prepared):
        nonlocal reload_fill_checked
        recreated = False
        floor_recreated = False
        # Transient fill/floor are intentionally absent after a map reload.
        # Recreate only these, not character bindings or the saved camera.
        if request['action'] == 'reload' and request['framing'] == FRAMING and not reload_fill_checked:
            # This is the synchronous first post-load inspection. Later deferred
            # refresh callbacks can only read state, never create this actor.
            reload_fill_checked = True
            if view.light() is None:
                view.ensure_fill(request)
                recreated = True
            if view.floor() is None:
                view.ensure_floor()
                floor_recreated = True
        result = original_state(request, data, plan, prepared)
        result['motion_review_view'] = view.readback(request)
        result['motion_review_view']['transient_fill_recreated_after_reload'] = recreated
        result['motion_review_view']['transient_floor_recreated_after_reload'] = floor_recreated
        result['success'] = result['success'] and result['motion_review_view']['success']
        return result
    def run(request):
        if request.get('action') == 'restore':
            view.hide()
        return original_run(request)
    review.snapshot_scene, review.restore_scene = snapshot, restore
    app.state = review.state = state
    app.run = run
    return view
