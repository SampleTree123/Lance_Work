"""Optional camera/fill lifecycle without UE, original source edits or root locking."""
import argparse
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motion_library_panorama_v1 as panorama


def vector(x=0., y=0., z=0.):
    return NS(x=x, y=y, z=z)


def rotation(pitch=0., yaw=0., roll=0.):
    return NS(pitch=pitch, yaw=yaw, roll=roll)


class Component:
    def __init__(self):
        self.values = {'intensity': 100., 'cast_shadows': True, 'field_of_view': 50.,
            'static_mesh': None, 'override_materials': [], 'cast_shadow': True, 'collision': 'query'}
        self.visible, self.color = True, 'old_color'
    def set_mobility(self, value): self.mobility = value
    def set_intensity(self, value): self.values['intensity'] = value
    def set_light_color(self, value, _): self.color = value
    def set_cast_shadows(self, value): self.values['cast_shadows'] = value
    def set_visibility(self, value, _): self.visible = value
    def is_visible(self): return self.visible
    def get_light_color(self): return self.color
    def get_editor_property(self, key): return self.values[key]
    def set_editor_property(self, key, value): self.values[key] = value
    def get_local_bounds(self): return vector(-50., -50., -50.), vector(50., 50., 50.)
    def set_static_mesh(self, value): self.values['static_mesh'] = value
    def get_num_materials(self): return max(len(self.values['override_materials']), len(self.values['static_mesh'].materials))
    def get_material(self, i):
        overrides = self.values['override_materials']
        return overrides[i] if i < len(overrides) else self.values['static_mesh'].materials[i]
    def set_material(self, i, value):
        overrides = self.values['override_materials']
        while len(overrides) <= i: overrides.append(None)
        overrides[i] = value
    def set_cast_shadow(self, value): self.values['cast_shadow'] = value
    def set_collision_enabled(self, value): self.values['collision'] = value
    def get_collision_enabled(self): return self.values['collision']


class Asset:
    def __init__(self, name, materials=()): self.name, self.materials = name, list(materials)
    def get_path_name(self): return self.name


class Actor:
    def __init__(self, label='', loc=None, rot=None):
        self.label, self.loc, self.rot = label, loc or vector(), rot or rotation()
        self.tags, self.component = [], Component()
        self.transient = False
        self.root_component, self.scale = self.component, vector(1., 1., 1.)
    def get_actor_label(self): return self.label
    def set_actor_label(self, value): self.label = value
    def get_actor_location(self): return self.loc
    def get_actor_rotation(self): return self.rot
    def get_actor_scale3d(self): return self.scale
    def set_actor_scale3d(self, value): self.scale = value
    def set_actor_location(self, value, *args): self.loc = value
    def set_actor_rotation(self, value, *args): self.rot = value
    def get_component_by_class(self, _): return self.component
    def get_editor_property(self, key): return getattr(self, key)
    def set_editor_property(self, key, value): setattr(self, key, value)


class Directional(Actor):
    pass


class StaticActor(Actor):
    pass


@pytest.fixture
def rig():
    camera = Actor('Camera')
    old_fill = Actor('Fill', vector(200., 0., 190.))
    floor = StaticActor('Floor', vector(0., 0., -5.))
    floor.scale = vector(6., 7., .05)
    floor.component.set_static_mesh(Asset('/Engine/BasicShapes/Cube', [Asset('/Materials/CurrentFloor')]))
    actors = [old_fill, camera, floor]
    def spawn(cls, location, rot, *, transient):
        assert transient is True
        actor = cls(loc=location, rot=rot)
        actor.transient = transient
        actors.append(actor)
        return actor
    def destroy(actor):
        actors.remove(actor)
        return True
    # Match UE5.8 EditorActorSubsystem.cpp:383-386: editor enumeration omits
    # RF_Transient, whereas GameplayStatics enumerates them in the same world.
    subsystem = NS(get_all_level_actors=lambda: [a for a in actors if not a.transient], spawn_actor_from_class=spawn, destroy_actor=destroy)
    level = NS(editor_invalidate_viewports=lambda: None)
    world = object()
    editor = NS(get_editor_world=lambda: world)
    def world_actors(selected_world, cls):
        assert selected_world is world
        return [a for a in actors if isinstance(a, cls)]
    u = NS(EditorActorSubsystem='actors', LevelEditorSubsystem='levels', UnrealEditorSubsystem='editor', Actor=Actor,
        get_editor_subsystem=lambda kind: {'actors': subsystem, 'levels': level, 'editor': editor}[kind],
        GameplayStatics=NS(get_all_actors_of_class=world_actors),
        DirectionalLight=Directional, DirectionalLightComponent='light', CameraComponent='camera',
        StaticMeshActor=StaticActor, StaticMeshComponent='mesh', CollisionEnabled=NS(NO_COLLISION='none'),
        Vector=vector, Rotator=rotation, Name=str, LinearColor=lambda *values: values,
        ComponentMobility=NS(MOVABLE='movable'),
        EditorLevelLibrary=NS(set_level_viewport_camera_info=lambda *args: None))
    characters = {'female': Actor(loc=vector(0., -95., 0.)), 'male': Actor(loc=vector(0., 95., 0.))}
    app = NS(unreal=u, fixed=NS(actor_for=lambda sex: characters[sex]),
        legacy=NS(PREFIX='', find=lambda name: {'Camera': camera, 'Floor': floor}.get(name)))
    def original_view(request):
        assert request['framing'] in ('full', 'head')
        camera.loc, camera.rot = vector(490., 0., 110.), rotation(yaw=180.)
        camera.component.values['field_of_view'] = 50.
    return panorama.PanoramaView(app), actors, camera, old_fill, original_view


