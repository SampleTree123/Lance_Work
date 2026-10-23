import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load('cc_compile_character_refresh_v1')
RUNNER = load('cc_run_character_refresh_v1')
LAYER_UI = load('cc_skingen_controls_v1')


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    makeup, redness = tmp_path / 'makeup', tmp_path / 'redness'
    monkeypatch.setattr(COMPILER, 'MAKEUP_ROOT', makeup)
    monkeypatch.setattr(COMPILER, 'REDNESS_ROOT', redness)
    for group in ('Male', 'Trimmed'):
        (makeup / group).mkdir(parents=True)
        for name in ('A', 'B', 'C'):
            (makeup / group / (name + '.ccSkinGenPreset')).write_bytes((group + name).encode())
    redness.mkdir()
    (redness / 'Redness').mkdir()
    for name in ('Hemoglobin F', 'Hemoglobin M', 'Redness/Female', 'Redness/Male', 'Redness/Mature Female', 'Redness/Mature Male'):
        (redness / (name + '.ccSkinGenPreset')).write_bytes(name.encode())

    def asset(asset_id, slot, extension, sex='unknown'):
        path = tmp_path / (asset_id + extension)
        path.write_bytes(asset_id.encode())
        return dict(COMPILER.file_ref(path), asset_id=asset_id, slot=slot, asset_form='asset',
                    display_name=asset_id, sex_hint=sex)

    pools = {'skins': [asset('skin_f', 'skin', '.ccSkin', 'female'), asset('skin_m', 'skin', '.ccSkin', 'male')],
             'eyelashes': [asset('lash' + str(i), 'eyelashes', '.ccAvatarPreset') for i in range(9)],
             'eyes': [asset('eye' + str(i), 'eyes', '.ccEye') for i in range(12)]}
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps({'component_pools': pools}), encoding='utf-8')
    source, backup = tmp_path / 'source.ccProject', tmp_path / 'backup.ccProject'
    source.write_bytes(b'source')
    backup.write_bytes(b'backup')
    request = {'sex': 'female', 'character_id': 'PERSON_1', 'seed': 42,
        'redness_policy': 'experimental_optional',  # Explicit historical-path regression only.
        'skin_selection_reason': 'Reference visible skin has the selected color range',
        'skin_asset_id': 'skin_f', 'eyelash_asset_id': 'lash0', 'eye_asset_id': 'eye0',
        'source_project': COMPILER.file_ref(source), 'current_scene_backup': COMPILER.file_ref(backup),
        'redness_choice': 'hemoglobin', 'redness_opacity': 50}
    return request, registry


def test_compile_is_deterministic_explicit_and_never_complete(inputs):
    request, registry = inputs
    first = COMPILER.compile_request(request, registry)
    assert first == COMPILER.compile_request(request, registry)
    config = first['refresh_assembly']
    assert config['assets']['skin']['asset_id'] == 'skin_f'
    assert Path(config['assets']['makeup_eyebrow']['path']).parent.name == 'Trimmed'
    assert config['recipe_complete'] is False
    assert config['geometry']['allowances'] == []
    assert config['phases'] == ['skin', 'remove_legacy_brow_parts', 'eyes', 'makeup_eyebrow']
    assert 'eyelashes' not in config['phases'] and 'redness' not in config['phases']


def test_skin_is_required_and_cannot_be_silently_randomized(inputs):
    request, registry = inputs
    del request['skin_asset_id']
    with pytest.raises(KeyError):
        COMPILER.compile_request(request, registry)


def test_user_excluded_redness_is_not_a_component_or_pending_requirement(inputs):
    request, registry = inputs
    request.update(redness_policy='excluded_by_user', include_redness_layers=False)
    result = COMPILER.compile_request(request, registry)['refresh_assembly']
    assert result['redness_policy'] == 'excluded_by_user'
    assert not result['include_redness_layers'] and result['verify_layer_persistence']
    assert not any('redness' in item for item in result['pending_phases'] + result['pending_validation'])
    assert result['assets']['redness']['application_status'] == 'excluded_by_user_historical_reference_only'
    request.pop('redness_choice')
    request.pop('redness_opacity')
    assert 'redness' not in COMPILER.compile_request(request, registry)['refresh_assembly']['assets']
    request['include_redness_layers'] = True
    with pytest.raises(ValueError, match='User-excluded'):
        COMPILER.compile_request(request, registry)


