"""Offline regression of the identity extension's transactional boundaries."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'ue_cfd_native_batch40_modular_review_v1.py'


def functions(*names, **values):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), 'exec'), values)
    return values


class Body:
    def __init__(self, mesh, motion='shared_walk', position=1.5):
        self.mesh, self.motion, self.position = mesh, motion, position

    def get_skeletal_mesh_asset(self):
        return self.mesh

    def set_skeletal_mesh_asset(self, mesh):
        self.mesh = mesh
        self.position = 0.

    def get_editor_property(self, name):
        assert name == 'animation_data'
        return SimpleNamespace(get_editor_property=lambda key: self.motion)

    def get_position(self):
        return self.position

    def set_position(self, value, fire):
        self.position = value


def test_identity_then_supports_use_same_body_and_retain_playback_time():
    bodies = {sex: Body(sex + '_old') for sex in ('female', 'male')}
    prepared = {sex: {'body_mesh': sex + '_new', 'review_motion': 'shared_walk'} for sex in bodies}
    applied = []

    def apply(plan, entries):
        # Existing runtime's invariant is satisfied before its five support
        # meshes and garment/hair slots are atomically reassembled.
        assert all(bodies[s].mesh == entries[s]['body_mesh'] for s in bodies)
        applied.append(True)

    ns = functions('apply_identity', 'set_animation',
                   fixed=SimpleNamespace(body_for=bodies.__getitem__, object_path=lambda v: v,
                                         actor_for=lambda s: s, actor_components=lambda actor: {}),
                   _apply=apply, _animation=lambda request, prepared: None)
    ns['apply_identity']({'appearance': {s: {'hair_color': 'original', 'eye_color': 'original'} for s in bodies}}, prepared)
    ns['set_animation']({'action_index': 2}, prepared)
    assert applied and all(body.position == 1.5 for body in bodies.values())


def test_failure_rollback_restores_body_before_five_support_parts():
    body = Body('new')
    snapshot = {'characters': {'female': {'body': body, 'components': [(body, {'mesh': 'old'})]}}}
    sequence = []

    def restore(old):
        assert body.mesh == 'old'
        sequence.append('supports_and_motion')
        return []

    ns = functions('restore_identity', _restore=restore)
    assert ns['restore_identity'](snapshot) == []
    assert sequence == ['supports_and_motion']


def test_body_rollback_failure_is_not_suppressed():
    body = Body('new')
    def broken(value):
        raise RuntimeError('invalid component')
    body.set_skeletal_mesh_asset = broken
    snapshot = {'characters': {'female': {'body': body, 'components': [(body, {'mesh': 'old'})]}}}
    ns = functions('restore_identity', _restore=lambda old: ['follower failure'])
    errors = ns['restore_identity'](snapshot)
    assert 'female/body_identity' in errors[0]
    assert errors[1] == 'follower failure'


def test_release_only_departed_identity_after_gc():
    events = []
    ns = functions('release_departed',
                   legacy=SimpleNamespace(cache=lambda: {'compatibility': {}}),
                   gc=SimpleNamespace(collect=lambda: events.append('gc')),
                   transfer=SimpleNamespace(release_saved_case_packages=lambda key: events.append(key) or key))
    assert ns['release_departed']({'AM1', 'AF1'}, {'AM1', 'AF2'}) == ['AF1']
    assert events == ['gc', 'AF1']


def test_state_checks_actual_shared_skeleton_not_only_requested_id():
    base = {'success': True, 'sources': {}, 'bindings': {'success': True, 'errors': [], 'appearance_readback': {},
             'characters': {'female': {}}}}
    plan = {'sources': {'character_registry': {'sha256': 'x'}, 'appearance_palette': {'sha256': 'palette'}},
            'characters': {'female': {'case': {'character_id': 'AF2', 'skeleton': 'female_shared'}}}}
    mesh = SimpleNamespace(get_editor_property=lambda key: 'wrong_skeleton')
    ns = functions('state', _state=lambda *args: base,
                   fixed=SimpleNamespace(BASES=('Body', 'Eyes'), object_path=lambda v: v,
                    body_for=lambda sex: SimpleNamespace(get_skeletal_mesh_asset=lambda: mesh)))
    result = ns['state']({}, {}, plan, {})
    assert not result['success']
    assert result['bindings']['errors'] == ['female/shared_skeleton_mismatch']
    assert result['bindings']['characters']['female']['character_id'] == 'AF2'


def test_stage_isolated_destination_and_no_broad_save():
    source = SOURCE.read_text(encoding='utf-8')
    assert "ASSET_ROOT = identities.batch.UE_ROOT + '/ModularReview'" in source
    assert "fixed.BP_ROOT = ASSET_ROOT + '/FixedSlotRuntime'" in source
    assert 'save_dirty_packages' not in source
    assert 'save_directory' not in source
    # Rollback must surround the Body update; original runtime only had outfit rollback.
    tree = ast.parse(source)
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    calls = [ast.unparse(n.func) for n in ast.walk(run) if isinstance(n, ast.Call)]
    assert calls.index('review.run') < calls.index('release_departed')


def test_missing_optional_viewport_does_not_block_new_isolated_map(tmp_path):
    writes, opened = [], []
    levels = SimpleNamespace(eject_pilot_level_actor=lambda: None,
                             new_level=lambda path: opened.append(path) or True)
    ns = functions('ensure_level', ROOT=tmp_path, LEVEL='/Game/OwnedReview',
        os=SimpleNamespace(getpid=lambda: 123),
        unreal=SimpleNamespace(LevelEditorSubsystem=object,
            get_editor_subsystem=lambda cls: levels,
            EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_map_packages=lambda: []),
            EditorLevelLibrary=SimpleNamespace(get_level_viewport_camera_info=lambda: None),
            EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda path: False)),
        legacy=SimpleNamespace(world_path=lambda: '/Game/Original', now=lambda: 'now'),
        review=SimpleNamespace(write=lambda name, value: writes.append((name, value))))
    assert ns['ensure_level']() is levels
    assert opened == ['/Game/OwnedReview']
    assert writes[0][1]['camera_unavailable'] is True
    assert writes[0][1]['level'] == '/Game/Original'
    assert 'camera_position' not in writes[0][1]


def test_dirty_map_still_blocks_even_when_viewport_unavailable(tmp_path):
    ns = functions('ensure_level', ROOT=tmp_path, LEVEL='/Game/OwnedReview',
        unreal=SimpleNamespace(LevelEditorSubsystem=object,
            get_editor_subsystem=lambda cls: object(),
            EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_map_packages=lambda: ['dirty'])),
        legacy=SimpleNamespace(world_path=lambda: '/Game/Original', path=lambda value: value))
    with pytest.raises(RuntimeError, match='unsaved changes'):
        ns['ensure_level']()


class Template:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path


def template_namespace(rows, expected=('Body', 'Eyes')):
    base = SimpleNamespace(get_data=lambda h: rows[h][0], get_component=lambda h: rows[h][1])
    return functions('unique_template_handles',
        fixed=SimpleNamespace(COMPONENTS=expected, _base=lambda: base),
        unreal=SimpleNamespace(SkeletalMeshComponent=Template,
            SubobjectDataBlueprintFunctionLibrary=SimpleNamespace(get_variable_name=lambda data: data)))


def test_template_handles_accept_same_object_reported_twice():
    rows = [('Body', Template('/BP:Body')), ('Body', Template('/BP:Body')),
            ('Eyes', Template('/BP:Eyes')), ('Eyes', Template('/BP:Eyes'))]
    ns = template_namespace(rows)
    subsystem = SimpleNamespace(k2_gather_subobject_data_for_blueprint=lambda bp: range(len(rows)))
    assert ns['unique_template_handles'](None, subsystem) == {'Body': 0, 'Eyes': 2}


def test_template_handles_reject_same_name_distinct_objects():
    rows = [('Body', Template('/BP:Body')), ('Body', Template('/Other:Body')), ('Eyes', Template('/BP:Eyes'))]
    ns = template_namespace(rows)
    subsystem = SimpleNamespace(k2_gather_subobject_data_for_blueprint=lambda bp: range(len(rows)))
    with pytest.raises(RuntimeError, match='distinct objects'):
        ns['unique_template_handles'](None, subsystem)


def test_template_handles_reject_missing_slots_despite_duplicates():
    rows = [('Body', Template('/BP:Body')), ('Body', Template('/BP:Body'))]
    ns = template_namespace(rows)
    subsystem = SimpleNamespace(k2_gather_subobject_data_for_blueprint=lambda bp: range(len(rows)))
    with pytest.raises(RuntimeError, match='exactly 38'):
        ns['unique_template_handles'](None, subsystem)


def test_interrupted_clone_requires_explicit_recovery_receipt(tmp_path):
    ns = functions('authorize_interrupted_clone', ROOT=tmp_path)
    with pytest.raises(RuntimeError, match='no inspected recovery authorization'):
        ns['authorize_interrupted_clone'](None, None, 'target', 'source', 'hash', 'female', None)


def test_cloned_metadata_is_written_explicitly():
    tags = {}
    ns = functions('stamp_clone_metadata',
        fixed=SimpleNamespace(OWNER_TAG='owner', COPY_ROUTING_TAG='routing', COMPONENTS=('Body', 'Eyes'),
                              COPY_ROUTING_VERSION='actor_slot_tags_v1', digest=lambda values: 'component-hash'),
        unreal=SimpleNamespace(EditorAssetLibrary=SimpleNamespace(
            set_metadata_tag=lambda bp, name, value: tags.update({name: value}))))
    ns['stamp_clone_metadata'](None, {'sources': {'standard_candidate': {'sha256': 'selected-hash'}}})
    assert tags == {'owner': 'component-hash', 'routing': 'actor_slot_tags_v1', 'CompleteSourceSHA256': 'selected-hash'}


def test_recovery_metadata_keeps_empty_tags_and_in_progress_exact():
    tags = {'state': 'in_progress'}
    ns = functions('recovery_metadata',
        fixed=SimpleNamespace(OWNER_TAG='owner', COPY_ROUTING_TAG='routing', BUILD_STATE_TAG='state'),
        unreal=SimpleNamespace(EditorAssetLibrary=SimpleNamespace(get_metadata_tag=lambda bp, name: tags.get(name))))
    assert ns['recovery_metadata'](None) == {'owner': '', 'routing': '', 'state': 'in_progress',
        'CFD40ModularRegistry': '', 'CompleteSourceSHA256': ''}
