#!/usr/bin/env python3
"""Build a portable local review page and frame sheets for the fixed LoRA suite.

Copies only the referenced small videos; never modifies source media or model
files. Implementation/output owner: ../training_integration.md.
"""

import argparse
from html import escape
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
from PIL import Image, ImageDraw

from build_datamake_teacher_forced_conversation import sha256_file


def video_check(path):
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    first = last = None
    size = None
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        size = [frame.shape[1], frame.shape[0]]
        small = cv2.resize(frame, (128, 72)).astype(np.float32)
        if first is None:
            first = small
        last = small
        frame_count += 1
    declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    if not frame_count or frame_count != declared or fps <= 0:
        raise RuntimeError(f"Incomplete/invalid video: {path}, decoded={frame_count}, declared={declared}, fps={fps}")
    return {"decoded_frames": frame_count, "fps": fps, "size": size,
            "duration_seconds": frame_count / fps,
            "first_last_mean_absolute_pixel_difference": float(np.abs(first - last).mean()),
            "sha256": sha256_file(path)}


def preview_frame(path, fraction):
    capture = cv2.VideoCapture(str(path))
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.set(cv2.CAP_PROP_POS_FRAMES, round((count - 1) * fraction))
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Cannot read preview: {path}")
    return Image.fromarray(cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2RGB))


def comparison_runs(specs):
    runs = []
    for spec in specs:
        label, root = spec.split("=", 1)
        root = Path(root).resolve()
        manifest = json.loads((root / "manifest.json").read_text())
        if manifest["status"] != "generated":
            raise ValueError(f"Comparison inference is not finished: {root}")
        outputs = {
            (case["name"], item["round"]): item
            for case in manifest["cases"] for item in case["outputs"]
        }
        runs.append((label, root, manifest, outputs))
    return runs


