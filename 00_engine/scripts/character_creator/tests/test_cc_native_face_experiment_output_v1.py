"""Offline output and source safety boundaries; never import or call CC."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location('native_face_output_test', Path(__file__).resolve().parents[1] / 'cc_native_face_library_v1.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


@pytest.fixture
def roots(tmp_path, monkeypatch):
    old, new = tmp_path / 'old', tmp_path / native.FIVE_SECOND_EXPERIMENT_ID
    projects, templates = tmp_path / 'source_copies', tmp_path / 'templates'
    for name, value in [('ROOT', old), ('FIVE_SECOND_ROOT', new), ('PROJECT_COPIES', projects), ('TEMPLATES', templates)]:
        monkeypatch.setattr(native, name, str(value))
    return old, new, projects, templates


def test_omitted_selector_preserves_old_output_root(roots):
    old, new, _, _ = roots
    assert native.validated_output_directory({}, str(old / 'job')) == str(old / 'job')
    with pytest.raises(ValueError, match='experiment root'):
        native.validated_output_directory({}, str(new / 'job'))


def test_explicit_selector_uses_only_new_output_root(roots):
    old, new, _, _ = roots
    request = {'experiment_id': native.FIVE_SECOND_EXPERIMENT_ID}
    assert native.validated_output_directory(request, str(new / 'job')) == str(new / 'job')
    for path in (old / 'job', new.parent / (new.name + '_other') / 'job', new / '..' / 'escape'):
        with pytest.raises(ValueError, match='experiment root'):
            native.validated_output_directory(request, str(path))


@pytest.mark.parametrize('selector', [None, '', '../escape', 'native_face_library_20261007_v1', 'unknown', 1])
def test_unknown_explicit_selectors_fail_closed(roots, selector):
    with pytest.raises(ValueError, match='experiment_id'):
        native.validated_output_directory({'experiment_id': selector}, str(roots[1] / 'job'))


@pytest.mark.parametrize('mutation', ['outside_project', 'outside_template', 'changed_sha', 'unsupported_extension'])
def test_new_output_branch_keeps_source_guards_before_cc_loading(roots, mutation):
    _, new, projects, templates = roots
    request = {'experiment_id': native.FIVE_SECOND_EXPERIMENT_ID, 'operation': 'inspect_export',
               'project_copy': {'path': str(projects / 'known.ccProject'), 'sha256': 'expected'},
               'performance': {'path': str(templates / 'HD Idle.iMotionPlus'), 'sha256': 'expected'}}
    if mutation == 'outside_project': request['project_copy']['path'] = str(new / 'other.ccProject')
    elif mutation == 'outside_template': request['performance']['path'] = str(new / 'other.iTalk')
    elif mutation == 'changed_sha': request['performance']['sha256'] = 'different'
    elif mutation == 'unsupported_extension': request['performance']['path'] = str(templates / 'other.py')
    # Empty RLPy deliberately has no loading API: reaching CC would fail the test.
    api = SimpleNamespace(RLPy=SimpleNamespace(), sha256_file=lambda _: 'expected')
    with pytest.raises(ValueError, match='source|performance'):
        native.run({'native_face_library': request}, str(new / 'job'), lambda _: None, api)
