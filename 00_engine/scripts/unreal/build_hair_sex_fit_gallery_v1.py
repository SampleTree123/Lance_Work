"""Make a read-only six-view gallery and validate captured review images."""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import os
from pathlib import Path
import struct

from PIL import Image


ENGINE = Path(__file__).resolve().parents[2]
ROOT = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
PLAN = ROOT / "review_plan.json"
SOURCE_REVIEW = ENGINE / "scripts/character_creator/cc_scalp_hair_selection_review_v1.json"
VIEWS = ("front", "front_left", "left", "back", "right", "front_right")
VIEW_LABELS = ("正面", "左前 45°", "左侧", "背面", "右侧", "右前 45°")


def image_name(case: dict, view: str) -> str:
    return f"{case['review_index']:03d}_{case['sex']}_{case['hair_id']}_{view}.png"


def inspect_png(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False}
    data = path.read_bytes()
    if len(data) < 32 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return {"exists": True, "valid_png_header": False, "bytes": len(data)}
    width, height = struct.unpack(">II", data[16:24])
    try:
        with Image.open(path) as image:
            image.load()
            zero_alpha = "A" in image.getbands() and image.getchannel("A").getextrema() == (0, 0)
            rgb_extrema = image.convert("RGB").getextrema()
            uniform_rgb = all(low == high for low, high in rgb_extrema)
            visible = not zero_alpha and not uniform_rgb
            mode = image.mode
    except (OSError, ValueError):
        return {"exists": True, "valid_png_header": True, "decodable": False,
                "width": width, "height": height, "bytes": len(data)}
    return {"exists": True, "valid_png_header": True, "decodable": True,
            "displayable": visible, "zero_alpha": zero_alpha, "uniform_rgb": uniform_rgb, "mode": mode,
            "sha256": hashlib.sha256(data).hexdigest(),
            "width": width, "height": height, "bytes": len(data)}