def test_current_default_excludes_redness_and_closes_editor_with_real_evidence(inputs):
    request, registry = inputs
    for name in ('redness_policy', 'redness_choice', 'redness_opacity'):
        request.pop(name)
    config = COMPILER.compile_request(request, registry)['refresh_assembly']
    assert config['redness_policy'] == 'excluded_by_user' and config['finalize_editor_closed']
    assert config['verify_layer_persistence'] and config['capture_pixel_evidence']
    assert 'redness' not in config['assets']
    assert all('redness' not in name for name in config['pending_phases'] + config['pending_validation'])


def test_rejects_wrong_sex_skin_and_unapproved_opacity(inputs):
    request, registry = inputs
    request['skin_asset_id'] = 'skin_m'
    with pytest.raises(ValueError, match='sex mismatch'):
        COMPILER.compile_request(request, registry)
    request['skin_asset_id'] = 'skin_f'
    request['redness_opacity'] = 80
    with pytest.raises(ValueError, match='opacity50/100'):
        COMPILER.compile_request(request, registry)


def test_gate_checks_last_native_vertex_without_lash_allowance():
    before = {'working_subdivision_level': 0, 'local': [[0., 0., 0.] for _ in range(14164)]}
    after = {'working_subdivision_level': 0, 'local': [row[:] for row in before['local']]}
    after['local'][-1][0] = .00019
    assert RUNNER.all_vertex_gate(before, after)['passed']
    after['local'][-1][0] = .00021
    result = RUNNER.all_vertex_gate(before, after)
    assert not result['passed'] and result['failed_vertex_indices'] == [14163]
    assert result['allowances'] == []


def test_gate_rejects_widened_threshold_or_inactive_working_cage():
    snapshot = {'working_subdivision_level': 1, 'local': []}
    with pytest.raises(ValueError, match='SubD0'):
        RUNNER.all_vertex_gate(snapshot, snapshot)
    with pytest.raises(ValueError, match='Strict'):
        RUNNER.all_vertex_gate(snapshot, snapshot, threshold_mm=25)


@pytest.mark.parametrize('scene_ids,selected_after,success', [
    ([7], [7], True), ([7], [], False), ([7], [7, 8], False),
    ([8], [8], False), ([7, 8], [7], False), ([], [], False),
])
def test_preset_selection_requires_unique_identity_and_exact_readback(scene_ids, selected_after, success):
    item = lambda value: SimpleNamespace(GetID=lambda: value)
    state, calls = {'selected': [item(99)]}, []

    def select(avatar):
        calls.append(avatar.GetID())
        state['selected'] = [item(value) for value in selected_after]

    api = SimpleNamespace(RLPy=SimpleNamespace(RScene=SimpleNamespace(
        GetAvatars=lambda: [item(value) for value in scene_ids],
        GetSelectedObjects=lambda: state['selected'], SelectObject=select)))
    audit = {}
    if success:
        assert RUNNER.select_preset_avatar(api, '7', audit).GetID() == 7
        assert audit['selected_ids_before'] == ['99']
        assert audit['selected_ids_after'] == ['7'] and audit['verified']
    else:
        with pytest.raises(ValueError, match='Preset target'):
            RUNNER.select_preset_avatar(api, '7', audit)
    if scene_ids != [7]:
        assert not calls  # Identity failure must occur before any selection write.


@pytest.mark.parametrize('sex,choice', [(sex, choice) for sex in ('female', 'male')
    for choice in ('hemoglobin', 'redness', 'mature_redness')])
def test_redness_contract_binds_all_six_exact_sex_type_files(tmp_path, monkeypatch, sex, choice):
    monkeypatch.setattr(RUNNER, 'REDNESS_ROOT', str(tmp_path))
    relative = {'hemoglobin': 'Hemoglobin {}.ccSkinGenPreset'.format('M' if sex == 'male' else 'F'),
        'redness': 'Redness/{}.ccSkinGenPreset'.format(sex.title()),
        'mature_redness': 'Redness/Mature {}.ccSkinGenPreset'.format(sex.title())}[choice]
    names = ['Hemoglobin'] if choice == 'hemoglobin' else ['upper face', 'mid face', 'lower face']
    asset = {'path': str(tmp_path / relative), 'choice': choice, 'opacity': 100, 'requested_layers': names}
    assert RUNNER.redness_contract(asset, sex) == names
    asset['path'] = str(tmp_path / 'Wrong.ccSkinGenPreset')
    with pytest.raises(ValueError, match='exact requested'):
        RUNNER.redness_contract(asset, sex)


