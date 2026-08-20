from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat


CORE_IMAGES = (
    ("reconstructed_preview.png", "Full body"),
    ("face_front.png", "Face front"),
    ("face_three_quarter.png", "Face 3/4"),
    ("face_profile.png", "Face profile"),
    ("hair_rear_three_quarter.png", "Hair rear 3/4"),
    ("hair_rear.png", "Hair rear"),
)

DYNAMIC_IMAGES = (
    ("face_front.png", "Neutral"),
    ("face_blink_bilateral_front.png", "Blink"),
    ("face_look_left_front.png", "Look left"),
    ("face_look_right_front.png", "Look right"),
    ("face_squint_front.png", "Squint"),
    ("face_widen_front.png", "Widen"),
    ("face_smile_front.png", "Smile"),
    ("face_jaw_open_front.png", "Jaw open"),
    ("face_post_pose_neutral_front.png", "Restored neutral"),
)

REQUIRED_RESULT_FLAGS = (
    "source_matches_library",
    "reconstruction_matches_library",
    "appearance_matches_recipe",
    "morphs_unchanged_after_appearance",
    "face_matches_recipe",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a compact visual review package for the ten-character CC showcase."
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hardlink_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size == source.stat().st_size:
            return "existing"
        destination.unlink()
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf") if bold else Path("C:/Windows/Fonts/segoeui.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def inspect_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        rgb = image.convert("RGB")
        grayscale = rgb.convert("L")
        stddev = float(ImageStat.Stat(grayscale).stddev[0])
        width, height = rgb.size
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "grayscale_stddev": round(stddev, 4),
        "nonblank": stddev >= 2.0,
    }


def paste_contained(
    canvas: Image.Image,
    source_path: Path,
    box: tuple[int, int, int, int],
    background: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    target_size = (right - left, bottom - top)
    with Image.open(source_path) as source:
        contained = ImageOps.contain(source.convert("RGB"), target_size, Image.Resampling.LANCZOS)
    x = left + (target_size[0] - contained.width) // 2
    y = top + (target_size[1] - contained.height) // 2
    ImageDraw.Draw(canvas).rectangle(box, fill=background)
    canvas.paste(contained, (x, y))


def make_character_sheet(
    character_id: str,
    bodyfit_id: str,
    source_dir: Path,
    destination: Path,
    evidence_mode: str,
) -> None:
    canvas = Image.new("RGB", (1536, 1120), (238, 240, 243))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34, bold=True)
    label_font = load_font(22, bold=True)
    meta_font = load_font(20)
    draw.text((32, 24), character_id, fill=(24, 28, 34), font=title_font)
    draw.text(
        (32, 70),
        f"BodyFit: {bodyfit_id} | Evidence: {evidence_mode} | Source: 1024 x 1024",
        fill=(78, 85, 95),
        font=meta_font,
    )
    cell_width = 496
    cell_height = 485
    image_height = 430
    for index, (filename, label) in enumerate(CORE_IMAGES):
        row, column = divmod(index, 3)
        left = 16 + column * 512
        top = 115 + row * 495
        paste_contained(
            canvas,
            source_dir / filename,
            (left, top, left + cell_width, top + image_height),
            (20, 23, 29),
        )
        draw.text((left + 8, top + image_height + 9), label, fill=(34, 39, 47), font=label_font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)


def make_pose_sheet(
    character_id: str,
    source_dir: Path,
    destination: Path,
) -> None:
    canvas = Image.new("RGB", (1536, 1610), (238, 240, 243))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34, bold=True)
    label_font = load_font(22, bold=True)
    meta_font = load_font(20)
    draw.text((32, 24), f"{character_id}: Dynamic pose evidence", fill=(24, 28, 34), font=title_font)
    draw.text(
        (32, 70),
        "Neutral, bilateral blink, gaze, eyelids, mouth, and restored neutral",
        fill=(78, 85, 95),
        font=meta_font,
    )
    cell_width = 496
    image_height = 430
    for index, (filename, label) in enumerate(DYNAMIC_IMAGES):
        row, column = divmod(index, 3)
        left = 16 + column * 512
        top = 115 + row * 495
        paste_contained(
            canvas,
            source_dir / filename,
            (left, top, left + cell_width, top + image_height),
            (20, 23, 29),
        )
        draw.text((left + 8, top + image_height + 9), label, fill=(34, 39, 47), font=label_font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)


