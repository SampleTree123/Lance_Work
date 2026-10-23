"""Offline contract and mutation-order tests; no Unreal import or application I/O."""
import json
import ast
import runpy
from pathlib import Path
import sys
from types import SimpleNamespace
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_complete_character_fixed_slot_runtime_v1 as runtime


def asset(name, slot, mesh_count=1):
    root = '/Game/DataMake/CharacterFactory/Wardrobe/Test/' + name
    return {'asset_id': name, 'slot': slot, 'ue_case_root': root,
            'ue_mesh_paths': [root + f'/Meshes/M{i}.M{i}' for i in range(mesh_count)]}


@pytest.fixture
def inputs(tmp_path):
    pieces = [asset('shirt', 'shirts'), asset('pants', 'pants'), asset('skirt', 'skirts'),
              asset('coat', 'coats'), asset('a_belt', 'family_accessory'), asset('z_necklace', 'family_accessory')]
    family = {'family_id': 'female.layered', 'sex': 'female', 'assets': pieces,
              'assembly_mode': 'slot_groups', 'hair_interface': {'allow_all': True, 'deny_all': False},
              'assembly': {'groups': [
                  {'group_id': 'pants', 'required_slots': ['shirts', 'pants'], 'optional_slots': ['coats'],
                   'slot_pools': {'shirts': ['shirt'], 'pants': ['pants'], 'coats': ['coat']},
                   'required_assets': [], 'optional_assets': ['a_belt', 'z_necklace']},
                  {'group_id': 'skirt', 'required_slots': ['shirts', 'skirts'], 'optional_slots': [],
                   'slot_pools': {'shirts': ['shirt'], 'skirts': ['skirt']}, 'required_assets': [], 'optional_assets': []}]}}
    hair = {'hair_id': 'hair_both', 'sex': 'both', 'reviewed_sexes': ['female'],
            'meshes': [{'path': '/Game/Test/H.H'}],
            'fit_variants': {sex: {'skeleton_path': f'/Game/Test/{sex}S.{sex}S',
                                  'meshes': [{'path': f'/Game/Test/{sex}H.{sex}H'}]} for sex in runtime.SEXES}}
    registry = {'schema_version': 4, 'families': [family], 'hair_assets': [hair],
                'shared_shoe_assets': [{'asset_id': 'heels', 'sex': 'female',
                                       'ue_asset_paths': ['/Game/Test/Heels.Heels']}]}
    registry_path = tmp_path / 'registry.json'
    registry_path.write_text(json.dumps(registry), encoding='utf-8')
    cases = [{'sex': sex, 'character_id': sex, 'skeleton': f'/Game/Test/{sex}S.{sex}S',
              'standard_candidate_ready': True,
              'meshes': [{'role': role, 'path': f'/Game/Test/{sex}_{role}.{sex}_{role}'}
                         for role in runtime.BASE_ROLES]} for sex in runtime.SEXES]
    standard = tmp_path / 'standard.json'
    standard.write_text(json.dumps({'cases': cases}), encoding='utf-8')
    return registry, registry_path, standard


def choice(*extras, group='pants'):
    return {'family_id': 'female.layered', 'group_id': group,
            'family_asset_ids': ['shirt', 'skirt' if group == 'skirt' else 'pants', *extras]}


def plan_for(inputs, female):
    return runtime.make_plan(inputs[1], {'female': female, 'male': {}}, inputs[2])


def test_accessory_owner_does_not_shift_when_earlier_accessory_removed(inputs):
    both = plan_for(inputs, choice('a_belt', 'z_necklace'))
    one = plan_for(inputs, choice('z_necklace'))
    rows = lambda p: {r['owner_asset_id']: r['component_name']
                      for r in p['characters']['female']['assignments'] if r['kind'] == 'clothing'}
    assert rows(both)['z_necklace'] == rows(one)['z_necklace'] == 'BundlePart02'
    assert 'BundlePart01' in one['characters']['female']['unused_slots']
    reordered = choice('z_necklace', 'a_belt')
    reordered['family_asset_ids'].reverse()
    assert rows(plan_for(inputs, reordered)) == rows(both)


def test_layered_and_skirt_choices_preserve_formal_rules(inputs):
    layered = plan_for(inputs, choice('coat'))['characters']['female']
    used = {r['component_name'] for r in layered['assignments']}
    assert {'UpperInner', 'UpperOuter', 'Bottom'} <= used
    skirt = plan_for(inputs, choice(group='skirt'))['characters']['female']
    assert 'UpperOuter' in skirt['unused_slots']
    with pytest.raises(runtime.formal.RegistryError):
        plan_for(inputs, choice('skirt'))
    with pytest.raises(runtime.formal.RegistryError):
        runtime.make_plan(inputs[1], {'female': {}, 'male': choice()}, inputs[2])


def test_reviewed_hair_permissions_also_apply_to_naked_character(inputs):
    female = plan_for(inputs, {'hair_id': 'hair_both'})['characters']['female']
    assert next(r for r in female['assignments'] if r['kind'] == 'hair')['mesh_path'] == '/Game/Test/femaleH.femaleH'
    with pytest.raises(runtime.formal.RegistryError, match='not available'):
        runtime.make_plan(inputs[1], {'female': {}, 'male': {'hair_id': 'hair_both'}}, inputs[2])
    # A geometry fit for both sexes does not grant original usage permission.
    registry = inputs[0]
    registry['hair_assets'][0].update(sex='female', reviewed_sexes=['female'])
    inputs[1].write_text(json.dumps(registry), encoding='utf-8')
    with pytest.raises(runtime.formal.RegistryError):
        runtime.make_plan(inputs[1], {'female': {}, 'male': {'hair_id': 'hair_both'}}, inputs[2])


def test_outfit_deny_clears_whole_hair_and_keeps_request_reason(inputs):
    registry = inputs[0]
    registry['families'][0]['hair_interface'] = {'allow_all': False, 'deny_all': True}
    inputs[1].write_text(json.dumps(registry), encoding='utf-8')
    female = plan_for(inputs, {**choice(), 'hair_id': 'hair_both'})['characters']['female']
    assert female['resolved']['requested_hair_id'] == 'hair_both'
    assert female['resolved']['resolved_hair_id'] is None
    assert female['resolved']['hair_reason'] == 'deny_all'
    assert set(runtime.HAIRS) <= set(female['unused_slots'])


