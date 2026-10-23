import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import audit_wardrobe_progress_v1 as audit


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_pending_batch_is_not_exported(tmp_path):
    write(tmp_path / "cc_export.json", {"presets": [{"preset_id": "a"}]})
    write(tmp_path / "batch_001/cc_export.json", {"presets": [{"preset_id": "a"}]})
    result = audit.audit(tmp_path, tmp_path / "reports")
    assert result["cc_exported_units"] == result["ue_transferred_units"] == 0
    assert result["not_exported_units"] == 1


@pytest.mark.parametrize("second", ["a", "unknown"])
def test_duplicate_or_unknown_unit_rejected(tmp_path, second):
    write(tmp_path / "cc_export.json", {"presets": [{"preset_id": "a"}]})
    write(tmp_path / "batch_001/cc_export.json", {"presets": [{"preset_id": "a"}]})
    write(tmp_path / "batch_002/cc_export.json", {"presets": [{"preset_id": second}]})
    with pytest.raises(ValueError, match="Duplicate or unknown"):
        audit.audit(tmp_path, tmp_path / "reports")


def test_changed_evidence_rejected(tmp_path):
    path = tmp_path / "asset.txt"
    path.write_text("before")
    record = {"path": str(path), "sha256": audit.file_hash(path)}
    assert audit.verify_record(record) == path
    path.write_text("after")
    with pytest.raises(ValueError, match="changed"):
        audit.verify_record(record)


def test_mapping_inheritance_requires_same_bytes_and_explicit_source(tmp_path):
    old = tmp_path / "v2/batch_001/ue_import.json"
    new = tmp_path / "v3/batch_001/ue_import.json"
    write(old, {"preserve": True})
    write(new, {"preserve": True})
    evidence = {"path": str(old), "sha256": audit.file_hash(old)}
    assert not audit.mapping_manifest_matches(new.parents[1], new.parent, evidence)
    write(new.parents[1] / "revision.json", {"reused_finalized_manifests": {"batch_001": evidence}})
    assert audit.mapping_manifest_matches(new.parents[1], new.parent, evidence)
    write(new, {"changed": True})
    assert not audit.mapping_manifest_matches(new.parents[1], new.parent, evidence)
    write(new, {"preserve": True})
    write(old, {"changed": True})
    with pytest.raises(ValueError, match="changed"):
        audit.mapping_manifest_matches(new.parents[1], new.parent, evidence)
