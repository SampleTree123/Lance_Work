"""Run only after root authorizes finalization; refuse incomplete corrected media.

No UE, rendering, encoding, cleanup, candidate edits, or old sync script execution.
"""
from pathlib import Path
import copy
import hashlib
import html
import json
import os
import re
import statistics
import struct

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
CORRECTED = RUN / "corrected"
OLD = RUN.parent / "dataset_render_pilot_20261023_v1"
DOC = ROOT / "20_planning/data_design/character_creator/full_process"
PROFILE = RUN.parent / "dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json"


def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()
def write(path, value):
    path = Path(path); temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
def relative(path, directory=RUN): return os.path.relpath(path, directory).replace("\\", "/")
def require(value, message):
    if not value: raise RuntimeError(message)
def section(path, title, body):
    text = path.read_text(encoding="utf-8")
    pattern = r"\n## " + re.escape(title) + r"\n[\s\S]*?(?=\n## |\Z)"
    block = "\n## " + title + "\n\n" + body.rstrip() + "\n"
    text = re.sub(pattern, lambda m: block, text) if re.search(pattern, text) else text.rstrip() + block
    path.write_text(text, encoding="utf-8")
def expected_signature(job):
    return hashlib.sha256(json.dumps({"version": 2, "job": job}, sort_keys=True).encode()).hexdigest()
def verified_render(path, job):
    receipt = read(path)
    require(receipt.get("status") == "completed" and receipt.get("success") is True, f"MRQ incomplete: {path}")
    require(receipt.get("job_signature") == expected_signature(job), f"Old/missing MRQ policy signature: {path}")
    readiness = receipt.get("render_contract", {}).get("texture_readiness", {})
    require("FULLY_LOAD" in readiness.get("texture_streaming", ""), f"FULLY_LOAD evidence absent: {path}")
    return receipt


def collect():
    # Complete ALL validation before changing any documentation authority.
    jobs, references = read(CORRECTED / "pilot_jobs.json")["jobs"], read(CORRECTED / "reference_pilot_jobs.json")["jobs"]
    require(len(jobs) == 12 and len(references) == 6, "Expected corrected 12 main + 6 reference definitions")
    require(len({j["job_id"] for j in jobs + references}) == 18, "Duplicate output IDs")
    old = {j["job_id"]: j for j in read(OLD / "pilot_jobs.json")["jobs"]}
    records = []
    for job in jobs:
        jid = job["job_id"]; directory = CORRECTED / "jobs" / jid
        require(old[jid]["state"] == job["state"], "Adopted sampled state changed: " + jid)
        media = read(directory / "media_receipt.json"); video = directory / "video.mp4"
        require(media.get("status") == "success" and media.get("render_signature") == expected_signature(job), "Missing/current-policy media signature: " + jid)
        require(video.is_file() and sha(video) == media.get("video_sha256"), "Video missing or hash mismatch: " + jid)
        check = media.get("media", {})
        require((check.get("decoded_frames"), check.get("fps"), check.get("width"), check.get("height")) == (300, 30, job["width"], job["height"]), "Media dimensions/frame check failed: " + jid)
        require(check.get("verification") == "full_ffmpeg_decode_xerror", "Full decode receipt missing: " + jid)
        provenance = media.get("render_provenance", {})
        receipt_path = CORRECTED / provenance["receipt_relative_path"]
        require(receipt_path.resolve().is_relative_to((CORRECTED / "render_receipts").resolve()), "Receipt escapes corrected run")
        require(sha(receipt_path) == provenance.get("receipt_sha256"), "MRQ provenance hash mismatch: " + jid)
        verified_render(receipt_path, job)
        prep = read(directory / "prepared.json")
        require(prep.get("persistent_materials", {}).get("version") == "dataset_persistent_materials_v2", "Persistent material preparation missing: " + jid)
        records.append({"job_id": jid, "bytes": video.stat().st_size, "media": check, "timing": media.get("timing", {}),
                        "preparation_seconds": prep.get("preparation_seconds"), "receipt": relative(receipt_path)})
    ref_results = read(CORRECTED / "REFERENCE_RESULTS.json").get("results", [])
    indexed = {x["job_id"]: x for x in ref_results}
    require(set(indexed) == {j["job_id"] for j in references}, "Six corrected reference results are not complete")
    for job in references:
        jid = job["job_id"]; receipt_path = Path(indexed[jid]["receipt"])
        if not receipt_path.is_absolute(): receipt_path = CORRECTED / receipt_path
        require(receipt_path.resolve().is_relative_to((CORRECTED / "render_receipts").resolve()), "Reference receipt escapes corrected run")
        verified_render(receipt_path, job)
        frames = list((CORRECTED / "jobs" / jid / "frames").glob("*.png"))
        require(len(frames) == 1 and frames[0].name == "frame_0000.png", "Expected exactly one reference PNG: " + jid)
        with frames[0].open("rb") as f: header = f.read(33)
        require(header[:8] == b"\x89PNG\r\n\x1a\n", "Reference PNG header invalid: " + jid)
        width, height, bits, channels = struct.unpack(">IIBB", header[16:26])
        require((width, height, bits) == (job["width"], job["height"], 8) and channels in (2, 6), "Reference PNG profile mismatch: " + jid)
        if job["reference_kind"] in ("identity", "hair"):
            prep = read(CORRECTED / "jobs" / jid / "prepared.json")
            require(prep.get("details", {}).get("persistent_materials", {}).get("version") == "dataset_persistent_materials_v2", "Reference persistent materials absent: " + jid)
    reload = read(RUN / "MATERIAL_RELOAD_CHECK.json")
    require(reload.get("success") is True and len(reload.get("checks", [])) == 6 and all(x.get("match") is True for x in reload["checks"]), "Actual six-binding material reload check failed")
    for filename in ("TEXTURE_LOG_EXTRACT.json", "COMPARISON.png"):
        require((RUN / filename).is_file(), "Cold-cache A/B evidence missing: " + filename)
    return jobs, references, records