def test_locked_bundle_cannot_be_partially_selected_and_has_stable_parts(inputs):
    registry = inputs[0]
    pieces = [asset('part_b', 'full_body'), asset('part_a', 'full_body'), asset('shoe', 'shoes')]
    common_root = pieces[0]['ue_case_root']
    for row in pieces:
        row['ue_case_root'] = common_root
        row['ue_mesh_paths'] = [common_root + '/Meshes/' + row['asset_id'] + '.' + row['asset_id']]
    family = registry['families'][0]
    family.update(assembly_mode='locked_bundle', assets=pieces,
                  assembly={'bundle': {'bundle_id': 'whole', 'required_assets': [r['asset_id'] for r in pieces]}})
    inputs[1].write_text(json.dumps(registry), encoding='utf-8')
    selected = {'family_id': family['family_id'], 'group_id': 'whole'}
    rows = plan_for(inputs, selected)['characters']['female']['assignments']
    by_owner = {r.get('owner_asset_id'): r['component_name'] for r in rows if r['kind'] == 'clothing'}
    assert by_owner == {'part_a': 'FullBody', 'part_b': 'BundlePart01', 'shoe': 'Footwear'}
    with pytest.raises(runtime.formal.RegistryError, match='whole'):
        plan_for(inputs, {**selected, 'family_asset_ids': ['part_a']})


def test_no_implicit_pose_mask_or_capacity_expansion(inputs):
    with pytest.raises(ValueError, match='not implemented'):
        plan_for(inputs, {**choice(), 'occlusion': {'body_triangles': [1]}})
    registry = inputs[0]
    registry['families'][0]['assets'].extend(asset('extra' + str(i), 'family_accessory') for i in range(11))
    inputs[1].write_text(json.dumps(registry), encoding='utf-8')
    with pytest.raises(ValueError, match='capacity|exceeds'):
        plan_for(inputs, choice())


def test_exact_six_base_parts_and_sources_reread_fresh(inputs):
    first = plan_for(inputs, {})
    assert first['component_count'] == 38
    assert len(set(first['component_names'])) == 38
    assert len(first['characters']['female']['assignments']) == 6
    assert first['limitations']['human_review_R10'] == 'pending'
    assert first['limitations']['shoe_pose_and_ground_contact'] == 'not_corrected_by_slot_assembly'
    inputs[0]['note'] = 'changed source bytes'
    inputs[1].write_text(json.dumps(inputs[0]), encoding='utf-8')
    second = plan_for(inputs, {})
    assert first['sources']['registry']['sha256'] != second['sources']['registry']['sha256']
    assert first['plan_sha256'] != second['plan_sha256']
    source = json.loads(inputs[2].read_text())
    source['cases'][0]['meshes'].pop()
    inputs[2].write_text(json.dumps(source), encoding='utf-8')
    with pytest.raises(ValueError, match='six'):
        plan_for(inputs, {})


