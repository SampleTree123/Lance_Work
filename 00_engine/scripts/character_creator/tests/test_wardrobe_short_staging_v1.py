import ast
import json
import os
from pathlib import Path
import tempfile
import time

import pytest


def helper():
    source = Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "_outfit_gate_export_attempt_root")
    ns = {"os": os, "time": time, "tempfile": tempfile, "ReconstructionError": RuntimeError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), ns)
    return ns[node.name]


def test_stage_is_short_unique_same_volume_and_keeps_final_untouched(tmp_path):
    cc = tmp_path / "exports/character_creator"
    final = cc / "wardrobe_average/sex/bodyfit/family/Coats/long_case_id/fbx"
    make = helper()
    first, second = Path(make(str(final))), Path(make(str(final)))
    assert first != second
    assert first.parent == cc / ".fbx_stage"
    assert first.is_dir() and second.is_dir()
    assert not final.exists()
    assert len(str(first)) < len(str(final))


def test_other_export_layout_retains_sibling_staging(tmp_path):
    final = tmp_path / "other/fbx"
    actual = Path(helper()(str(final)))
    assert actual.parent == final.parent
    assert actual.name.startswith("fbx.partial_")
    assert not final.exists()


def test_stage_cannot_escape_through_link(tmp_path, monkeypatch):
    cc = tmp_path / "exports/character_creator"
    original = os.path.realpath
    def resolve(path, **kwargs):
        return str(tmp_path / "outside") if str(path).endswith(".fbx_stage") else original(path, **kwargs)
    monkeypatch.setattr(os.path, "realpath", resolve)
    with pytest.raises(RuntimeError, match="escapes"):
        helper()(str(cc / "case/fbx"))


def test_real_export_function_writes_attempt_log_before_sdk(tmp_path):
    source = Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {"write_json", "_outfit_gate_export_attempt_root", "_outfit_gate_export_reference_character"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    class ReachedSDK(Exception):
        pass
    class SDK:
        def __getattr__(self, name):
            raise ReachedSDK(name)
    ns = {"os": os, "time": time, "tempfile": tempfile, "json": json,
          "ReconstructionError": RuntimeError, "RLPy": SDK()}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), ns)
    final, diagnostic = tmp_path / "exports/character_creator/case/fbx", tmp_path / "report"
    with pytest.raises(ReachedSDK):
        ns["_outfit_gate_export_reference_character"](None, str(final), "test", str(diagnostic), 10)
    result = json.loads((diagnostic / "test_export_attempt.json").read_text())
    assert Path(result["attempt_root"]).is_dir()
    assert result["final_root"] == str(final)
    assert result["preserve_failed_attempt"] is True
