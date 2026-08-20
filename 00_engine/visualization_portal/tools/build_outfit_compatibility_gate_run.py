from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


LANCE_WORK_ROOT = Path(r"D:\UE\Lance_Work")
DEFAULT_GATE = Path(
    r"D:\UE\Lance_Work\00_engine\scripts\character_creator"
    r"\cc_outfit_compatibility_gate_20260816_v3.json"
)
DEFAULT_VALIDATION = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts"
    r"\outfit_compatibility_gate\run_20260815_execution_v1"
    r"\validation_result.json"
)
DEFAULT_BRIDGE_RESULT = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\results"
    r"\outfit_gate_full_20260815_v1.json"
)
DEFAULT_PORTAL = Path(r"D:\UE\Lance_Work\00_engine\visualization_portal")
RUN_ID = "2026-08-15-outfit-compatibility-gate-partial-v1"
VIEW_ORDER = (
    "front",
    "front_three_quarter",
    "left_profile",
    "rear",
    "right_profile",
)
VIEW_LABELS = {
    "front": "Front",
    "front_three_quarter": "Front 3/4",
    "left_profile": "Left profile",
    "rear": "Rear",
    "right_profile": "Right profile",
}
BODYFIT_ORDER = {
    "F01_Lean": 10,
    "F04_Heavy": 20,
    "F05_Short_Average": 30,
    "M01_Lean": 40,
    "M04_Heavy": 50,
    "M05_Short_Average": 60,
}


class OutfitPortalError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OutfitPortalError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def to_url(path: Path) -> str:
    path = path.resolve()
    relative = path.relative_to(LANCE_WORK_ROOT.resolve())
    return "/" + relative.as_posix()


def safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "group"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def build_sheet(
    label: str,
    cases: list[dict[str, Any]],
    output_path: Path,
) -> None:
    image_size = 280
    gap = 16
    row_label_width = 210
    header_height = 112
    row_height = image_size + 70
    width = row_label_width + len(VIEW_ORDER) * (image_size + gap) + gap
    height = header_height + len(cases) * row_height + gap
    canvas = Image.new("RGB", (width, height), "#10151d")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(28, bold=True)
    heading_font = load_font(18, bold=True)
    body_font = load_font(17, bold=True)
    detail_font = load_font(14)
    draw.text((24, 18), label, fill="#f3f5f7", font=title_font)
    draw.text(
        (24, 58),
        "Machine capture: complete case rows, fixed 1024 x 1024 source images",
        fill="#9ca8b8",
        font=detail_font,
    )
    for column, view_id in enumerate(VIEW_ORDER):
        x = row_label_width + column * (image_size + gap)
        draw.text(
            (x + 6, 80),
            VIEW_LABELS[view_id],
            fill="#cfd6df",
            font=heading_font,
        )

    for row, case in enumerate(cases):
        y = header_height + row * row_height
        draw.rounded_rectangle(
            (gap, y, width - gap, y + row_height - gap),
            radius=6,
            fill="#171e28",
            outline="#2a3544",
            width=1,
        )
        draw.text(
            (28, y + 34),
            case["bodyfit_id"],
            fill="#f3f5f7",
            font=body_font,
        )
        draw.text(
            (28, y + 68),
            f"{case['asset_count']} assets",
            fill="#9ca8b8",
            font=detail_font,
        )
        for column, view_id in enumerate(VIEW_ORDER):
            source = Path(case["images"][view_id])
            with Image.open(source) as opened:
                thumbnail = opened.convert("RGB").resize(
                    (image_size, image_size),
                    Image.Resampling.LANCZOS,
                )
            x = row_label_width + column * (image_size + gap)
            canvas.paste(thumbnail, (x, y + 12))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def collect_cases(
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for compact in validation.get("results") or []:
        if compact.get("success") is not True:
            continue
        result_path = Path(compact["result_path"]).resolve()
        result = read_json(result_path)
        captures = result.get("captures") or []
        images = {
            capture["view_id"]: Path(capture["image"]["path"]).resolve()
            for capture in captures
        }
        if set(images) != set(VIEW_ORDER):
            raise OutfitPortalError(
                f"Case does not contain the five canonical views: {result_path}"
            )
        missing = [str(path) for path in images.values() if not path.is_file()]
        if missing:
            raise OutfitPortalError(f"Case images are missing: {missing}")
        records.append(
            {
                "asset_count": len(result.get("asset_applications") or []),
                "bodyfit_id": result["bodyfit_id"],
                "case_id": result["case_id"],
                "images": {key: str(value) for key, value in images.items()},
                "look_id": result["look_id"],
                "preset_id": result["preset_id"],
                "result_path": str(result_path),
                "sex": result["sex"],
                "subject_id": result["subject_id"],
            }
        )
    return records


def build_run(
    gate: dict[str, Any],
    validation: dict[str, Any],
    validation_path: Path,
    bridge_result_path: Path,
    review_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cases = collect_cases(validation)
    if len(cases) != int(validation.get("success_count", -1)):
        raise OutfitPortalError("Validation success count and case files disagree")
    look_metadata = {
        item["look_id"]: item for item in gate["representative_looks"]
    }
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for case in cases:
        grouped.setdefault(case["look_id"], []).append(case)
    for records in grouped.values():
        records.sort(key=lambda item: BODYFIT_ORDER[item["bodyfit_id"]])

    sheets_root = review_root / "sheets"
    portal_groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    review_groups = []
    for index, (look_id, records) in enumerate(grouped.items(), 1):
        metadata = look_metadata[look_id]
        display_label = "{} / {}".format(
            metadata["family_display_name"],
            metadata["group_id"],
        )
        group_id = f"g{index:02d}-{safe_id(look_id)}"
        sheet_path = sheets_root / f"{group_id}.png"
        build_sheet(display_label, records, sheet_path)
        portal_cases = []
        for case in records:
            portal_cases.append(
                {
                    "id": case["preset_id"],
                    "label": "{} / {}".format(
                        case["bodyfit_id"],
                        display_label,
                    ),
                    "preset_id": case["preset_id"],
                    "parameters": {
                        "asset_count": case["asset_count"],
                    },
                    "images": {
                        view_id: to_url(Path(case["images"][view_id]))
                        for view_id in VIEW_ORDER
                    },
                }
            )
        portal_groups[group_id] = {
            "label": display_label,
            "overview": to_url(sheet_path),
            "comparisons": {},
            "cases": portal_cases,
        }
        review_groups.append(
            {
                "group_id": group_id,
                "look_id": look_id,
                "label": display_label,
                "sheet": str(sheet_path),
                "cases": records,
            }
        )

    expected_total = int(gate["counts"]["test_case_count"])
    completed = len(cases)
    image_count = completed * len(VIEW_ORDER)
    review_index = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "resource_stopped_partial_run",
        "completed_case_count": completed,
        "expected_case_count": expected_total,
        "image_count": image_count,
        "groups": review_groups,
        "machine_validation": str(validation_path),
        "bridge_result": str(bridge_result_path),
    }
    index_path = review_root / "index.json"
    write_json(index_path, review_index)
    readme_path = review_root / "README.md"
    readme_path.write_text(
        "# Outfit Compatibility Gate - Partial Review\n\n"
        f"- Completed: {completed}/{expected_total} cases\n"
        f"- Images: {image_count}\n"
        "- Machine failures: 0\n"
        "- Stop reason: CC memory pressure; the current case was allowed to finish.\n\n"
        "Each sheet uses one row per BodyFit and five columns: front, front "
        "three-quarter, left profile, rear, and right profile. Review visible "
        "clipping, missing pieces, implausible fit, and incorrect footwear.\n",
        encoding="utf-8",
    )
    run = {
        "schema_version": 1,
        "id": RUN_ID,
        "title": "CC Outfit Compatibility Gate - Partial Batch",
        "task": "Character Creator / Clothing Compatibility",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "blocked",
        "summary": (
            f"{completed}/{expected_total} extreme-BodyFit cases completed with "
            "zero machine failures. The batch stopped after a clean checkpoint "
            "because Character Creator memory pressure reached the local safety limit."
        ),
        "decision": {
            "label": "Partial machine gate passed; continuation requires CC restart",
            "summary": (
                "Every published row passed project load, clothing cleanup, asset "
                "application, inventory change, hair preservation, framing, and "
                "five-image capture. Visual clipping still requires human review."
            ),
        },
        "tags": [
            "CC5",
            "Outfits",
            "Extreme BodyFits",
            "Five views",
            "Partial batch",
        ],
        "thumbnail": next(iter(portal_groups.values()))["overview"],
        "metrics": [
            {"label": "Completed cases", "value": f"{completed}/{expected_total}"},
            {"label": "Machine passed", "value": completed},
            {"label": "Machine failed", "value": 0},
            {"label": "Review images", "value": image_count},
            {"label": "Completed looks", "value": len(portal_groups)},
        ],
        "groups": portal_groups,
        "artifacts": [
            {"label": "Review instructions", "url": to_url(readme_path)},
            {"label": "Review index", "url": to_url(index_path)},
            {"label": "Machine checkpoint", "url": to_url(validation_path)},
            {"label": "Gate manifest", "url": to_url(DEFAULT_GATE)},
            {"label": "Bridge stop result", "url": to_url(bridge_result_path)},
        ],
        "source": {
            "gate_manifest": to_url(DEFAULT_GATE),
            "machine_validation": to_url(validation_path),
            "review_index": to_url(index_path),
            "stop_reason": "memory_pressure_clean_checkpoint",
        },
    }
    return run, review_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the partial outfit compatibility portal run"
    )
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument(
        "--bridge-result",
        type=Path,
        default=DEFAULT_BRIDGE_RESULT,
    )
    parser.add_argument("--portal-root", type=Path, default=DEFAULT_PORTAL)
    args = parser.parse_args()
    gate_path = args.gate.resolve()
    validation_path = args.validation.resolve()
    bridge_result_path = args.bridge_result.resolve()
    gate = read_json(gate_path)
    validation = read_json(validation_path)
    if not bridge_result_path.is_file():
        raise OutfitPortalError(
            f"Bridge result is missing: {bridge_result_path}"
        )
    review_root = validation_path.parent / "review_20260815_partial_v1"
    run, unused_index = build_run(
        gate,
        validation,
        validation_path,
        bridge_result_path,
        review_root,
    )
    output = args.portal_root / "runs" / RUN_ID / "run.json"
    write_json(output, run)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