def test_prepared_source_or_plan_tampering_stops_before_unreal(inputs, monkeypatch):
    plan = plan_for(inputs, {})
    monkeypatch.setattr(runtime, '_ue', lambda: pytest.fail('No Unreal access before provenance validation'))
    altered = json.loads(json.dumps(plan))
    altered['characters']['female']['assignments'][0]['mesh_path'] = '/Game/Foreign/B.B'
    with pytest.raises(RuntimeError, match='Plan content changed'):
        runtime._verify_plan(altered)
    inputs[1].write_text(inputs[1].read_text() + '\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='Plan source changed'):
        runtime._verify_plan(plan)


PROPERTY_NOTIFY_NEVER = object()


class Actor:
    def __init__(self, sex):
        self.sex, self.tags, self.writes = sex, [runtime.OWNER_TAG, 'keep_tag'], []
    def get_editor_property(self, name):
        assert name == 'tags'
        return self.tags
    def set_editor_property(self, name, value, **kwargs):
        assert name == 'tags' and kwargs == {'notify_mode': PROPERTY_NOTIFY_NEVER}
        self.tags = list(value)
        self.writes.append(list(value))
    def get_actor_label(self): return runtime.actor_label(self.sex)
    def get_class(self): return None


class Component:
    """Small stateful test double for apply/rollback, not a fake Unreal success."""
    def __init__(self, name):
        self.name, self.mesh = name, 'original_' + name
        self.props = {'override_materials': ['stale_override'], 'leader_pose_component': None,
                      'anim_class': 'old_abp', 'component_tags': [], 'hidden_in_game': False,
                      'use_bounds_from_leader_pose_component': False}
        self.visible, self.tick, self.mode = True, True, 'OLD_MODE'
        self.mesh_changes, self.anim_changes = 0, 0
        self.instance_identity, self.rebuild_count = object(), 0
        self.editor_property_writes, self.native_material_writes = [], []
        self.material_render_updates = 0
    def modify(self): pass
    def get_name(self): return self.name
    def get_editor_property(self, name): return self.props[name]
    def set_editor_property(self, name, value, **kwargs):
        assert set(kwargs) <= {'notify_mode'}
        changed = self.props.get(name) != value
        self.editor_property_writes.append((name, value, kwargs.get('notify_mode')))
        self.props[name] = list(value) if isinstance(value, list) else value
        # The real isolated BP probe confirmed this rule: changed default
        # notifications rebuild an SCS instance; same-value writes do not.
        if changed and kwargs.get('notify_mode') is not PROPERTY_NOTIFY_NEVER:
            self.rebuild_count += 1
            self.instance_identity = object()
    def set_material(self, index, value):
        assert index >= 0
        materials = self.props['override_materials']
        unchanged = index < len(materials) and materials[index] == value
        self.native_material_writes.append((index, value))
        if unchanged:
            return
        materials.extend([None] * max(0, index + 1 - len(materials)))
        materials[index] = value
        self.material_render_updates += 1
    def get_skeletal_mesh_asset(self): return self.mesh
    def set_skeletal_mesh_asset(self, value): self.mesh = value; self.mesh_changes += 1
    def set_leader_pose_component(self, value, *_): self.props['leader_pose_component'] = value
    def set_anim_instance_class(self, value): self.props['anim_class'] = value; self.anim_changes += 1
    def set_animation_mode(self, value): self.mode = value
    def get_animation_mode(self): return self.mode
    def set_visibility(self, value, *_): self.visible = value
    def is_visible(self): return self.visible
    def set_hidden_in_game(self, value): self.props['hidden_in_game'] = value
    def set_component_tick_enabled(self, value): self.tick = value
    def is_component_tick_enabled(self): return self.tick
    def set_collision_enabled(self, value): pass
    def set_update_animation_in_editor(self, value): pass
    def add_tick_prerequisite_component(self, body): self.prerequisite = body
    def remove_tick_prerequisite_component(self, body): self.prerequisite = None
    def get_attach_parent(self): return self.parent


def fake_unreal(monkeypatch):
    monkeypatch.setattr(runtime, '_ue', lambda: SimpleNamespace(
        Name=str, AnimationMode=SimpleNamespace(ANIMATION_BLUEPRINT='ABP'),
        PropertyAccessChangeNotifyMode=SimpleNamespace(NEVER=PROPERTY_NOTIFY_NEVER),
        CollisionEnabled=SimpleNamespace(NO_COLLISION='NONE')))


def test_component_probe_model_distinguishes_changed_default_and_never_notification():
    component = Component('Footwear')
    original = component.instance_identity
    component.set_editor_property('component_tags', [])
    assert component.instance_identity is original and component.rebuild_count == 0
    component.set_editor_property('component_tags', ['changed'])
    assert component.instance_identity is not original and component.rebuild_count == 1
    after_default = component.instance_identity
    component.set_editor_property('component_tags', [], notify_mode=PROPERTY_NOTIFY_NEVER)
    assert component.instance_identity is after_default and component.rebuild_count == 1


@pytest.mark.parametrize('name,follow', [('Body', None), ('Footwear', 'leader_pose'), ('HairPart01', 'copy_pose')])
def test_apply_and_restore_never_reconstruct_any_instance_path(monkeypatch, name, follow):
    fake_unreal(monkeypatch)
    body = Component('Body')
    component = body if name == 'Body' else Component(name)
    component.props['override_materials'] = ['old_material', None, None]
    component.props['component_tags'] = ['retained_tag']
    original_identity = component.instance_identity
    saved = runtime._snapshot(component)
    row = {'mesh': component.mesh if component == body else 'new_mesh',
           'compatibility': {'follow_mode': follow},
           'copy_pose_blueprint': SimpleNamespace(generated_class=lambda: 'new_copy_abp')}
    runtime._set_component(component, row, body)
    assert component.props['override_materials'] == []
    assert component.instance_identity is original_identity and component.rebuild_count == 0
    if component != body:
        assert component.mesh == 'new_mesh'
        assert component.props['use_bounds_from_leader_pose_component'] is (follow == 'leader_pose')
        runtime._set_component(component, None, body)
        assert component.mesh is None and not component.visible
    runtime._restore(component, saved, body)
    assert component.instance_identity is original_identity and component.rebuild_count == 0
    assert runtime._snapshot(component) == saved
    assert component.props['override_materials'] == ['old_material', None, None]
    assert component.material_render_updates >= 2  # Native clear + native restore.
    assert all(mode is PROPERTY_NOTIFY_NEVER for _, _, mode in component.editor_property_writes)


@pytest.mark.parametrize('before,after', [
    (['old', None, None], []),
    (['old', 'tail', None], ['new', None, None]),
    ([], [None, 'restored', None, None]),
    ([None, None], []),
    ([], [None, None]),
])
def test_override_materials_use_native_updates_and_preserve_exact_sparse_shape(monkeypatch, before, after):
    fake_unreal(monkeypatch)
    component = Component('Footwear')
    component.props['override_materials'] = list(before)
    original_identity = component.instance_identity
    desired = list(after)
    runtime._set_override_materials(component, desired)
    assert component.props['override_materials'] == after
    assert desired == after  # Caller-owned snapshot/list must remain intact.
    assert component.instance_identity is original_identity and component.rebuild_count == 0
    for index, value in enumerate(before):
        wanted = after[index] if index < len(after) else None
        if value is not None and value != wanted:
            # Native replacement invokes the removal/update path too; an
            # unnecessary intermediate None is not part of the contract.
            assert (index, wanted) in component.native_material_writes
    for index, value in enumerate(after):
        if value is not None:
            assert (index, value) in component.native_material_writes
    if any(value is not None for value in before + after):
        assert component.material_render_updates > 0
    assert all(mode is PROPERTY_NOTIFY_NEVER for _, _, mode in component.editor_property_writes)


def test_switch_clears_unused_mesh_material_and_copy_pose_state(monkeypatch):
    fake_unreal(monkeypatch)
    body, component = Component('Body'), Component('HairPart01')
    copy_row = {'mesh': 'braid', 'compatibility': {'follow_mode': 'copy_pose'},
                'copy_pose_blueprint': SimpleNamespace(generated_class=lambda: 'braid_abp')}
    runtime._set_component(component, copy_row, body)
    assert component.props['leader_pose_component'] is None
    assert component.props['anim_class'] == 'braid_abp'
    assert runtime.COPY_TAG in component.props['component_tags']
    runtime._set_component(component, None, body)
    assert component.mesh is None and not component.visible and not component.tick
    assert component.props['override_materials'] == []
    assert component.props['anim_class'] is None and runtime.COPY_TAG not in component.props['component_tags']
    runtime._set_component(component, {'mesh': 'plain', 'compatibility': {'follow_mode': 'leader_pose'}}, body)
    assert component.props['leader_pose_component'] == body
    assert component.props['anim_class'] is None and component.visible


def test_body_animation_survives_apply_and_rollback(monkeypatch):
    fake_unreal(monkeypatch)
    body = Component('Body')
    saved = runtime._snapshot(body)
    runtime._set_component(body, {'mesh': body.mesh}, body)
    runtime._restore(body, saved, body)
    assert body.mesh_changes == body.anim_changes == 0
    assert body.props['anim_class'] == 'old_abp'
    assert body.props['override_materials'] == ['stale_override']


def test_pair_apply_failure_restores_both_characters(monkeypatch, inputs):
    fake_unreal(monkeypatch)
    plan = plan_for(inputs, {})
    actors, components, prepared = {}, {}, {}
    for sex in runtime.SEXES:
        actors[sex] = Actor(sex)
        components[sex] = {name: Component(name) for name in runtime.COMPONENTS}
        body = components[sex]['Body']
        for c in components[sex].values(): c.parent = body
        prepared[sex] = {'body_mesh': body.mesh, 'assignments': [
            {'component_name': name, 'mesh': components[sex][name].mesh,
             'compatibility': {'follow_mode': 'leader_pose'}} for name in runtime.BASES]}
    monkeypatch.setattr(runtime, '_assert_level', lambda: None)
    monkeypatch.setattr(runtime, '_verify_plan', lambda p: None)
    monkeypatch.setattr(runtime, '_owned_actor', lambda sex: actors[sex])
    monkeypatch.setattr(runtime, 'actor_components', lambda actor: components[actor.sex])
    monkeypatch.setattr(runtime, 'readback', lambda *args: {'success': False, 'errors': ['injected readback failure']})
    with pytest.raises(RuntimeError, match=r'rollback_errors=\[\]'):
        runtime.apply_prepared(plan, prepared)
    for cs in components.values():
        for name, c in cs.items():
            assert c.mesh == 'original_' + name
            assert c.props['override_materials'] == ['stale_override']
            assert c.props['anim_class'] == 'old_abp'
        assert cs['Body'].anim_changes == 0


def rollback_pair(monkeypatch, inputs):
    """Expose a live component lookup whose objects may be replaced by SCS."""
    fake_unreal(monkeypatch)
    actors, live, prepared = {}, {}, {}
    for sex in runtime.SEXES:
        actors[sex] = Actor(sex)
        live[sex] = {name: Component(name) for name in runtime.COMPONENTS}
        body = live[sex]['Body']
        for name, component in live[sex].items():
            component.parent = body
            if name != 'Body':
                component.props['leader_pose_component'] = body
        prepared[sex] = {'body_mesh': body.mesh, 'assignments': [
            {'component_name': name, 'mesh': live[sex][name].mesh,
             'compatibility': {'follow_mode': 'leader_pose'}} for name in runtime.BASES]}
    monkeypatch.setattr(runtime, '_assert_level', lambda: None)
    monkeypatch.setattr(runtime, '_verify_plan', lambda plan: None)
    monkeypatch.setattr(runtime, '_owned_actor', lambda sex: actors[sex])
    monkeypatch.setattr(runtime, 'actor_components', lambda actor: live[actor.sex])
    return plan_for(inputs, {}), live, prepared


def test_reconstruction_rejected_and_rollback_targets_fresh_components_and_body(monkeypatch, inputs):
    plan, live, prepared = rollback_pair(monkeypatch, inputs)
    original = live['female']
    saved = {name: runtime._snapshot(component) for name, component in original.items()}
    apply_one = runtime._set_component
    def replace_after_apply(component, row, body):
        apply_one(component, row, body)
        if component is original[runtime.COMPONENTS[-1]]:
            replacement = {name: Component(name) for name in runtime.COMPONENTS}
            new_body = replacement['Body']
            for name, fresh in replacement.items():
                fresh.parent = new_body
                if name != 'Body':
                    fresh.mesh = None
            live['female'] = replacement
    monkeypatch.setattr(runtime, '_set_component', replace_after_apply)
    monkeypatch.setattr(runtime, 'readback', lambda *args: pytest.fail('Identity loss must be rejected before normal readback'))
    with pytest.raises(RuntimeError, match=r'reconstructed during switch: female/.*rollback_errors=\[\]'):
        runtime.apply_prepared(plan, prepared)
    assert live['female']['Body'] is not original['Body']
    assert original['Footwear'].mesh is None  # Stale instances were not "restored".
    for name, component in live['female'].items():
        expected = dict(saved[name])
        if expected['leader'] is original['Body']:
            expected['leader'] = live['female']['Body']
        assert runtime._snapshot(component) == expected
        assert component.rebuild_count == 0


def test_silent_rollback_failure_is_reported_by_fresh_state_verification(monkeypatch, inputs):
    plan, live, prepared = rollback_pair(monkeypatch, inputs)
    restore_one = runtime._restore
    def silent_restore_failure(component, old, body):
        restore_one(component, old, body)
        if component is live['female']['Footwear']:
            component.mesh = 'wrong_mesh_after_restore'  # No exception from setter.
    monkeypatch.setattr(runtime, '_restore', silent_restore_failure)
    monkeypatch.setattr(runtime, 'readback', lambda *args: {'success': False, 'errors': ['injected failure']})
    with pytest.raises(RuntimeError, match='female/Footwear: restored state or component identity differs') as error:
        runtime.apply_prepared(plan, prepared)
    assert 'rollback_errors=[]' not in str(error.value)
    assert live['male']['Footwear'].mesh == 'original_Footwear'


def test_actor_slot_tags_apply_clear_and_exact_failure_rollback(monkeypatch, inputs):
    plan, live, prepared = rollback_pair(monkeypatch, inputs)
    actors = {sex: runtime._owned_actor(sex) for sex in runtime.SEXES}
    actors['female'].tags += [runtime.ACTOR_COPY_PREFIX + 'HairPart17']
    baseline = {sex: list(a.tags) for sex, a in actors.items()}
    copy_row = {'component_name': 'HairPart01', 'mesh': 'braid',
                'compatibility': {'follow_mode': 'copy_pose'},
                'copy_pose_blueprint': SimpleNamespace(generated_class=lambda: 'abp')}
    prepared['female']['assignments'].append(copy_row)
    def rejected(*_):
        assert actors['female'].tags == [runtime.OWNER_TAG, 'keep_tag', runtime.ACTOR_COPY_PREFIX + 'HairPart01']
        assert runtime.COPY_TAG in live['female']['HairPart01'].props['component_tags']
        return {'success': False, 'errors': ['later transaction failed']}
    monkeypatch.setattr(runtime, 'readback', rejected)
    with pytest.raises(RuntimeError, match=r'rollback_errors=\[\]'):
        runtime.apply_prepared(plan, prepared)
    assert {sex: a.tags for sex, a in actors.items()} == baseline
    monkeypatch.setattr(runtime, 'readback', lambda *_: {'success': True})
    runtime.apply_prepared(plan, prepared)
    assert actors['female'].tags[-1] == runtime.ACTOR_COPY_PREFIX + 'HairPart01'
    prepared['female']['assignments'].remove(copy_row)
    runtime.apply_prepared(plan, prepared)
    assert actors['female'].tags == [runtime.OWNER_TAG, 'keep_tag']


def test_readback_rejects_missing_or_stale_actor_tag_even_with_correct_component_copy_state(monkeypatch, inputs):
    plan, live, prepared = rollback_pair(monkeypatch, inputs)
    actors = {sex: runtime._owned_actor(sex) for sex in runtime.SEXES}
    monkeypatch.setattr(runtime, 'object_path', lambda obj: obj if isinstance(obj, str) else None)
    for sex in runtime.SEXES:
        for row in plan['characters'][sex]['assignments']:
            row['mesh_path'] = live[sex][row['component_name']].mesh
    copy_row = {'component_name': 'HairPart01', 'mesh': 'braid',
                'compatibility': {'follow_mode': 'copy_pose'},
                'copy_pose_blueprint': SimpleNamespace(generated_class=lambda: 'abp')}
    prepared['female']['assignments'].append(copy_row)
    plan['characters']['female']['assignments'].append({'component_name': 'HairPart01', 'mesh_path': 'braid'})
    assert runtime.apply_prepared(plan, prepared)['success']
    actors['female'].tags.remove(runtime.ACTOR_COPY_PREFIX + 'HairPart01')
    report = runtime.readback(plan, prepared)
    assert 'female/actor_copy_tags' in report['errors']
    assert 'female/HairPart01/copy_pose_binding' in report['errors']
    actors['female'].tags += [runtime.ACTOR_COPY_PREFIX + 'HairPart01', runtime.ACTOR_COPY_PREFIX + 'HairPart17']
    report = runtime.readback(plan, prepared)
    assert 'female/HairPart17/stale_unused_animation' in report['errors']


def test_ui_transaction_restores_actor_tags_after_later_animation_failure(monkeypatch):
    fake_unreal(monkeypatch)
    source = Path(runtime.__file__).with_name('ue_complete_character_slot_review_v1.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'restore_scene')
    context = {'fixed': runtime, 'unreal': SimpleNamespace(CameraComponent=object)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), context)
    actor = Actor('female')
    before = list(actor.tags) + [runtime.ACTOR_COPY_PREFIX + 'HairPart17']
    runtime._set_actor_copy_tags(actor, [runtime.ACTOR_COPY_PREFIX + 'HairPart01'])
    actor.set_actor_rotation = lambda *args: None
    body = SimpleNamespace(override_animation_data=lambda *args: None, get_anim_instance=lambda: None,
                           set_animation_mode=lambda *args: None)
    camera = SimpleNamespace(set_actor_location=lambda *args: None, set_actor_rotation=lambda *args: None,
                             get_component_by_class=lambda *args: SimpleNamespace(set_editor_property=lambda *args: None))
    snapshot = {'characters': {'female': {'actor': actor, 'actor_tags': before, 'rotation': 0,
                'body': body, 'components': [], 'animation': None, 'looping': False, 'playing': False,
                'position': 0., 'rate': 1., 'animation_mode': 'old'}}, 'camera': camera,
                'camera_location': 0, 'camera_rotation': 0, 'camera_fov': 45}
    assert context['restore_scene'](snapshot) == []
    assert actor.tags == before


@pytest.mark.skipif(not runtime.formal.REVIEWED_POOL_REGISTRY.exists(), reason='Local published evidence unavailable')
def test_real_retained_coverage_resolves_without_restoring_removed_items():
    registry = runtime.formal.read_registry(runtime.formal.current_registry_path())
    # Published mapping explicitly removes the cyberpunk mask from its remaining
    # locked bundle; blindly replaying the unmodified old choice must fail.
    receipt = runtime.read_json(runtime.formal.current_registry_publication_path())
    mapping = runtime.read_json(receipt['mapping_report'])
    retained, rejected, meshes = {}, {}, set()
    for sex in runtime.SEXES:
        retained[sex] = rejected[sex] = 0
        for look in (r for r in mapping['outfits'] if r['character_sex'] == sex):
            if look['status'] == 'excluded':
                rejected[sex] += 1
                continue
            resolved = runtime.formal.resolve_selection(registry, **look['request'])
            rows = runtime.stable_outfit_assignments(registry, resolved)
            assert {r['mesh_path'] for r in rows} == {r['mesh_path'] for r in resolved['assignments']}
            assert len({r['component_name'] for r in rows}) == len(rows)
            assert all(r['component_name'] in runtime.SLOTS for r in rows)
            meshes.update(r['mesh_path'] for r in rows)
            retained[sex] += 1
    assert retained == {'female': 79, 'male': 73}
    assert rejected == {'female': 16, 'male': 5}
    assert all('cybmask' not in mesh.lower() for mesh in meshes)
    assert sum(runtime.formal.hair_available_to(h, 'male') for h in registry['hair_assets']) == 13
    assert sum(runtime.formal.hair_available_to(h, 'female') for h in registry['hair_assets']) == 20


class Pin:
    def __init__(self, node, name):
        self.node, self.name, self.value, self.inputs, self.outputs = node, name, None, [], []
    def get_pin_name(self): return self.name
    def set_pin_value(self, value): self.value = value; return True
    def get_pin_value(self): return self.value or ''
    def get_owning_node(self): return self.node
    def list_connected_pins(self): return self.inputs + self.outputs
    def is_same_native_pin(self, other): return self is other
    def break_pin_links(self):
        for p in self.inputs: p.outputs.remove(self)
        for p in self.outputs: p.inputs.remove(self)
        self.inputs, self.outputs = [], []
        return True


class Node:
    def __init__(self, label, pins):
        self.label, self.pins = label, {}
        for name in pins: self.pins[name] = Pin(self, name)
    def list_all_pins(self): return list(self.pins.values())
    def set_node_pos(self, position): self.position = position
    def get_node_pos(self): return getattr(self, 'position', (0, 0))
    def get_editor_property(self, name):
        assert name == 'function_reference'
        return SimpleNamespace(get_editor_property=lambda prop: self.label.rsplit(':', 1)[-1])


class Entry(Node): pass
class Getter(Node): pass
class Branch(Node): pass
class Call(Node): pass
class Sequence(Node): pass


@pytest.fixture
def graph_tools(monkeypatch, tmp_path):
    graph = SimpleNamespace(nodes=[Entry('entry', ['then'])])
    calls = {'getters': [], 'functions': [], 'branches': 0, 'palette': 0, 'add_pin': 0}
    class Editor:
        def remove_nodes(self, nodes):
            graph.nodes[:] = [n for n in graph.nodes if n not in nodes]
        def add_get_member_variable_node(self, name):
            calls['getters'].append(name)
            node = Getter(name, [name]); graph.nodes.append(node); return node
        def add_branch_node(self):
            calls['branches'] += 1
            node = Branch('branch', ['execute', 'then', 'else', 'Condition'])
            graph.nodes.append(node); return node
        def add_call_function_node(self, path):
            calls['functions'].append(path)
            assert path in runtime.DIRECT_FUNCTIONS.values()
            pins = (['self', 'Tag', 'ReturnValue'] if path == runtime.DIRECT_FUNCTIONS['has_tag'] else
                    ['execute', 'then', 'self', 'NewLeaderBoneComponent', 'bForceUpdate', 'bInFollowerShouldTickPose'])
            if path == runtime.DIRECT_FUNCTIONS['has_tag'] and calls.get('new_check_impure'):
                pins = ['execute', 'then'] + pins
            node = Call(path, pins); graph.nodes.append(node); return node
        def add_node_pin(self, seq):
            calls['add_pin'] += 1
            name = 'then_' + str(len(seq.pins) - 1)
            seq.pins[name] = Pin(seq, name)
            return True
    editor = Editor()
    fake = SimpleNamespace(K2Node_FunctionEntry=Entry, K2Node_VariableGet=Getter,
                           K2Node_IfThenElse=Branch, K2Node_CallFunction=Call,
                           K2Node_ExecutionSequence=Sequence, Name=str, IntPoint=lambda x,y:(x,y),
                           BlueprintEditorLibrary=SimpleNamespace(find_graph=lambda bp,name: graph),
                           BlueprintGraphEditor=SimpleNamespace(get_graph_editor=lambda g:editor))
    monkeypatch.setattr(runtime, '_ue', lambda: fake)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, '_export_call_reference', lambda node, directory: {'member': node.label.rsplit(':', 1)[-1]})
    def connect(a,b): a.outputs.append(b); b.inputs.append(a)
    helpers = SimpleNamespace(find_pin=lambda n,p:n.pins[p], only_pin=lambda n:next(iter(n.pins.values())), connect=connect)
    monkeypatch.setattr(runtime, '_base', lambda: helpers)
    def palette(*args):
        calls['palette'] += 1
        assert args[3] == 'K2Node_ExecutionSequence'
        node = Sequence('sequence', ['execute', 'then_0', 'then_1'])
        graph.nodes.append(node)
        return node
    monkeypatch.setattr(runtime, '_palette_node', palette)
    for name in ('editor_toolset', 'editor_toolset.toolsets', 'editor_toolset.toolsets.blueprint'):
        module = ModuleType(name)
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules['editor_toolset.toolsets.blueprint'].BlueprintTools = SimpleNamespace(find_nodes=lambda g:list(g.nodes))
    return graph, calls


