"""Reuse the fixed-slot review implementation in the isolated CFD pair map.

Only the root session executes this worker. Existing clothes/hair/CopyPose assets
are consumed read-only; new character blueprints and motion copies stay isolated.
"""
import hashlib
import importlib
import json
from pathlib import Path
import uuid

import unreal
import run_cfd_native_pair_transfer_v1 as transfer
import ue_complete_character_slot_review_v1 as review
importlib.reload(review)  # Original worker reloads its dependencies first.

fixed, legacy = review.fixed, review.legacy
OLD_REVIEW_ASSET_ROOT = '/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005'
fixed.ROOT = transfer.RUN / 'runtime'
fixed.STANDARD = transfer.RUN / 'standard_candidate_registry.json'
fixed.LEVEL = transfer.LEVEL
fixed.ASSET_ROOT = transfer.UE_ROOT
fixed.BP_ROOT = transfer.UE_ROOT + '/FixedSlotRuntime'
original_make_plan = fixed.make_plan


def isolated_plan(registry_path, choices_by_sex, source_registry_path=None):
    return original_make_plan(registry_path, choices_by_sex,
                              fixed.STANDARD if source_registry_path is None else source_registry_path)


fixed.make_plan = isolated_plan
legacy.ROOT = transfer.RUN / 'runtime'
legacy.SOURCE = fixed.STANDARD
legacy.LEVEL = transfer.LEVEL
legacy.ASSET_ROOT = transfer.UE_ROOT
legacy.CACHE = '_dm_cfd_native_pair_review_cache_v1'
legacy.THROTTLE = '_dm_cfd_native_pair_original_cpu_throttle_v1'
legacy.REFRESH = '_dm_cfd_native_pair_legacy_refresh_v1'
review.ROOT = transfer.RUN / 'runtime'
review.REFRESH = '_dm_cfd_native_pair_slot_refresh_v1'


def existing_copy_pose_path(mesh):
    suffix = hashlib.sha256(legacy.path(mesh.get_editor_property('skeleton')).encode()).hexdigest()[:12]
    return OLD_REVIEW_ASSET_ROOT + '/Followers/ABP_CCWH_CopyPose_' + suffix


# The rig is that of the retained follower, independent of the new leader's ID.
# preflight still verifies graph, target skeleton, and common bone hierarchy.
legacy.copy_pose_path = existing_copy_pose_path


def stage(request):
    """Build only this new pair's map; no migration/deletion of old actors."""
    levels = legacy.ensure_level()
    legacy.environment()
    data = review.contract.catalog()
    # Initial UI choices use the existing contract. Body animation starts static.
    request = review.current_request(dict(request, action='show', action_index=0,
                                           playing=False, save=False))
    plan, prepared = review.load_plan(request, data)
    fixed.build_blueprints(plan, prepared)
    for sex in fixed.SEXES:
        actor = fixed.actor_for(sex)
        if actor is None:
            bp = unreal.load_asset(fixed.blueprint_path(sex))
            actor = legacy.actors().spawn_actor_from_class(
                bp.generated_class(), unreal.Vector(0, -95 if sex == 'female' else 95, 0),
                unreal.Rotator(yaw=-90))
            if actor is None:
                raise RuntimeError('Cannot spawn isolated character: ' + sex)
            actor.set_actor_label(fixed.actor_label(sex))
            actor.set_editor_property('tags', [unreal.Name(fixed.OWNER_TAG)])
        fixed._owned_actor(sex)  # Reject an unrelated actor with a matching label.
    fixed.apply_prepared(plan, prepared)
    review.set_animation(request, prepared)
    review.set_view(request)
    result = review.state(request, data, plan, prepared)
    if not result['success']:
        raise RuntimeError('New pair stage readback failed: ' + str(result))
    if not levels.save_current_level():
        raise RuntimeError('Could not save isolated pair map')
    review.write('current_case.json', result)
    review.write('stage_report.json', result)
    return result


if __name__ == '__main__':
    incoming = globals().get('DM_SLOT_REVIEW_REQUEST', {})
    try:
        result = stage(incoming) if globals().get('DM_CFD_PAIR_STAGE') else review.run(incoming)
        result_file = review.write('replies/' + uuid.uuid4().hex + '.json', result)
        print(review.MARKER + json.dumps({'success': result.get('success', False),
                                          'result_file': str(result_file)}))
    except Exception as exc:
        review.write('last_error.json', {'success': False, 'at': legacy.now(), 'error': str(exc)})
        raise
