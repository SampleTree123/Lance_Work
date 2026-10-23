"""Offline first-run injection and proven bounded-entry boundaries; no SDK."""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

CC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_tested_bounded_first_run', CC / 'cc_run_character_refresh_bounded_entry_v1.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def case(tmp_path):
    source, asset = tmp_path / 'own.ccProject', tmp_path / 'own.ccSkinGenPreset'
    source.write_bytes(b'own geometry source')
    asset.write_bytes(b'own selected Makeup')
    api = SimpleNamespace(sha256_file=sha)
    pin = lambda path: {'path': str(path), 'sha256': sha(path)}
    config = {'source_project': pin(source), 'assets': {'makeup_eyebrow': pin(asset)},
        'redness_policy': 'excluded_by_user', 'include_redness_layers': False,
        **{key: True for key in ('verify_layer_persistence', 'capture_pixel_evidence',
             'finalize_editor_closed', 'restore_four_skin_normals_after_editor_close')}}
    control = {'schema': wrapper.SCHEMA, 'first_run': True, 'policy': wrapper.POLICY,
        'max_reentry_per_runtime_avatar': 1, 'implementation': pin(Path(wrapper.__file__)),
        'source_project': copy.deepcopy(config['source_project']),
        'makeup_asset': copy.deepcopy(config['assets']['makeup_eyebrow'])}
    return {'diagnostic_mode': 'character_refresh_normals', 'refresh_assembly': config,
            'prelash_bounded_entry': control}, api


def test_only_two_calls_added_all_original_wait_save_layers_geometry_pixels_kept():
    path = CC / 'cc_run_character_refresh_v1.py'
    assert sha(path) == wrapper.FROZEN['cc_run_character_refresh_v1']
    source = path.read_text(encoding='utf-8-sig')
    tree = ast.parse(wrapper.transform(source))
    names = {'_initialize_bounded_report', '_before_bounded_activation'}
    additions = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id in names]
    assert len(additions) == 2
    activation = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'activate_target_editor')
    insertion = next(i for i, n in enumerate(activation.body) if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
        and n.value.func.id == '_before_bounded_activation')
    operation = next(i for i, n in enumerate(activation.body) if isinstance(n, ast.FunctionDef) and n.name == 'operation')
    assert insertion < operation
    class StripOnlyAddedCalls(ast.NodeTransformer):
        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id in names:
                return None
            return self.generic_visit(node)
    assert ast.dump(StripOnlyAddedCalls().visit(tree), include_attributes=False) == ast.dump(ast.parse(source), include_attributes=False)
    with pytest.raises(ValueError, match='anchors changed'):
        wrapper.transform(source.replace("report.setdefault('editor_activation_audits'", "report.setdefault('unknown_activation_audits'"))


def test_first_run_binding_and_honest_report_provenance(tmp_path):
    library, api = case(tmp_path)
    provenance = wrapper.validate(library, api)
    report = {'implementation_sha256': wrapper.FROZEN['cc_run_character_refresh_v1']}
    wrapper.initialize_report(report, provenance)
    assert report['implementation_sha256'] == sha(wrapper.__file__)
    assert report['base_runner_implementation_sha256'] == wrapper.FROZEN['cc_run_character_refresh_v1']
    assert report['runtime_wrapper']['first_run'] is True
    assert report['runtime_wrapper']['source_pins']['cc_refresh_skin_normal_closure_v1']['sha256'] == wrapper.FROZEN['cc_refresh_skin_normal_closure_v1']
    assert 'checkpoint_repair' not in report
    for key, replacement in [('source_project', {'path': 'other', 'sha256': '0' * 64}),
                             ('makeup_asset', {'path': 'other', 'sha256': '0' * 64}),
                             ('first_run', False)]:
        changed = copy.deepcopy(library)
        changed['prelash_bounded_entry'][key] = replacement
        with pytest.raises(ValueError, match='same-source/same-Makeup'):
            wrapper.validate(changed, api)
    changed = copy.deepcopy(library)
    changed['saved_editing_resume'] = {}
    with pytest.raises(ValueError, match='failed checkpoint'):
        wrapper.validate(changed, api)


def test_real_bounded_entry_one_own_reentry_per_runtime_avatar_and_shared_report(tmp_path, monkeypatch):
    library, api = case(tmp_path)
    core = wrapper.private_module('cc_repair_refresh_editing_checkpoint_v3')
    report = {'config': library['refresh_assembly'], 'loads': [],
              'implementation_sha256': wrapper.FROZEN['cc_run_character_refresh_v1']}
    wrapper.initialize_report(report, wrapper.validate(library, api))
    live = {'id': 'first', 'ready': False}
    api.RLPy = SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: [SimpleNamespace(GetID=lambda: live['id'])]))
    calls = []
    monkeypatch.setattr(core, 'click_appearance', lambda *args: calls.append('normal Appearance click'))
    monkeypatch.setattr(core, 'ready', lambda *args: (live['ready'], {'fixture_ready': live['ready']}))
    def cancel(asset, api, observed_report, checkpoint, audit):
        assert asset == library['refresh_assembly']['assets']['makeup_eyebrow']
        calls.append('own preset exact Cancel')
        observed_report['loads'].append({'cancel_count': 1, 'application_accepted': False})
        live['ready'] = True
    monkeypatch.setattr(core, 'cancel_only_reentry', cancel)
    wrapper.before_activation(core, api, None, report, lambda *args: None, 'first', 'before_save')
    assert report['loads'] == [{'cancel_count': 1, 'application_accepted': False}]
    assert 'checkpoint_repair' not in report
    live['ready'] = False
    with pytest.raises(ValueError, match='Only one own exact-Cancel'):
        wrapper.before_activation(core, api, None, report, lambda *args: None, 'first', 'again')
    live['id'] = 'reloaded'
    wrapper.before_activation(core, api, None, report, lambda *args: None, 'reloaded', 'after_reload')
    assert calls.count('own preset exact Cancel') == 2
    assert report['bounded_editor_entry']['reentry_attempted_avatar_ids'] == ['first', 'reloaded']


def test_exact_dialog_predicate_still_rejects_unknown_or_disabled_buttons():
    core = wrapper.private_module('cc_repair_refresh_editing_checkpoint_v3')
    buttons = [{'text': text, 'class_name': 'QPushButton', 'visible': True,
                'enabled': True, 'checkable': False} for text in ('Add', 'Replace', 'Cancel')]
    observed = {'class_name': 'QMessageBox', 'window_title': 'Character Creator 5',
                'labels': [core.QUESTION], 'direct_text': [], 'buttons': buttons}
    assert core.cancel_question(observed)
    unknown = copy.deepcopy(observed)
    unknown['labels'] = ['Overwrite or discard unrelated data?']
    assert not core.cancel_question(unknown)
    disabled = copy.deepcopy(observed)
    disabled['buttons'][2]['enabled'] = False
    assert not core.cancel_question(disabled)
