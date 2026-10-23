"""Apply the existing modular wardrobe pipeline to one temporary scene actor.

The caller owns actor creation/destruction and serialization of editor work.
Never launches editors, edits source assets, or touches saved shooting points.
"""
from __future__ import annotations

import copy
import hashlib
import math
import types
from pathlib import Path

import scene_site_appearance_v1 as contract
import ue_complete_character_fixed_slot_runtime_v1 as fixed
import ue_complete_character_wardrobe_hair_review_v1 as review
import hair_eye_color_runtime_v1 as colors
import ue_hair_coverage_runtime_v1 as hair_coverage

ASSET_ROOT = '/Game/DataMake/Appearance/Materials'
COMPOSITE_ROOT = '/Game/DataMake/Animations/Expressions'
FOLLOWER_ROOT = '/Game/DataMake/Appearance/Followers'
CACHE_KEY = '_dm_scene_site_appearance_cache_v1'


def invalidate_cache(u, actor=None):
    """Call when the session input guard detects changes or destroys actors."""
    cache = getattr(u, CACHE_KEY, None)
    if cache is not None:
        if actor is None:
            cache.clear()
        else:
            cache.pop(actor.get_path_name(), None)


def formal_copy_pose_blueprint(u, mesh):
    """Persist a derived follower for the current skeleton, outside retired maps.

    Reuse the validated graph builder with private globals so neither legacy
    review paths nor another caller's module state are modified.
    """
    skeleton = mesh.get_editor_property('skeleton')
    skeleton_path = fixed.object_path(skeleton)
    suffix = hashlib.sha256(skeleton_path.encode()).hexdigest()[:12]
    target = FOLLOWER_ROOT + '/ABP_CCWH_CopyPose_' + suffix
    original = review.copy_pose_blueprint
    namespace = dict(original.__globals__, unreal=u, copy_pose_path=lambda _mesh: target)
    builder = types.FunctionType(original.__code__, namespace, original.__name__,
                                 original.__defaults__, original.__closure__)
    blueprint = builder(mesh)
    if (not isinstance(blueprint, u.AnimBlueprint) or blueprint.generated_class() is None
            or blueprint.get_editor_property('target_skeleton') != skeleton):
        raise ValueError('正式跟随动画的骨架或编译结果不正确：' + target)
    return blueprint