def test_direct_graph_preserves_all_37_copytag_branches_with_one_palette_lookup(graph_tools):
    graph, calls = graph_tools
    result = runtime.build_construction_graph(object())
    assert calls['palette'] == 1 and calls['add_pin'] == 35
    assert calls['getters'] == list(runtime.COMPONENTS)
    assert calls['branches'] == 37
    assert calls['functions'].count(runtime.DIRECT_FUNCTIONS['has_tag']) == 37
    assert calls['functions'].count(runtime.DIRECT_FUNCTIONS['leader']) == 74
    assert result['node_count'] == 188
    seq = next(n for n in graph.nodes if isinstance(n, Sequence))
    for index, name in enumerate(runtime.COMPONENTS[1:]):
        branch = seq.pins[f'then_{index}'].outputs[0].node
        tag = branch.pins['Condition'].inputs[0].node
        assert tag.pins['Tag'].value == runtime.ACTOR_COPY_PREFIX + name
        assert not tag.pins['self'].inputs
        yes = branch.pins['then'].outputs[0].node
        no = branch.pins['else'].outputs[0].node
        assert not yes.pins['NewLeaderBoneComponent'].inputs  # Explicitly None.
        assert no.pins['NewLeaderBoneComponent'].inputs[0].node.label == 'Body'
        for call in (yes, no):
            assert call.pins['self'].inputs[0].node.label == name
            assert call.pins['bForceUpdate'].value == 'true'
            assert call.pins['bInFollowerShouldTickPose'].value == 'false'


