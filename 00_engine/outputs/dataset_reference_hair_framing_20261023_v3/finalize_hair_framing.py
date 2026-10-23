"""Root-triggered four-image receipt handoff. No UE, job edits or broad scans."""
from pathlib import Path
import copy
import html
import importlib.util
import json
import os
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
IDENTITY = RUN.parent / "dataset_reference_portraits_20261023_v2"
OTHER = RUN.parent / "dataset_reference_production_20261023_v1"
DOC = ROOT / "20_planning/data_design/character_creator/full_process"
PROFILE = RUN.parent / "dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json"
BRANCH = "dataset_design_branch_20261021"
# Reuse the already reviewed pure helpers; importing the v2 finalizer has no writes.
spec = importlib.util.spec_from_file_location("portrait_handoff_helpers", IDENTITY / "finalize_portraits.py")
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
read, write, require, digest, objhash = H.read, H.write, H.require, H.digest, H.objhash
def rel(path, directory=RUN): return os.path.relpath(path, directory).replace("\\", "/")


def collect():
    jobs = read(RUN / "hair_framing_pilot_jobs.json")["jobs"]
    summary = read(RUN / "PLAN_SUMMARY.json")
    require((summary["total_reference_jobs"], summary["static_images"], summary["motion_clips"], summary["identity_portraits"]) == (2458, 1649, 809, 80), "Unexpected plan counts")
    require(len(jobs) == 4 and len({j["job_id"] for j in jobs}) == 4, "Expected four distinct hair images")
    require({(j["carrier_sex"], j["view"]) for j in jobs} == {(s, v) for s in ("female", "male") for v in ("front", "back")}, "Missing sex/view pair")
    carriers = {j["job_id"]: j for j in read(RUN / "carrier_jobs.json")["jobs"]}
    signature, versions = H.current_signature()  # Actual current worker.signature AST; no UE imports.
    records = []
    for job in jobs:
        jid = job["job_id"]; directory = RUN / "jobs" / jid
        require(job["reference_kind"] == "hair" and job.get("framing_policy") == "shared_head_shoulders", "Wrong hair policy")
        require(job.get("garments_present") is True and job.get("neutral_garment_color") is True, "Missing simple gray clothing flags")
        require(objhash(carriers[job["source_job_id"]]) == job["source_job_sha256"], "Carrier changed: " + jid)
        expected = signature(job); prep = read(directory / "prepared.json"); receipt = read(directory / "media_receipt.json")
        require(prep.get("success") is True and prep.get("signature") == expected, "Stale preparation: " + jid)
        require(receipt.get("status") == "success" and receipt.get("render_signature") == expected, "Missing current media success: " + jid)
        provenance = receipt.get("render_provenance", {})
        require(provenance.get("signature") == expected and provenance.get("receipt_relative_path"), "Current MRQ binding missing")
        mrqpath = (RUN / provenance["receipt_relative_path"]).resolve()
        require(mrqpath.is_relative_to((RUN / "render_receipts").resolve()) and digest(mrqpath) == provenance.get("receipt_sha256"), "MRQ receipt path/hash mismatch")
        mrq = read(mrqpath)
        require(mrq.get("success") is True and mrq.get("status") == "completed" and mrq.get("job_signature") == expected, "Current MRQ failed")
        image = directory / "frames/frame_0000.png"; media = receipt.get("media", {})
        require(set(image.parent.glob("*.png")) == {image} and digest(image) == receipt.get("image_sha256"), "PNG count/hash mismatch")
        require((media.get("format"), media.get("frames"), media.get("width"), media.get("height"), media.get("bits_per_channel")) == ("PNG", 1, 1024, 1024, 8), "PNG profile mismatch")
        require(media.get("verification") == "all_chunk_crc_and_full_idat_zlib_decode", "Full PNG verification receipt missing")
        records.append({"job_id": jid, "sex": job["carrier_sex"], "view": job["view"], "hair_id": job["hair_id"],
            "carrier_identity": job["carrier_identity"], "source_job_id": job["source_job_id"], "source_job_sha256": job["source_job_sha256"],
            "render_signature": expected, "media": rel(image), "image_sha256": receipt["image_sha256"],
            "media_check": media, "media_receipt": rel(directory / "media_receipt.json"), "mrq_receipt": rel(mrqpath)})
    return records, versions


