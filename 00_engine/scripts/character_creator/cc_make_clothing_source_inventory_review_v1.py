"""Render package cards and review sheets for a clothing source inventory."""

from __future__ import annotations

import argparse
import json
import os
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError


SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_INVENTORY = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_source_inventory"
    / "inventory_20260811_v1"
    / "inventory.json"
)
DEFAULT_OUTPUT = DEFAULT_INVENTORY.parent / "review"

CARD_SIZE = (1000, 720)
SHEET_COLUMNS = 3
SHEET_ROWS = 2


class ReviewError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidates = (
        windows / ("msyhbd.ttc" if bold else "msyh.ttc"),
        windows / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windows / ("arialbd.ttf" if bold else "arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    selected_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
    line_spacing: int = 7,
) -> int:
    words = text.replace("\\", "/").split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if draw.textlength(candidate, font=selected_font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        while draw.textlength(current, font=selected_font) > max_width:
            cut = max(1, int(len(current) * max_width / draw.textlength(current, font=selected_font)))
            while cut > 1 and draw.textlength(current[:cut], font=selected_font) > max_width:
                cut -= 1
            lines.append(current[:cut])
            current = current[cut:]
    if current:
        lines.append(current)
    lines = lines[:max_lines]
    if len(lines) == max_lines and " ".join(lines) != text:
        while lines[-1] and draw.textlength(lines[-1] + "...", font=selected_font) > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."
    x, y = xy
    bbox = draw.textbbox((0, 0), "Ag", font=selected_font)
    line_height = bbox[3] - bbox[1] + line_spacing
    for line in lines:
        draw.text((x, y), line, fill=fill, font=selected_font)
        y += line_height
    return y


def safe_preview(path_value: str | None, size: tuple[int, int]) -> Image.Image | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file() or path.stat().st_size <= 0:
        return None
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        return ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    except (OSError, ValueError, UnidentifiedImageError):
        return None


def status_color(package: dict[str, Any]) -> tuple[int, int, int]:
    if package.get("payload_gate") == "all_wearables_suspected_placeholders":
        return (221, 92, 92)
    content_class = package["content_class"]
    if content_class == "clothing_only":
        return (101, 204, 142)
    if content_class == "clothing_with_character":
        return (242, 187, 88)
    if content_class in {"character_only", "accessory_only"}:
        return (232, 143, 94)
    return (164, 174, 188)


def render_card(package: dict[str, Any], output: Path) -> None:
    canvas = Image.new("RGB", CARD_SIZE, (17, 20, 25))
    draw = ImageDraw.Draw(canvas)
    accent = status_color(package)
    draw.rectangle((0, 0, CARD_SIZE[0], 11), fill=accent)

    title_font = font(29, True)
    body_font = font(18)
    body_bold = font(18, True)
    small_font = font(15)
    draw_wrapped_text(
        draw,
        (28, 30),
        package["label"],
        fill=(242, 244, 247),
        selected_font=title_font,
        max_width=944,
        max_lines=2,
        line_spacing=5,
    )

    preview_box = (28, 118, 514, 570)
    draw.rounded_rectangle(preview_box, radius=7, fill=(27, 31, 38), outline=(59, 66, 78))
    preview = safe_preview(
        package.get("preview_paths", [None])[0]
        if package.get("preview_paths")
        else None,
        (preview_box[2] - preview_box[0] - 20, preview_box[3] - preview_box[1] - 20),
    )
    if preview:
        x = preview_box[0] + (preview_box[2] - preview_box[0] - preview.width) // 2
        y = preview_box[1] + (preview_box[3] - preview_box[1] - preview.height) // 2
        canvas.paste(preview, (x, y))
    else:
        draw.text(
            (preview_box[0] + 48, preview_box[1] + 185),
            "No embedded preview",
            fill=(150, 159, 171),
            font=font(24, True),
        )
        draw.text(
            (preview_box[0] + 61, preview_box[1] + 226),
            "CC visual inspection required",
            fill=(105, 115, 128),
            font=font(17),
        )

    x = 544
    y = 120
    rows = (
        ("Sex label", package["sex_label"]),
        ("Source", package["source_type"]),
        ("Content", package["content_class"]),
        ("Wearables", str(package["wearable_count"])),
        ("Payload", package.get("payload_gate", "not_scanned")),
        ("Slots", ", ".join(package["slots"]) or "unresolved"),
        ("Modularity", package["modularity_hint"]),
        ("Policy hint", package["look_policy_hint"]),
        ("Style tags", ", ".join(package["style_tags"]) or "unclassified"),
    )
    for key, value in rows:
        draw.text((x, y), key, fill=(153, 169, 191), font=body_bold)
        y = draw_wrapped_text(
            draw,
            (x + 145, y),
            value,
            fill=(231, 234, 239),
            selected_font=body_font,
            max_width=286,
            max_lines=2,
            line_spacing=3,
        )
        y += 8

    category_text = ", ".join(
        f"{key}:{value}" for key, value in package["category_counts"].items()
    )
    draw.text((28, 594), "Counts", fill=(153, 169, 191), font=body_bold)
    draw_wrapped_text(
        draw,
        (112, 594),
        category_text or "none",
        fill=(220, 224, 231),
        selected_font=small_font,
        max_width=850,
        max_lines=2,
        line_spacing=3,
    )
    draw.text((28, 654), package["package_id"], fill=accent, font=small_font)
    draw_wrapped_text(
        draw,
        (300, 654),
        package["relative_path"],
        fill=(125, 135, 149),
        selected_font=small_font,
        max_width=670,
        max_lines=2,
        line_spacing=2,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def render_sheet(
    title: str,
    card_paths: list[Path],
    output: Path,
) -> None:
    cell_size = (500, 360)
    title_height = 64
    canvas = Image.new(
        "RGB",
        (SHEET_COLUMNS * cell_size[0], title_height + SHEET_ROWS * cell_size[1]),
        (17, 20, 25),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((22, 16), title, fill=(242, 244, 247), font=font(25, True))
    for index, card_path in enumerate(card_paths):
        with Image.open(card_path) as source:
            card = source.convert("RGB").resize(cell_size, Image.Resampling.LANCZOS)
        x = (index % SHEET_COLUMNS) * cell_size[0]
        y = title_height + (index // SHEET_COLUMNS) * cell_size[1]
        canvas.paste(card, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def group_id(package: dict[str, Any]) -> str:
    source = "archives" if package["source_type"] == "zip" else "loose"
    return f"{package['sex_label']}_{source}"


def build_review(inventory_path: Path, output_dir: Path) -> dict[str, Any]:
    inventory_path = inventory_path.resolve()
    output_dir = output_dir.resolve()
    inventory = read_json(inventory_path)
    if inventory.get("schema_version") != 1:
        raise ReviewError("Unsupported inventory schema")
    packages = inventory.get("packages") or []
    if not packages:
        raise ReviewError("Inventory does not contain packages")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for package in packages:
        grouped.setdefault(group_id(package), []).append(package)

    review_groups = []
    page_capacity = SHEET_COLUMNS * SHEET_ROWS
    for identifier in ("female_archives", "female_loose", "male_archives", "male_loose"):
        group_packages = grouped.get(identifier, [])
        if not group_packages:
            continue
        cases = []
        card_paths: list[Path] = []
        for package in group_packages:
            card_path = output_dir / "cards" / identifier / f"{package['package_id']}.png"
            render_card(package, card_path)
            card_paths.append(card_path)
            cases.append(
                {
                    "package_id": package["package_id"],
                    "label": package["label"],
                    "sex_label": package["sex_label"],
                    "source_type": package["source_type"],
                    "content_class": package["content_class"],
                    "clothing_candidate": package["clothing_candidate"],
                    "wearable_count": package["wearable_count"],
                    "slots": package["slots"],
                    "style_tags": package["style_tags"],
                    "modularity_hint": package["modularity_hint"],
                    "look_policy_hint": package["look_policy_hint"],
                    "relative_path": package["relative_path"],
                    "source_path": package["source_path"],
                    "card": str(card_path.resolve()),
                    "preview_count": len(package.get("preview_paths") or []),
                }
            )
        pages: dict[str, str] = {}
        for page_index, start in enumerate(range(0, len(card_paths), page_capacity), start=1):
            page_path = output_dir / "sheets" / identifier / f"page_{page_index:03d}.png"
            render_sheet(
                f"{identifier.replace('_', ' ').title()} - page {page_index}",
                card_paths[start : start + page_capacity],
                page_path,
            )
            pages[f"page_{page_index:03d}"] = str(page_path.resolve())
        review_groups.append(
            {
                "group_id": identifier,
                "label": identifier.replace("_", " ").title(),
                "package_count": len(cases),
                "clothing_candidate_count": sum(
                    case["clothing_candidate"] for case in cases
                ),
                "overview": next(iter(pages.values())),
                "pages": pages,
                "cases": cases,
            }
        )

    summary = inventory["summary"]
    review = {
        "schema_version": 1,
        "review_id": "cc_clothing_source_inventory_review_20260811_v1",
        "status": "source_inventory_complete_package_review_pending",
        "inventory": str(inventory_path),
        "package_count": summary["package_count"],
        "clothing_candidate_count": summary["clothing_candidate_count"],
        "non_clothing_package_count": summary["non_clothing_package_count"],
        "wearable_count": summary["wearable_count"],
        "preview_count": summary["preview_count"],
        "duplicate_archive_group_count": len(
            inventory.get("duplicate_archive_groups") or []
        ),
        "groups": review_groups,
    }
    write_json_atomic(output_dir / "index.json", review)
    readme = "\n".join(
        (
            "# CC Clothing Source Inventory Review",
            "",
            "This review is a source-discovery gate, not a production approval.",
            "",
            f"- Packages: `{review['package_count']}`",
            f"- Clothing candidates: `{review['clothing_candidate_count']}`",
            f"- Non-clothing or unresolved packages: `{review['non_clothing_package_count']}`",
            f"- Wearable asset entries: `{review['wearable_count']}`",
            f"- Copied preview images: `{review['preview_count']}`",
            f"- Exact duplicate archive groups: `{review['duplicate_archive_group_count']}`",
            "",
            "## Interpretation",
            "",
            "- `sex_label` comes from the user-provided root and is not a fit test.",
            "- `clothing_with_character` contains clothing plus a character/project asset.",
            "- `locked_look_first` means the first CC test should preserve the authored outfit.",
            "- `constrained_modular_candidate` still requires layer, collision, pose, and BodyFit gates.",
            "- A missing preview does not reject a package; it means CC must provide the visual evidence.",
            "",
        )
    )
    write_text_atomic(output_dir / "README.md", readme)
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render clothing source inventory review")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review = build_review(args.inventory, args.output_dir)
    print((args.output_dir.resolve() / "index.json"))
    print(
        "packages={} clothing_candidates={} previews={}".format(
            review["package_count"],
            review["clothing_candidate_count"],
            review["preview_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
