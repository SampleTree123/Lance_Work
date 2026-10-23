"""Reconcile the bounded route experiment from persisted evidence, offline only.

No CC calls, no asset writes, and no promotion of API success to visual acceptance.
The height bands are descriptive diagnostics, not anatomical acceptance masks.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from cc_compare_headshot_geometry_v1 import head_ids, read_obj, stats


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def mesh_comparison(a_path, b_path):
    a, auv, af = read_obj(a_path)
    b, buv, bf = read_obj(b_path)
    if af != bf or not np.array_equal(auv, buv):
        raise ValueError("Topology or UV mismatch")
    d = np.linalg.norm(b - a, axis=1) * 10
    ids = head_ids()
    outside = np.setdiff1d(np.arange(len(a)), ids)
    changed = a[d > 0.1]
    return {
        "a": str(a_path), "b": str(b_path), "topology_uv_identical": True,
        "registration": "exported coordinates; no best-fit registration",
        "all_vertices": stats(a, b, np.arange(len(a))),
        "installed_head": stats(a, b, ids),
        "outside_installed_head": stats(a, b, outside),
        "changed_over_0_1mm_reference_bounds_cm":
            [changed.min(0).tolist(), changed.max(0).tolist()] if len(changed) else None,
        "reference_height_diagnostics": {
            str(z): stats(a, b, np.flatnonzero(a[:, 2] < z))
            for z in (100, 120, 130, 135, 140, 145, 150) if np.any(a[:, 2] < z)
        },
        "interpretation": "Height bands are diagnostics only; installed head excludes some neck vertices. Neither is a final body acceptance mask.",
    }


def summarize(root):
    root = Path(root)
    matrix = read(root / "route_matrix.json")
    summary = {"updated_at": datetime.now().astimezone().isoformat(),
               "overall_acceptance": "pending", "cases": [],
               "no_formal_assets_changed": True}
    for case in matrix["cases"]:
        cid = case["case_id"]
        out = root / cid
        row = {"case_id": cid, "route": case["route"], "sex": case["sex"],
               "generation": "not_started", "validation": "not_started",
               "visual_acceptance": "pending", "scalp_hair_acceptance": "pending"}
        photo = Path(case["photo_path"])
        row["photo_sha_matches"] = hashlib.sha256(photo.read_bytes()).hexdigest() == case["photo_sha256"]
        gp = out / "generate/photo_generation_report.json"
        if gp.exists():
            g = read(gp)
            row["generation_report"] = str(gp)
            row["generation_phase"] = g.get("stage")
            row["generation"] = "evidence_collected" if g.get("success") else "incomplete"
            pp = Path(g["project_path"]) if g.get("project_path") else None
            if pp and pp.exists():
                row["candidate_sha_matches"] = hashlib.sha256(pp.read_bytes()).hexdigest() == g.get("project_sha256")
                row["candidate_project"] = str(pp)
            if case["route"] == 1 and g.get("before_obj_path") and g.get("obj_path"):
                row["generation_body_comparison"] = mesh_comparison(g["before_obj_path"], g["obj_path"])
        vp = out / "validate/route_validation_report.json"
        if vp.exists():
            v = read(vp)
            row["validation_report"] = str(vp)
            row["validation_phase"] = v.get("phase")
            row["validation"] = "evidence_collected" if v.get("success") else ("failed" if v.get("error") else "in_progress")
            row["error"] = v.get("error")
            row["state_checkpoints"] = {
                key: {f: v[key].get(f) for f in ("subdivision", "max_subdivision", "profile_uid", "expression_count")}
                for key in ("generated_state", "profile_upgraded_state", "final_state_before_save", "reloaded_subd0_state", "subd1_state", "reloaded_subd1_state", "final_restored_state") if key in v
            }
            comparisons = {
                "save_reload": ("before_save_body.obj", "reloaded_subd0_body.obj"),
                "subdivision_roundtrip": ("reloaded_subd0_body.obj", "after_subdivision_body.obj"),
                "appearance_geometry": ("generated_body.obj", "appearance_support_body.obj"),
            }
            for name, (a, b) in comparisons.items():
                a, b = vp.parent/a, vp.parent/b
                if a.exists() and b.exists():
                    row[name] = mesh_comparison(a, b)
        case["status"] = row["validation"] if row["validation"] != "not_started" else row["generation"]
        case["visual_acceptance"] = "pending"
        summary["cases"].append(row)
    matrix["updated_at"] = summary["updated_at"]
    matrix["status_semantics"] = "Evidence collection only. Visual, geometry and scalp/hair gates must be accepted separately."
    (root/"route_matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (root/"route_progress_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    report = summarize(parser.parse_args().root)
    print(json.dumps([{k: row[k] for k in ("case_id", "generation", "validation")} for row in report["cases"]], indent=2))
