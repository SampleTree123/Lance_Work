from pathlib import Path
import copy
import importlib.util
import json

import pytest

RUN = Path(__file__).resolve().parents[3] / 'outputs/production_workflow_20261017_v1'
SPEC = importlib.util.spec_from_file_location('formal_palette_compatibility_test', RUN / 'asset_inventory_formal_runtime_v1.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_current_palette_binds_only_recorded_compatible_code():
    original = m.read(m.BEFORE)['palette']
    current = m.current_palette(original)
    assert current['hair'][:len(original['hair'])] == original['hair'] and current['eye'] == original['eye']
    assert current['hair'] == original['hair']
    assert len(current['hair_color_trials']) == 10
    assert current['hair_color_method'] == 'neutral_base_v2'
    assert not any(row.get('experimental') for row in current['hair_color_trials'])
    assert current['source'] == m.record(m.SCRIPTS / 'hair_eye_color_runtime_v1.py')
    assert current['code_compatibility_source'] == m.record(RUN / 'hair_eye_color_formal_root_compatibility_v1.json')
    wrong = copy.deepcopy(original)
    wrong['source']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='proof mismatch'):
        m.current_palette(wrong)


def test_changed_palette_semantics_rejected_even_with_matching_current_pin(tmp_path, monkeypatch):
    original = m.read(m.BEFORE)['palette']
    proof = m.read(RUN / 'hair_eye_color_formal_root_compatibility_v1.json')
    current = tmp_path / 'hair_eye_color_runtime_v1.py'
    current.write_text(Path(proof['current_source']['path']).read_text(encoding='utf-8') + "\nPRESETS['hair']['black'] = (1., 0., 0., 1.)\n", encoding='utf-8')
    proof['current_source'] = m.record(current)
    (tmp_path / 'hair_eye_color_formal_root_compatibility_v1.json').write_text(json.dumps(proof), encoding='utf-8')
    monkeypatch.setattr(m, 'RUN', tmp_path)
    monkeypatch.setattr(m, 'SCRIPTS', tmp_path)
    with pytest.raises(ValueError, match='semantics changed'):
        m.current_palette(original)