@pytest.mark.parametrize('move_eye_phase,verify_layers,include_redness,persistence_drift,expect_success', [
    (False, False, False, False, True), (True, False, False, False, False),
    (False, True, False, False, True), (False, True, False, True, False),
    (False, True, 'hemoglobin', False, True), (False, True, 'redness', False, True),
    (False, True, 'mature_redness', False, True),
    ('pixel_damage', False, False, False, False),
    ('pixel_damage_restore', False, False, False, True),
    ('auto_raise', False, False, False, True),
    ('auto_measure_drift', False, False, False, False),
    ('auto_switch_failure', False, False, False, False),
    ('post_makeup_eye_damage', False, False, False, False),
    ('closed_path', True, False, False, True),
    ('closed_layer_drift', True, False, True, False),
])
def test_partial_runner_stops_on_geometry_or_reload_drift_and_never_runs_lashes(inputs, tmp_path, monkeypatch, move_eye_phase, verify_layers, include_redness, persistence_drift, expect_success):
    request, registry = inputs
    request.update(verify_layer_persistence=verify_layers, include_redness_layers=bool(include_redness))
    closed_mode = move_eye_phase in ('closed_path', 'closed_layer_drift')
    if closed_mode:
        request.update(redness_policy='excluded_by_user', finalize_editor_closed=True)
    request['restore_non_skin_materials'] = move_eye_phase == 'pixel_damage_restore'
    if include_redness:
        request['redness_choice'] = include_redness
    library = COMPILER.compile_request(request, registry)
    root = tmp_path / 'run'
    root.mkdir()
    monkeypatch.setattr(RUNNER, 'RUN_ROOT', str(root))
    monkeypatch.setattr(RUNNER, 'REDNESS_ROOT', str(COMPILER.REDNESS_ROOT))
    calls, state = [], {'drift': 0., 'level': 0, 'reloaded': False, 'layer_values': {}, 'written_names': [], 'switches': [], 'selected': []}

    def switch(level):
        state['switches'].append(level)
        if not (move_eye_phase == 'auto_switch_failure' and level == 0):
            state['level'] = level
        if move_eye_phase == 'auto_measure_drift' and level == 0:
            state['drift'] = .00021
        return SimpleNamespace(IsError=lambda: False)

    avatar = SimpleNamespace(GetID=lambda: 1, GetSubdivMeshLevel=lambda: state['level'], SwitchSubdivMeshLevel=switch)

    def snapshot(avatar, **kwargs):
        rows = [[0., 0., 0.] for _ in range(14164)]
        rows[-1][0] = state['drift']
        return {'working_subdivision_level': state['level'], 'local': rows}

    def apply(avatar, assets, **kwargs):
        slot = assets[0]['slot']
        calls.append(slot)
        if slot == 'eyes':
            state['selected'] = []  # Eye material application can lose the panel target.
        if slot == 'eyes' and move_eye_phase is True:
            state['drift'] = .00021
        return avatar, {'slot': slot}

    def save(path):
        calls.append('save')
        Path(path).write_bytes(b'partial candidate')
        return SimpleNamespace(IsError=lambda: False)

    def load(path, label, api, receipt, checkpoint, **kwargs):
        receipt.append({'label': label})
        calls.append('makeup' if kwargs.get('stage') == 'makeup_preset' else 'load')
        if kwargs.get('stage') == 'makeup_preset' and str(move_eye_phase).startswith('auto_'):
            state['level'] = 1
        if kwargs.get('stage') == 'makeup_preset':
            state['selected'] = []  # Require a fresh target before editor activation too.
        if label.startswith('Reload'):
            state['reloaded'] = True
        state['editor_visible'] = False
        return {'status': 'ok'}

    def layer_value(api, name):
        value = state['layer_values'].get(name, 100)
        if state['reloaded'] and persistence_drift:
            value = 50
        return {'layer_name': name, 'opacity': value, 'slider_opacity': value,
                'row_enable_flags_uninterpreted': []}

    def opacity_write(api, name, opacity, audit):
        state['layer_values'][name] = opacity
        state['written_names'].append(name)
        audit.update(layer_name=name, target=opacity, verified=True)
        return audit

    def activate_editor(editor, **kwargs):
        assert state['selected'] == [avatar], 'Editor requires the current avatar selection'
        state['selected'] = []  # Reproduce a lost target before the redness load.
        return {'checked': True}

    def select_avatar(current):
        state['selected'] = [current]

    def load_redness(path):
        assert state['selected'] == [avatar], 'Preset target must be rebound after editor activation'
        calls.append('redness')
        return SimpleNamespace(IsError=lambda: False)

    editor = SimpleNamespace(isVisible=lambda: state.get('editor_visible', False))

    def reveal_editor(api, audit):
        state['editor_visible'] = True
        audit['verified'] = True
        calls.append('reveal_editor')
        return audit

    ui = SimpleNamespace(guarded_action=lambda operation, *args, **kwargs: operation(),
        activate_editor=activate_editor, unique_widget=lambda *args: editor, reveal_editor=reveal_editor,
        widget_record=lambda widget: {'isEnabled': bool(state['selected'])},
        SELECTORS={'editor': (), 'table': ()}, select_category=lambda *args: {},
        read_layer_opacity=layer_value, set_layer_opacity=opacity_write,
        layer_persistence_signature=LAYER_UI.layer_persistence_signature,
        capture=lambda *args: ({'table': {'rows': []}}, {}), table_record=lambda *args: {'rows': []})

    probe = SimpleNamespace(inside=lambda path, root: Path(path).resolve().is_relative_to(Path(root).resolve()),
        reference=lambda ref, *args: ref['path'], MAKEUP_ROOT=str(COMPILER.MAKEUP_ROOT),
        guarded_load=load, status_record=lambda raw: {'IsError': raw.IsError()})
    monkeypatch.setitem(sys.modules, 'cc_makeup_probe_v1', probe)
    monkeypatch.setitem(sys.modules, 'cc_capture_assembly_geometry_v1', SimpleNamespace(capture_body_snapshot=snapshot))
    monkeypatch.setitem(sys.modules, 'cc_skingen_controls_v1', ui)
    def wait_ready(api, ui, avatar_id, audit, modal, checkpoint):
        assert state['selected'] == [avatar]
        audit['ready'] = True
        return audit
    monkeypatch.setitem(sys.modules, 'cc_finalize_refresh_partial_v1', SimpleNamespace(
        capture_protected=lambda *args: {'native': 'all original support mocked here; helper tested separately'},
        wait_editor_ready=wait_ready))
    pixel_calls = []

    def pixel_capture(avatar, output, label, api):
        pixel_calls.append(label)
        folder = Path(output) / ('pixels_' + label)
        folder.mkdir()
        result = {'checkpoint': label, 'pixel_capture_complete': True}
        (folder / 'materials.json').write_text(json.dumps(result), encoding='utf-8')
        return result

    pixels = SimpleNamespace(SKINS=frozenset(), capture_stage=pixel_capture, compare_pixels=lambda before, after, *args, **kwargs:
        {'passed': not (move_eye_phase in ('pixel_damage', 'pixel_damage_restore') and after['checkpoint'] == 'after_skin')},
        compare_eye_pixels=lambda before, after, *args: {'passed': move_eye_phase != 'post_makeup_eye_damage'},
        restore_evidenced_support=lambda *args: {'passed': True}, compare_skin_pixels=lambda *args: {'passed': True})
    monkeypatch.setitem(sys.modules, 'cc_refresh_material_pixels_v1', pixels)
    def finish_closed(context):
        assert context.report['layer_persistence_passed']
        assert context.report['layers_before_save'] == context.report['layers_after_reload']
        assert context.original_support
        assert pixel_calls == ['source', 'after_skin', 'after_eyes'], 'Never accept active SkinGen pixels'
        calls.append('close_verified_editor')
        state['level'] = 0
        context.pixel_stage('saved')
        context.pixel_stage('reloaded')
        closed = Path(context.output_dir) / 'PRELASH_skin_makeup_eye_editor_closed_subd0.ccProject'
        save(str(closed))
        context.report.update(candidate=COMPILER.file_ref(closed), saved_candidate=COMPILER.file_ref(closed),
            final_working_subdivision_level=0, final_subdivision_scope='Actual editor closed and0 saved/reloaded')
        for label in ('saved', 'reloaded'):
            context.report['pixel_checks']['selected_eyes_to_' + label + '_no_allowances'] = {'passed': True}
        return str(closed)
    monkeypatch.setitem(sys.modules, 'cc_refresh_closed_assembly_v1', SimpleNamespace(finish=finish_closed))
    monkeypatch.setattr(RUNNER.importlib, 'reload', lambda module: module)
    api = SimpleNamespace(sha256_file=lambda path: COMPILER.file_ref(path)['sha256'], now=lambda: 'test',
        write_json=lambda value, path: Path(path).write_text(json.dumps(value), encoding='utf-8'),
        avatar_material_fingerprint=lambda avatar: {'digest': 'metadata_only'},
        load_file_with_optional_skin_material_dialog=lambda *args: (calls.append('skin') or {'IsError': False}, {}),
        remove_existing_avatar_part=lambda avatar, slot: (avatar, {'removed_count': 0}),
        apply_appearance_assets=apply, checked=lambda *args: {'IsError': False},
        QtWidgets=SimpleNamespace(QApplication=SimpleNamespace(allWidgets=lambda: [], processEvents=lambda: None)),
        RLPy=SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=select_avatar,
            GetSelectedObjects=lambda: state['selected']), RFileIO=SimpleNamespace(SaveProject=save, LoadFile=load_redness)))
    result = RUNNER.run(library, str(root / 'candidate'), lambda text: None, api)
    assert result['success'] is expect_success
    assert result['recipe_complete'] is False
    assert 'eyelashes' not in calls
    assert ('save' in calls) is (move_eye_phase not in (True, 'pixel_damage', 'auto_measure_drift', 'auto_switch_failure'))
    if not expect_success:
        message = ('Actual working subdivision' if move_eye_phase == 'auto_switch_failure' else
                   ('Selected eye/support' if move_eye_phase == 'post_makeup_eye_damage' else
                   ('Protected support' if move_eye_phase == 'pixel_damage' else ('Saved/reloaded' if closed_mode else ('0.002mm' if move_eye_phase else 'Saved/reloaded')))))
        assert message in result['error']['message']
    if expect_success and verify_layers:
        assert result['layer_persistence_passed']
        assert len(result['editor_activation_audits']) == 2
        for audit in result['editor_activation_audits']:
            assert audit['target_selection']['verified']
            assert audit['checkbox_after_target_selection']['isEnabled']
            assert audit['reveal_editor']['verified']
        assert not result['editor_activation_audits'][0]['checkbox_before_target_selection']['isEnabled']
    if expect_success and include_redness:
        assert result['redness_target_selection']['verified']
        assert result['redness_target_selection']['selected_ids_before'] == []
        assert result['redness_target_selection']['selected_ids_after'] == ['1']
        assert calls.count('redness') == 1
        assert all(value == 50 for value in state['layer_values'].values())
        assert state['written_names'] == library['refresh_assembly']['assets']['redness']['requested_layers']
        assert 'redness_exact_layer_opacity_and_reload' not in result['pending_phases']
    if expect_success:
        expected = ['source', 'after_skin'] + (['after_support_restore'] if move_eye_phase == 'pixel_damage_restore' else []) + ['after_eyes', 'saved', 'reloaded']
        assert pixel_calls == expected
        assert calls.index('eyes') < calls.index('makeup')
        assert result['pixel_checks']['selected_eyes_to_saved_no_allowances']['passed']
        assert result['pixel_checks']['selected_eyes_to_reloaded_no_allowances']['passed']
        if closed_mode:
            assert result['editing_checkpoint']['path'].endswith('EDITING_skin_makeup_eye.ccProject')
            assert result['candidate']['path'].endswith('PRELASH_skin_makeup_eye_editor_closed_subd0.ccProject')
            assert result['editing_checkpoint_unchanged'] and result['final_working_subdivision_level'] == 0
            assert result['editor_activation_audits'][1]['readiness_wait']['ready']
            assert 'redness' not in ' '.join(result['pending_phases'])
    if move_eye_phase == 'pixel_damage':
        assert pixel_calls == ['source', 'after_skin'] and 'makeup' not in calls
    if move_eye_phase == 'auto_raise':
        step = next(step for step in result['steps'] if step['phase'] == 'makeup_eyebrow')
        assert step['raw_working_subdivision_level'] == 1
        assert step['measured_working_subdivision_level'] == 0
        assert step['working_subdivision_level_after_gate'] == result['final_working_subdivision_level'] == 1
        assert [item['actual'] for item in step['subdivision_transitions']] == [0, 1]
    if move_eye_phase == 'auto_measure_drift':
        step = next(step for step in result['steps'] if step['phase'] == 'makeup_eyebrow')
        assert step['local_cage_diagnostic']['maximum_displacement_mm'] == 0
        assert not step['geometry_against_source']['passed']
        assert step['geometry_against_source']['failed_vertex_indices'] == [14163]
        assert step['working_subdivision_level_after_gate'] == 1
