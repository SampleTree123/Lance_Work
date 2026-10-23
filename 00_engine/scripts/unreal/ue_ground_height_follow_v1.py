"""Vertical terrain compensation shared by review and sequence preparation.

No IK or bone edits: actor Z = placement Z + ground(t) - ground(start).
Pelvis XY comes from the evaluated animation, including in-skeleton travel.
No previous-frame state is used, so scrubbing and rendering are deterministic.
Three explicit saved sites use an infinite fixed plane instead of collision
traces. This preserves the saved actor placement and authored jump/bone Z.
"""
from collections import OrderedDict
import copy
import math

VERSION = 'ground_height_follow_v1'
_POSE_XY = OrderedDict()

# User saved /1 shooting planes. Analytic/infinite XY coverage introduces no
# visible actor, collision mesh, terrain edit, shadow or saved-level mutation.
# The original placement is retained as recovery evidence, not rewritten.
FIXED_SUPPORT_VERSION = 'fixed_saved_site_plane_v1'
FIXED_SITE_SUPPORT = {
    'site_98aac485de': {'map': '/Game/Scenes/Kowloon/Maps/Kowloon',
        'name': '九龙巷道/1', 'saved_position_cm': {'x': 658.468, 'y': -250.807, 'z': 0.}},
    'site_235511f7b9': {'map': '/Game/Scenes/Madeline/Maps/Exterior',
        'name': '教堂 /1', 'saved_position_cm': {'x': 0., 'y': 0., 'z': 0.}},
    'site_cbee266c51': {'map': '/Game/Scenes/racing_track/map/racing_track',
        'name': '赛车场/1', 'saved_position_cm': {'x': -42040., 'y': -62220., 'z': -14110.}},
}


def support_for_site(site):
    """Resolve only the three explicit saved sites; never guess by scene name."""
    site = site or {}
    configured = FIXED_SITE_SUPPORT.get(site.get('site_id'))
    if configured is None:
        return None
    if site.get('map') != configured['map']:
        raise ValueError('固定拍摄地面与已保存点位的场景不一致。')
    try:
        plane_z = float(site['position']['z'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('固定拍摄地面需要当前点位的有效高度。') from exc
    if not math.isfinite(plane_z):
        raise ValueError('固定拍摄地面需要当前点位的有效高度。')
    return {'version': FIXED_SUPPORT_VERSION, 'site_id': site['site_id'],
            **copy.deepcopy(configured), 'plane_z_cm': plane_z,
            'coverage': 'infinite_xy', 'implementation': 'analytic_no_scene_actor',
            'source_scene_modified': False, 'authored_animation_z': 'preserved', 'ik': 'none'}


def require_trajectory_support(trajectory, site):
    """Prevent a previously prepared collision curve from bypassing a site plane."""
    support = support_for_site(site)
    if support is not None:
        if (trajectory.get('support_policy') != FIXED_SUPPORT_VERSION
                or trajectory.get('support_plane') != support):
            raise ValueError('Prepared trial lacks current fixed shooting plane; preserve it and choose a new trial ID')
        frames = trajectory.get('frames', [])
        if not frames or any(not math.isfinite(float(row['actor_z_cm']))
                             or not math.isfinite(float(row.get('offset_z_cm', 0.)))
                             or abs(float(row['actor_z_cm'])-float(frames[0]['actor_z_cm'])) > 1e-6
                             or abs(float(row.get('offset_z_cm', 0.))) > 1e-6 for row in frames):
            raise ValueError('Fixed shooting plane requires constant actor Z and preserved animation Z')
    return trajectory


def actor_height(base_z, start_ground_z, ground_z):
    values = (base_z, start_ground_z, ground_z)
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('地面高度包含无效数值。')
    return float(base_z) + (float(ground_z) - float(start_ground_z))


def body_component(u, actor):
    bodies = [c for c in actor.get_components_by_class(u.SkeletalMeshComponent)
              if c.get_name() == 'Body']
    if len(bodies) != 1:
        raise ValueError('地面跟随无法定位人物身体组件。')
    return bodies[0]


def pelvis_position(u, animation, t):
    key = (animation.get_path_name(), round(float(t), 7))
    if key in _POSE_XY:
        _POSE_XY.move_to_end(key)
        return u.Vector(*_POSE_XY[key])
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE,
        'should_retarget': False, 'extract_root_motion': False,
        'incorporate_root_motion_into_pose': True, 'evaluate_curves': False})
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(animation, float(t), options)
    if not u.AnimPoseExtensions.is_valid(pose):
        raise ValueError('地面跟随无法读取当前动作姿态。')
    if 'pelvis' not in {str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}:
        raise ValueError('地面跟随需要人物 pelvis 骨骼。')
    point = u.AnimPoseExtensions.get_bone_pose(pose, u.Name('pelvis'), u.AnimPoseSpaces.WORLD).translation
    _POSE_XY[key] = (float(point.x), float(point.y), float(point.z))
    if len(_POSE_XY) > 2400:
        _POSE_XY.popitem(last=False)
    return point