@pytest.mark.parametrize('old_impure,new_impure', [(False, False), (False, True), (True, False), (True, True)])
@pytest.mark.parametrize('legacy_sequences', [False, True])
def test_patch_only_tag_checks_preserves_components_and_old_sequence_topology(graph_tools, old_impure, new_impure, legacy_sequences):
    graph, calls = graph_tools
    bp = object()
    runtime.build_construction_graph(bp)
    base = runtime._base()
    actor_checks = [n for n in graph.nodes if isinstance(n, Call) and n.label == runtime.DIRECT_FUNCTIONS['has_tag']]
    branches = []
    for node in actor_checks:
        name = node.pins['Tag'].value[len(runtime.ACTOR_COPY_PREFIX):]
        getter = next(n for n in graph.nodes if isinstance(n, Getter) and n.label == name)
        node.label = '/Script/Engine.ActorComponent:ComponentHasTag'
        node.pins['Tag'].value = runtime.COPY_TAG
        base.connect(getter.pins[name], node.pins['self'])
        branch = node.pins['ReturnValue'].outputs[0].node
        branches.append(branch)
    if legacy_sequences:
        # Original shipped BP chains 37 Sequence nodes instead of one fanout.
        seq = next(n for n in graph.nodes if isinstance(n, Sequence))
        for pin in seq.list_all_pins(): pin.break_pin_links()
        graph.nodes.remove(seq)
        previous = graph.nodes[0].pins['then']
        for branch in branches:
            sequence = Sequence('legacy_sequence', ['execute', 'then_0', 'then_1'])
            graph.nodes.append(sequence)
            base.connect(previous, sequence.pins['execute'])
            base.connect(sequence.pins['then_0'], branch.pins['execute'])
            previous = sequence.pins['then_1']
    if old_impure:
        for node, branch in zip(actor_checks, branches):
            upstream = branch.pins['execute'].inputs[0]
            branch.pins['execute'].break_pin_links()
            node.pins['execute'], node.pins['then'] = Pin(node, 'execute'), Pin(node, 'then')
            base.connect(upstream, node.pins['execute'])
            base.connect(node.pins['then'], branch.pins['execute'])
    untouched = [n for n in graph.nodes if n not in actor_checks]
    noncheck_links = [(p, list(p.list_connected_pins())) for n in untouched for p in n.list_all_pins()
                      if isinstance(n, Sequence) or isinstance(n, Getter)]
    calls['new_check_impure'] = new_impure
    before_count = len(graph.nodes)
    result = runtime.patch_copy_routing_graph(bp)
    assert result['replaced_check_count'] == 37 and len(graph.nodes) == before_count
    assert all(node in graph.nodes for node in untouched)
    assert all(node not in graph.nodes for node in actor_checks)
    assert sum(isinstance(n, Sequence) for n in graph.nodes) == (37 if legacy_sequences else 1)
    for pin, previous in noncheck_links:
        # Only links leading to the replaced checks are allowed to differ.
        preserved = [p for p in previous if p.node not in actor_checks]
        for p in preserved:
            if p.node not in branches: assert p in pin.list_connected_pins()
    assert runtime.inspect_copy_routing_graph(bp)['mode'] == runtime.COPY_ROUTING_VERSION
    assert runtime.patch_copy_routing_graph(bp)['replaced_check_count'] == 0