def main():
    jobs, references, records = collect()
    runrel = relative(RUN, ROOT); correctedrel = relative(CORRECTED, ROOT)
    summary = {"schema": "dataset_texture_quality_finalization_v1", "status": "corrected_media_technical_pass_user_review_pending",
        "main_clips": len(jobs), "reference_prototypes": len(references), "old_12_quality": "visually_rejected_technical_decode_and_resume_evidence_only",
        "texture_policy": "FULLY_LOAD", "material_policy": "dataset_persistent_materials_v2", "material_reload_bindings": 6,
        "user_visual_acceptance": False, "server_verified": False, "candidate_modified": False, "source_scenes_modified": False,
        "scope": "bounded current-policy receipt/hash/media checks; no fresh decode or UE execution by this script", "jobs": records}
    bytes_total = sum(x["bytes"] for x in records)
    encode_median = statistics.median(x["timing"]["encode_seconds"] for x in records)
    report = f'''# 纹理清晰度修正与待审样片

修正策略下的 **{len(jobs)}条主视频和{len(references)}张参考图原型已输出并通过本轮技术检查**。主片均300帧、30fps、10秒，横1920×1080／竖1080×1920；成片SHA、完整解码回执、当前worker签名及成功MRQ来源已核对。用户画面质量接受仍为pending，服务器尚未验证。

旧12条的解码与续跑结果仅保留为技术证据；其模糊画面已拒绝，不能作为生产质量接受结果。新旧逐节点入口见[审查页](REVIEW.md)／[视频画廊](REVIEW.html)。

## 已证实的冷缓存原因与修正

同一1024方图、同相机、同黑发人物，两组均先StreamOut4096驱逐。继承流送时脸、头发base/opacity和裙子实际驻留64×64；FULLY_LOAD组脸/头发2048×2048、裙子4096×4096。依据为[原始纹理日志提取](TEXTURE_LOG_EXTRACT.json)与[对照图](COMPARISON.png)。这是该固定参考样本的受控纹理驻留差异，不把暖缓存或不同输出分辨率混作原因证明，也不外推所有资产/服务器都通过。

主worker VERSION2、reference VERSION5共享FULLY_LOAD；相机、动作、源场景、输出规格和AA不因纹理修正而改变。旧scene_resources中的NONE描述被texture_readiness实际FULLY_LOAD记录覆盖。动态发色MID由v2 helper冻结到owned MIC；[真实地图磁盘重载检查](MATERIAL_RELOAD_CHECK.json)六个binding全部一致。此检查与冷缓存纹理A/B是两个不同证据。

## 实际输出与限制

本批主视频共{bytes_total / 1024**2:.1f} MiB，编码中位{encode_median:.2f}秒；实际逐节点回执见[汇总](FINALIZATION.json)。完整加载改变资源需求，旧速度和显存范围不能当新策略吞吐；新GPU原始采样若存在保留为[gpu_telemetry.csv](gpu_telemetry.csv)，本脚本不从不完整采样推断峰值。

参考图仍是中性布置原型，身份、黑发前后、单件和背景需用户检查；专用动作reference尚未制作，载体未定，后续须与主片共用production10时钟。下一步先由用户审查新画面与压缩，再验证Linux构建/插件/资源和同节点服务器样片。R17与唯一current父计划继续；不启动全量生产、训练、上传或清理原帧。
'''
    (RUN / "REPORT.md").write_text(report, encoding="utf-8")
    md = ["# 修正后画面审查", "", "12主片＋6参考原型。技术检查通过；请确认脸、发丝、衣料清晰度与发色、镜头、动作和压缩。旧12画面质量已拒绝。", "", "[报告](REPORT.md) · [画廊](REVIEW.html) · [冷缓存A/B](COMPARISON.png)", "", "## 主视频", ""]
    cards = []
    for job in jobs:
        jid = job["job_id"]; new = f"corrected/jobs/{jid}/video.mp4"; old = relative(OLD / "jobs" / jid / "video.mp4")
        md.append(f"- {jid}：[修正后]({new}) · [旧模糊版本，仅作对照]({old})")
        cards.append(f'<article><h3>{html.escape(jid)}</h3><video controls preload="metadata" src="{new}"></video><p><a href="{old}">旧模糊版本对照</a></p></article>')
    md += ["", "## 参考图原型", ""]
    refcards = []
    for job in references:
        jid = job["job_id"]; png = f"corrected/jobs/{jid}/frames/frame_0000.png"
        md.append(f"- [{jid}]({png})")
        refcards.append(f'<article><h3>{html.escape(jid)}</h3><a href="{png}"><img loading="lazy" src="{png}"></a></article>')
    (RUN / "REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RUN / "REVIEW.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>修正后画面待审</title><style>body{background:#141922;color:#eef;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}article{background:#222c3b;padding:16px;border-radius:10px;overflow:hidden}video,img{width:100%;height:420px;object-fit:contain;background:#080b10}a{color:#9cf}h3{overflow-wrap:anywhere}</style><h1>修正后12条主片 · 6参考图原型</h1><p>技术检查通过，用户质量审查待完成。旧片为拒绝的模糊对照。<a href="COMPARISON.png">冷缓存纹理A/B</a></p><main>' + "".join(cards) + '</main><h2>参考图原型</h2><main>' + "".join(refcards) + '</main></html>', encoding="utf-8")
    profile = read(PROFILE)
    profile.update(status="corrected_12_main_6_reference_technical_pass_user_quality_review_and_server_pending", render_started=True, formal_production_render_started=False, last_updated="2026-10-23")
    profile["pending"] = ["user_corrected_sample_quality_review", "reference_presentation_and_motion_carrier", "full_reference_manifest_execution", "server_exact_build_plugins_and_resource_profile", "local_render_and_server_sample_comparison"]
    profile.setdefault("render_quality", {}).update(texture_streaming="MRQ_FULLY_LOAD_used_textures", texture_readiness_evidence=runrel + "/TEXTURE_LOG_EXTRACT.json", persistent_material_policy="dataset_persistent_materials_v2")
    profile["local_pilot"] = {"run_root": correctedrel, "main_clips": 12, "reference_image_prototypes": 6, "technical_media_pass": True, "user_visual_acceptance": False, "linux_tested": False, "old_pilot_quality_rejected": True, "quality_report": runrel + "/REPORT.md"}
    profile["output_format"].update(remaining_encoder_details="corrected 12 full-decode receipts and current MRQ provenance verified; compression/visual review pending", compression_quality_validated=False)
    write(PROFILE, profile)
    # These are new-run copies; preserve adopted jobs and update only profile metadata.
    for name in ("main_jobs.json", "pilot_jobs.json", "reference_pilot_jobs.json"):
        manifest_path = CORRECTED / name
        manifest = read(manifest_path)
        manifest["profile"] = copy.deepcopy(profile)
        write(manifest_path, manifest)
    notice = "\n> 2026-10-23更新：本页为旧版技术试跑记录，画面模糊已被用户指出。清晰度修正后的结果请使用[新审查入口](../dataset_texture_quality_20261023_v1/REVIEW.md)及[修正报告](../dataset_texture_quality_20261023_v1/REPORT.md)。旧耗时、显存和体积仅为旧策略历史数据。\n"
    for name in ("HANDOFF.md", "REVIEW.md", "PILOT_REPORT.md"):
        old_path = OLD / name
        old_text = old_path.read_text(encoding="utf-8")
        if notice.strip() not in old_text:
            first, rest = old_text.split("\n", 1)
            old_path.write_text(first + "\n" + notice + rest, encoding="utf-8")
    statepath = DOC / "project_management/status/PROJECT_STATE.json"
    state = read(statepath); before = copy.deepcopy(state); branch = state["dataset_design_branch_20261021"]
    branch.update(status="configuration_accepted_corrected_local_media_technical_pass_user_review_server_pending", formal_render_started=False,
        next_action="用户审查纹理修正后的12条主视频及6参考图原型；确认画面后再进行Linux同节点小样与资源核验，专用动作参考载体待定。")
    branch["media_profile"] = {"path": "render_preparation/VIDEO_PROFILE.json", **copy.deepcopy(profile)}
    prep = branch.setdefault("render_preparation", {})
    prep.update(parameterized_executor_status="current_quality_policy_12_main_6_reference_technical_pass", local_pilot_completed=True,
        texture_quality_correction={"root": runrel, "corrected_root": correctedrel, "main_clips": 12, "reference_prototypes": 6, "report": runrel + "/REPORT.md", "review": runrel + "/REVIEW.md", "user_quality_accepted": False, "server_verified": False, "old_12_visual_quality_rejected": True})
    if isinstance(prep.get("local_pilot"), dict): prep["local_pilot"].update(quality_accepted_by_user=False, visual_quality_rejected=True, scope="old12 retained technical decode/resume evidence; corrected review supersedes old quality")
    require({k:v for k,v in before.items() if k != "dataset_design_branch_20261021"} == {k:v for k,v in state.items() if k != "dataset_design_branch_20261021"}, "Another state branch changed")
    write(statepath, state)
    statuspath = DOC / "project_management/status/PROJECT_STATUS.md"
    text = statuspath.read_text(encoding="utf-8"); start = text.index("## 渲染准备："); end = text.index("## 当前数据集分支：", start)
    text = text[:start] + f'''## 渲染准备：纹理修正后本地媒体技术通过，用户画面审查待完成（2026-10-23）

旧12片虽解码/续跑通过，画面模糊已拒绝。冷缓存同镜头对照定位为纹理实际驻留64×64；FULLY_LOAD恢复脸/头发2048、衣服4096，并将临时发色材质持久化到owned MIC，六binding实际重载一致。修正策略下12主片与6参考图原型技术检查通过，尚未获得用户质量确认。见[新审查入口]({relative(RUN / 'REVIEW.md', statuspath.parent)})及[证据报告]({relative(RUN / 'REPORT.md', statuspath.parent)})。

下一步由用户确认清晰度、发色、动作/镜头及压缩，再进行Linux同节点小样；专用动作参考载体未定。候选和源场景不变，全量生产、服务器验证和训练均未开始。R17及唯一current父计划继续，其他分支不变。

''' + text[end:]
    statuspath.write_text(text, encoding="utf-8")
    technical = DOC / "technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md"
    section(technical, "2026-10-23：纹理冷缓存修正与新媒体审查", f'''本Technical拥有`{runrel}/`，包括`probe.py`、`sample_gpu.py`、`rerender_references.py`与`finalize_quality_docs.py`（本Run有界prototype辅助）；通用现用helper `00_engine/scripts/unreal/dataset_persistent_materials_v1.py`（v2）冻结临时MID到owned MIC。`ue_dataset_render_v11.py` VERSION2与reference VERSION5使用FULLY_LOAD；驱动以当前render_signature、成功MRQ回执来源及视频hash拒绝复用旧质量媒体。旧12技术证据保留，但画面质量拒绝。本节取代此前“继承纹理流送足够”的本地质量结论。

同1024、同相机、同黑发、两组均StreamOut4096的A/B实际驻留由64×64恢复脸/发2048与裙4096；六binding地图磁盘重载匹配。新12视频＋6参考图技术结果、精确回执和限制见[报告]({relative(RUN / 'REPORT.md', technical.parent)})与[汇总]({relative(RUN / 'FINALIZATION.json', technical.parent)})。仅20项相关测试由主会话报告通过；不宣称全库审计或服务器通过。没有修改候选/源场景；用户视觉质量与参考布置仍待确认，动作reference暂无专用样片。''')
    plan = DOC / "project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md"
    section(plan, "R17 纹理修正后媒体更新（2026-10-23）", f'''R17保持in_progress。旧12画面质量已拒绝；已完成受控冷缓存定位、持久材质实际重载检查、修正后12视频与6参考原型的技术检查。用户质量接受、正式参考布置/动作载体、Linux同任务小样与全量生产仍待完成。证据见[新报告]({relative(RUN / 'REPORT.md', plan.parent)})；不关闭父计划，不修改其他需求。''')
    write(RUN / "FINALIZATION.json", summary)
    print(json.dumps({"status": summary["status"], "main_clips": 12, "references": 6, "review": str(RUN / "REVIEW.md"), "other_state_branches_unchanged": True}))


if __name__ == "__main__": main()
