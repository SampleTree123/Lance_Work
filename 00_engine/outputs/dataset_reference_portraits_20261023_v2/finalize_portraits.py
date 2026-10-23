"""Root-triggered, bounded six-image receipt validation and document handoff.

No UE operations, job changes, encoding, cleanup, or broad audits. Importing this
module does not finalize anything. Run only after the root finishes the render.
"""
from pathlib import Path
from types import SimpleNamespace
import ast
import copy
import hashlib
import html
import json
import os
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
OLD = RUN.parent / "dataset_reference_production_20261023_v1"
DOC = ROOT / "20_planning/data_design/character_creator/full_process"
PROFILE = RUN.parent / "dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json"
BRANCH = "dataset_design_branch_20261021"


def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def objhash(value): return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)
def rel(path, directory=RUN): return os.path.relpath(path, directory).replace("\\", "/")
def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
def section(path, title, body):
    text = path.read_text(encoding="utf-8")
    pattern = r"\n## " + re.escape(title) + r"\n[\s\S]*?(?=\n## |\Z)"
    block = "\n## " + title + "\n\n" + body.rstrip() + "\n"
    path.write_text(re.sub(pattern, lambda _: block, text) if re.search(pattern, text) else text.rstrip() + "\n" + block, encoding="utf-8")


def version(path):
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("Missing worker VERSION")


def current_signature():
    """Run the actual current pure signature function without importing UE code."""
    scripts = ROOT / "00_engine/scripts/unreal"
    worker = scripts / "ue_dataset_reference_v11.py"
    versions = {"reference_version": version(worker), "main_policy_version": version(scripts / "ue_dataset_render_v11.py")}
    tree = ast.parse(worker.read_text(encoding="utf-8-sig"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "signature")
    scope = {"VERSION": versions["reference_version"], "hashlib": hashlib, "json": json,
             "module": lambda name: SimpleNamespace(VERSION=versions["main_policy_version"])}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(worker), "exec"), scope)
    return scope["signature"], versions


