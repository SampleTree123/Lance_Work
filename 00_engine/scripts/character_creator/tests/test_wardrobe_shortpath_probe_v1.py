import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_prepare_wardrobe_shortpath_probe_v1 import prepare


def test_probe_preserves_source_and_all_non_destination_case_fields(tmp_path):
    source = tmp_path / "source.json"
    original = {"presets": [{"preset_id": "a", "selected_assets": [{"sha256": "original"}],
                             "production_output": {"export_root": str(tmp_path / "original"),
                                                   "project_path": str(tmp_path / "original/project.ccProject"),
                                                   "export_basename": "unchanged", "flag": True}}]}
    source.write_text(json.dumps(original), encoding="utf-8")
    output = tmp_path / "probe.json"
    prepare(source, "a", tmp_path / "short", output)
    value = json.loads(output.read_text())
    assert json.loads(source.read_text()) == original
    assert value["presets"][0]["selected_assets"] == original["presets"][0]["selected_assets"]
    assert value["presets"][0]["production_output"]["export_basename"] == "unchanged"
    assert value["presets"][0]["production_output"]["flag"] is True
    assert value["shortpath_probe"]["original_production_output"] == original["presets"][0]["production_output"]
    with pytest.raises(FileExistsError):
        prepare(source, "a", tmp_path / "short", output)
    with pytest.raises(ValueError, match="known case"):
        prepare(source, "missing", tmp_path / "other", tmp_path / "other.json")
    with pytest.raises(ValueError, match="isolated"):
        prepare(source, "a", tmp_path / "original/child", tmp_path / "nested.json")