def make_overview(
    characters: list[dict[str, Any]],
    image_name: str,
    destination: Path,
    title: str,
) -> None:
    columns = 5
    rows = 2
    canvas = Image.new("RGB", (1800, 1500), (238, 240, 243))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(36, bold=True)
    label_font = load_font(21, bold=True)
    meta_font = load_font(18)
    draw.text((34, 28), title, fill=(24, 28, 34), font=title_font)
    draw.text(
        (34, 78),
        "Ten unique Character Creator 5 assemblies | Review source images: 1024 x 1024",
        fill=(78, 85, 95),
        font=meta_font,
    )
    cell_width = 344
    cell_height = 650
    image_height = 570
    for index, character in enumerate(characters):
        row, column = divmod(index, columns)
        left = 20 + column * 356
        top = 130 + row * 675
        source = Path(character["selected_result_dir"]) / image_name
        paste_contained(
            canvas,
            source,
            (left, top, left + cell_width, top + image_height),
            (20, 23, 29),
        )
        draw.text(
            (left + 4, top + image_height + 9),
            character["short_label"],
            fill=(32, 37, 45),
            font=label_font,
        )
        draw.text(
            (left + 4, top + image_height + 39),
            character["evidence_mode"],
            fill=(88, 95, 104),
            font=meta_font,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)


def discover_successful_results(
    artifact_root: Path,
    expected_ids: set[str],
    excluded_root: Path,
) -> dict[str, tuple[Path, dict[str, Any]]]:
    candidates: dict[str, list[tuple[Path, dict[str, Any]]]] = {
        character_id: [] for character_id in expected_ids
    }
    for path in artifact_root.rglob("result.json"):
        if path.is_relative_to(excluded_root):
            continue
        try:
            result = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        character_id = result.get("preset_id")
        if result.get("success") is True and character_id in candidates:
            candidates[character_id].append((path, result))
    selected: dict[str, tuple[Path, dict[str, Any]]] = {}
    missing: list[str] = []
    for character_id, values in candidates.items():
        if not values:
            missing.append(character_id)
            continue
        values.sort(key=lambda item: item[0].stat().st_mtime_ns)
        selected[character_id] = values[-1]
    if missing:
        raise RuntimeError(f"Missing successful results: {', '.join(sorted(missing))}")
    return selected


def result_evidence_mode(result: dict[str, Any]) -> str:
    validation = result.get("facial_pose_validation")
    if not isinstance(validation, dict):
        return "static six-view"
    liveness = validation.get("evidence_liveness")
    if isinstance(liveness, dict) and liveness.get("status") == "passed":
        return "dynamic pose passed"
    return "static six-view"