def collect():
    jobs = read(RUN / "portrait_pilot_jobs.json")["jobs"]
    full = read(RUN / "reference_jobs.json")["jobs"]
    indexed = {j["job_id"]: j for j in full}
    carriers = {j["job_id"]: j for j in read(RUN / "carrier_jobs.json")["jobs"]}
    binding = read(RUN / "reference_bindings.json")
    require(len(full) == 2458 and sum(j["reference_kind"] == "motion" for j in full) == 809, "Expected 2458 total / 809 motion")
    require(sum(j["reference_kind"] == "identity" for j in full) == 80, "Expected 80 identity portraits")
    require(len(jobs) == 6 and len({j["job_id"] for j in jobs}) == 6, "Expected six distinct pilot images")
    identities = [j for j in jobs if j["reference_kind"] == "identity"]
    hair = [j for j in jobs if j["reference_kind"] == "hair"]
    require(len(identities) == 4 and {j["target_identity"] for j in identities} == {"CFD40_WF_002", "CFD40_AM_001"}, "Expected two identities, two portraits each")
    require(len(hair) == 2 and {j["view"] for j in hair} == {"front", "back"} and len({j["source_job_id"] for j in hair}) == 1, "Hair pair must retain the same carrier")
    for identity in {j["target_identity"] for j in identities}:
        pair = [j for j in identities if j["target_identity"] == identity]
        require(len(pair) == 2 and len({j["hair_id"] for j in pair}) == 2 and all(j["hair_color"] == "silver_white" for j in pair), "Identity pair hair mismatch")
    signature, versions = current_signature()
    records = []
    for job in jobs:
        jid = job["job_id"]; directory = RUN / "jobs" / jid
        require(indexed.get(jid) == job, "Pilot differs from full plan: " + jid)
        require(job.get("garments_present") is False, "Portrait garment hiding flag missing: " + jid)
        require(objhash(carriers[job["source_job_id"]]) == job["source_job_sha256"], "Carrier changed: " + jid)
        expected = signature(job)
        prepared = read(directory / "prepared.json")
        require(prepared.get("success") is True and prepared.get("signature") == expected, "Preparation missing or stale: " + jid)
        receipt = read(directory / "media_receipt.json")
        require(receipt.get("status") == "success" and receipt.get("render_signature") == expected, "Current successful media receipt missing: " + jid)
        provenance = receipt.get("render_provenance", {})
        require(provenance.get("signature") == expected, "Current MRQ signature missing: " + jid)
        require(provenance.get("receipt_relative_path"), "Portable MRQ path missing: " + jid)
        mrqpath = (RUN / provenance["receipt_relative_path"]).resolve()
        require(mrqpath.is_relative_to((RUN / "render_receipts").resolve()), "MRQ path escapes run")
        require(digest(mrqpath) == provenance.get("receipt_sha256"), "MRQ receipt hash changed: " + jid)
        mrq = read(mrqpath)
        require(mrq.get("success") is True and mrq.get("status") == "completed" and mrq.get("job_signature") == expected, "Current MRQ failed: " + jid)
        require("FULLY_LOAD" in mrq.get("render_contract", {}).get("texture_readiness", {}).get("texture_streaming", ""), "Full texture policy missing: " + jid)
        image = directory / "frames/frame_0000.png"
        require(set(image.parent.glob("*.png")) == {image}, "Expected one PNG: " + jid)
        require(receipt.get("media_kind") == "png" and digest(image) == receipt.get("image_sha256"), "PNG hash mismatch: " + jid)
        media = receipt.get("media", {})
        require((media.get("format"), media.get("frames"), media.get("width"), media.get("height"), media.get("bits_per_channel")) == ("PNG", 1, 1024, 1024, 8), "PNG profile mismatch: " + jid)
        require(media.get("verification") == "all_chunk_crc_and_full_idat_zlib_decode", "Full PNG verification receipt missing: " + jid)
        records.append({"job_id": jid, "reference_kind": job["reference_kind"], "target_identity": job["target_identity"],
            "hair_id": job["hair_id"], "hair_color": job["hair_color"], "view": job["render_view"],
            "source_job_id": job["source_job_id"], "source_job_sha256": job["source_job_sha256"], "render_signature": expected,
            "media": rel(image), "image_sha256": receipt["image_sha256"], "bytes": image.stat().st_size,
            "mrq_receipt": rel(mrqpath), "media_receipt": rel(directory / "media_receipt.json"), "media_check": media,
            "visual_acceptance": "pending_current_six_image_review"})
    oldbinding = read(OLD / "reference_bindings.json")
    require(binding["reference_links"] == oldbinding["reference_links"], "Original provenance links changed")
    require(len(binding["identity_reference_pools"]) == 40, "Expected 40 logical identity pools")
    oldresult = read(OLD / "EXECUTION_RESULT.json")
    accepted = [r for r in oldresult["records"] if r["reference_kind"] in ("motion", "scene", "garment")]
    require(len(accepted) == 8, "Expected previous four motion and four other static samples")
    return jobs, records, versions, accepted


