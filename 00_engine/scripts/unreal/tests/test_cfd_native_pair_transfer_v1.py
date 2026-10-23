import importlib.util
import json
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parents[1] / 'run_cfd_native_pair_transfer_v1.py'
SPEC = importlib.util.spec_from_file_location('cfd_transfer_test', PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def extracted():
    return {'expected_meshes': [dict(source_name=n, model_name=n,
             expected_materials=['skin'], expected_nonzero_morph_names=['Smile'],
             position_delta_audit=[], fbx_morph_names=['Smile', 'TinyDelta']) for n in mod.ROLES]}


def test_all_source_morphs_kept_including_tiny_channels():
    rows = mod.expectation(extracted())
    assert len(rows) == 6
    assert {r['role'] for r in rows} == set(mod.ROLES.values())
    assert all(r['expected_morph_names'] == ['Smile', 'TinyDelta'] for r in rows)


def test_only_import_allows_native_autosetup_options_window():
    assert mod.remote_unattended('import') is False
    assert all(mod.remote_unattended(action) is True for action in ('audit', 'stage', 'open', 'status', 'prepare'))


def test_extra_native_component_is_not_silently_discarded():
    value = extracted()
    value['expected_meshes'].append(dict(value['expected_meshes'][0], source_name='HD_Brow'))
    with pytest.raises(ValueError, match='six-part'):
        mod.expectation(value)


def test_existing_preparation_cannot_be_replaced(tmp_path):
    path = tmp_path / 'manifest.json'
    mod.write_once(path, {'sha': 'original'})
    mod.write_once(path, {'sha': 'original'})
    with pytest.raises(ValueError, match='preserve evidence'):
        mod.write_once(path, {'sha': 'changed'})
    assert json.loads(path.read_text()) == {'sha': 'original'}


def test_import_uses_unique_worker_and_isolated_roots(monkeypatch):
    class Worker:
        @staticmethod
        def main(path, audit_only):
            return path, audit_only
    worker = Worker()
    class Loader:
        def exec_module(self, module):
            assert module is worker
    class Spec:
        loader = Loader()
    seen = []
    def make_spec(name, path):
        seen.append((name, path))
        return Spec()
    monkeypatch.setattr(mod.importlib.util, 'spec_from_file_location', make_spec)
    monkeypatch.setattr(mod.importlib.util, 'module_from_spec', lambda spec: worker)
    assert mod.editor_import(True) == (mod.MANIFEST, True)
    assert worker.REPORT_ROOT == mod.RUN
    assert worker.UE_ROOT == '/Game/DataMake/Validation/CFDNativePair20261006'
    assert worker.WITNESS_SUBDIR == 'MaterialWitnessInteractive'
    assert worker.WITNESS_AUTOMATED is False
    assert seen[0][0] == '_dm_cfd_native_pair_import_v1'
    assert 'complete_character_skeleton_pilot_20261005' not in str(worker.REPORT_ROOT)