def test_mixed_or_missing_graph_rejected_before_node_mutation(graph_tools):
    graph, _ = graph_tools
    runtime.build_construction_graph(object())
    check = next(n for n in graph.nodes if isinstance(n, Call) and n.label == runtime.DIRECT_FUNCTIONS['has_tag'])
    check.pins['Tag'].value = runtime.ACTOR_COPY_PREFIX + 'Body'
    before = list(graph.nodes)
    with pytest.raises(RuntimeError, match='Unknown/duplicate'):
        runtime.patch_copy_routing_graph(object())
    assert graph.nodes == before


@pytest.mark.parametrize('role,member', [('tag', 'ComponentHasTag'), ('leader', 'SetLeaderPoseComponent')])
def test_real_public_export_identifies_member_without_private_property(role, member):
    folder = runtime.ROOT / 'tonight_20261006_v1/runtime'
    receipt_path = folder / 'public_graph_probe_20261005T234809_daa1c6d7.json'
    if not receipt_path.exists(): pytest.skip('Local real UE evidence unavailable')
    receipt = runtime.read_json(receipt_path)
    row = next(r for r in receipt['nodes'] if r['role'] == role)
    export = Path(row['export_path'])
    assert runtime.source_record(export)['sha256'] == row['export_sha256']
    text = export.read_text(encoding='utf-8-sig')
    assert runtime.parse_call_reference_export(text, row['node_path'])['member'] == member
    with pytest.raises(RuntimeError, match='identity/class'):
        runtime.parse_call_reference_export(text, row['node_path'] + '_other')
    with pytest.raises(RuntimeError, match='owner'):
        runtime.parse_call_reference_export(text.replace('/Script/Engine.ActorComponent', '/Script/Engine.Actor')
                                           if role == 'tag' else text.replace('/Script/Engine.SkinnedMeshComponent', '/Script/Engine.Actor'), row['node_path'])


