"""Root-triggered finalization after the current 4 motion + 7 image pilot succeeds.

No UE connection, job edits, media encoding, cleanup, or whole-repository audit.
All required evidence is checked before the first document write.
"""
from pathlib import Path
import ast
import copy
import hashlib
import html
import json
import os
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
SCRIPTS = ROOT / "00_engine/scripts/unreal"
DOC = ROOT / "20_planning/data_design/character_creator/full_process"
PROFILE = RUN.parent / "dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json"


def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()
def object_hash(value): return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)
def rel(path, directory=RUN): return os.path.relpath(path, directory).replace("\\", "/")
def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
def version(path):
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("Missing worker VERSION: " + str(path))
def section(path, title, body):
    text = path.read_text(encoding="utf-8")
    pattern = r"\n## " + re.escape(title) + r"\n[\s\S]*?(?=\n## |\Z)"
    block = "\n## " + title + "\n\n" + body.rstrip() + "\n"
    text = re.sub(pattern, lambda _: block, text) if re.search(pattern, text) else text.rstrip() + block
    path.write_text(text, encoding="utf-8")


def gallery_label(job):
    if job["reference_kind"] == "motion":
        cameras = {"front_full": "正面全身", "orbit_120": "120度环绕", "orbit_360": "360度环绕",
                   "dolly_out_front": "正面后拉", "dolly_in_front": "正面推进"}
        return " · ".join(({"female": "女", "male": "男"}[job["sex"]],
            {"landscape": "横屏", "portrait": "竖屏"}[job["aspect"]], cameras.get(job["camera_id"], "动作镜头")))
    if job["reference_kind"] == "garment":
        return {"shirts": "单件上衣", "shoes": "鞋子", "family_accessory": "配件",
                "pants": "单件裤子", "skirts": "单件裙子", "coats": "单件外套"}.get(job.get("slot"), "单件服装")
    if job["reference_kind"] == "hair":
        return "发型正面" if job.get("view") == "front" else "发型背面"
    return {"scene": "背景", "identity": "人物正面照"}.get(job["reference_kind"], "参考图")