def validate_and_gather(
    artifact_root: Path,
    output_dir: Path,
    presets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    expected_ids = {str(item["preset_id"]) for item in presets}
    selected = discover_successful_results(artifact_root, expected_ids, output_dir)
    characters: list[dict[str, Any]] = []
    for preset in presets:
        character_id = str(preset["preset_id"])
        result_path, result = selected[character_id]
        result_dir = result_path.parent
        failed_flags = [name for name in REQUIRED_RESULT_FLAGS if result.get(name) is not True]
        if failed_flags:
            raise RuntimeError(f"{character_id}: failed result flags: {failed_flags}")

        project_record = result.get("character_project")
        if not isinstance(project_record, dict):
            raise RuntimeError(f"{character_id}: character_project record missing")
        project_path = Path(str(project_record.get("path", "")))
        if not project_path.is_file() or project_path.stat().st_size < 1024 * 1024:
            raise RuntimeError(f"{character_id}: invalid project: {project_path}")
        project_hash = sha256_file(project_path)
        if project_hash != project_record.get("sha256"):
            raise RuntimeError(f"{character_id}: project SHA-256 mismatch")

        image_records: dict[str, dict[str, Any]] = {}
        for source_image in sorted(result_dir.glob("*.png")):
            record = inspect_image(source_image)
            if record["width"] != 1024 or record["height"] != 1024 or not record["nonblank"]:
                raise RuntimeError(f"{character_id}: invalid image: {source_image.name}: {record}")
            image_records[source_image.name] = record
        for filename, _ in CORE_IMAGES:
            if filename not in image_records:
                raise RuntimeError(f"{character_id}: required image missing: {filename}")

        character_dir = output_dir / "characters" / character_id
        image_dir = character_dir / "images"
        link_modes: set[str] = set()
        for source_image in sorted(result_dir.glob("*.png")):
            link_modes.add(hardlink_or_copy(source_image, image_dir / source_image.name))
        project_destination = output_dir / "projects" / f"{character_id}.ccProject"
        link_modes.add(hardlink_or_copy(project_path, project_destination))
        link_modes.add(hardlink_or_copy(result_path, character_dir / "result.json"))

        evidence_mode = result_evidence_mode(result)
        review_sheet = character_dir / "review_sheet.png"
        make_character_sheet(
            character_id,
            str(preset.get("bodyfit_id", "unknown")),
            result_dir,
            review_sheet,
            evidence_mode,
        )
        pose_sheet: Path | None = None
        if evidence_mode == "dynamic pose passed":
            missing_dynamic = [name for name, _ in DYNAMIC_IMAGES if name not in image_records]
            if missing_dynamic:
                raise RuntimeError(f"{character_id}: dynamic pose images missing: {missing_dynamic}")
            pose_sheet = character_dir / "pose_sheet.png"
            make_pose_sheet(character_id, result_dir, pose_sheet)
        short_label = str(preset.get("bodyfit_id", character_id))
        character = {
            "character_id": character_id,
            "short_label": short_label,
            "sex": preset.get("sex"),
            "bodyfit_id": preset.get("bodyfit_id"),
            "body_class": preset.get("body_class"),
            "age_label": preset.get("age_label"),
            "face_recipe_id": preset.get("face_recipe_id"),
            "appearance_recipe_id": preset.get("appearance_recipe_id"),
            "scalp_hair_display_name": preset.get("scalp_hair_display_name"),
            "evidence_mode": evidence_mode,
            "selected_result": str(result_path),
            "selected_result_dir": str(result_dir),
            "image_count": len(image_records),
            "images": image_records,
            "project": {
                "source_path": str(project_path),
                "review_path": str(project_destination),
                "bytes": project_path.stat().st_size,
                "sha256": project_hash,
            },
            "review_sheet": str(review_sheet),
            "pose_sheet": str(pose_sheet) if pose_sheet else None,
            "gather_modes": sorted(link_modes),
            "result_flags": {name: result.get(name) for name in REQUIRED_RESULT_FLAGS},
        }
        characters.append(character)
    return characters


def build_html(characters: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for character in characters:
        character_id = html.escape(character["character_id"])
        project_name = f"{character_id}.ccProject"
        pose_link = (
            f' · <a href="characters/{character_id}/pose_sheet.png">Pose sheet</a>'
            if character["pose_sheet"]
            else ""
        )
        rows.append(
            f"""
            <article class="card">
              <a href="characters/{character_id}/review_sheet.png">
                <img src="characters/{character_id}/review_sheet.png" alt="{character_id} review sheet">
              </a>
              <div class="body">
                <h2>{html.escape(character['short_label'])}</h2>
                <p>{character_id}</p>
                <p>{html.escape(character['evidence_mode'])} | {character['image_count']} source images</p>
                <p><a href="projects/{project_name}">Open CC project</a> ·
                   <a href="characters/{character_id}/index.html">All screenshots</a>{pose_link}</p>
              </div>
            </article>
            """
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CC5 Ten Character Showcase Review</title>
  <style>
    :root {{ color-scheme: light; font-family: "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #eef0f3; color: #1c2026; }}
    header {{ padding: 28px 32px 18px; background: #fff; border-bottom: 1px solid #cfd4da; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    header p, .body p {{ margin: 6px 0; color: #555d68; }}
    .overview {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 20px 24px 0; }}
    .overview img {{ display: block; width: 100%; background: #15181d; border: 1px solid #c4c9d0; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; padding: 20px 24px 36px; }}
    .card {{ background: #fff; border: 1px solid #cfd4da; border-radius: 6px; overflow: hidden; }}
    .card img {{ display: block; width: 100%; background: #171a20; }}
    .body {{ padding: 14px 16px 17px; }}
    h2 {{ margin: 0 0 6px; font-size: 20px; letter-spacing: 0; }}
    a {{ color: #1261a0; }}
    @media (max-width: 900px) {{ .overview {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Character Creator 5: Ten Character Showcase</h1>
    <p>10 projects, one character per BodyFit, 1024 × 1024 source screenshots.</p>
    <p>Click a review sheet for full resolution. Project files are NTFS hardlinks to the validated originals.</p>
  </header>
  <section class="overview">
    <a href="overview_full_body.png"><img src="overview_full_body.png" alt="Full body overview"></a>
    <a href="overview_face_front.png"><img src="overview_face_front.png" alt="Face overview"></a>
  </section>
  <main>{''.join(rows)}</main>
</body>
</html>
"""


def build_character_html(character: dict[str, Any]) -> str:
    character_id = html.escape(character["character_id"])
    pose_link = (
        '<a href="pose_sheet.png">Open dynamic pose sheet</a> · '
        if character["pose_sheet"]
        else ""
    )
    figures: list[str] = []
    for filename in sorted(character["images"]):
        escaped_name = html.escape(filename)
        figures.append(
            f'<figure><a href="images/{escaped_name}"><img src="images/{escaped_name}" '
            f'alt="{escaped_name}"></a><figcaption>{escaped_name}</figcaption></figure>'
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{character_id} screenshots</title>
  <style>
    body {{ margin: 0; background: #eef0f3; color: #1c2026; font-family: "Segoe UI", sans-serif; }}
    header {{ padding: 24px 28px; background: #fff; border-bottom: 1px solid #cfd4da; }}
    h1 {{ margin: 0 0 8px; font-size: 27px; letter-spacing: 0; }}
    p {{ margin: 5px 0; color: #555d68; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; padding: 20px; }}
    figure {{ margin: 0; background: #fff; border: 1px solid #cfd4da; border-radius: 6px; overflow: hidden; }}
    img {{ display: block; width: 100%; background: #171a20; }}
    figcaption {{ padding: 10px 12px; font-size: 14px; overflow-wrap: anywhere; }}
    a {{ color: #1261a0; }}
  </style>
</head>
<body>
  <header>
    <h1>{character_id}</h1>
    <p>{html.escape(character['bodyfit_id'])} | {html.escape(character['evidence_mode'])} | {character['image_count']} screenshots</p>
    <p><a href="../../index.html">Back to overview</a> · {pose_link}<a href="../../projects/{character_id}.ccProject">Open CC project</a></p>
  </header>
  <main>{''.join(figures)}</main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    manifest_path = args.manifest.resolve()
    output_dir = args.output.resolve()
    if not artifact_root.is_dir():
        raise FileNotFoundError(artifact_root)
    manifest = read_json(manifest_path)
    presets = manifest.get("presets")
    if not isinstance(presets, list) or len(presets) != 10:
        raise RuntimeError("Manifest must contain exactly ten presets")
    output_dir.mkdir(parents=True, exist_ok=True)
    characters = validate_and_gather(artifact_root, output_dir, presets)

    for character in characters:
        character_index = output_dir / "characters" / character["character_id"] / "index.html"
        character_index.write_text(build_character_html(character), encoding="utf-8", newline="\n")

    full_body_hashes = {item["images"]["reconstructed_preview.png"]["sha256"] for item in characters}
    face_hashes = {item["images"]["face_front.png"]["sha256"] for item in characters}
    if len(full_body_hashes) != 10:
        raise RuntimeError("Full-body screenshots are not unique across all ten characters")
    if len(face_hashes) != 10:
        raise RuntimeError("Face-front screenshots are not unique across all ten characters")

    make_overview(
        characters,
        "reconstructed_preview.png",
        output_dir / "overview_full_body.png",
        "Ten BodyFits: Full-body Review",
    )
    make_overview(
        characters,
        "face_front.png",
        output_dir / "overview_face_front.png",
        "Ten Characters: Face-front Review",
    )
    (output_dir / "index.html").write_text(build_html(characters), encoding="utf-8", newline="\n")

    summary = {
        "schema_version": 1,
        "status": "passed",
        "artifact_root": str(artifact_root),
        "manifest": str(manifest_path),
        "review_root": str(output_dir),
        "character_count": len(characters),
        "project_count": len(characters),
        "source_resolution": [1024, 1024],
        "unique_full_body_count": len(full_body_hashes),
        "unique_face_front_count": len(face_hashes),
        "dynamic_pose_passed_count": sum(
            item["evidence_mode"] == "dynamic pose passed" for item in characters
        ),
        "static_six_view_count": sum(
            item["evidence_mode"] == "static six-view" for item in characters
        ),
        "characters": characters,
    }
    write_json(output_dir / "showcase_summary.json", summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "review_root": summary["review_root"],
                "character_count": summary["character_count"],
                "project_count": summary["project_count"],
                "dynamic_pose_passed_count": summary["dynamic_pose_passed_count"],
                "static_six_view_count": summary["static_six_view_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
