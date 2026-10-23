"""Evidence checks for reload/animation failure reporting without loading UE."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'ue_complete_character_slot_review_v1.py'


def function(name, **context):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(context)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('wrong_motion,wrong_playing', [(True, False), (False, True), (True, True)])
def test_saved_components_do_not_mask_failed_animation(wrong_motion, wrong_playing):
    motions = {'female': {'animation': 'female_clip', 'playing': True},
               'male': {'animation': 'wrong' if wrong_motion else 'male_clip', 'playing': not wrong_playing}}
    fixed = SimpleNamespace(readback=lambda *a: {'success': True}, object_path=lambda x: x)
    legacy = SimpleNamespace(now=lambda: 'now', world_path=lambda: 'review')
    state = function('state', fixed=fixed, legacy=legacy, animation_readback=lambda: motions)
    result = state({'action_index': 1, 'playing': True}, {'sources': {}},
                   {'plan_sha256': 'p', 'limitations': {}},
                   {'female': {'review_motion': 'female_clip'}, 'male': {'review_motion': 'male_clip'}})
    assert not result['success']
    assert bool(result['animation_errors'])
    assert result['human_acceptance'] == 'pending'


def test_missing_bone_never_becomes_component_origin_evidence():
    body = SimpleNamespace(get_anim_instance=lambda: None, get_bone_index=lambda name: -1 if name == 'hand_l' else 1)
    sample = function('animation_readback', fixed=SimpleNamespace(body_for=lambda sex: body))
    with pytest.raises(RuntimeError, match='missing bones'):
        sample()


def test_rollback_restores_original_mode_after_single_node_override():
    calls = []
    actor = SimpleNamespace(tags=['DM_CCWH_SLOT_COPY_HairPart01'], set_actor_rotation=lambda *a: None)
    actor.get_editor_property = lambda name: getattr(actor, name)
    before_tags = ['DM_CCWH_FIXED_SLOT_V1', 'keep_tag', 'DM_CCWH_SLOT_COPY_HairPart17']
    body = SimpleNamespace(override_animation_data=lambda *a: calls.append('override_single_node'),
                           get_anim_instance=lambda: None,
                           set_animation_mode=lambda mode: calls.append('mode:' + mode))
    camera = SimpleNamespace(set_actor_location=lambda *a: None, set_actor_rotation=lambda *a: None,
                             get_component_by_class=lambda *a: SimpleNamespace(set_editor_property=lambda *a: None))
    restore = function('restore_scene', fixed=SimpleNamespace(_restore=lambda *a: None,
                       _set_instance_property=lambda obj, name, value: setattr(obj, name, list(value))),
                       unreal=SimpleNamespace(CameraComponent=object))
    snapshot = {'characters': {'female': {'components': [], 'body': body, 'animation_mode': 'blueprint',
                'animation': None, 'looping': False, 'playing': False, 'position': 0., 'rate': 1.,
                'actor': actor, 'actor_tags': before_tags, 'rotation': 0}},
                'camera': camera, 'camera_location': 0, 'camera_rotation': 0, 'camera_fov': 50}
    assert restore(snapshot) == []
    assert calls == ['override_single_node', 'mode:blueprint']
    assert actor.tags == before_tags
