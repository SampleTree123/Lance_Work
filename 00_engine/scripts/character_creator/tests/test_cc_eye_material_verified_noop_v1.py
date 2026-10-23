"""Fail-closed opt-in eye-material no-op checks, without importing CC/RLPy."""

import ast
import hashlib
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "cc_validate_body_reconstruction.py"


def extract_helper():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8-sig"))
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef)
                and item.name == "appearance_eye_material_noop_verified")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {
        "sha256_file": lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest(),
    }
    exec(compile(ast.fix_missing_locations(module), str(SCRIPT), "exec"), namespace)
    return namespace[node.name]


@pytest.fixture
def call_args(tmp_path):
    asset = tmp_path / "Eyes_01.ccEye"
    asset.write_bytes(b"approved existing eye material")
    return {
        "item": {"slot": "eyes", "path": str(asset),
                 "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()},
        "status": {"returned": True, "is_error": False},
        "dialog_policy": {"clicked_count": 1},
        "before": {"digest": "approved-eye-fingerprint"},
        "after": {"digest": "approved-eye-fingerprint"},
        "geometry_preserved": True,
        "support_preserved": True,
    }


def test_exact_verified_eye_material_noop_passes(call_args):
    assert extract_helper()(**call_args) is True


@pytest.mark.parametrize("field,value", [
    ("dialog_policy", None), ("dialog_policy", {"clicked_count": 0}),
    ("dialog_policy", {"clicked_count": 2}),
    ("status", {"returned": False, "is_error": False}),
    ("status", {"returned": True, "is_error": True}),
    ("status", {"returned": 1, "is_error": False}),
    ("status", {"returned": True}),
    ("geometry_preserved", False), ("support_preserved", False),
    ("geometry_preserved", 1), ("support_preserved", None),
    ("after", {"digest": "changed-eye-fingerprint"}),
    ("before", {}), ("after", {}),
])
def test_missing_or_failed_evidence_never_passes(call_args, field, value):
    call_args[field] = value
    assert extract_helper()(**call_args) is False


@pytest.mark.parametrize("field,value", [
    ("sha256", None), ("sha256", ""), ("sha256", "0" * 64),
    ("slot", "skin"), ("slot", "eyelashes"),
])
def test_wrong_asset_hash_or_slot_never_passes(call_args, field, value):
    call_args["item"][field] = value
    assert extract_helper()(**call_args) is False


def test_non_eye_extension_never_passes(call_args, tmp_path):
    asset = tmp_path / "samebytes.ccSkin"
    asset.write_bytes(Path(call_args["item"]["path"]).read_bytes())
    call_args["item"]["path"] = str(asset)
    assert extract_helper()(**call_args) is False


def test_asset_bytes_changed_after_manifest_never_pass(call_args):
    Path(call_args["item"]["path"]).write_bytes(b"changed after selection")
    assert extract_helper()(**call_args) is False


def test_missing_digests_in_nonempty_fingerprints_never_pass(call_args):
    call_args["before"] = {"mesh_digests": {}}
    call_args["after"] = {"mesh_digests": {}}
    assert extract_helper()(**call_args) is False


def test_empty_digests_never_pass(call_args):
    call_args["before"] = {"digest": ""}
    call_args["after"] = {"digest": ""}
    assert extract_helper()(**call_args) is False


def test_non_string_digests_never_pass(call_args):
    call_args["before"] = {"digest": 1234}
    call_args["after"] = {"digest": 1234}
    assert extract_helper()(**call_args) is False


def test_legacy_default_is_false():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8-sig"))
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef)
                and item.name == "apply_appearance_assets")
    defaults = dict(zip([arg.arg for arg in node.args.args][-len(node.args.defaults):], node.args.defaults))
    assert ast.literal_eval(defaults["allow_verified_material_noop"]) is False
