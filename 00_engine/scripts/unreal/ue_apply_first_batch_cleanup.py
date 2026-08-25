"""Apply the reference-checked First Batch cleanup audit inside Unreal."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
AUDIT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_cleanup_20260824_v1"
    / "cleanup_audit.json"
)
RESULT = AUDIT.with_name("cleanup_result.json")


report = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
if report.get("mode") != "audit_only":
    raise RuntimeError(f"Unexpected cleanup audit mode: {report.get('mode')}")
rows = [row for row in report["assets"] if row.get("safe_to_delete")]
safe_paths = {row["asset"] for row in rows}
if len(rows) != report["counts"]["safe_to_delete"]:
    raise RuntimeError("Cleanup audit count changed or is malformed")

# Delete candidate referencers before the assets they reference. Cycles are
# handled deterministically after all acyclic edges have been consumed.
remaining = {row["asset"]: row for row in rows}
ordered = []
while remaining:
    leaves = sorted(
        path
        for path, row in remaining.items()
        if not any(ref in remaining for ref in row.get("referencers", []))
    )
    if not leaves:
        leaves = [sorted(remaining)[0]]
    for path in leaves:
        ordered.append(remaining.pop(path))

deleted = []
failed = []
already_absent = []
for row in ordered:
    path = row["asset"]
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        already_absent.append(path)
        continue
    current_external = sorted(
        ref.split(".", 1)[0]
        for ref in unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            path, load_assets_to_confirm=True
        )
        if ref.split(".", 1)[0] not in safe_paths
    )
    if current_external:
        failed.append(
            {
                "asset": path,
                "reason": "new_external_referencer",
                "external_referencers": current_external,
            }
        )
        continue
    if unreal.EditorAssetLibrary.delete_asset(path):
        deleted.append(path)
    else:
        failed.append({"asset": path, "reason": "delete_asset_returned_false"})

unreal.SystemLibrary.collect_garbage()
still_present = [
    path for path in deleted if unreal.EditorAssetLibrary.does_asset_exist(path)
]
result = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed" if not failed and not still_present else "failed",
    "audit": str(AUDIT),
    "candidate_count": len(rows),
    "deleted_count": len(deleted),
    "already_absent_count": len(already_absent),
    "failed_count": len(failed),
    "still_present_count": len(still_present),
    "deleted": deleted,
    "already_absent": already_absent,
    "failed": failed,
    "still_present": still_present,
}
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    "DM_FIRST_BATCH_CLEANUP_RESULT="
    + json.dumps(
        {
            "status": result["status"],
            "result": str(RESULT),
            "deleted_count": len(deleted),
            "already_absent_count": len(already_absent),
            "failed_count": len(failed),
            "still_present_count": len(still_present),
        },
        ensure_ascii=False,
    )
)