def collect():
    motion = read(RUN / "motion_pilot_jobs.json")["jobs"]
    static = read(RUN / "static_pilot_jobs.json")["jobs"]
    full = read(RUN / "reference_jobs.json")["jobs"]
    carriers = {j["job_id"]: j for j in read(RUN / "carrier_jobs.json")["jobs"]}
    config = read(RUN / "motion_carriers.json")
    require(len(motion) == 4 and len(static) == 7 and len(full) == 2418, "Expected current 4 motion + 7 static / 2418 full definitions")
    require(len({j["job_id"] for j in motion + static}) == 11, "Duplicate pilot IDs")
    require(sum(j["reference_kind"] == "motion" for j in full) == 809, "Expected 809 full motion references")
    full_ids = {j["reference_id"] for j in full}
    binding_ids = {j["reference_id"] for j in read(RUN / "reference_bindings.json")["requirements"]}
    require(len(full_ids) == 2418 and full_ids == binding_ids, "Full original-reference ID binding is incomplete")
    require(all(j.get("source_job_id") in carriers and not j.get("status", "").startswith("blocked") for j in full), "Full entry contains missing/blocked carriers")
    require({(j["sex"], j["aspect"]) for j in motion} == {(s, a) for s in ("female", "male") for a in ("landscape", "portrait")}, "Pilot lacks sex/aspect coverage")
    require(sorted(j["reference_kind"] for j in static) == ["garment", "garment", "garment", "hair", "hair", "identity", "scene"], "Unexpected static pilot kinds")
    hair = [j for j in static if j["reference_kind"] == "hair"]
    require({j["view"] for j in hair} == {"front", "back"} and len({j["source_job_id"] for j in hair}) == 1, "Hair views must retain the same carrier")
    garment_slots = {j.get("slot") for j in static if j["reference_kind"] == "garment"}
    require(garment_slots == {"shirts", "shoes", "family_accessory"}, "Static pilot must include shirt, shared shoe and accessory")
    versions = {"reference_version": version(SCRIPTS / "ue_dataset_reference_v11.py"), "main_policy_version": version(SCRIPTS / "ue_dataset_render_v11.py")}
    indexed = {j["job_id"]: j for j in full}
    records = []
    for job in motion + static:
        jid = job["job_id"]; directory = RUN / "jobs" / jid
        require(indexed.get(jid) == job, "Pilot definition differs from full original-ID plan: " + jid)
        carrier = carriers[job["source_job_id"]]
        require(object_hash(carrier) == job.get("source_job_sha256"), "Carrier hash changed: " + jid)
        signature_value = {**versions, "job": job}
        if job.get("reference_kind") == "garment" and job.get("slot") == "shoes":
            signature_value["shoe_framing_version"] = 1
        expected = object_hash(signature_value)
        prep = read(directory / "prepared.json")
        require(prep.get("success") is True and prep.get("signature") == expected, "Preparation is missing/stale: " + jid)
        receipt = read(directory / "media_receipt.json")
        require(receipt.get("status") == "success" and receipt.get("render_signature") == expected, "Current successful media receipt missing: " + jid)
        provenance = receipt.get("render_provenance", {})
        require(provenance.get("signature") == expected, "Media lacks current MRQ binding: " + jid)
        relative_receipt = provenance.get("receipt_relative_path")
        require(relative_receipt, "Portable MRQ receipt path missing: " + jid)
        mrq_path = (RUN / relative_receipt).resolve()
        require(mrq_path.is_relative_to((RUN / "render_receipts").resolve()), "MRQ receipt escapes this Run")
        require(digest(mrq_path) == provenance.get("receipt_sha256"), "Bound MRQ receipt changed: " + jid)
        mrq = read(mrq_path)
        require(mrq.get("status") == "completed" and mrq.get("success") is True and mrq.get("job_signature") == expected, "Current MRQ not successful: " + jid)
        readiness = mrq.get("render_contract", {}).get("texture_readiness", {})
        require("FULLY_LOAD" in readiness.get("texture_streaming", ""), "Texture readiness policy absent: " + jid)
        media = receipt.get("media", {})
        if job["reference_kind"] == "motion":
            selection = config[job["sex"]]["selection"]; state = carrier["state"]
            require(state["identity"] == selection["character_id"] and state["hair"] == selection["choice"]["hair_id"] and state["wardrobe"] == selection["choice"] and state["hair_color"] == selection["hair_color"], "Motion pilot is not using latest frozen selection: " + jid)
            require((job["frames"], job["fps"], job["phase_seconds"], job["play_rate"]) == (300, 30, 0, 1), "Motion clock differs from production10")
            require((media.get("decoded_frames"), media.get("fps"), media.get("width"), media.get("height")) == (300, 30, job["width"], job["height"]), "Motion media profile mismatch: " + jid)
            require(media.get("verification") == "full_ffmpeg_decode_xerror", "Full motion decode receipt missing: " + jid)
            output = directory / "video.mp4"
            require(digest(output) == receipt.get("video_sha256"), "Motion video hash mismatch: " + jid)
        else:
            output = directory / "frames/frame_0000.png"
            require(set(output.parent.glob("*.png")) == {output}, "Expected one static reference PNG: " + jid)
            require(receipt.get("media_kind") == "png" and digest(output) == receipt.get("image_sha256"), "PNG media signature mismatch: " + jid)
            require((media.get("format"), media.get("frames"), media.get("width"), media.get("height"), media.get("bits_per_channel")) == ("PNG", 1, job["width"], job["height"], 8), "PNG profile mismatch: " + jid)
            require(bool(media.get("verification")), "PNG structural/decompression verification absent: " + jid)
        records.append({"job_id": jid, "reference_kind": job["reference_kind"], "source_job_id": job["source_job_id"],
            "source_job_sha256": job["source_job_sha256"], "render_signature": expected,
            "media": rel(output), "bytes": output.stat().st_size, "media_check": media,
            "mrq_receipt": rel(mrq_path), "media_receipt": rel(directory / "media_receipt.json"),
            "visual_acceptance": "pending_new_pilot_review"})
    return motion, static, full, carriers, config, versions, records


