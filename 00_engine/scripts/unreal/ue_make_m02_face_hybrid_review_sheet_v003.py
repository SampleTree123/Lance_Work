#!/usr/bin/env python3
"""Build a labeled contact sheet for the M02 v003 hybrid-face PIE review."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


OUTPUT_DIR = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_face_hybrid_review_v003"
)
REPORT_PATH = OUTPUT_DIR / "pie_review.json"
SHEET_PATH = OUTPUT_DIR / "m02_face_hybrid_pie_contact_sheet.png"
BODY_ORDER = ("audience", "walk_wander")
STATE_ORDER = (
    "neutral_front",
    "blink_front",
    "jaw_front",
    "jaw_three_quarter",
    "gaze_opposite_front",
)
TILE_SIZE = (520, 293)
LABEL_HEIGHT = 66
MARGIN = 28
GAP = 14
HEADER_HEIGHT = 78


def load_font(path, size):
    candidate = Path(path)
    if candidate.is_file():
        return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


title_font = load_font(r"C:\Windows\Fonts\arialbd.ttf", 30)
label_font = load_font(r"C:\Windows\Fonts\arial.ttf", 20)
detail_font = load_font(r"C:\Windows\Fonts\arial.ttf", 16)

report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
records = {
    (record["body_id"], record["id"]): record
    for record in report.get("records", [])
}
missing = [
    f"{body}+{state}"
    for body in BODY_ORDER
    for state in STATE_ORDER
    if (body, state) not in records
]
if missing:
    raise RuntimeError("Missing review cells: " + ", ".join(missing))

width = MARGIN * 2 + len(STATE_ORDER) * TILE_SIZE[0] + (len(STATE_ORDER) - 1) * GAP
row_height = TILE_SIZE[1] + LABEL_HEIGHT
height = MARGIN * 2 + HEADER_HEIGHT + len(BODY_ORDER) * row_height + GAP
sheet = Image.new("RGB", (width, height), "#17191d")
draw = ImageDraw.Draw(sheet)
draw.text(
    (MARGIN, MARGIN),
    "M02 v003 Hybrid Face Layer - PIE Review",
    fill="#f2f4f7",
    font=title_font,
)
draw.text(
    (MARGIN, MARGIN + 40),
    "Two Body-only motions; one shared face clip with bones + Morph curves",
    fill="#aeb6c2",
    font=detail_font,
)

for row, body_id in enumerate(BODY_ORDER):
    y = MARGIN + HEADER_HEIGHT + row * (row_height + GAP)
    for column, state_id in enumerate(STATE_ORDER):
        x = MARGIN + column * (TILE_SIZE[0] + GAP)
        record = records[(body_id, state_id)]
        image_path = Path(record["capture"]["path"])
        with Image.open(image_path) as source:
            tile = ImageOps.fit(
                source.convert("RGB"), TILE_SIZE, method=Image.Resampling.LANCZOS
            )
        sheet.paste(tile, (x, y))
        draw.rectangle(
            (x, y + TILE_SIZE[1], x + TILE_SIZE[0], y + row_height),
            fill="#242830",
        )
        draw.text(
            (x + 12, y + TILE_SIZE[1] + 8),
            f"{body_id} | {state_id}",
            fill="#f2f4f7",
            font=label_font,
        )
        max_head_rotation = max(
            item["rotation_delta_degrees"]
            for item in record["head_neck_comparison"].values()
        )
        draw.text(
            (x + 12, y + TILE_SIZE[1] + 37),
            f"sample {record['sample_time']:.2f}s | head/neck delta {max_head_rotation:.3f} deg",
            fill="#aeb6c2",
            font=detail_font,
        )

sheet.save(SHEET_PATH, optimize=True)
print(
    json.dumps(
        {
            "sheet": str(SHEET_PATH),
            "size": list(sheet.size),
            "success": bool(report.get("success")),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
