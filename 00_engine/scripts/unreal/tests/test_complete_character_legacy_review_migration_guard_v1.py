"""Legacy migration guard using fake actors only; never import/connect Unreal."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'ue_complete_character_wardrobe_hair_review_v1.py'
LEVEL = '/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001'
ASSET_ROOT = LEVEL.rsplit('/', 1)[0]
PREFIX = 'DM_CCWH_'


def functions(*names, **context):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = dict(LEVEL=LEVEL, ASSET_ROOT=ASSET_ROOT, PREFIX=PREFIX, **context)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace


def actor(sex='female', *, label=None, owned=True, matching_class=True):
    name = f'BP_DM_Complete_{sex.title()}_FixedSlots_v001'
    cls = ASSET_ROOT + '/FixedSlotRuntime/' + name + '.' + name + '_C' if matching_class else '/Script/Engine.SkeletalMeshActor'
    return SimpleNamespace(get_actor_label=lambda: label or PREFIX + sex + '_Character',
                           get_editor_property=lambda key: ['DM_CCWH_FIXED_SLOT_V1'] if owned else [],
                           get_class=lambda: SimpleNamespace(get_path_name=lambda: cls))


def namespace(rows=(), level=LEVEL, *extra):
    return functions('path', 'assert_legacy_review_unmigrated', *extra,
                     world_path=lambda: level,
                     actors=lambda: SimpleNamespace(get_all_level_actors=lambda: list(rows)))


@pytest.mark.parametrize('rows', [[], [actor(label='DM_CCWH_female_Body')], [actor(owned=False)],
                                 [actor(matching_class=False)], [actor(label='UnrelatedActor')]])
def test_unmigrated_or_unrelated_actor_does_not_trigger_guard(rows):
    namespace(rows)['assert_legacy_review_unmigrated']()


@pytest.mark.parametrize('rows', [[actor()], [actor('male')], [actor(), actor('male')]])
def test_confirmed_owned_actor_blocks_even_partial_pair(rows):
    with pytest.raises(RuntimeError, match='固定槽位角色'):
        namespace(rows)['assert_legacy_review_unmigrated']()


def test_same_actor_labels_in_another_current_map_are_not_migration_evidence():
    ns = namespace([actor(), actor('male')], '/Game/OtherReview')
    ns['actors'] = lambda: pytest.fail('Do not inspect unrelated worlds')
    ns['assert_legacy_review_unmigrated']()


def test_blueprint_presence_is_not_queried_or_used_as_migration_evidence():
    ns = namespace([])
    ns['unreal'] = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(
        does_asset_exist=lambda _: pytest.fail('A built Blueprint is not a migrated actor')))
    ns['assert_legacy_review_unmigrated']()


@pytest.mark.parametrize('action', ['show', 'view', 'playback', 'reload'])
def test_old_entry_rejects_before_catalog_or_any_stage_work(action):
    ns = namespace([actor()], LEVEL, 'main')
    ns['DM_CC_REVIEW_REQUEST'] = {'action': action}
    ns['CONTRACT'] = SimpleNamespace(catalog=lambda: pytest.fail('Guard must precede old preparation'))
    with pytest.raises(RuntimeError, match='open_complete_character_slot_review_v1'):
        ns['main']()


def test_direct_legacy_stage_is_guarded_before_actor_mutation():
    ns = namespace([actor()], LEVEL, 'stage')
    ns['unreal'] = SimpleNamespace(Vector=lambda *a: pytest.fail('No old actor mutation allowed'))
    with pytest.raises(RuntimeError, match='固定槽位角色'):
        ns['stage']({'female': {}})


def test_target_map_loaded_later_is_checked_before_save_environment_or_stage():
    world = ['/Game/UnmigratedOtherMap']
    ns = namespace([actor()], LEVEL, 'main')
    ns.update(world_path=lambda: world[0], DM_CC_REVIEW_REQUEST={'action': 'reload'},
              CONTRACT=SimpleNamespace(catalog=lambda: {}),
              normalize_request=lambda *a: {'action_index': 0}, prepare=lambda *a: {})
    def load():
        world[0] = LEVEL
        return SimpleNamespace(save_current_level=lambda: pytest.fail('Must not save migrated map through old UI'))
    ns['ensure_level'] = load
    ns['environment'] = lambda: pytest.fail('Must not restage environment')
    with pytest.raises(RuntimeError, match='固定槽位角色'):
        ns['main']()


def test_restore_remains_available_after_migration():
    ns = namespace([actor()], LEVEL, 'main')
    ns.update(DM_CC_REVIEW_REQUEST={'action': 'restore'}, restore=lambda: {'success': True, 'editor_closed': False})
    assert ns['main']() == {'success': True, 'editor_closed': False}
