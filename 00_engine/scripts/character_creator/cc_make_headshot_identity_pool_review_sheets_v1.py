"""Build visual-review sheets for the ten-prototype Headshot identity pool."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = SCRIPT_ROOT / "cc_headshot_face_prototype_registry_v1.json"
DEFAULT_VALIDATION = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "headshot_face_prototype_registry_validation_20260810_v4.json"
)
DEFAULT_OUTPUT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "headshot_identity_pool_10"
    / "review_20260810_v2"
)
VIEW_FILES = {
    "neutral_front": "post_pose_neutral_front.png",
    "neutral_three_quarter": "neutral_three_quarter.png",
    "blink_bilateral": "blink_bilateral_front.png",
    "smile_subtle": "smile_subtle_front.png",
    "smile_medium": "smile_medium_front.png",
    "smile_broad": "smile_broad_front.png",
    "jaw_open": "jaw_open_front.png",
}


class ReviewError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def font(size: int, bold: bool = False):
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidates = (
        windows / ("arialbd.ttf" if bold else "arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ReviewError("Missing review image: {}".format(path))
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    contained = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (18, 21, 26))
    canvas.paste(
        contained,
        ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2),
    )
    return canvas


def render_comparison(
    title: str,
    records: list[dict[str, Any]],
    image_key: str,
    output: Path,
) -> None:
    cell = (460, 460)
    label_height = 82
    title_height = 72
    width = len(records) * cell[0]
    height = title_height + cell[1] + label_height
    sheet = Image.new("RGB", (width, height), (18, 21, 26))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 17), title, fill=(242, 244, 247), font=font(27, True))
    for column, record in enumerate(records):
        x = column * cell[0]
        y = title_height
        sheet.paste(fit_image(Path(record["views"][image_key]), cell), (x, y))
        mapped = record["source_reference_mapped"]
        status = "mapped" if mapped else "source mapping pending"
        draw.rectangle(
            (x, y + cell[1], x + cell[0], y + cell[1] + label_height),
            fill=(29, 33, 40),
        )
        draw.text(
            (x + 14, y + cell[1] + 10),
            record["prototype_id"],
            fill=(238, 241, 245),
            font=font(20, True),
        )
        draw.text(
            (x + 14, y + cell[1] + 42),
            status,
            fill=(126, 211, 144) if mapped else (244, 190, 93),
            font=font(16),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", optimize=True)


def render_source_identity_comparison(
    title: str,
    records: list[dict[str, Any]],
    output: Path,
) -> None:
    cell = (430, 430)
    column_width = 460
    title_height = 70
    row_label_height = 42
    footer_height = 62
    width = len(records) * column_width
    height = title_height + (cell[1] + row_label_height) * 2 + footer_height
    sheet = Image.new("RGB", (width, height), (18, 21, 26))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 16), title, fill=(242, 244, 247), font=font(27, True))
    for column, record in enumerate(records):
        x = column * column_width + (column_width - cell[0]) // 2
        source_y = title_height + row_label_height
        generated_y = source_y + cell[1] + row_label_height
        draw.text(
            (x + 8, title_height + 8),
            "Source photograph",
            fill=(170, 199, 235),
            font=font(17, True),
        )
        sheet.paste(fit_image(Path(record["source_reference"]), cell), (x, source_y))
        draw.text(
            (x + 8, source_y + cell[1] + 8),
            "Headshot neutral",
            fill=(170, 199, 235),
            font=font(17, True),
        )
        sheet.paste(
            fit_image(Path(record["views"]["neutral_front"]), cell),
            (x, generated_y),
        )
        footer_y = generated_y + cell[1]
        draw.rectangle(
            (column * column_width, footer_y, (column + 1) * column_width, height),
            fill=(29, 33, 40),
        )
        draw.text(
            (column * column_width + 16, footer_y + 15),
            record["prototype_id"]
            + (
                " - accepted"
                if record["visual_status"] == "passed"
                else " - pending user acceptance"
            ),
            fill=(244, 190, 93)
            if record["visual_status"] != "passed"
            else (126, 211, 144),
            font=font(17, True),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", optimize=True)


def build_review(
    registry_path: Path,
    validation_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    registry_path = registry_path.resolve()
    validation_path = validation_path.resolve()
    output_dir = output_dir.resolve()
    registry = read_json(registry_path)
    validation = read_json(validation_path)
    if validation.get("success") is not True:
        raise ReviewError("Prototype registry validation did not pass")
    if int(validation.get("prototype_count", -1)) != 10:
        raise ReviewError("Review requires exactly ten prototypes")
    if int(validation.get("production_enabled_count", -1)) != 0:
        raise ReviewError("Headshot production selection must remain disabled")

    validation_by_id = {
        item["prototype_id"]: item for item in validation["prototypes"]
    }
    records: list[dict[str, Any]] = []
    for registry_record in registry.get("prototypes") or []:
        prototype_id = registry_record["prototype_id"]
        manifest_path = Path(registry_record["manifest"]["path"]).resolve()
        manifest = read_json(manifest_path)
        evidence_dir = manifest_path.parent / "evidence"
        views = {
            view: str((evidence_dir / filename).resolve())
            for view, filename in VIEW_FILES.items()
        }
        for view, path in views.items():
            if not Path(path).is_file():
                raise ReviewError("{} is missing {}".format(prototype_id, view))
        verified = validation_by_id.get(prototype_id)
        if not verified:
            raise ReviewError("Validation omits {}".format(prototype_id))
        source_record = (manifest.get("canonical_assets") or {}).get(
            "source_reference"
        )
        record = {
            "prototype_id": prototype_id,
            "sex": registry_record["sex"],
            "status": registry_record["status"],
            "visual_status": verified["visual_status"],
            "source_reference_mapped": verified["source_reference_mapped"],
            "source_reference_status": verified["source_reference_status"],
            "source_reference": source_record["path"] if source_record else None,
            "views": views,
            "manifest": str(manifest_path),
        }
        if not record["source_reference_mapped"] and record["visual_status"] == "passed":
            raise ReviewError("Unmapped source was incorrectly accepted")
        records.append(record)

    groups = []
    for sex in ("female", "male"):
        cases = sorted(
            (record for record in records if record["sex"] == sex),
            key=lambda record: record["prototype_id"],
        )
        if len(cases) != 5:
            raise ReviewError("{} group does not contain five cases".format(sex))
        if any(not case["source_reference"] for case in cases):
            raise ReviewError("{} group still has an unmapped source".format(sex))
        sheets = {}
        source_match = output_dir / sex / "source_identity_match.png"
        render_source_identity_comparison(
            "{} Headshot identity pool - Source Match".format(sex.title()),
            cases,
            source_match,
        )
        sheets["source_identity_match"] = str(source_match)
        for view in VIEW_FILES:
            path = output_dir / sex / (view + "_comparison.png")
            render_comparison(
                "{} Headshot identity pool - {}".format(
                    sex.title(), view.replace("_", " ").title()
                ),
                cases,
                view,
                path,
            )
            sheets[view] = str(path)
        groups.append(
            {
                "sex": sex,
                "overview": sheets["source_identity_match"],
                "comparisons": sheets,
                "cases": cases,
            }
        )

    mapped_count = sum(record["source_reference_mapped"] for record in records)
    accepted_count = sum(record["visual_status"] == "passed" for record in records)
    index = {
        "schema_version": 1,
        "review_id": "headshot_identity_pool_10_review_20260810_v2",
        "status": "all_sources_mapped_user_visual_review_pending",
        "prototype_count": len(records),
        "female_count": 5,
        "male_count": 5,
        "machine_passed_count": 10,
        "source_reference_mapped_count": mapped_count,
        "source_reference_pending_count": len(records) - mapped_count,
        "visual_accepted_count": accepted_count,
        "visual_pending_count": len(records) - accepted_count,
        "production_enabled_count": 0,
        "registry": str(registry_path),
        "machine_validation": str(validation_path),
        "groups": groups,
    }
    index_path = output_dir / "index.json"
    write_json(index_path, index)
    write_text(
        output_dir / "README.md",
        "# Headshot Identity Pool 10 Review\n\n"
        "All ten source photographs are now hash-locked and mapped. Review female "
        "and male candidates separately. Start with Source Match, then compare neutral identity, "
        "three-quarter silhouette, bilateral blink, three smile strengths, and jaw "
        "opening. F_HS_001/002 and M_HS_001/002 were previously accepted. The six "
        "new candidates passed machine gates and source mapping, but still require "
        "explicit user visual acceptance. Production "
        "selection remains disabled.\n",
    )
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build_review(args.registry, args.validation, args.output)
    except (OSError, ValueError, KeyError, ReviewError) as exc:
        print("ERROR: {}".format(exc))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