def request(framing=panorama.FRAMING):
    return {'framing': framing, 'focus': 'both', 'action': 'view'}


def test_panorama_preserves_existing_fill_and_normal_view_hides_only_auxiliary(rig):
    view, actors, camera, old_fill, normal = rig
    before = copy.deepcopy(vars(old_fill))
    view.apply(request(), normal)
    assert camera.loc.x == 1600. and camera.component.values['field_of_view'] == 35.
    assert view.readback(request())['success']
    auxiliary = view.light()
    assert auxiliary is not old_fill and auxiliary.component.visible
    assert auxiliary.component.values['cast_shadows'] is False
    assert auxiliary.component.values['intensity'] == 10.
    assert view.floor().component.visible
    assert vars(old_fill.loc) == vars(before['loc']) and old_fill.component.values == before['component'].values
    view.apply(request('head'), normal)
    assert camera.loc.x == 490. and not auxiliary.component.visible
    assert not view.floor().component.visible
    assert view.readback(request('head'))['success']
    view.apply(request(), normal)
    assert view.light() is auxiliary and len(actors) == 5


def test_rollback_removes_only_new_auxiliary_and_restores_previous_visibility(rig):
    view, actors, camera, old_fill, normal = rig
    empty = view.snapshot()
    view.apply(request(), normal)
    view.restore(empty)
    assert view.light() is None and view.floor() is None and old_fill in actors
    view.apply(request(), normal)
    prior = view.snapshot()
    view.hide()
    view.restore(prior)
    assert view.light().component.visible and view.readback(request())['success']


def test_transient_helpers_survive_worker_handoff_and_are_found_for_hide_and_rollback(rig):
    view, actors, _, _, normal = rig
    empty = view.snapshot()
    view.apply(request(), normal)
    light, floor = view.light(), view.floor()
    assert light.transient and floor.transient
    assert light not in view.actors().get_all_level_actors()
    assert floor not in view.actors().get_all_level_actors()
    another_worker = panorama.PanoramaView(view.app)
    assert another_worker.light() is light and another_worker.floor() is floor
    assert another_worker.readback(request())['success']
    another_worker.hide()
    assert not light.component.visible and not floor.component.visible
    another_worker.restore(empty)
    assert light not in actors and floor not in actors


def test_transient_orphans_are_not_invisible_to_duplicate_and_owner_guards(rig):
    view, actors, _, _, normal = rig
    view.apply(request(), normal)
    duplicate = Directional(panorama.LABEL)
    duplicate.transient, duplicate.tags = True, [panorama.OWNER]
    actors.append(duplicate)
    with pytest.raises(ValueError, match='Duplicate panorama fill'):
        panorama.PanoramaView(view.app).light()
    actors.remove(duplicate)
    view.floor().tags = []
    with pytest.raises(ValueError, match='foreign floor'):
        panorama.PanoramaView(view.app).floor()