def prepare(u, selection, motion, *, body_action_id=None, data=None, path_overlay=None):
    """Load and validate all parts before modifying the temporary actor.

    path_overlay maps old object paths to verified relocated object paths. It is
    deliberately explicit; no folder scan or basename fallback is permitted.
    """
    formal = contract.formal_runtime()
    domain = formal[1] if formal else contract
    data = domain.catalog() if data is None else data
    # The accepted face curves are composed over the actual body below; the
    # historical six-body library is not a restriction on new body motions.
    selection = domain.validate_selection(selection, data)
    sex = selection['sex']
    people = domain.identities.identity_catalog()
    case = people['by_id'][selection['character_id']]
    registry, _source = domain.slots._registry()
    canonical = domain.slots.to_runtime_choice(sex, selection['choice'])
    resolved, followers = fixed._selection(registry, sex, canonical)
    base = [{'component_name': fixed.BASE_ROLES[m['role']], 'mesh_path': m['path'],
             'kind': 'body' if m['role'] == 'body' else 'face_support'} for m in case['meshes']]
    overlay = {**getattr(domain, 'formal_path_overlay', {}), **(path_overlay or {})}
    review.cache()['compatibility'].clear()
    def load(path):
        return u.load_asset(overlay.get(path, path))
    body = load(next(r['mesh_path'] for r in base if r['kind'] == 'body'))
    if not isinstance(body, u.SkeletalMesh):
        raise ValueError('角色身体资产缺失。')
    if fixed.object_path(body.get_editor_property('skeleton')) != overlay.get(case['skeleton'], case['skeleton']):
        raise ValueError('角色身体骨架与目录不一致。')
    prepared = []
    for assignment in base + followers:
        row = copy.deepcopy(assignment)
        mesh = body if row['kind'] == 'body' else load(row['mesh_path'])
        if not isinstance(mesh, u.SkeletalMesh):
            raise ValueError('外观部件资产缺失：' + row['mesh_path'])
        if not mesh.get_editor_property('materials') or any(m.get_editor_property('material_interface') is None
                for m in mesh.get_editor_property('materials')):
            raise ValueError('外观部件材质缺失：' + row['mesh_path'])
        row['mesh'] = mesh
        if row['kind'] == 'hair' and fixed.object_path(mesh.get_editor_property('skeleton')) != overlay.get(
                resolved['hair_skeleton_path'], resolved['hair_skeleton_path']):
            raise ValueError('发型骨架与所选性别的已验收版本不一致。')
        if row['kind'] != 'body':
            row['compatibility'] = review.compatibility(body, mesh)
            if row['compatibility']['follow_mode'] == 'copy_pose':
                if formal:
                    bp = formal_copy_pose_blueprint(u, mesh)
                else:
                    skeleton_path = fixed.object_path(mesh.get_editor_property('skeleton'))
                    historical = next((old for old, new in overlay.items() if new == skeleton_path and '.' in old), skeleton_path)
                    suffix = hashlib.sha256(historical.encode()).hexdigest()[:12]
                    path = review.ASSET_ROOT + '/Followers/ABP_CCWH_CopyPose_' + suffix
                    bp = load(path)
                    if (not isinstance(bp, u.AnimBlueprint) or bp.generated_class() is None
                            or bp.get_editor_property('target_skeleton') != mesh.get_editor_property('skeleton')):
                        raise ValueError('部件所需的既有跟随动画缺失：' + path)
                row['copy_pose_blueprint'] = bp
        prepared.append(row)
    face = None
    if selection['face_id'] != 'none':
        import ue_cfd40_full_motion_loop_v1 as source_loop
        loop = source_loop.private_module('ue_cfd40_full_motion_loop_v1')
        loop.RUN = contract.ROOT.parent / 'appearance_composites'
        loop.ASSET_ROOT = COMPOSITE_ROOT
        if formal:
            choices, selection_record = formal[0].accepted_faces()
            # The unchanged composer pins the old shared-skeleton root in one
            # guard. Compile a PRIVATE copy with that exact constant remapped;
            # every bone/curve/source preservation check remains byte-identical.
            composer_path = Path(__file__).with_name('ue_compose_native_face_body_v1.py')
            text = composer_path.read_text(encoding='utf-8')
            old_root = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_'
            expected = {s: domain.identities.identity_catalog()['skeletons'][s].split('.')[0]
                        for s in ('female', 'male')}
            old_guard = "expected = '" + old_root + "' + sex.title() + '_v1'"
            if text.count(old_guard) != 1:
                raise ValueError('原表情合成器骨架保护规则已变化，不能自动改写。')
            text = text.replace(old_guard, 'expected = FORMAL_SKELETON_PACKAGES[sex]')
            composer = types.ModuleType('_dm_scene_formal_face_composer')
            composer.__file__ = str(Path(__file__).resolve())
            composer.FORMAL_SKELETON_PACKAGES = expected
            exec(compile(text, str(composer_path), 'exec'), composer.__dict__)
            composer.RUN, composer.ASSET_ROOT = loop.RUN, COMPOSITE_ROOT + '/Composites'
            loop.composer = lambda: composer
            original_record = loop.record
            def code_record(path):
                row = original_record(path)
                if Path(path).resolve() == Path(__file__).resolve():
                    row['adapted_from'] = original_record(composer_path)
                    row['formal_catalog'] = domain.formal_runtime_source
                return row
            loop.record = code_record
        else:
            choices, selection_record = loop.accepted_faces()
        choice, accepted_report = choices[(sex, selection['face_id'])]
        if motion is None:
            motion = load(choice['asset'])
            face = {'kind': 'accepted_static_face', 'face_id': selection['face_id'],
                    'accepted_selection': selection_record, 'animation_path': fixed.object_path(motion)}
        else:
            action = {'path': fixed.object_path(motion), 'action_id': body_action_id or fixed.object_path(motion)}
            motion, face = loop.ensure_composite(u, sex, action, choice, accepted_report, selection_record)
            face['face_id'] = selection['face_id']
    if motion is not None and (not isinstance(motion, u.AnimSequence)
            or motion.get_editor_property('skeleton') != body.get_editor_property('skeleton')):
        raise ValueError('动作或表情动画不属于当前性别的共享骨架。')
    return {'selection': selection, 'assignments': prepared, 'motion': motion,
            'face': face, 'resolved': resolved, 'body': body}