def ground_height(u, world, point, reference_z, ignored):
    hit = u.SystemLibrary.line_trace_single(world,
        u.Vector(point.x, point.y, reference_z + 100.),
        u.Vector(point.x, point.y, reference_z - 1000.),
        u.TraceTypeQuery.ECC_VISIBILITY, True, ignored, u.DrawDebugTrace.NONE)
    if not hit or not hit.to_tuple()[0]:
        raise ValueError('人物当前位置下方没有可碰撞地面，请调整拍摄点。')
    return float(hit.to_tuple()[5].z)


def sample(u, actor, animation, time_seconds, *, source_start_seconds=0., ignore_actors=None, site=None):
    """Actor must be at its uncorrected placement when this function is called."""
    base_z = float(actor.get_actor_location().z)
    body = body_component(u, actor)
    transform = body.get_world_transform()
    start = u.MathLibrary.transform_location(transform, pelvis_position(u, animation, source_start_seconds))
    point = u.MathLibrary.transform_location(transform, pelvis_position(u, animation, time_seconds))
    support = support_for_site(site)
    if support is not None:
        start_ground = current_ground = support['plane_z_cm']
    else:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        ignored = list(ignore_actors or [])
        if actor not in ignored:
            ignored.append(actor)
        start_ground = ground_height(u, world, start, base_z, ignored)
        current_ground = (start_ground if abs(point.x-start.x) + abs(point.y-start.y) < 1e-6
                          else ground_height(u, world, point, base_z, ignored))
    z = actor_height(base_z, start_ground, current_ground)
    return {'version': VERSION, 'actor_z_cm': z, 'offset_z_cm': z-base_z,
            'baseline_ground_z_cm': start_ground, 'ground_z_cm': current_ground,
            'anchor': 'pelvis', 'world_xy_cm': [float(point.x), float(point.y)],
            'camera_policy': 'unchanged',
            'support_policy': FIXED_SUPPORT_VERSION if support else 'collision_trace_v1',
            'support_plane': support}


def apply_preview(w, actual, body_time, source_start_seconds=0.):
    d = w.live()
    actor = d['character']
    animation = w.u.load_asset(actual['animation_path'])
    if animation is None:
        raise ValueError('地面跟随无法加载当前动作。')
    result = sample(w.u, actor, animation, body_time,
                    source_start_seconds=source_start_seconds, ignore_actors=w.owned(), site=d.get('site'))
    location = actor.get_actor_location()
    actor.set_actor_location(w.u.Vector(location.x, location.y, result['actor_z_cm']), False, False)
    d['ground_height_follow'] = result
    return result


def sample_trajectory(u, actor, animation, *, frame_count, fps=30., source_start_seconds=0., ignore_actors=None, site=None):
    """Read-only bake samples; the caller writes absolute Actor Z keys."""
    if frame_count < 1 or fps <= 0:
        raise ValueError('Invalid ground-follow sampling clock')
    frames = []
    for index in range(frame_count+1):
        t = index / fps
        result = sample(u, actor, animation, source_start_seconds+t,
                        source_start_seconds=source_start_seconds, ignore_actors=ignore_actors, site=site)
        frames.append({'frame': index, 't': t, 'actor_z_cm': result['actor_z_cm'],
                       'offset_z_cm': result['offset_z_cm']})
    return {'version': VERSION, 'frames': frames, 'anchor': 'pelvis',
            'baseline_ground_z_cm': result['baseline_ground_z_cm'], 'camera_policy': 'unchanged',
            'support_policy': result['support_policy'], 'support_plane': result['support_plane']}