def main():
    records, versions = collect()  # No document write before all four receipt chains pass.
    runrel = rel(RUN, ROOT)
    result = {"schema": "dataset_hair_framing_execution_result_v11_v3", "status": "four_hair_images_technical_pass_user_review_pending",
        "full_plan_ready": True, "full_reference_tasks": 2458, "static_tasks": 1649, "motion_tasks": 809, "identity_portraits": 80,
        "hair_reference_images": 112, "verified_unique_pilot_tasks": 4, "static_pilot_images": 4, "motion_pilot_clips": 0,
        "remaining_current_run_tasks": 2454, "new_pilot_visual_acceptance": "pending", "focused_tests_passed": 27,
        "focused_test_scope": "16 driver + 6 planner + 5 portrait tests reported by root; not rerun by finalizer",
        "camera": {"policy": "shared_head_shoulders", "distance_cm": 110, "center_z_relative_to_head_cm": 3,
                   "horizontal_fov_degrees": 28, "width": 1024, "height": 1024, "same_numeric_parameters_both_sexes": True,
                   "coverage": "most hair including majority of long hair; longest styles may crop"},
        "garments_present": True, "neutral_garment_color": True, "worker_versions": versions, "records": records,
        "identity_jobs_unchanged_from_v2": True, "identity_sample_run": rel(IDENTITY, ROOT), "prior_accepted_other_samples": 8,
        "prior_other_media_run": rel(OTHER, ROOT), "candidate_or_jobs_modified_by_finalizer": False,
        "server_verified": False, "whole_dataset_media_verified": False, "whole_repository_audit_run": False,
        "transfer_manifest_current_for_this_run": False, "upload_next_step": "Regenerate transfer manifest with current v3 --run-root at upload time"}
    md = ["# 发型参考：男女统一构图", "", "男女使用同一组头部相对相机参数，展示大部分发型；简单灰衣物遮住入镜身体。本轮4图技术通过，等待人工确认。", "", "[打开画廊](REVIEW.html) · [详细报告](REPORT.md)", ""]
    rows = []
    for sex, label in (("male", "男性：正面与背面"), ("female", "女性：正面与背面")):
        md += ["## " + label, ""]; cards = []
        for view in ("front", "back"):
            r = next(r for r in records if r["sex"] == sex and r["view"] == view); title = "正面" if view == "front" else "背面"
            md.append(f"- [{title}]({r['media']})")
            cards.append(f'<article><h3>{title}</h3><a href="{r["media"]}"><img alt="{label} {title}" src="{r["media"]}"></a></article>')
        rows.append(f'<h2>{label}</h2><div class="pair">' + "".join(cards) + '</div>'); md.append("")
    md += [f"身份双白发和脸部取景保持：[查看v2身份小样]({rel(IDENTITY / 'REVIEW.html')})（其中旧发型图为历史版本）。", "", f"已接受的4动作视频及背景、衬衫、鞋、配件：[查看原样片]({rel(OTHER / 'REVIEW.html')})。"]
    (RUN / "REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RUN / "REVIEW.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>发型参考：男女统一构图</title><style>body{background:#151a24;color:#eef;font:16px system-ui;max-width:1150px;margin:30px auto;padding:0 20px}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{background:#253043;padding:14px;border-radius:10px}img{width:100%;display:block}a{color:#adf}p{line-height:1.7}</style><h1>发型参考：男女统一构图</h1><p>头部相对距离110厘米、中心高3厘米、视角28°，男女相同。展示大部分发型，最长发型允许裁切；简单灰衣物覆盖入镜身体。当前4图技术通过，等待人工确认。</p>' + "".join(rows) + f'<p><a href="{rel(IDENTITY / "REVIEW.html")}">身份双白发沿用v2</a>（旧发型图为历史版本） · <a href="{rel(OTHER / "REVIEW.html")}">其他已接受样片</a></p></html>', encoding="utf-8")
    (RUN / "REPORT.md").write_text(f'''# 发型统一构图与简单灰衣物小样

当前2458项参考计划保持：1649静态（含80身份图、112发型图）与809动作。本轮完成男女各正背面共4图的当前worker签名、载体哈希、成功MRQ来源及PNG完整结构／解压检查回执核验；[当前画廊](REVIEW.md)等待用户确认。不能推断其余发型或全部媒体已接受。

男女相同头部相对相机参数：中心Z+3cm、距离110cm、水平FOV28°、1024方图，正背面仅方向对应变化。目标为展示大部分发型（含多数长发），不要求最长发型完整入镜。固定简单衣物覆盖入镜身体，拍摄副本中统一灰色；源服装几何和源材质不改写。具体衣物以[hair_carrier_clothing.json](hair_carrier_clothing.json)为准。签名shared_hair_framing_version=1使旧发型构图失效，其他类别保持续跑兼容。

身份80图、原ID、原始及有效绑定、发型双载体组、809动作与v2保持，详见[离线检查](OFFLINE_VALIDATION.json)；身份双白发紧脸小样继续由[v2审查]({rel(IDENTITY / 'REVIEW.html')})提供。v2发型图和前轮任务数字保留历史，本v3为当前发型入口。此前4动作及背景、衬衫、鞋、配件共8项沿用用户接受：[原样片]({rel(OTHER / 'REVIEW.html')})。

主会话报告16驱动＋6计划＋5小样测试，共27项通过。本收尾仅检查4图回执链，不重复测试、不重审配置图、不扫描大资源树、不操作UE。精确结果见[EXECUTION_RESULT.json](EXECUTION_RESULT.json)，重建命令见[PLAN_README.md](PLAN_README.md)。旧迁移清单不含v3，上传时需用当前--run-root重新生成；本轮不刷新约107GiB资源统计。R17继续in_progress，唯一current父计划保持；下一步人工审查4图，再继续其余参考及Linux同节点／资源核验。
''', encoding="utf-8")
    execution = {k: result[k] for k in ("status", "full_plan_ready", "full_reference_tasks", "static_tasks", "motion_tasks", "identity_portraits", "hair_reference_images", "verified_unique_pilot_tasks", "static_pilot_images", "motion_pilot_clips", "remaining_current_run_tasks", "new_pilot_visual_acceptance", "server_verified", "focused_tests_passed")}
    execution.update(run_root=runrel, report=runrel + "/REPORT.md", review=runrel + "/REVIEW.md", result=runrel + "/EXECUTION_RESULT.json", full_reference_media_completed=False,
                     identity_sample_run=rel(IDENTITY, ROOT), prior_other_media_run=rel(OTHER, ROOT), prior_accepted_other_samples=8)
    profile = read(PROFILE); previous = copy.deepcopy(profile.get("reference_execution"))
    if previous and previous.get("run_root") != runrel: profile.setdefault("reference_execution_history", []).append(previous)
    profile.setdefault("static_reference_presentation", {}).update(status="shared_hair_four_images_technical_pass_user_review_pending",
        hair="same_head_relative_camera_both_sexes; most_hair_visible_longest_may_crop; fixed_simple_gray_clothes; retain_two_carriers_front_back_groups",
        hair_garments_present=True, hair_neutral_garment_color=True, hair_camera=copy.deepcopy(result["camera"]), hair_clothing_configuration=runrel + "/hair_carrier_clothing.json")
    profile["reference_execution"] = copy.deepcopy(execution)
    profile["pending"] = list(dict.fromkeys([p for p in profile.get("pending", []) if p != "user_current_six_identity_hair_image_review"] + ["user_current_four_shared_hair_image_review"]))
    statepath = DOC / "project_management/status/PROJECT_STATE.json"; state = read(statepath); before = copy.deepcopy(state); branch = state[BRANCH]
    snapshot = RUN / "PRE_FINALIZATION_AUTHORITIES.json"
    if not snapshot.exists(): write(snapshot, {"video_profile": read(PROFILE), "dataset_design_branch": before[BRANCH]})
    branch.update(status="2458_reference_plan_shared_hair_four_images_technical_pass_user_review_pending", next_action="审查男女统一相机与简单灰衣物发型4图；身份双白发沿用v2，其余已接受样片沿用，之后继续参考及Linux同节点／资源核验。")
    branch["media_profile"] = {"path": "render_preparation/VIDEO_PROFILE.json", **copy.deepcopy(profile)}
    prep = branch.setdefault("render_preparation", {})
    if prep.get("reference_execution", {}).get("run_root") != runrel: prep.setdefault("reference_execution_history", []).append(copy.deepcopy(prep.get("reference_execution", {})))
    prep["reference_execution"] = copy.deepcopy(execution); prep["static_reference_presentation"] = copy.deepcopy(profile["static_reference_presentation"])
    require({k:v for k,v in before.items() if k != BRANCH} == {k:v for k,v in state.items() if k != BRANCH}, "Unrelated state changed")
    write(PROFILE, profile); write(statepath, state)
    statuspath = DOC / "project_management/status/PROJECT_STATUS.md"; text = statuspath.read_text(encoding="utf-8")
    text = text.replace("## 渲染准备：身份双白发与去衣物6图技术通过待审（2026-10-23）", "## 历史身份与发型v2：双白发与去衣物6图（2026-10-23）")
    title = "渲染准备：男女同相机发型4图技术通过待审（2026-10-23）"
    text = re.sub(r"\n## " + re.escape(title) + r"\n[\s\S]*?(?=\n## |\Z)", "", text); first = text.index("\n## ")
    body = f"2458参考任务保持；当前发型使用男女相同头部相对相机参数（110cm／Z+3cm／FOV28°／1024方图），展示大部分发型，最长发型允许裁切；简单灰衣物覆盖入镜身体。男女正背面4图当前回执链技术通过，待[人工审查]({rel(RUN / 'REVIEW.md', statuspath.parent)})。身份80图及v2双白发紧脸小样保持，其他8项沿用用户接受；旧发型图保留历史。\n\n27项直接测试通过，未做全库或服务器验证；当前[报告]({rel(RUN / 'REPORT.md', statuspath.parent)})为v3，旧迁移清单需在上传时重新生成。下一步审查4图，再继续其余参考及Linux同节点／资源核验；R17与唯一current父计划保持。"
    statuspath.write_text(text[:first] + "\n## " + title + "\n\n" + body + "\n" + text[first:], encoding="utf-8")
    technical = DOC / "technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md"
    H.section(technical, "2026-10-23：男女统一发型相机与灰衣物v3", f"本Technical拥有`{runrel}/`及`finalize_hair_framing.py`（有界prototype，复用v2收尾脚本的纯签名／读写helper）。`reference_plan_v11.py --identity-portrait-variants --shared-hair-framing --hair-carrier-clothing <config>`保持2458任务及80身份／809动作，112发型任务设置framing_policy=shared_head_shoulders、garments_present=true、neutral_garment_color=true；carrier服装、hair_id与appearance/hash一致。\n\nworker固定男女头部相对距离110cm、中心Z+3cm、FOV28°、1024方图，展示大部分发型，最长可裁切；仅owned stage的衣物材质改灰。shared_hair_framing_version=1使相关旧图失效。4图当前签名／成功MRQ／PNG完整检查回执通过，16＋6＋5共27直接测试通过，人工待审；不保证112图全验。身份v2规则及其他8样片接受保持，原图、链接和主任务不改。当前[报告]({rel(RUN / 'REPORT.md', technical.parent)})与[命令]({rel(RUN / 'PLAN_README.md', technical.parent)})替代旧发型入口，旧报告保留历史。上传时以v3重建迁移清单，本轮不重复大目录扫描／catalog或全库审计。")
    plan = DOC / "project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md"
    H.section(plan, "R17 最新参考：同相机灰衣物发型v3（2026-10-23）", f"R17继续in_progress，父计划唯一current。2458任务保持，发型男女同参数、简单灰衣物；男女正背4图技术通过待审，身份v2与其他接受结果沿用。最新[报告]({rel(RUN / 'REPORT.md', plan.parent)})／[审查]({rel(RUN / 'REVIEW.md', plan.parent)})为当前发型入口，旧版本保留。全量参考、Linux同节点／资源核验及上传清单重建待继续，不结项或晋升Gate。")
    write(RUN / "EXECUTION_RESULT.json", result)
    write(RUN / "DOCUMENTATION_SYNC.json", {"status": "bounded_owner_sync_passed", "modified_owners": [rel(p, ROOT) for p in (PROFILE, statepath, statuspath, technical, plan)], "unrelated_project_state_branches_unchanged": True, "R17": "in_progress", "whole_audit_or_resource_scan": False})
    print(json.dumps({"status": result["status"], "verified_images": 4, "review": str(RUN / "REVIEW.md")}))


if __name__ == "__main__": main()
