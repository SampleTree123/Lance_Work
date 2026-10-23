import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_build_wardrobe_library_v1 as library
import cc_prepare_wardrobe_batch_v1 as batch


def module():
    return {"sha256": "a" * 64, "slot": "shirts",
            "cloth_options_policy": "fit_body_shape", "asset_id": "first"}


def test_identical_bytes_with_different_names_share_one_export():
    first = module()
    second = {**first, "asset_id": "second", "source_path": "elsewhere"}
    assert library.unit_key("male", [first], False) == library.unit_key("male", [second], False)


def test_bodyfit_and_fit_policy_cannot_be_deduplicated():
    first = module()
    key = library.unit_key("male", [first], False)
    assert key != library.unit_key("female", [first], False)
    assert key != library.unit_key("male", [{**first, "cloth_options_policy": "keep_cloth_shape"}], False)
    assert key != library.unit_key("male", [first], True)


def test_prepare_selects_only_requested_units_and_preserves_rules(tmp_path):
    source = tmp_path / "library"
    source.mkdir()
    presets = [{"preset_id": uid, "production_output": {
        "project_path": str(tmp_path / f"{uid}.ccProject"),
        "export_root": str(tmp_path / uid),
    }} for uid in ("M_A", "F_B")]
    (source / "cc_export.json").write_text(json.dumps({"presets": presets}), encoding="utf-8")
    (source / "ue_import.json").write_text(json.dumps({
        "cases": [{"case_id": "M_BASE"}, {"case_id": "M_A"}, {"case_id": "F_B"}],
        "families": [{"constraints": {"allow_cross_family_components": False}}],
    }), encoding="utf-8")
    destination = tmp_path / "batch"
    batch.prepare(source, destination, ["F_B"])
    actual = json.loads((destination / "ue_pending.json").read_text())
    assert actual["cases"] == [{"case_id": "F_B"}]
    assert actual["families"][0]["constraints"]["allow_cross_family_components"] is False
    with pytest.raises(FileExistsError):
        batch.prepare(source, destination, ["F_B"])
    with pytest.raises(ValueError, match="Unknown units"):
        batch.prepare(source, tmp_path / "other", ["F_MISSING"])


def test_segment_rejects_names_without_safe_characters():
    with pytest.raises(ValueError):
        library.segment("../")
    assert library.segment("Casual 01 & 04") == "Casual_01_04"