def main():
    motion, static, full, carriers, config, versions, records = collect()
    runrel = rel(RUN, ROOT)
    selected = {}
    for sex in ("female", "male"):
        job = next(j for j in motion if j["sex"] == sex); src = carriers[job["source_job_id"]]
        selected[sex] = {"selection": copy.deepcopy(config[sex]["selection"]),
            "wardrobe_labels": [a.get("label", a["asset_id"]) for a in src["appearance"]["wardrobe_assets"]],
            "source_job_id": config[sex]["source_job_id"]}
    result = {"schema": "dataset_reference_pilot_execution_result_v11_v1", "status": "11_current_policy_pilot_tasks_technical_pass_new_media_review_pending",
        "full_plan_ready": True, "full_reference_tasks": 2418, "static_tasks": 1609, "motion_tasks": 809,
        "verified_unique_pilot_tasks": 11, "motion_pilot_clips": 4, "static_pilot_images": 7, "remaining_full_tasks": 2407,
        "worker_versions": versions, "motion_carriers": selected, "user_presentation_design_accepted": True,
        "focused_tests_passed": 31, "focused_test_evidence_scope": "main session reported 31 focused tests passed; finalizer does not rerun tests",
        "shoe_framing": {"version": 1, "front_and_back_elevation_degrees": 25,
            "pilot_rendered_views": [j["view"] for j in static if j.get("slot") == "shoes"], "signature_scope": "garment shoes only; other six static tasks retain resume compatibility"},
        "prior_clear_12_main_6_reference_quality_accepted": True, "new_pilot_visual_acceptance": "pending",
        "server_verified": False, "whole_dataset_media_verified": False, "whole_repository_audit_run": False,
        "candidate_modified": False, "jobs_modified_by_finalizer": False, "ue_operations_by_finalizer": False,
        "validation_scope": "this 11-job receipt/hash/source-signature chain only; no fresh decode or UE operations", "records": records}
    md = ["# 本轮动作与参考图", "", "这里展示4段动作视频和7张参考图。请查看人物动作是否清楚、服装是否合适，以及鞋面和发型是否完整。", "", "[打开画廊](REVIEW.html) · [详细记录](REPORT.md)", "", "## 动作视频", ""]
    videos, images = [], []
    by_id = {j["job_id"]: j for j in motion + static}
    for record in records:
        job = by_id[record["job_id"]]; jid = job["job_id"]; media = record["media"]
        if job["reference_kind"] == "motion":
            label = gallery_label(job)
            md.append(f"- {label}：[播放]({media})")
            videos.append(f'<article><h3>{html.escape(label)}</h3><video controls preload="metadata" src="{media}"></video><p>10秒 · 每秒30帧</p></article>')
        else:
            label = gallery_label(job)
            images.append(f'<article><h3>{html.escape(label)}</h3><a href="{media}"><img loading="lazy" alt="{html.escape(label)}" src="{media}"></a></article>')
    md += ["", "## 静态参考图", "", "背景、单件衬衫、共享鞋、配件、身份及同一载体发型前后各一张。", ""]
    md += [f"- [{gallery_label(by_id[r['job_id']])}]({r['media']})" for r in records if r["reference_kind"] != "motion"]
    (RUN / "REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RUN / "REVIEW.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>本轮动作与参考图</title><style>body{background:#141922;color:#eef;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}article{background:#222c3b;padding:16px;border-radius:10px;overflow:hidden}video,img{width:100%;height:440px;object-fit:contain;background:#080b10}a{color:#9cf}p{overflow-wrap:anywhere}</style><h1>4段动作视频与7张参考图</h1><p>请查看人物动作是否清楚、服装是否合适，以及鞋面和发型是否完整。点击图片可以查看原图。</p><main>' + "".join(videos) + '</main><h2>参考图</h2><main>' + "".join(images) + '</main></html>', encoding="utf-8")
    carrier_lines = []
    for sex, values in selected.items():
        s = values["selection"]
        carrier_lines.append(f"- {sex}：{s['character_id']}，{', '.join(values['wardrobe_labels'])}，{s['choice']['hair_id']}，{s['hair_color']}。")
    report = f'''# 全量参考入口与本轮11项执行结果

**2418项原reference ID已绑定全量执行入口；本轮实际完成并核对的是4条动作视频和7张静态图。** 当前worker签名、carrier哈希、成功MRQ回执来源与媒体哈希一致；动作成片完整解码回执通过，静态PNG结构/解压检查通过。本报告不表示2407项其余任务已执行，也不表示服务器或全库验证。

展示方案及此前清晰版12主片/6图已获用户接受；本轮新增动作载体、灰棚地面和7图仍需[人工审查](REVIEW.md)。首轮女性宽裤草稿媒体已在同一job目录中被新轮替代，保留的是日志，不能声称旧媒体仍在。当前展示读取最新motion_carriers.json，为新选择与当前worker策略，不能把旧轮回执当成新轮成功。

鞋的正面/背面取景均改为抬高25°，便于看清鞋面与立体形状；本轮共享鞋正面使用shoe_framing_version=1新签名重渲染。该签名增量仅作用于garment/shoes，其他6静态任务可按原签名续用，不作无必要重渲染。主会话已完成31项直接相关测试并全部通过；本finalizer只核验回执链，不再次执行测试。

## 当前固定动作载体

''' + "\n".join(carrier_lines) + '''

动作直接复用对应已有production10资产：start0、rate1、30fps、300帧、10秒，不重新烘焙、慢放、重复或补hold。四样本覆盖男女横竖，包含front_full和orbit_120；灰背景/地面及灯光为当前reference worker实现。

## 绑定、续跑与范围

统一入口reference_jobs.json含1609静态图与809动作视频；carrier_jobs.json提供来源。scene保留原main ID/state，其余carrier为明确标识的参考组合，不新增数据图节点。原reference IDs、每步reference_links、28发型双载体完整组及既定视角保持；含单件鞋和配件，单件图无人体。完整组前后视角不能分开随机选载体。

每任务source_job_sha256绑定其carrier内容；prepare/render的当前worker版本签名随任务保存。PNG/MP4媒体回执绑定成功MRQ来源及文件SHA；缺少签名、旧版本、载体变动或媒体损坏时不得直接resume复用。原始视频帧清理后的复用仍须成功回执和成片哈希一致；本脚本不清理任何素材。

精确11项证据见EXECUTION_RESULT.json。这里只检查当前Run的11任务链，不重审候选图、不运行全库测试、不推断Linux/服务器画面和资源。R17及唯一current父计划继续；全量入口ready与全部媒体完成是不同状态。下一步审查新增11项，并按授权推进其余参考生成及Linux同节点资源/画面对照。
'''
    (RUN / "REPORT.md").write_text(report, encoding="utf-8")
    profile = read(PROFILE)
    profile.setdefault("motion_reference_presentation", {}).update(status="assets_selected_4_current_policy_pilot_technical_pass_new_media_review_pending",
        selected_character_ids={s: v["selection"]["character_id"] for s, v in selected.items()},
        selected_wardrobe_ids={s: v["selection"]["choice"] for s, v in selected.items()},
        selected_hair_ids={s: v["selection"]["choice"]["hair_id"] for s, v in selected.items()}, carrier_configuration=runrel + "/motion_carriers.json")
    profile.setdefault("static_reference_presentation", {}).update(status="design_confirmed_7_current_policy_pilot_technical_pass_new_media_review_pending")
    resolved_pending = {"motion_reference_asset_selection_and_local_sample", "full_reference_manifest_execution",
                        "reference_presentation_and_motion_carrier", "full_reference_execution_implementation"}
    profile["pending"] = list(dict.fromkeys([p for p in profile.get("pending", []) if p not in resolved_pending]
        + ["user_new_11_reference_pilot_media_review", "remaining_2407_reference_media_execution"]))
    execution = {k: result[k] for k in ("full_plan_ready", "full_reference_tasks", "static_tasks", "motion_tasks", "verified_unique_pilot_tasks", "motion_pilot_clips", "static_pilot_images", "remaining_full_tasks", "new_pilot_visual_acceptance", "server_verified")}
    execution.update(run_root=runrel, report=runrel + "/REPORT.md", review=runrel + "/REVIEW.md", result=runrel + "/EXECUTION_RESULT.json")
    execution.update(implementation_status="full_reference_execution_entry_ready", motion_carrier_selection="configured",
                     full_reference_media_completed=False, focused_tests_passed=31)
    profile["reference_execution"] = copy.deepcopy(execution)
    profile["motion_timing"]["dedicated_reference_integration_status"] = "4_current_policy_production10_reference_pilots_technical_pass_no_rebake"
    write(PROFILE, profile)
    statepath = DOC / "project_management/status/PROJECT_STATE.json"
    state = read(statepath); before = copy.deepcopy(state); branch = state["dataset_design_branch_20261021"]
    branch.update(status="configuration_accepted_reference_plan_ready_11_local_pilots_technical_pass_new_media_review_server_pending",
        next_action="审查当前固定载体的4动作视频与7静态参考图；按授权推进其余参考生成，随后进行Linux同节点小样及资源核验。")
    branch["media_profile"] = {"path": "render_preparation/VIDEO_PROFILE.json", **copy.deepcopy(profile)}
    branch.setdefault("render_preparation", {})["reference_execution"] = copy.deepcopy(execution)
    branch["render_preparation"]["motion_reference_presentation"] = copy.deepcopy(profile["motion_reference_presentation"])
    branch["render_preparation"]["static_reference_presentation"] = copy.deepcopy(profile["static_reference_presentation"])
    require({k:v for k,v in before.items() if k != "dataset_design_branch_20261021"} == {k:v for k,v in state.items() if k != "dataset_design_branch_20261021"}, "Unrelated project state changed")
    write(statepath, state)
    statuspath = DOC / "project_management/status/PROJECT_STATUS.md"
    text = statuspath.read_text(encoding="utf-8"); start = text.index("## 渲染准备："); end = text.index("## 当前数据集分支：", start)
    text = text[:start] + f'''## 渲染准备：参考全量入口ready，本轮11素材技术通过待审（2026-10-23）

修正后12主片/6图清晰度及参考展示方案已由用户确认。现已绑定原2418项reference IDs的全量入口，当前固定男女载体实跑4条动作视频，并完成背景、衬衫、共享鞋、配件、身份及同载体发型前后共7图；当前签名/来源/媒体技术检查通过。本轮新增11项尚待人工审查，不能写成全量媒体完成。见[本轮审查]({rel(RUN / 'REVIEW.md', statuspath.parent)})与[执行报告]({rel(RUN / 'REPORT.md', statuspath.parent)})。

动作复用原production10时钟，无重新烘焙。候选、源场景与原参考需求保持；其余参考生成、Linux同节点样片与资源核验待继续，尚无服务器或全库媒体验证。R17与唯一current父计划保持，其他分支不变。

''' + text[end:]
    statuspath.write_text(text, encoding="utf-8")
    technical = DOC / "technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md"
    section(technical, "2026-10-23：全量参考绑定与11任务小样交接", f'''本Technical拥有`{runrel}/`。`00_engine/scripts/dataset/reference_plan_v11.py`产生2080 main-schema兼容carrier与2418原ID参考任务、hair完整组/步骤绑定和4motion pilot；`00_engine/scripts/unreal/ue_dataset_reference_v11.py`拥有canonical静态PNG与灰棚动作参考执行。`run_dataset_render_v11.py`分流PNG/MP4，校验当前worker/载体/成功MRQ provenance；`encode_render_v11.py`支持safe ref_*并对动作300帧全解码。Run内`select_static_pilot.py`及`finalize_reference_pilot.py`为本次有界prototype辅助，不是全量完成证明。

当前4motion＋7static按现行版本技术通过；全量2418入口ready，其余2407未由本脚本验证。展示方案及之前clear12/6已接受，本轮新增素材人工审查pending。最新男女selection直接读取motion_carriers，女Workout_BlueOutfit取代首轮宽裤；旧草稿媒体同目录替代，仅日志保留。鞋前/后相机抬高25°，shoe_framing_version=1只使鞋重渲染，其他6图可续用。主会话31项focused tests通过；不改动作烘焙或相机规则。正式绑定与精确回执见[执行结果]({rel(RUN / 'EXECUTION_RESULT.json', technical.parent)})／[报告]({rel(RUN / 'REPORT.md', technical.parent)})。本次仅校验这条任务链，未改候选、job文件或其他状态分支，未执行UE、全库审计、Linux或服务器验证。''')
    plan = DOC / "project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md"
    section(plan, "R17 参考全量入口与11任务小样（2026-10-23）", f'''R17继续in_progress，父计划不结项。2418项原reference绑定与固定男女载体入口已ready，当前11任务技术检查通过；新增媒体人工审查、其余参考生成、Linux同节点/资源核验仍待完成。[本轮交接]({rel(RUN / 'REPORT.md', plan.parent)})不代表全量或服务器验证。''')
    write(RUN / "EXECUTION_RESULT.json", result)
    print(json.dumps({"status": result["status"], "verified_tasks": 11, "full_plan_tasks": 2418, "review": str(RUN / "REVIEW.md"), "unrelated_state_branches_unchanged": True}))


if __name__ == "__main__": main()