def test_floor_reuses_actual_mesh_material_and_derives_lower_extended_geometry(rig):
    view, _, _, _, normal = rig
    source, mesh, materials, original = view.source_floor()
    view.apply(request(), normal)
    ground = view.floor()
    assert ground.component.values['static_mesh'] is mesh
    assert ground.component.get_material(0) is materials[0]
    assert vars(ground.scale) == dict(x=40., y=40., z=.05)
    assert ground.loc.z == -5.25
    row = view.floor_readback(True)
    assert row['success'] and row['source_geometry']['world_min_xy'] == [-2000., -2000.]
    assert row['source_geometry']['top_z_cm'] == -2.75
    assert view.source_floor()[3] == original and source.component.values['override_materials'] == []
    ground.component.set_material(0, Asset('/Wrong'))
    assert not view.floor_readback(True)['success']
    view.apply(request(), normal)
    ground.scale.x = 2.
    assert not view.floor_readback(True)['success']


def test_floor_geometry_uses_measured_bounds_not_assumed_cube_size():
    result = panorama.floor_geometry([-20., 0., -2.], [20., 80., 2.], [10., 20., 4.], [2., 3., .5], [0., 0., 0.])
    assert result['scale'] == [100., 50., .5]
    assert result['location'] == [10., -1860., 3.75]
    assert result['world_min_xy'] == [-1990., -1860.]
    assert result['top_z_cm'] == 4.75
    with pytest.raises(ValueError, match='axis-aligned'):
        panorama.floor_geometry([-50.]*3, [50.]*3, [0.]*3, [1.]*3, [0., 90., 0.])


def test_foreign_floor_is_not_adopted_and_transaction_removes_only_owned_fill(rig):
    view, actors, _, _, normal = rig
    before = view.snapshot()
    foreign = StaticActor(panorama.FLOOR_LABEL)
    actors.append(foreign)
    with pytest.raises(ValueError, match='foreign floor'): view.apply(request(), normal)
    with pytest.raises(RuntimeError, match='foreign floor'): view.restore(before)
    assert view.light() is None and foreign in actors
    assert foreign.component.values['static_mesh'] is None


def test_floor_snapshot_restores_existing_owned_geometry_material_and_hidden_state(rig):
    view, _, _, _, normal = rig
    view.apply(request(), normal)
    view.hide()
    previous = view.snapshot()
    ground = view.floor()
    ground.set_actor_scale3d(vector(1., 2., 3.))
    ground.component.set_material(0, Asset('/Changed'))
    ground.component.set_visibility(True, True)
    view.restore(previous)
    assert ground.scale == previous['floor']['scale'] and not ground.component.visible
    assert ground.component.get_material(0) is previous['floor']['override_materials'][0]
    assert view.readback(request('full'))['success']


def test_foreign_or_duplicate_same_label_light_is_never_adopted(rig):
    view, actors, _, old_fill, normal = rig
    foreign = Directional(panorama.LABEL)
    actors.append(foreign)
    with pytest.raises(ValueError, match='foreign'): view.apply(request(), normal)
    assert foreign.component.values['intensity'] == 100.
    actors.append(Directional(panorama.LABEL))
    with pytest.raises(ValueError, match='Duplicate'): view.hide()
    assert old_fill.component.visible


def test_readback_catches_moved_camera_wrong_fov_and_visible_fill_in_normal_mode(rig):
    view, _, camera, _, normal = rig
    view.apply(request(), normal)
    camera.loc.x = 900.
    assert not view.readback(request())['success']
    assert not view.readback(request('full'))['success']
    view.apply(request(), normal)
    view.light().component.values['cast_shadows'] = True
    assert not view.readback(request())['success']


def test_framing_token_maps_only_for_private_legacy_boundary_and_cli():
    original = request()
    assert panorama.legacy_request(original)['framing'] == 'full'
    assert original['framing'] == panorama.FRAMING
    parser = argparse.ArgumentParser()
    parser.add_argument('--framing', choices=('full', 'head'))
    panorama.extend_parser(parser)
    assert parser.parse_args(['--framing', panorama.FRAMING]).framing == panorama.FRAMING
    assert parser.parse_args(['--framing', 'head']).framing == 'head'


@pytest.mark.parametrize('key,value', [('camera_x_cm', -1), ('camera_fov_degrees', 180), ('fill_intensity', float('nan'))])
def test_unreviewed_profile_parameters_still_require_finite_safe_numbers(monkeypatch, key, value):
    monkeypatch.setitem(panorama.PROFILE, key, value)
    with pytest.raises(ValueError): panorama.profile()