def main():
    jobs, records, versions, accepted = collect()  # All checks precede document writes.
    runrel = rel(RUN, ROOT); oldrel = rel(OLD, ROOT)
    result = {"schema": "dataset_portrait_reference_execution_result_v11_v2",
        "status": "six_current_policy_images_technical_pass_user_review_pending", "full_plan_ready": True,
        "full_reference_tasks": 2458, "static_tasks": 1649, "motion_tasks": 809, "identity_logical_requirements": 40,
        "identity_portraits": 80, "additional_identity_references": 40, "verified_unique_pilot_tasks": 6,
        "static_pilot_images": 6, "motion_pilot_clips": 0, "remaining_current_run_tasks": 2452,
        "prior_accepted_other_samples": 8, "prior_accepted_other_run": oldrel,
        "previous_other_media_acceptance_basis": "User accepted the preceding samples except identity/hair; root relayed explicit scope",
        "new_pilot_visual_acceptance": "pending", "worker_versions": versions, "focused_tests_passed": 26,
        "focused_test_scope": "16 driver + 5 planner + 5 portrait worker tests reported by root; finalizer does not rerun tests",
        "root_representative_visual_inspection": "all six viewed; tight face/chin retained and hair garments hidden; user acceptance pending",
        "transfer_manifest_current_for_this_run": False,
        "upload_next_step": "Regenerate transfer manifest with --run-root dataset_reference_portraits_20261023_v2 at upload time; old v1 manifest excludes this run",
        "candidate_modified": False, "jobs_modified_by_finalizer": False, "ue_operations_by_finalizer": False,
        "whole_repository_audit_run": False, "server_verified": False, "whole_dataset_media_verified": False,
        "validation_scope": "six current signatures/carrier hashes/successful MRQ and full PNG verification receipts; previous eight acceptance linked separately",
        "records": records, "previous_accepted_media": accepted}
    byid = {j["job_id"]: j for j in jobs}
    hairlabels = {"HAIR_HB1_05": "高发髻", "HAIR_HB1_11": "高马尾", "HAIR_HB1_13": "武士发髻", "HAIR_HB3_01": "后梳短发"}
    cards = []; md = ["# 身份与发型新版参考图", "", "本轮为两位人物各两种白色发型，以及同一载体的黑发正背面，共6图。请检查脸部是否清楚、两种发型是否容易区分。", "", "[打开画廊](REVIEW.html) · [详细报告](REPORT.md)", ""]
    for identity, title in (("CFD40_WF_002", "女性身份：两种白发"), ("CFD40_AM_001", "男性身份：两种白发"), (None, "黑发参考：同一载体正背面")):
        group = [r for r in records if (r["reference_kind"] == "identity" and r["target_identity"] == identity) or (identity is None and r["reference_kind"] == "hair")]
        md += ["## " + title, ""]
        articles = []
        for record in group:
            job = byid[record["job_id"]]
            label = hairlabels.get(job["hair_id"], job["hair_id"]) if identity else ("正面" if job["view"] == "front" else "背面")
            md.append(f"- [{label}]({record['media']})")
            articles.append(f'<article><h3>{html.escape(label)}</h3><a href="{record["media"]}"><img alt="{html.escape(title + ' · ' + label)}" src="{record["media"]}"></a></article>')
        cards.append(f'<h2>{html.escape(title)}</h2><div class="pair">' + "".join(articles) + '</div>')
        md.append("")
    priorlink = rel(OLD / "REVIEW.html")
    md += ["## 之前已接受的其他样片", "", f"4条动作视频及背景、衬衫、鞋子、配件沿用上轮接受结果：[查看上轮画廊]({priorlink})。上轮身份和发型图是历史版本，本页6图为当前待审版本。", "", "身份图紧贴面部取景，不刻意展示脖子或肩膀；为保全下巴轮廓，可保留极细下缘。本轮只拍两人，未逐人验收其余38人。"]
    (RUN / "REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RUN / "REVIEW.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>身份与发型新版参考图</title><style>body{background:#151a24;color:#eef;font:16px system-ui;max-width:1180px;margin:30px auto;padding:0 20px}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{background:#253043;border-radius:10px;padding:14px}img{display:block;width:100%;height:auto}a{color:#a9d4ff}p{line-height:1.7}@media(max-width:650px){.pair{grid-template-columns:1fr}}</style><h1>身份与发型新版参考图</h1><p>两位人物各两种白发，另有同载体黑发正背面。点击图片查看原图。当前6图技术检查通过，等待人工确认。身份图紧贴脸部；保留下巴轮廓时允许极细下缘。</p>' + "".join(cards) + f'<h2>之前已接受的其他样片</h2><p><a href="{priorlink}">4条动作视频与背景、衬衫、鞋、配件</a>继续沿用上轮接受结果；该画廊的旧身份、发型图只作历史记录。</p></html>', encoding="utf-8")
    (RUN / "REPORT.md").write_text(f'''# 身份双发型与去服装参考小样

当前全量计划为2458项：1649静态图（含40人各两种白发、共80身份图）与809动作视频。本轮实际核验的是4张身份图和2张同载体黑发图；6图当前worker签名、载体哈希、成功MRQ来源、PNG哈希及完整结构／解压检查回执通过，仍待[人工审查](REVIEW.md)。不能推断40人全部构图已验收，也没有服务器或全库媒体验证。

用户已接受上轮除身份、发型以外的样片：4动作视频及背景、衬衫、鞋子、配件。它们继续使用[旧运行报告]({rel(OLD / 'REPORT.md')})和[原画廊]({priorlink})，原报告中的11项／2418任务是当时历史状态，保留不回写；本轮新参考入口以此目录为准。上轮身份、发型已由当前方案替代，尚未接受本轮新图。

身份图统一正式白色silver_white，每人两种不同既有发型，允许多个人物复用同一组合；通过固定头部锚点收紧脸部构图，不刻意展示脖子或肩膀，为保全下巴轮廓可留极细下缘，外围头发可以裁切。身份及头发任务garments_present=false，拍摄时隐藏衣物而保留载体原穿搭来源；头发图仍用原黑色、原两个载体和既定相机，本小样只核对其中同一载体前后两图。

## 全量绑定与复现入口

reference_jobs.json／static_reference_jobs.json／motion_reference_jobs.json及carrier_jobs.json为本轮入口，新增40个身份参考ID，不新增或更改已采用图节点、边、链和主任务。每个原身份需求作为逻辑池保留，第一图沿用原ID，第二图稳定派生；identity_reference_pools.json列出40个两图池。reference_bindings.json的reference_links保留原来源；实际使用effective_reference_links，每条身份编辑步骤只选一图，记录selection_seed、原reference_ids和选中ID。非身份链接、28发型双载体组和809动作任务保持。完整发型前后图仍作为一组选择载体。

离线直接核验见[OFFLINE_VALIDATION.json](OFFLINE_VALIDATION.json)，发型目录及既有来源证据见[IDENTITY_HAIR_SELECTION.json](IDENTITY_HAIR_SELECTION.json)，生成命令见[PLAN_README.md](PLAN_README.md)。主会话报告16项驱动＋5项计划＋5项小样实现测试，共26项通过；本收尾脚本不重复运行测试，不扩展全库审计。精确6图回执见[EXECUTION_RESULT.json](EXECUTION_RESULT.json)。当前Run其余2452项未由本脚本核验；已接受旧8项另按原来源引用，未计作本Run新渲染。

当前驱动的默认参考运行目录已切换到本v2。旧v1迁移清单不包含本目录，不能作为当前上传清单；实际上传时需以本目录的--run-root重新生成清单，本轮延后资源大目录统计刷新，不重复扫描约107GiB素材。

本Technical所有者为DATASET_DESIGN_EXPLORATION_20261021.md；finalize_portraits.py仅为该Run有界prototype收尾，不操作UE、不改任务、不清理媒体。R17继续in_progress，唯一current父计划及其他分支保持；下一步审查本轮6图，再按授权生成其余参考及进行Linux同节点／资源核验。
''', encoding="utf-8")
    execution = {k: result[k] for k in ("status", "full_plan_ready", "full_reference_tasks", "static_tasks", "motion_tasks", "identity_logical_requirements", "identity_portraits", "verified_unique_pilot_tasks", "static_pilot_images", "motion_pilot_clips", "remaining_current_run_tasks", "prior_accepted_other_samples", "new_pilot_visual_acceptance", "server_verified", "focused_tests_passed")}
    execution.update(run_root=runrel, report=runrel + "/REPORT.md", review=runrel + "/REVIEW.md", result=runrel + "/EXECUTION_RESULT.json", full_reference_media_completed=False,
                     prior_other_media_run=oldrel, current_run_scope="six_portrait_images_only")
    profile = read(PROFILE)
    previous = copy.deepcopy(profile.get("reference_execution"))
    if previous and previous.get("run_root") != runrel:
        profile.setdefault("reference_execution_history", []).append(previous)
    profile.setdefault("static_reference_presentation", {}).update(status="identity_hair_design_confirmed_six_image_technical_pass_user_review_pending",
        identity="two_different_existing_hairstyles_per_identity_all_silver_white_select_one_per_identity_step",
        identity_hair_color="silver_white", identity_framing="tight_face_no_intentional_neck_or_shoulders_keep_chin_thin_lower_margin_allowed",
        identity_garments_present=False, hair_garments_present=False,
        hair="retain_existing_black_two_carriers_and_camera_views_hide_garments_select_whole_group",
        changes_to_existing_reference_views_or_counts=True, identity_reference_pool_count=40, identity_reference_image_count=80)
    profile["reference_execution"] = copy.deepcopy(execution)
    profile["pending"] = list(dict.fromkeys([p for p in profile.get("pending", []) if p not in ("user_new_11_reference_pilot_media_review", "remaining_2407_reference_media_execution")]
        + ["user_current_six_identity_hair_image_review", "remaining_current_reference_plan_execution"]))
    statepath = DOC / "project_management/status/PROJECT_STATE.json"
    state = read(statepath); before = copy.deepcopy(state); branch = state[BRANCH]
    branch.update(status="configuration_accepted_2458_reference_plan_ready_six_portrait_images_technical_pass_review_pending",
        next_action="审查当前身份双白发与去衣物发型6图；其余已接受样片沿用，再按授权生成其余参考并进行Linux同节点／资源核验。")
    branch["media_profile"] = {"path": "render_preparation/VIDEO_PROFILE.json", **copy.deepcopy(profile)}
    prep = branch.setdefault("render_preparation", {})
    if prep.get("reference_execution", {}).get("run_root") != runrel:
        prep.setdefault("reference_execution_history", []).append(copy.deepcopy(prep.get("reference_execution", {})))
    prep["reference_execution"] = copy.deepcopy(execution)
    prep["static_reference_presentation"] = copy.deepcopy(profile["static_reference_presentation"])
    require({k:v for k,v in before.items() if k != BRANCH} == {k:v for k,v in state.items() if k != BRANCH}, "Unrelated project state changed")
    # Preserve the pre-finalization owner snapshots inside this Run once.
    snapshot = RUN / "PRE_FINALIZATION_AUTHORITIES.json"
    if not snapshot.exists(): write(snapshot, {"video_profile": read(PROFILE), "dataset_design_branch": before[BRANCH]})
    write(PROFILE, profile); write(statepath, state)
    statuspath = DOC / "project_management/status/PROJECT_STATUS.md"
    text = statuspath.read_text(encoding="utf-8")
    oldtitle = "## 渲染准备：参考全量入口ready，本轮11素材技术通过待审（2026-10-23）"
    text = text.replace(oldtitle, "## 历史参考首轮：2418任务与11项技术小样（2026-10-23）")
    statuspath.write_text(text, encoding="utf-8")
    title = "渲染准备：身份双白发与去衣物6图技术通过待审（2026-10-23）"
    body = f"当前参考入口为2458项（1649静态，其中80身份图；809动作），新运行两人各两种白发＋同一载体黑发前后共6图技术检查通过，等待[人工审查]({rel(RUN / 'REVIEW.md', statuspath.parent)})。上轮4动作和背景、衬衫、鞋、配件已获用户接受并沿用；旧身份／发型仅保留历史。新图紧贴面部，不刻意展示脖肩，为保留下巴可留极细下缘，未逐人验收全部40人。\n\n每条身份步骤从两图中确定性随机选一，保留原链接来源；新增40参考ID，已采用节点、边、链和主任务保持。详见[本轮报告]({rel(RUN / 'REPORT.md', statuspath.parent)})。仅26项直接测试及6图回执链通过，未做全库／服务器验证；旧迁移清单不含v2，上传时再重新生成。下一步审查6图再继续其余参考和Linux同节点／资源核验，R17及唯一current父计划保持。"
    text = statuspath.read_text(encoding="utf-8")
    pattern = r"\n## " + re.escape(title) + r"\n[\s\S]*?(?=\n## |\Z)"
    text = re.sub(pattern, "", text)
    first = text.index("\n## ")
    statuspath.write_text(text[:first] + "\n## " + title + "\n\n" + body + "\n" + text[first:], encoding="utf-8")
    technical = DOC / "technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md"
    section(technical, "2026-10-23：身份双白发、有效绑定与去衣物6图", f"本Technical拥有`{runrel}/`及Run内`finalize_portraits.py`（有界prototype）。`reference_plan_v11.py --identity-portrait-variants`生成2458参考任务、2120载体，40逻辑身份池各两种silver_white发型，新增40参考ID；原reference_links保留来源，effective_reference_links记录每条身份步骤单图选择及selection_seed。非身份绑定、发型双载体组与809动作任务保持，不修改已采用图或主作业。\n\nworker消费garments_present=false隐藏身份／发型衣物；身份framing_policy=tight_face_no_neck_or_shoulders采用固定脸部锚点，允许极细下缘保留下巴。signature的portrait_presentation_version与identity_framing_version使相关旧图失效，保留其他类别续跑兼容。两人4身份图＋同载体黑发前后2图当前签名、成功MRQ和完整PNG检查回执通过，16＋5＋5共26项直接测试通过；仅技术通过、人工待审，不保证其余38人构图。此前其他8项沿用用户接受，旧身份／发型和2418计数保留历史。驱动默认参考目录为v2；旧v1迁移清单不含v2，上传时用新--run-root重建，本轮延后大目录统计。证据与命令见[本轮报告]({rel(RUN / 'REPORT.md', technical.parent)})及[PLAN_README]({rel(RUN / 'PLAN_README.md', technical.parent)})。本次只同步当前绑定、展示和证据指针，不运行全树审计、catalog重建、UE或服务器验证。")
    plan = DOC / "project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md"
    section(plan, "R17 最新参考：双白发与去衣物6图（2026-10-23）", f"R17继续in_progress，本父计划唯一current。用户接受前轮除身份／发型外的8项；本轮更新为2458参考任务（新增40身份图），两人双白发与去衣物黑发前后共6图技术通过、人工待审，原图／主任务保持。最新[报告]({rel(RUN / 'REPORT.md', plan.parent)})与[审查]({rel(RUN / 'REVIEW.md', plan.parent)})覆盖前轮身份／发型规则，其他样片接受沿用；剩余参考生成、Linux同节点／资源验证及全量生产继续待完成，不结项或晋升Gate。")
    write(RUN / "EXECUTION_RESULT.json", result)
    write(RUN / "DOCUMENTATION_SYNC.json", {"status": "bounded_owner_sync_passed", "modified_owners": [rel(p, ROOT) for p in (PROFILE, statepath, statuspath, technical, plan)],
        "unrelated_project_state_branches_unchanged": True, "parent_R17": "in_progress", "current_parent_plan_preserved": True,
        "whole_audit_or_catalog_rebuild": False, "source_graph_and_job_files_written": False})
    print(json.dumps({"status": result["status"], "verified_images": 6, "full_reference_tasks": 2458, "review": str(RUN / "REVIEW.md")}))


if __name__ == "__main__": main()