def test_public_export_actor_self_context_only_allows_actor_has_tag():
    path = '/Game/Owned.BP:UserConstructionScript.Call_1'
    header = 'Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="Call_1" ExportPath="/Script/BlueprintGraph.K2Node_CallFunction\'' + path + '\'"\n'
    text = header + ' FunctionReference=(MemberName="ActorHasTag",bSelfContext=True)\nEnd Object\n'
    assert runtime.parse_call_reference_export(text, path) == {'member': 'ActorHasTag', 'member_parent': None, 'self_context': True}
    with pytest.raises(RuntimeError, match='owner'):
        runtime.parse_call_reference_export(text.replace('ActorHasTag', 'ComponentHasTag'), path)
    with pytest.raises(RuntimeError, match='exactly one'):
        runtime.parse_call_reference_export(text.replace('End Object', ' FunctionReference=(MemberName="ActorHasTag",bSelfContext=True)\nEnd Object'), path)


def test_completed_bp_inventory_keeps_actual_duplicate_handles_but_rejects_distinct_objects():
    folder = runtime.ROOT / 'tonight_20261006_v1/runtime'
    probe = folder / 'template_handle_probe_20261005T235509_6b503ab8.json'
    if not probe.exists(): pytest.skip('Local completed-BP handle evidence unavailable')
    snapshot = runpy.run_path(str(folder / 'patch_fixed_slot_actor_tag_graph_v1.py'), run_name='offline_only')['template_snapshot']
    refs = {}
    class Ref:
        def __init__(self, path): self.path = path
    def ref(path):
        if path is None: return None
        if path not in refs: refs[path] = Ref(path)
        return refs[path]
    class Obj(Ref):
        def __init__(self, row): super().__init__(row['path']); self.row = row
        def get_class(self): return ref(self.row['class'])
        def get_outer(self): return ref(self.row['outer'])
    class AC(Obj):
        def get_owner(self): return ref(self.row.get('owner'))
    class SC(AC):
        def get_attach_parent(self): return ref(self.row.get('attach_parent'))
    class SK(SC):
        def get_skeletal_mesh_asset(self): return ref(self.row.get('mesh'))
    source = runtime.read_json(probe)['blueprints']['female']
    objects, handles = {}, []
    for row in source['rows']:
        raw = row['raw']
        cls = SK if raw['is_skeletal_mesh_component'] else SC if row['flags']['is_component'] else Obj
        objects.setdefault(raw['path'], cls(raw))
    for row in source['rows']:
        parent = row['parent']
        handles.append({'object': objects[row['raw']['path']], 'flags': row['flags'], 'name': row['variable_name'],
                        'blueprint': ref(row['blueprint']), 'parent': None if parent is None else
                        {'object': objects[parent['raw']['path']], 'name': parent['variable_name']}})
    api = SimpleNamespace(get_data=lambda x: x, get_object=lambda x: x['object'],
                          get_variable_name=lambda x:x['name'], get_parent_handle=lambda x:x['parent'],
                          is_handle_valid=lambda x:x is not None, get_blueprint=lambda x:x['blueprint'])
    for flag in source['rows'][0]['flags']:
        setattr(api, flag, lambda data, key=flag:data['flags'][key])
    subsystem = SimpleNamespace(k2_gather_subobject_data_for_blueprint=lambda bp:handles)
    u = SimpleNamespace(SubobjectDataBlueprintFunctionLibrary=api, SubobjectDataSubsystem=object,
                        get_engine_subsystem=lambda _:subsystem, ActorComponent=AC, SceneComponent=SC, SkeletalMeshComponent=SK)
    fixed = SimpleNamespace(_ue=lambda:u, COMPONENTS=runtime.COMPONENTS,
                            object_path=lambda obj:obj.path if obj is not None else None)
    mesh_row = next(row['raw'] for row in source['rows'] if row['raw']['is_skeletal_mesh_component'])
    bp = SimpleNamespace(generated_class=lambda:ref(mesh_row['outer']))
    before = snapshot(fixed, bp)
    assert before['handle_count'] == 78 and before['unique_mesh_count'] == 38
    handles.reverse()
    assert snapshot(fixed, bp) == before  # Stable multiset, never discard repeats.
    name = 'BundlePart03'
    duplicate = [row for row in handles if row['name'] == name][1]
    duplicate['object'] = SK(duplicate['object'].row)
    with pytest.raises(RuntimeError, match='distinct object/data'):
        snapshot(fixed, bp)


