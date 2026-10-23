"""Offline source guard only; does not simulate a successful SDK capture."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('skin_probe', Path(__file__).parents[1] / 'cc_probe_refresh_skin_material_readonly_v1.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_changed_saved_source_is_rejected_before_any_scene_access(tmp_path):
    source = tmp_path / 'source.ccProject'
    source.write_bytes(b'actual test source')
    record = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'bytes': source.stat().st_size}
    source.write_bytes(b'changed source')
    api = SimpleNamespace(sha256_file=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(),
        RLPy=SimpleNamespace(RScene=SimpleNamespace(GetAvatars=lambda: pytest.fail('scene accessed'))))
    with pytest.raises(ValueError, match='source pin changed'):
        probe.run({'refresh_skin_material_readonly': {'expected_loaded_source': record}}, str(tmp_path / 'out'), lambda s: None, api)
    assert not (tmp_path / 'out').exists()
