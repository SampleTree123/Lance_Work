#!/usr/bin/env python3
"""Render complete chains as two aligned rows per history mode.

Use --suite for a clearly labelled preparation preview, --run-dir after inference.
Implementation/output owner: ../training_integration.md.
"""
import argparse
from html import escape
import json
from pathlib import Path
import shutil
from urllib.parse import quote

import cv2

from build_datamake_teacher_forced_conversation import sha256_file
from build_datamake_visual_sanity_review import video_check
from prepare_datamake_chain_review import load_suite, make_cases


def grouped_outputs(manifest):
    suite = manifest["chain_suite"]
    expected = make_cases(suite)
    expected_items = {(c["chain_id"], c["mode"], i["round"]): i for c in expected for i in c["outputs"]}
    actual = {}
    for case in manifest["cases"]:
        for item in case["outputs"]:
            key = (case["chain_id"], case["mode"], item["round"])
            if key in actual:
                raise ValueError(f"Duplicate chain/mode/round: {key}")
            actual[key] = item
    if actual != expected_items:
        raise ValueError("Incomplete or inconsistent chain results; prompts/GT/feedback/output mapping must match the frozen suite")
    return actual


def build_page(run, manifest, *, copy_media=False):
    preview = manifest["status"] == "prepared"
    if not preview and manifest["status"] != "generated":
        raise ValueError("Inference must finish before building the result review")
    suite = manifest["chain_suite"]
    outputs = grouped_outputs(manifest)
    references = run / "references"
    references.mkdir(exist_ok=True)
    audit = {"status": "prepared" if preview else "passed", "quality_status": "not_generated" if preview else "pending_user_visual_review",
             "media_mode": "copy" if copy_media else "symlink", "media": {}}
    def video(path, label, generated=False):
        if generated and preview:
            return f'<td class="video-cell"><div class="placeholder">待推理 · {escape(label)}</div></td>'
        if not path.is_file():
            raise FileNotFoundError(path)
        if generated or path.is_relative_to(run):
            local = path
        else:
            local = references / (sha256_file(path)[:16] + "_" + path.name)
            if copy_media:
                if local.is_symlink():
                    local.unlink()
                if not local.exists():
                    shutil.copy2(path, local)
            elif not local.exists():
                local.symlink_to(path.resolve())
        relative = local.relative_to(run).as_posix()
        if relative not in audit["media"]:
            audit["media"][relative] = video_check(local)
        return (f'<td class="video-cell"><video controls muted playsinline preload="none" '
                f'aria-label="{escape(label, quote=True)}" src="{quote(relative)}"></video>'
                f'<div class="caption">{escape(label)}</div></td>')

    title = "编辑链预览 · 尚未推理" if preview else f"编辑链结果 · LoRA step {manifest['completed_steps']}"
    parts = ['''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>完整编辑链</title>
<style>
:root{color-scheme:dark}body{margin:28px;font:15px/1.55 system-ui;background:#11151b;color:#e7edf4}
h1{font-size:26px}h2{font-size:21px}h3{margin:0;font-size:18px}p{color:#afbdcc}a{color:#8ec5ff}
article{margin:32px 0;border:1px solid #354355;border-radius:12px;padding:20px;background:#19212b}
.mode{padding:16px 0}.mode+.mode{border-top:3px solid #54677e;margin-top:22px;padding-top:26px}
.scroll{overflow-x:auto;padding-bottom:12px}table{border-collapse:separate;border-spacing:10px;table-layout:fixed}
th{min-width:76px;text-align:left;color:#b9c9db}td.video-cell{width:260px;min-width:260px;vertical-align:middle}
video,.placeholder{width:260px;aspect-ratio:16/9;object-fit:contain;background:#070a0e;border-radius:6px}
.placeholder{display:flex;align-items:center;justify-content:center;color:#96a8ba;border:1px dashed #58697c;box-sizing:border-box}
.caption{font-size:13px;color:#a7b9cc;padding:5px 0}.prompt{width:174px;min-width:174px;vertical-align:middle}
.prompt p{color:#e1e9f3;font-size:13px;line-height:1.45;margin:4px 0;overflow-wrap:anywhere}
.prompt span{color:#81bdff;font-size:24px}.prompt small{color:#92a5bb}button{border:1px solid #647c99;border-radius:5px;background:#293b51;color:white;padding:7px 12px;margin:10px 8px 12px 0;cursor:pointer}
.notice{border-left:3px solid #e3bc68;padding:10px 14px;background:#28271f}.help{font-size:13px}
.real-heading{border-top:3px solid #54677e;padding-top:28px;margin-top:40px}.real-prompt{white-space:pre-line;color:#e1e9f3}
@media(max-width:700px){body{margin:12px}article{padding:10px}}
</style></head><body>''', f"<h1>{escape(title)}</h1>",
        "<p>每个 case 展示一整条链：源视频 → 编辑指令 → 下一轮视频。横向滚动查看全链，上下两行按轮次对应。</p>"]
    if preview:
        parts.append('<p class="notice">这是推理前的样例与排版预览。真值视频可播放；所有推理位置均为占位，尚无模型生成结果。</p>')
    settings = suite["inference"]
    parts.append(f'<p class="help">{settings["diffusion_steps"]} steps · CFG {settings["cfg_text_scale"]} · noise seed {settings["noise_seed"]} · timestep shift {settings["timestep_shift"]}。<a href="manifest.json">样例与参数记录</a></p>')
    for row in suite["chains"]:
        chain, n = row["chain_id"], row["target_round"]
        parts.append(f'<article><h2>{n} 轮编辑链 · {escape(chain)}</h2>')
        for mode, title, description in (
            ("teacher_forced", "真值回填", "每轮从完整真实历史生成；本行生成视频仅用于展示，下一轮回填对应的真值视频。"),
            ("autoregressive", "自回填", "从同一个源视频开始，后续每轮接着使用本模型之前生成的视频与对话历史。"),
        ):
            parts.append(f'<section class="mode" data-mode="{mode}"><h3>{title}</h3><p>{description}</p><button data-play>两行从头播放</button><button data-pause>暂停两行</button><div class="scroll"><table><tbody>')
            for kind, label in (("inference", "推理结果"), ("ground_truth", "真值视频")):
                parts.append(f'<tr data-kind="{kind}"><th scope="row">{label}</th>')
                parts.append(video(Path(suite["media_root"]) / row["video_paths"][0], "Source · 原始视频"))
                for round_no in range(1, n + 1):
                    item = outputs[(chain, mode, round_no)]
                    prompt = f'<small>编辑 {round_no}</small><p>{escape(item["prompt"])}</p>' if kind == "inference" else ""
                    parts.append(f'<td class="prompt">{prompt}<span aria-hidden="true">→</span></td>')
                    generated = kind == "inference"
                    path = run / item["output"] if generated else Path(item["gt_target"])
                    parts.append(video(path, f"R{round_no}", generated=generated))
                parts.append('</tr>')
            parts.append('</tbody></table></div></section>')
        parts.append('</article>')
    if suite.get("real_cases"):
        from datamake_coinve_review_media import sampled_preview
        parts.append('<h2 class="real-heading">真实数据 · CoinVE 单轮编辑</h2><p>每例只生成一次。Source 与真值展示相同起点的 5 秒采样窗口，模型输出与真值分别标注。</p>')
        audit["real_paired_windows"] = {}
        for row in suite["real_cases"]:
            item = outputs[(row["chain_id"], "single_turn", 1)]
            crop = {"policy": row["crop_policy"], "start_seconds": row["crop_start_seconds"],
                    "duration_seconds": row["crop_duration_seconds"]}
            proxies = []
            for path in row["video_paths"]:
                proxy, evidence = sampled_preview(Path(path), crop, run, suite["real_media_sha256"][path])
                proxies.append(proxy)
                audit["real_paired_windows"][path] = evidence
            parts.append(f'<article data-origin="coinve"><h2>{escape(row["sample_id"])} · 单轮编辑</h2><p class="real-prompt">{escape(item["prompt"])}</p>')
            parts.append('<section class="mode" data-mode="single_turn"><button data-play>从头同时播放</button><button data-pause>暂停</button><div class="scroll"><table><tbody><tr data-kind="single_turn">')
            parts.append(video(proxies[0], "Source · 原始输入"))
            parts.append('<td class="prompt"><span aria-hidden="true">→</span><p>按照上方指令编辑</p></td>')
            parts.append(video(run / item["output"], "我们的模型输出", generated=True))
            parts.append(video(proxies[1], "真值 · Target"))
            parts.append('</tr></tbody></table></div></section></article>')
    parts.append('''<script>
document.querySelectorAll('[data-play]').forEach(button=>button.onclick=async()=>{
 const videos=[...button.closest('.mode').querySelectorAll('video')];
 videos.forEach(video=>{video.pause();video.currentTime=0});
 await Promise.allSettled(videos.map(video=>video.play()));
});
document.querySelectorAll('[data-pause]').forEach(button=>button.onclick=()=>{
 button.closest('.mode').querySelectorAll('video').forEach(video=>video.pause());
});
</script></body></html>''')
    (run / "index.html").write_text("\n".join(parts), encoding="utf-8")
    (run / "media_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    return audit


def main():
    cv2.setNumThreads(2)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--suite", type=Path, help="Create a preparation preview instead of a generated-result page")
    parser.add_argument("--copy-media", action="store_true", help="Copy referenced GT videos for a portable review; default uses symlinks")
    parser.add_argument("--refresh-preview", action="store_true", help="Update an existing prepared preview with --suite; generated runs are protected")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.suite:
        suite = load_suite(args.suite)
        manifest = {"status": "prepared", "chain_suite": suite, "chain_suite_sha256": sha256_file(args.suite), "cases": make_cases(suite)}
        if args.refresh_preview:
            previous = json.loads((run / "manifest.json").read_text())
            if previous["status"] != "prepared":
                raise ValueError("Only an ungenerated preparation preview can be refreshed")
        else:
            run.mkdir(parents=True, exist_ok=False)
        (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    else:
        if args.refresh_preview:
            parser.error("--refresh-preview requires --suite")
        manifest = json.loads((run / "manifest.json").read_text())
    audit = build_page(run, manifest, copy_media=args.copy_media)
    print(json.dumps({"page": str(run / "index.html"), "status": audit["status"], "checked_media": len(audit["media"])}))


if __name__ == "__main__":
    main()