def apply_actor(u, actor, selection, t, motion, *, body_action_id=None, data=None, path_overlay=None):
    """Apply at a paused sample time; preserve every follower and rollback on error.

    `actor` must be a scene review duplicate with the exact 38 existing modular
    components. `motion` is the caller's resolved AnimSequence (or None/static).
    Return actual component mesh paths for the caller's review receipt.
    """
    if not actor.get_actor_label().startswith('DM_SiteReview_'):
        raise ValueError('只允许修改拍摄点专用临时角色。')
    if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
        raise ValueError('预览时间必须为非负数字。')
    # A playback tick must not reread the complete registry, hash face evidence,
    # rebuild the component binding, or generate a material. Dependency/source
    # invalidation remains the caller's session input guard responsibility.
    key = contract.io.digest({'selection': selection, 'motion': fixed.object_path(motion), 'hair_coverage': hair_coverage.VERSION,
                              'body_action_id': body_action_id, 'overlay': path_overlay or {}})
    if not hasattr(u, CACHE_KEY):
        setattr(u, CACHE_KEY, {})
    cache = getattr(u, CACHE_KEY)
    actor_key = actor.get_path_name()
    previous = cache.get(actor_key)
    if previous and previous['actor'] == actor and previous['key'] == key:
        body = previous['body']
        clip = previous['motion']
        if clip:
            body.set_position(t, False)
        result = dict(previous['result'], time_seconds=t)
        return result
    prepared = prepare(u, selection, motion, body_action_id=body_action_id, data=data, path_overlay=path_overlay)
    cs = fixed.actor_components(actor)
    body = cs['Body']
    if any(c.get_attach_parent() != body for name, c in cs.items() if name != 'Body'):
        raise ValueError('临时角色部件未连接到同一身体。')
    old = {name: fixed._snapshot(c) for name, c in cs.items()}
    old_parent_bounds = {name: c.get_editor_property('use_attach_parent_bound') for name, c in cs.items()}
    old_tags = list(actor.get_editor_property('tags'))
    animation = body.get_editor_property('animation_data')
    old_animation = {'motion': animation.get_editor_property('anim_to_play'), 't': body.get_position(),
                     'playing': bool(body.get_anim_instance() and body.is_playing()),
                     'loop': animation.get_editor_property('saved_looping'),
                     'rate': animation.get_editor_property('saved_play_rate')}
    try:
        body.set_skeletal_mesh_asset(prepared['body'])
        fixed._set_actor_copy_tags(actor, fixed.expected_actor_copy_tags(prepared['assignments']))
        desired = {r['component_name']: r for r in prepared['assignments']}
        for name in fixed.COMPONENTS:
            row = desired.get(name)
            fixed._set_component(cs[name], row, body)
            # Leader-pose bounds alone fall back to the unmoving mesh bounds
            # when the body has no PhysicsAsset. These attached followers must
            # inherit the moving body's bounds to avoid close-camera culling.
            # Copy-pose followers retain their existing bounds policy.
            if row and name != 'Body' and row['compatibility']['follow_mode'] == 'leader_pose':
                fixed._set_instance_property(cs[name], 'use_attach_parent_bound', True)
        color = {k: prepared['selection'][k] for k in ('hair_color', 'eye_color')}
        if prepared['resolved'].get('resolved_hair_id') is None:
            color['hair_color'] = 'original'
        if color['hair_color'] != 'original':
            import hair_color_neutral_trial_runtime_v1 as neutral_colors
            neutral_colors.apply(color, cs, 1 if selection['sex'] == 'female' else 2, ASSET_ROOT)
        coverage = hair_coverage.apply(u, cs)
        clip = prepared['motion']
        body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
        body.set_enable_animation(True)
        body.set_update_animation_in_editor(True)
        body.set_component_tick_enabled(True)
        fixed._set_instance_property(body, 'pause_anims', False)
        body.override_animation_data(clip, False, False, t, 1.)
        if clip:
            body.play_animation(clip, False)
            body.set_position(t, False)
            body.stop()
        for name, c in cs.items():
            if c.get_skeletal_mesh_asset() != (desired[name]['mesh'] if name in desired else None):
                raise RuntimeError('外观实际加载与选择不一致：' + name)
        result = {'success': True, 'selection': prepared['selection'], 'time_seconds': t,
                'animation_path': fixed.object_path(clip), 'face': prepared['face'],
                'components': {name: fixed.object_path(c.get_skeletal_mesh_asset()) for name, c in cs.items()},
                'hair_reason': prepared['resolved'].get('hair_reason'), 'source_assets_modified': False,
                'hair_coverage': coverage}
        # Bound the cache to live temporary actors instead of keeping every
        # destroyed character and its component graph alive for the session.
        for old_key, entry in list(cache.items()):
            if not u.SystemLibrary.is_valid(entry['actor']):
                cache.pop(old_key, None)
        cache[actor_key] = {'actor': actor, 'key': key, 'body': body, 'motion': clip, 'result': result}
        return result
    except Exception as exc:
        errors = []
        try:
            body.set_skeletal_mesh_asset(old['Body']['mesh'])
            fixed._set_instance_property(actor, 'tags', old_tags)
            for name, c in cs.items():
                fixed._restore(c, old[name], body)
                fixed._set_instance_property(c, 'use_attach_parent_bound', old_parent_bounds[name])
            body.set_animation_mode(old['Body']['mode'])
            body.override_animation_data(old_animation['motion'], old_animation['loop'], old_animation['playing'],
                                          old_animation['t'], old_animation['rate'])
        except Exception as rollback:
            errors.append(str(rollback))
        raise RuntimeError('应用外观失败：' + str(exc) + '；恢复错误：' + str(errors)) from exc