def test_cancel_only_at_complete_follower_branch_boundary(graph_tools):
    graph, calls = graph_tools
    class Control:
        def tick(self, phase, sex=None, name=None, **kw):
            if phase == 'graph_component_complete' and kw['completed'] == 7:
                raise runtime.BuildCancelled('safe boundary')
    with pytest.raises(runtime.BuildCancelled):
        runtime.build_construction_graph(object(), Control(), 'female')
    assert calls['branches'] == 7
    assert calls['functions'].count(runtime.DIRECT_FUNCTIONS['leader']) == 14
    assert calls['getters'] == list(runtime.COMPONENTS[:8])


def test_progress_uses_loaded_hash_and_requires_matching_cancel_build_id(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    control = runtime.BuildProgress({'build_id':'review_test', 'progress_path':tmp_path/'progress.json',
                                     'cancel_path':tmp_path/'cancel.json'})
    control.cancel_path.write_text(json.dumps({'build_id':'other_attempt','cancel':True}))
    control.tick('template_component_complete', 'female', 'Body')
    assert json.loads(control.progress_path.read_text())['loaded_source_sha256'] == runtime.LOADED_SOURCE_SHA256
    control.cancel_path.write_text(json.dumps({'build_id':'review_test','cancel':True}))
    with pytest.raises(runtime.BuildCancelled, match='safe boundary'):
        control.tick('graph_component_complete', 'female', 'Eyes')
    control.tick('build_cancelled', check_cancel=False, status='cancelled')
    assert json.loads(control.progress_path.read_text())['status'] == 'cancelled'
    # A subsequent attempt is not cancelled by a stale previous-attempt marker.
    resumed = runtime.BuildProgress({'build_id':'resumed', 'progress_path':tmp_path/'resume.json',
                                     'cancel_path':control.cancel_path})
    resumed.tick('build_begin')
    with pytest.raises(ValueError, match='inside review'):
        runtime.BuildProgress({'progress_path': tmp_path.parent/'outside.json'})


def test_saved_legacy_female_reused_and_only_marked_incomplete_assets_resume(monkeypatch, inputs):
    plan = plan_for(inputs, {})
    class BP:
        def get_editor_property(self, name): return 'compiled'
    bp = BP()
    metadata = {runtime.OWNER_TAG:runtime.digest(list(runtime.COMPONENTS)),
                'CompleteSourceSHA256':plan['sources']['standard_candidate']['sha256']}
    monkeypatch.setattr(runtime, '_ue', lambda: SimpleNamespace(Blueprint=BP,
                       BlueprintStatus=SimpleNamespace(BS_UP_TO_DATE='compiled'),
                       EditorAssetLibrary=SimpleNamespace(get_metadata_tag=lambda _,key:metadata.get(key,''))))
    assert runtime._saved_build_state(bp, plan) == 'complete'
    for state in ('in_progress','cancelled','failed'):
        metadata[runtime.BUILD_STATE_TAG] = state
        assert runtime._saved_build_state(bp, plan) == 'resume'
    metadata[runtime.BUILD_STATE_TAG] = 'unknown'
    with pytest.raises(RuntimeError, match='Unknown incomplete'):
        runtime._saved_build_state(bp, plan)
    metadata.pop(runtime.OWNER_TAG)
    with pytest.raises(RuntimeError, match='unrecognized'):
        runtime._saved_build_state(bp, plan)


def test_sequence_palette_does_not_trial_spawn_unrelated_animation_functions(monkeypatch):
    created = []
    monkeypatch.setattr(runtime, '_ue', lambda: SimpleNamespace(K2Node_ExecutionSequence=Sequence))
    monkeypatch.setattr(runtime, '_base', lambda: None)
    def create(graph, type_id, pos):
        created.append(type_id)
        return Sequence('sequence', ['execute', 'then_0', 'then_1'])
    tools = SimpleNamespace(find_node_types=lambda g,q: ['Animation|PlaySequence', 'Animation|SequenceLength',
                                                        'Utilities|FlowControl|Sequence'], create_node=create)
    runtime._palette_node(tools, object(), ['Sequence', '序列'], 'K2Node_ExecutionSequence',
                          ['execute','then_0','then_1'], (0,0))
    assert created == ['Utilities|FlowControl|Sequence']
