"""Create a head-to-body scale comparison sheet from completed CC5 pilots."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKGROUND = (22, 25, 30)
PANEL_BACKGROUND = (29, 33, 39)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def font(size, bold=False):
    candidates = (
        (
            r"C:\Windows\Fonts\segoeuib.ttf"
            if bold
            else r"C:\Windows\Fonts\segoeui.ttf"
        ),
        (
            r"C:\Windows\Fonts\arialbd.ttf"
            if bold
            else r"C:\Windows\Fonts\arial.ttf"
        ),
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def resolved(path):
    return os.path.realpath(os.path.abspath(path))


def discover_results(artifact_roots):
    """Return the newest result for each preset, preferring later roots."""
    discovered = {}
    for root_priority, root in enumerate(artifact_roots):
        if not os.path.isdir(root):
            continue
        for current_root, _directories, filenames in os.walk(root):
            if "result.json" not in filenames:
                continue
            result_path = os.path.join(current_root, "result.json")
            try:
                result = read_json(result_path)
            except (OSError, ValueError):
                continue
            preset_id = result.get("preset_id")
            if not preset_id or result.get("success") is not True:
                continue
            rank = (root_priority, os.path.getmtime(result_path))
            previous = discovered.get(preset_id)
            if previous is None or rank > previous[0]:
                discovered[preset_id] = (rank, result_path, result)
    return {
        preset_id: {"path": item[1], "result": item[2]}
        for preset_id, item in discovered.items()
    }


def pilot_presets(library, bodyfit_prefix):
    prefix = "HBF_{}_".format(bodyfit_prefix.upper())
    presets = [
        preset
        for preset in library.get("presets", [])
        if str(preset.get("preset_id", "")).upper().startswith(prefix)
    ]
    presets.sort(
        key=lambda preset: float(
            preset["head_bodyfit_scale_pilot"]["head_scale_target"]
        )
    )
    if not presets:
        raise RuntimeError("No pilot presets match {}.".format(bodyfit_prefix))
    return presets


def foreground_vertical_bounds(image):
    grayscale = image.convert("L")
    mask = grayscale.point(lambda value: 255 if value >= 70 else 0)
    bounds = mask.getbbox()
    if bounds is None:
        return 0, image.height
    top = max(0, bounds[1])
    bottom = min(image.height, bounds[3])
    if bottom - top < image.height // 3:
        return 0, image.height
    return top, bottom


def normalized_subject(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    top, bottom = foreground_vertical_bounds(image)
    subject_height = max(1, bottom - top)
    target_height = int(size[1] * 0.88)
    scale = target_height / float(subject_height)
    resized = image.resize(
        (
            max(1, int(round(image.width * scale))),
            max(1, int(round(image.height * scale))),
        ),
        Image.Resampling.LANCZOS,
    )
    scaled_top = int(round(top * scale))
    scaled_bottom = int(round(bottom * scale))
    subject_center_x = resized.width // 2
    destination_bottom = size[1] - int(size[1] * 0.035)
    paste_x = size[0] // 2 - subject_center_x
    paste_y = destination_bottom - scaled_bottom
    canvas = Image.new("RGB", size, PANEL_BACKGROUND)
    canvas.paste(resized, (paste_x, paste_y))
    return canvas, {
        "detected_top": top,
        "detected_bottom": bottom,
        "normalization_scale": scale,
        "normalized_top": paste_y + scaled_top,
        "normalized_bottom": paste_y + scaled_bottom,
    }


def upper_body_view(normalized):
    width, height = normalized.size
    crop = (
        int(width * 0.12),
        0,
        int(width * 0.88),
        int(height * 0.56),
    )
    return ImageOps.fit(
        normalized.crop(crop),
        normalized.size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.42),
    )


def scale_label(value):
    if abs(value) < 1e-9:
        return "Head Scale 0.00"
    return "Head Scale {:+.2f}".format(value)


def render_sheet(library_path, artifact_roots, bodyfit_prefix, output_path):
    library = read_json(library_path)
    presets = pilot_presets(library, bodyfit_prefix)
    results = discover_results(artifact_roots)
    missing = [
        preset["preset_id"]
        for preset in presets
        if preset["preset_id"] not in results
    ]
    if missing:
        raise RuntimeError("Missing completed candidates: {}".format(", ".join(missing)))

    zero_preset = min(
        presets,
        key=lambda preset: abs(
            float(preset["head_bodyfit_scale_pilot"]["head_scale_target"])
        ),
    )
    source_result = results[zero_preset["preset_id"]]["result"]
    source_path = source_result["artifacts"]["source_preview"]
    entries = [
        {
            "kind": "matched_source",
            "label": "Matched source reference",
            "path": source_path,
            "preset_id": zero_preset["preset_id"],
            "result_path": results[zero_preset["preset_id"]]["path"],
            "target": None,
        }
    ]
    for preset in presets:
        preset_id = preset["preset_id"]
        target = float(
            preset["head_bodyfit_scale_pilot"]["head_scale_target"]
        )
        result_record = results[preset_id]
        entries.append(
            {
                "kind": "candidate",
                "label": scale_label(target),
                "path": result_record["result"]["artifacts"][
                    "reconstructed_preview"
                ],
                "preset_id": preset_id,
                "result_path": result_record["path"],
                "target": target,
            }
        )

    panel_size = (360, 360)
    column_width = panel_size[0]
    header_height = 108
    column_label_height = 42
    row_label_height = 32
    footer_height = 52
    width = len(entries) * column_width
    height = (
        header_height
        + column_label_height
        + panel_size[1]
        + row_label_height
        + panel_size[1]
        + footer_height
    )
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    bodyfit_id = presets[0].get("bodyfit_id") or bodyfit_prefix
    draw.text(
        (18, 13),
        "{} | head-to-body scale calibration".format(bodyfit_id),
        fill=(241, 243, 246),
        font=font(27, bold=True),
    )
    draw.text(
        (18, 51),
        "Source keeps the template-matched head. Candidates share one random face.",
        fill=(181, 188, 198),
        font=font(16),
    )
    draw.text(
        (18, 76),
        "Character height is normalized for proportion review; compare head size, neck, and shoulders.",
        fill=(181, 188, 198),
        font=font(16),
    )

    records = []
    top_y = header_height + column_label_height
    lower_label_y = top_y + panel_size[1]
    lower_y = lower_label_y + row_label_height
    for index, entry in enumerate(entries):
        x = index * column_width
        normalized, metrics = normalized_subject(entry["path"], panel_size)
        upper_body = upper_body_view(normalized)
        sheet.paste(normalized, (x, top_y))
        sheet.paste(upper_body, (x, lower_y))
        draw.text(
            (x + 12, header_height + 10),
            entry["label"],
            fill=(235, 238, 242),
            font=font(17, bold=True),
        )
        draw.text(
            (x + 12, lower_label_y + 7),
            "Upper-body crop",
            fill=(177, 184, 194),
            font=font(14, bold=True),
        )
        if index:
            draw.line(
                (x, header_height, x, height - footer_height),
                fill=(65, 71, 80),
                width=1,
            )
        records.append(
            {
                "image": entry["path"],
                "kind": entry["kind"],
                "label": entry["label"],
                "normalization": metrics,
                "preset_id": entry["preset_id"],
                "result_path": entry["result_path"],
                "target": entry["target"],
            }
        )

    draw.text(
        (18, height - footer_height + 15),
        "Visual decision status: pending user selection",
        fill=(206, 211, 218),
        font=font(16, bold=True),
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    index_path = os.path.splitext(output_path)[0] + ".json"
    write_json(
        {
            "artifact_roots": artifact_roots,
            "bodyfit_id": bodyfit_id,
            "contact_sheet": output_path,
            "entries": records,
            "library_file": library_path,
            "schema_version": 1,
            "visual_review_status": "pending",
        },
        index_path,
    )
    return index_path


def main():
    parser = argparse.ArgumentParser(
        description="Create a CC5 head-to-body scale comparison sheet."
    )
    parser.add_argument("--library-file", required=True)
    parser.add_argument("--artifact-root", action="append", required=True)
    parser.add_argument("--bodyfit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    library_path = resolved(args.library_file)
    artifact_roots = [resolved(path) for path in args.artifact_root]
    output_path = resolved(args.output)
    index_path = render_sheet(
        library_path,
        artifact_roots,
        args.bodyfit,
        output_path,
    )
    print("Created head-bodyfit contact sheet -> {}".format(output_path))
    print("Review index -> {}".format(index_path))


if __name__ == "__main__":
    main()