def local_reference(run, references, path):
    """Keep different runs' identically named turn00.mp4 files distinct."""
    if path.is_relative_to(run):
        return path
    local = references / (sha256_file(path)[:16] + "_" + path.name)
    if not local.exists():
        shutil.copy2(path, local)
    return local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--label", help="Current run's display label")
    parser.add_argument("--compare-run", action="append", default=[], metavar="LABEL=RUN_DIR",
                        help="Compare fixed-suite runs; replaces the legacy Stage 2 column")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = json.loads((run / "manifest.json").read_text())
    if manifest["status"] != "generated":
        raise ValueError("Inference must finish before building the review")
    cv2.setNumThreads(2)
    references = run / "references"
    references.mkdir(exist_ok=True)
    current_label = args.label or f"LoRA step{manifest['completed_steps']}"
    comparisons = comparison_runs(args.compare_run)
    stage2 = run.parent / "stage2_3669_visual_sanity_20260903"
    rows = []
    audit = {"status": "passed", "quality_status": "pending_user_visual_review", "outputs": {},
             "label": current_label, "comparisons": [], "reference_media": {}}
    for index, (label, root, other, _) in enumerate(comparisons):
        local_manifest = references / f"comparison_{index}_manifest.json"
        shutil.copy2(root / "manifest.json", local_manifest)
        audit["comparisons"].append({
            "label": label, "run_dir": str(root), "completed_steps": other["completed_steps"],
            "manifest": local_manifest.relative_to(run).as_posix(),
            "preprocessing": other.get("preprocessing", {"mode": "legacy_inference_preset"}),
        })
    for case in manifest["cases"]:
        for item in case["outputs"]:
            result = run / item["output"]
            audit["outputs"][item["output"]] = video_check(result)
            if case["mode"] == "autoregressive":
                prior = stage2 / "autoregressive_chain3_step3669_30step_cfg1_seed42" / result.name
            else:
                old_name = case["name"].removeprefix("teacher_forced_")
                prior = stage2 / f"{old_name}_step3669_30step_cfg1_seed42" / "turn00.mp4"
            comparison_paths = []
            for label, root, _, outputs in comparisons:
                other = outputs[(case["name"], item["round"])]
                if other["prompt"] != item["prompt"] or other["gt_target"] != item["gt_target"]:
                    raise ValueError(f"Different prompt/target in comparison {label}")
                comparison_paths.append((label, root / other["output"]))
            if not comparisons:
                comparison_paths = [("STAGE2 (legacy resolution)", prior)]
            source = Path(item["actual_source"])
            if not source.is_absolute():
                source = run / source
            paths = []
            for label, path in [("SOURCE", source), ("GT TARGET", Path(item["gt_target"])), *comparison_paths, (current_label, result)]:
                local = local_reference(run, references, path)
                paths.append((label, local.relative_to(run).as_posix()))
                relative = local.relative_to(run).as_posix()
                if local != result and relative not in audit["reference_media"]:
                    audit["reference_media"][relative] = video_check(local)
            rows.append({"title": f"{case['mode']} R{item['round']} {item['edit_axis']}", "prompt": item["prompt"], "paths": paths})
    for fraction in (0.1, 0.5, 0.9):
        sheet = Image.new("RGB", (320 * len(rows[0]["paths"]), len(rows) * 220), "#15171a")
        draw = ImageDraw.Draw(sheet)
        for index, row in enumerate(rows):
            top = index * 220
            draw.text((8, top + 3), row["title"], fill="white")
            for column, (label, relative) in enumerate(row["paths"]):
                draw.text((column * 320 + 8, top + 18), label, fill="white")
                sheet.paste(preview_frame(run / relative, fraction), (column * 320, top + 36))
        sheet.save(run / f"comparison_{int(fraction * 100):02d}pct.jpg", quality=92)
    parts = ["""<!doctype html><html lang="zh"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lance LoRA 视觉检查</title><style>
body{font:16px system-ui;margin:24px;background:#15171a;color:#eee}
section{border-top:1px solid #555;margin-top:24px;padding-top:12px}
.videos{display:grid;grid-template-columns:repeat(var(--columns,4),minmax(240px,1fr));gap:10px;overflow-x:auto}
video{width:100%;background:#000}figure{margin:0}figcaption{padding:8px 0}
a{color:#8bcaff}button{padding:8px 16px;margin:8px 0}
@media(max-width:800px){.videos{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>""",
        f"<h1>Lance · {escape(current_label)}</h1>",
        "<p>validation 样例；30 steps，CFG=1，seed=42，timestep shift=3.5，KV cache 开启。不是训练中的单步 pred_x0。</p>",
        "<p>前三行是连续自回灌，后面是 GT 历史对照。SOURCE 是当前模型实际输入；不同模型自回灌第二轮以后的输入可能不同。GT 是原始渲染链目标。少量样例不代表整体泛化质量。</p>",
        f"<p>当前预处理：{escape(manifest.get('preprocessing', {}).get('mode', 'legacy_inference_preset'))}。标记 legacy/old resolution 的旧视频使用更高分辨率，不能作为仅改变训练步数的受控比较。A/B 若训练步数不同，也不是等步数基座消融。</p>",
        '<p><a href="manifest.json">完整输入、prompt 与参数</a> · <a href="media_audit.json">媒体检查</a> · <a href="comparison_50pct.jpg">中间帧对比</a></p>',
    ]
    for row in rows:
        parts += [f"<section><h2>{escape(row['title'])}</h2><p>{escape(row['prompt'])}</p>", f'<button onclick="playRow(this)">从头同时播放本行</button><div class="videos" style="--columns:{len(row["paths"])}">']
        for label, relative in row["paths"]:
            parts.append(f'<figure><video controls muted loop preload="metadata" src="{escape(relative, quote=True)}"></video><figcaption>{escape(label)} · <a href="{escape(relative, quote=True)}">打开视频</a></figcaption></figure>')
        parts.append("</div></section>")
    parts.append("<script>function playRow(b){b.closest('section').querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play()})}</script></html>")
    (run / "index.html").write_text("\n".join(parts), encoding="utf-8")
    (run / "media_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"Review: {run / 'index.html'}")


if __name__ == "__main__":
    main()