def build_gallery(root: Path = ROOT, *, scalp_hidden: bool = False) -> None:
    baseline_root = ROOT
    output_root = root.resolve()
    PLAN = output_root / "review_plan.json"
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_REVIEW.read_text(encoding="utf-8"))
    cards = []
    markdown_root = output_root / "markdown_cases"
    markdown_root.mkdir(exist_ok=True)
    title_text = "隐藏头皮覆盖层 · 发型六视审查" if scalp_hidden else "UE 发型标准角色六视图"
    intro = ("全部 40 款保留发型：女性 30 项、男性 21 项，共 306 张。这里只临时隐藏 Scalp 头皮覆盖层，保留其他发丝、辫子和发饰。"
             "HB1-05、HB1-20 没有 Scalp 命名槽，但有 Hairline 发际线覆盖层；本批未隐藏它，已另做补充对照。请检查黑色网格、发际线缺口及剃发区域；男性穿模仍待后续处理。"
             "每张图片下方可打开原版对照。此版本待你审查后决定是否采用，正式资产尚未改动。"
             if scalp_hidden else
             "本页仅供第一阶段视觉审查：女性 30 项、男性 21 项。六视图由同一 UE 审查关卡和 v003 角色蓝图拍摄。图片存在不代表发型通过人工审查；不涉及具体身份或服装搭配。单击图片可看原图。")
    markdown_index = [f"# {title_text}", "", intro, "", "打开单个发型查看六个方向；图片齐全不代表视觉通过。", ""]
    missing = []
    invalid = []
    image_count = 0
    for case in plan["cases"]:
        figures = []
        for view, label in zip(VIEWS, VIEW_LABELS):
            filename = image_name(case, view)
            info = inspect_png(output_root / "captures" / filename)
            if not info["exists"]:
                missing.append(filename)
                figure = f'<div class="missing">待生成：{html.escape(label)}</div>'
            elif (not info.get("valid_png_header") or not info.get("displayable")
                  or (info["width"], info["height"]) != (900, 900)):
                invalid.append(filename)
                figure = f'<div class="missing">图片异常：{html.escape(label)}</div>'
            else:
                image_count += 1
                image_source = "captures/" + html.escape(filename, quote=True) + "?v=" + info["sha256"][:12]
                figure = f'<a href="{image_source}" target="_blank"><img loading="lazy" src="{image_source}" alt="{html.escape(label)}"></a>'
            compare = ""
            if scalp_hidden:
                baseline = (baseline_root / "captures" / filename).resolve()
                compare = f' · <a href="{html.escape(os.path.relpath(baseline, output_root).replace(chr(92), chr(47)), quote=True)}" target="_blank">原版对照</a>'
            figures.append(f'<figure>{figure}<figcaption>{html.escape(label)}{compare}</figcaption></figure>')
        title = f"{case['review_index']:03d} · {case['hair_id']} · {case['display_name']}"
        source_item = next((item for item in source["items"]
                            if any(preset.startswith(case["hair_id"] + "_")
                                   for preset in item.get("source_preset_ids", []))), None)
        source_link = ""
        source_sheet = None
        if source_item:
            sheet = Path(source_item["existing_six_view_sheet"])
            if case["sex"] == "male":
                male_sheet = sheet.with_name(sheet.name.replace("_female_", "_male_"))
                if male_sheet.is_file():
                    sheet = male_sheet
            if sheet.is_file():
                source_sheet = sheet
                relative = os.path.relpath(sheet, output_root).replace("\\", "/")
                source_link = f'<a href="{html.escape(relative, quote=True)}" target="_blank">查看原 CC 六视图</a>'
        case_file = markdown_root / f"{case['review_index']:03d}_{case['sex']}_{case['hair_id']}.md"
        case_lines = [f"# {title}", "", f"标准角色：{'女性 F02' if case['sex'] == 'female' else '男性 M02'}", ""]
        coverage_note = ""
        if scalp_hidden:
            case_lines.extend(["候选效果：隐藏头皮覆盖层，其他发型材质保留。" if case["hair_id"] not in {"HAIR_HB1_05", "HAIR_HB1_20"}
                               else "本款没有 Scalp 命名槽，但有 Hairline 发际线覆盖层；本批没有隐藏它。", ""])
            if case["hair_id"] in {"HAIR_HB1_05", "HAIR_HB1_20"}:
                coverage_note = '<p>本款 Hairline 发际线层未被此批隐藏，因此与原版接近。</p>'
                diagnostic = baseline_root / "rendering_repair_v2/hairline_grid_diagnostic_20260930_v1/comparison.html"
                diagnostic_md = diagnostic.with_suffix(".md")
                if diagnostic.is_file():
                    link = html.escape(os.path.relpath(diagnostic, output_root).replace("\\", "/"), quote=True)
                    coverage_note = f'<p>本款 Hairline 发际线层未被此批隐藏，因此与原版接近。<a href="{link}" target="_blank">查看隐藏 Hairline 的补充对照</a></p>'
                if diagnostic_md.is_file():
                    case_lines.extend([f"[查看隐藏 Hairline 的补充对照]({diagnostic_md.as_posix()})", ""])
        if source_sheet:
            case_lines.extend([f"[对照原 CC 六视图]({source_sheet.as_posix()})", ""])
        for view, label in zip(VIEWS, VIEW_LABELS):
            capture = output_root / "captures" / image_name(case, view)
            case_lines.extend([f"## {label}", "", f"![{case['hair_id']} {label}]({capture.as_posix()})", ""])
            if scalp_hidden:
                baseline = baseline_root / "captures" / image_name(case, view)
                case_lines.extend([f"[查看原版同视角]({baseline.as_posix()})", ""])
        case_file.write_text("\n".join(case_lines), encoding="utf-8")
        if case["review_index"] in {1, 31}:
            markdown_index.extend([f"## {'女性' if case['sex'] == 'female' else '男性'}", ""])
        markdown_index.append(f"- [{case['review_index']:03d} · {case['hair_id']} · {case['display_name']}]({case_file.as_posix()})")
        cards.append(
            f'<article id="case-{case["review_index"]:03d}" class="case">'
            f'<header><h2>{html.escape(title)}</h2><span>{"女性" if case["sex"] == "female" else "男性"}标准角色 · {source_link}</span></header>'
            f'{coverage_note}'
            f'<div class="views">{"".join(figures)}</div></article>'
        )
    style = """
    :root{color-scheme:light;font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f4f5f7;color:#18202b}
    body{margin:0 auto;max-width:1500px;padding:20px 28px 80px}h1{margin:0 0 8px;font-size:28px}
    .intro{color:#4b5563;line-height:1.65;margin-bottom:28px}.case{background:white;border:1px solid #d9dde4;border-radius:12px;margin:22px 0;padding:16px;box-shadow:0 2px 8px #0001}
    header{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:12px}h2{font-size:18px;margin:0}header span{white-space:nowrap;color:#526071}
    .views{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}figure{margin:0}img{display:block;width:100%;aspect-ratio:1;object-fit:cover;background:#eee;border:1px solid #ddd}
    figcaption{text-align:center;padding:5px 0;color:#526071;font-size:13px}.missing{aspect-ratio:1;display:grid;place-items:center;background:#f6e8e8;color:#9b3333}
    nav{position:sticky;top:0;background:#f4f5f7ee;padding:10px 0;z-index:2}nav a{margin-right:18px;color:#2563ab;text-decoration:none}
    @media(max-width:900px){.views{grid-template-columns:repeat(2,minmax(0,1fr))}header{display:block}}
    """
    female_start = plan["cases"][0]["review_index"]
    male_start = next(case["review_index"] for case in plan["cases"] if case["sex"] == "male")
    markup = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title_text}</title><style>{style}</style></head><body>
    <h1>{title_text}</h1>
    <div class="intro">{intro}</div>
    <nav><a href="#case-{female_start:03d}">女性 30 项</a><a href="#case-{male_start:03d}">男性 21 项</a><span>已生成 {image_count}/306 张</span></nav>
    {''.join(cards)}
    </body></html>"""
    (output_root / "gallery.html").write_text(markup, encoding="utf-8")
    (output_root / "gallery_markdown.md").write_text("\n".join(markdown_index) + "\n", encoding="utf-8")
    report = {"cases": len(plan["cases"]), "expected_images": len(plan["cases"]) * len(VIEWS),
              "valid_images": image_count, "missing_images": missing, "invalid_images": invalid,
              "markdown_index": "gallery_markdown.md", "markdown_cases": len(plan["cases"]),
              "image_checks": ["PNG header", "decoded pixels", "900x900 size", "nonzero alpha if present", "nonuniform RGB"],
              "complete": not missing and not invalid, "visual_acceptance": "pending_human_review"}
    report["scalp_hidden_candidate"] = scalp_hidden
    (output_root / "gallery_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gallery": str(output_root / "gallery.html"), "valid_images": image_count,
                      "expected_images": report["expected_images"], "complete": report["complete"]}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--scalp-hidden", action="store_true")
    args = parser.parse_args()
    if not args.output_root.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Gallery output must remain inside the review Run Root")
    if args.scalp_hidden and args.output_root.resolve() == ROOT.resolve():
        raise ValueError("Keep the baseline gallery; use a separate hidden-scalp output directory")
    build_gallery(args.output_root, scalp_hidden=args.scalp_hidden)


if __name__ == "__main__":
    main()
