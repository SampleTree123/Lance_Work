from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
REQUIRED_RUN_FIELDS = {
    "schema_version",
    "id",
    "title",
    "task",
    "created_at",
    "status",
    "summary",
    "thumbnail",
    "groups",
}


class PortalDataError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortalDataError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PortalDataError(f"Expected a JSON object in {path}")
    return value


def validate_run(run: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_RUN_FIELDS - run.keys())
    if missing:
        raise PortalDataError(f"Missing run fields: {', '.join(missing)}")

    run_id = run["id"]
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise PortalDataError(
            "Run id must use 3-80 lowercase letters, numbers, and hyphens"
        )
    if run["schema_version"] != 1:
        raise PortalDataError("Only run schema_version 1 is supported")
    if not isinstance(run["groups"], dict) or not run["groups"]:
        raise PortalDataError("Run groups must be a non-empty object")

    try:
        datetime.fromisoformat(str(run["created_at"]))
    except ValueError as exc:
        raise PortalDataError("created_at must be an ISO-8601 timestamp") from exc

    for group_id, group in run["groups"].items():
        if not isinstance(group, dict):
            raise PortalDataError(f"Group {group_id} must be an object")
        cases = group.get("cases")
        if not isinstance(cases, list) or not cases:
            raise PortalDataError(f"Group {group_id} must contain cases")
        for case in cases:
            if not isinstance(case, dict) or not case.get("id"):
                raise PortalDataError(f"Group {group_id} contains a case without an id")
            images = case.get("images")
            if not isinstance(images, dict) or not images:
                raise PortalDataError(
                    f"Case {group_id}/{case.get('id')} must contain images"
                )

    review = run.get("review")
    if review is not None:
        if not isinstance(review, dict):
            raise PortalDataError("review must be an object")
        if review.get("schema_version") != 1:
            raise PortalDataError("Only review schema_version 1 is supported")
        if review.get("mode") != "candidate_review":
            raise PortalDataError("review mode must be candidate_review")
        review_id = review.get("review_id")
        if not isinstance(review_id, str) or not RUN_ID_PATTERN.fullmatch(review_id):
            raise PortalDataError("review_id must use the run id format")
        case_ids = [
            str(case["id"])
            for group in run["groups"].values()
            for case in group["cases"]
        ]
        if len(case_ids) != len(set(case_ids)):
            raise PortalDataError("Candidate review case ids must be globally unique")


def registry_entry(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run["id"],
        "title": run["title"],
        "task": run["task"],
        "created_at": run["created_at"],
        "status": run["status"],
        "summary": run["summary"],
        "thumbnail": run["thumbnail"],
        "tags": run.get("tags", []),
        "metrics": run.get("metrics", []),
        "run_file": f"./runs/{run['id']}/run.json",
    }


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def register_run(
    source: Path,
    portal_root: Path,
    *,
    replace: bool = False,
) -> tuple[Path, Path]:
    source = source.resolve()
    portal_root = portal_root.resolve()
    run = load_json(source)
    validate_run(run)

    target = portal_root / "runs" / run["id"] / "run.json"
    if target.exists() and source != target.resolve() and not replace:
        raise PortalDataError(
            f"Run {run['id']} already exists; pass --replace to update it"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    if source != target.resolve():
        shutil.copyfile(source, target)
    else:
        write_json_atomic(target, run)

    registry_path = portal_root / "data" / "registry.json"
    if registry_path.exists():
        registry = load_json(registry_path)
    else:
        registry = {"schema_version": 1, "generated_at": None, "runs": []}

    runs = [entry for entry in registry.get("runs", []) if entry.get("id") != run["id"]]
    runs.append(registry_entry(run))
    runs.sort(key=lambda entry: entry.get("created_at", ""), reverse=True)
    registry = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
    }
    write_json_atomic(registry_path, registry)
    return target, registry_path


def collect_local_urls(run: dict[str, Any]) -> list[str]:
    urls = [str(run.get("thumbnail", ""))]
    for group in run.get("groups", {}).values():
        urls.append(str(group.get("overview", "")))
        urls.extend(str(value) for value in group.get("comparisons", {}).values())
        for case in group.get("cases", []):
            urls.extend(str(value) for value in case.get("images", {}).values())
            urls.append(str(case.get("video", "")))
    urls.extend(str(item.get("url", "")) for item in run.get("artifacts", []))
    return sorted({url for url in urls if url.startswith("/")})


def validate_local_assets(run: dict[str, Any], lance_work_root: Path) -> list[str]:
    missing: list[str] = []
    for url in collect_local_urls(run):
        relative = Path(*url.lstrip("/").split("/"))
        if not (lance_work_root / relative).is_file():
            missing.append(url)
    return missing
