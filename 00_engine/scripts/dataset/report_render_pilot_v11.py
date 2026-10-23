"""Repeatable offline report of a partial or finished v11 render pilot.

Reads receipts, JSON lines and file metadata. Does not connect to UE, decode
media, hash raw frames, or alter driver/worker state. Existing encoder receipts
are the evidence for full media decoding; current file presence is rechecked.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

WORKSPACE = Path(__file__).resolve().parents[3]
PAIRS = [(0, 1, "camera"), (0, 2, "action"), (0, 5, "wardrobe"), (5, 18, "identity"),
         (967, 978, "hair_color"), (967, 979, "hair"), (3775, 3792, "hair"), (4040, 4058, "hair_color")]


def read(path, errors=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        if Path(path).exists() and errors is not None:
            errors.append({"file": str(path), "error": str(exc), "meaning": "may be changing during report snapshot"})
        return None


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, AttributeError):
        return None


def elapsed(start, end):
    a, b = timestamp(start), timestamp(end)
    return b - a if a is not None and b is not None and b >= a else None


def stats(values):
    values = sorted(float(v) for v in values if isinstance(v, (int, float)) and v >= 0)
    if not values:
        return {"n": 0}
    return {"n": len(values), "min": min(values), "median": statistics.median(values),
            "mean": statistics.mean(values), "max": max(values)}


def events(run, errors):
    output = []
    for path in sorted(run.glob("*driver.log")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            try:
                event = json.loads(line)
            except ValueError:
                continue  # A running writer may not have emitted its full line yet.
            if isinstance(event, dict):
                output.append(dict(event, source_file=path.name, source_line=line_no))
    return output


def gpu_samples(path):
    if not path.exists():
        return []
    output = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                output.append({key: float(row[key]) for key in ("unix_time", "used_mib", "gpu_percent", "power_w")})
            except (KeyError, TypeError, ValueError):
                continue
    return output


def gpu_summary(samples):
    if not samples:
        return {"samples": 0, "status": "not_sampled"}
    return {"samples": len(samples), "sample_window_seconds": max(s["unix_time"] for s in samples) - min(s["unix_time"] for s in samples),
            "peak_used_mib": max(s["used_mib"] for s in samples), "peak_gpu_percent": max(s["gpu_percent"] for s in samples),
            "peak_power_w": max(s["power_w"] for s in samples), "average_gpu_percent": statistics.mean(s["gpu_percent"] for s in samples),
            "scope": "sampled points only; may miss peaks; not necessarily entire pilot"}


def runtime_readback(job, snapshot):
    if not snapshot:
        return {"status": "missing", "meaning": "No PIE mesh readback saved for this job"}
    components = [{"actor": actor.get("actor"), **component} for actor in snapshot.get("actors", []) for component in actor.get("components", [])]
    actual = {c["mesh"] for c in components if c.get("mesh") and c.get("visible") is True}
    appearance = job.get("appearance", {})
    expected = {m["path"] for m in appearance.get("identity", {}).get("meshes", []) if m.get("path")}
    expected.update(m["path"] for m in appearance.get("hair", {}).get("fit", {}).get("meshes", []) if m.get("path"))
    expected.update(path for asset in appearance.get("wardrobe_assets", []) for path in asset.get("mesh_paths", []))
    missing, unexpected = sorted(expected - actual), sorted(actual - expected)
    return {"status": "matching_expected_visible_meshes" if not missing and not unexpected else "mesh_difference_needs_review",
            "world": snapshot.get("world"), "attempt_id": snapshot.get("attempt_id"), "stage": snapshot.get("stage"),
            "expected_mesh_count": len(expected), "actual_visible_mesh_count": len(actual), "missing_expected_meshes": missing,
            "unexpected_visible_meshes": unexpected, "components": components, "settings": snapshot.get("settings"),
            "boundary": "PIE mesh/visibility/leader readback only; not visual approval, animation trajectory or hair color/material verification"}


def render_summary(path, receipt):
    return {"file": str(path), "attempt_id": receipt.get("attempt_id"), "status": receipt.get("status"), "success": receipt.get("success"),
            "created_at": receipt.get("created_at"), "submitted_at": receipt.get("submitted_at"), "finished_at": receipt.get("finished_at"),
            "actual_render_seconds": elapsed(receipt.get("submitted_at"), receipt.get("finished_at")),
            "job_signature": receipt.get("job_signature"), "frames_directory": receipt.get("frames_directory"),
            "errors": receipt.get("errors", []), "render_contract": receipt.get("render_contract"),
            "queue_unchanged": receipt.get("global_queue_unchanged"), "input_files_unchanged": receipt.get("input_files_unchanged")}


def build(run, main_count=7203, action_ref_count=809):
    started = datetime.now(timezone.utc).isoformat()
    errors, failures = [], []
    manifest = read(run / "pilot_jobs.json", errors)
    if not manifest or not isinstance(manifest.get("jobs"), list):
        raise ValueError("Missing pilot_jobs.json jobs list")
    jobs, event_rows, samples = manifest["jobs"], events(run, errors), gpu_samples(run / "gpu_telemetry.csv")
    receipts = defaultdict(list)
    for path in sorted((run / "render_receipts").glob("*.json")):
        receipt = read(path, errors)
        if not receipt:
            continue
        for job in receipt.get("jobs", []):
            if job.get("shot_id"):
                receipts[job["shot_id"]].append((path, receipt))
    output = []
    for job in jobs:
        job_id, state = job["job_id"], job.get("state", {})
        directory = run / "jobs" / job_id
        prepared = read(directory / "prepared.json", errors) or {}
        media = read(directory / "media_receipt.json", errors) or {}
        attempt = read(directory / "driver_attempt.json", errors) or {}
        snapshot = read(directory / "runtime_snapshot.json", errors)
        renders = sorted(receipts[job_id], key=lambda item: (timestamp(item[1].get("submitted_at") or item[1].get("created_at")) or 0, str(item[0])))
        render_rows = [render_summary(path, value) for path, value in renders]
        latest = render_rows[-1] if render_rows else {}
        video = directory / "video.mp4"
        raw = list((directory / "frames").glob("frame_*.png"))
        raw_bytes = sum(path.stat().st_size for path in raw if path.is_file())
        current_spec = hashlib.sha256(json.dumps({"job": job, "encoding": media.get("encoding")}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        media_fields = media.get("media", {})
        fields_match = all(media_fields.get(key) == expected for key, expected in {
            "width": job.get("width"), "height": job.get("height"), "fps": job.get("fps", 30),
            "decoded_frames": job.get("frames", 300), "codec": "h264", "pixel_format": "yuv420p", "audio_streams": 0}.items())
        media_is_latest = not latest or (timestamp(latest.get("submitted_at")) or 0) <= (timestamp(media.get("finished_at")) or 0)
        media_ok = (media.get("status") == "success" and video.is_file() and media.get("spec_sha256") == current_spec
                    and fields_match and media_is_latest)
        if media_ok:
            status = "media_success"
        elif latest.get("status") in {"preparing", "submitted", "rendering"}:
            status = "render_in_progress_or_interrupted"
        elif latest.get("status") == "completed" and latest.get("success") is True:
            status = "render_complete_media_pending"
        elif latest.get("status") in {"failed", "setup_failed", "submission_outcome_unknown"}:
            status = "render_failed_or_unknown"
        elif prepared.get("success"):
            status = "prepared"
        else:
            status = "not_started"
        timing = {"preparation_seconds": prepared.get("preparation_seconds"), "preparation_stages": prepared.get("stage_seconds", {}),
                  "actual_render_seconds": latest.get("actual_render_seconds"), "encoder": media.get("timing", {}),
                  "latest_driver_attempt_only": attempt.get("timing"),
                  "source_policy": "prepared receipt + MRQ submitted_at-to-finished_at + media receipt; driver attempt may have been overwritten by resume"}
        chain = [timing["preparation_seconds"], timing["actual_render_seconds"], media.get("timing", {}).get("total_seconds")]
        timing["reconstructed_stage_sum_seconds"] = sum(chain) if all(isinstance(value, (int, float)) for value in chain) else None
        gpu_start, gpu_end = timestamp(latest.get("submitted_at")), timestamp(latest.get("finished_at"))
        job_samples = [s for s in samples if gpu_start is not None and gpu_start <= s["unix_time"] and (gpu_end is None or s["unix_time"] <= gpu_end)]
        row = {"job_id": job_id, "node_id": job.get("node_id"), "status": status, "sex": state.get("sex"),
               "orientation": state.get("aspect") or ("landscape" if job.get("width", 0) >= job.get("height", 0) else "portrait"),
               "scene": job.get("site", {}).get("map"), "state": state, "width": job.get("width"), "height": job.get("height"),
               "scene_reused": prepared.get("scene_reused"), "prepared_signature": prepared.get("signature"), "timing": timing,
               "render_attempts": render_rows, "latest_render": latest, "media": media.get("media"), "encoding": media.get("encoding"),
               "media_receipt_status": media.get("status"), "media_spec_matches_current_job": media.get("spec_sha256") == current_spec if media else None,
               "media_finished_at": media.get("finished_at"),
               "media_fields_match_job": fields_match if media else None, "media_receipt_covers_latest_render": media_is_latest,
               "media_validation_scope": "encoder full-decode receipt + current file existence/spec check; this report does not rehash/decode",
               "video_bytes": video.stat().st_size if video.is_file() else 0, "raw_frame_count": len(raw), "raw_bytes": raw_bytes,
               "input_channels": media.get("input_channels"), "runtime_readback": runtime_readback(job, snapshot),
               "gpu_during_latest_render": gpu_summary(job_samples), "resume_render": [e for e in event_rows if e.get("job_id") == job_id and e.get("phase") == "resume_render"],
               "latest_driver_reused_render": attempt.get("reused_render")}
        output.append(row)
        for render in render_rows:
            if render["status"] in {"failed", "setup_failed", "submission_outcome_unknown"} or render["errors"]:
                failures.append({"source": render["file"], "at": render.get("finished_at"), "job_id": job_id, "kind": "render_attempt", "status": render["status"], "errors": render["errors"], "later_media_success": media_ok})
        media_attempt = read(directory / "media_attempt.json", errors) or {}
        if media_attempt.get("status") == "failed":
            failures.append({"source": str(directory / "media_attempt.json"), "at": media_attempt.get("finished_at"), "job_id": job_id, "kind": "media_attempt", "error": media_attempt.get("error"), "later_media_success": media_ok})
    by_id = {row["job_id"]: row for row in output}
    for path in sorted((run / "remote").glob("*.json")):
        value = read(path, errors) or {}
        if value.get("error"):
            job_id = value.get("request", {}).get("job_id")
            detail = value.get("remote_reply", {}).get("result") or str(value["error"])
            summary = next((line.strip() for line in reversed(detail.splitlines()) if line.strip()), detail)
            classification = ("appearance_selection_validation" if "validate_selection" in detail else
                              "temporary_actor_label_guard" if "ue_scene_site_appearance_v1.py" in detail and "apply_actor" in detail else
                              "owned_map_save" if "Cannot save owned map" in detail else
                              "editor_discovery" if "Need one editor" in detail else "remote_exception")
            failures.append({"source": str(path), "at": value.get("finished_at") or value.get("started_at"), "job_id": job_id, "kind": "remote_request", "action": value.get("request", {}).get("action"),
                             "classification": classification, "error": summary[:1500], "detail": detail[-4000:],
                             "later_media_success": by_id.get(job_id, {}).get("status") == "media_success"})
    failures += [{"source": e["source_file"], "at": e.get("at"), "job_id": e.get("job_id"), "kind": "driver_event", "phase": e.get("phase"), "error": e.get("error"),
                  "later_media_success": by_id.get(e.get("job_id"), {}).get("status") == "media_success"}
                 for e in event_rows if e.get("phase") in {"failed", "fatal"}]
    # Reference PNG jobs have no main-video media receipt. Resolve their old
    # request errors against successful reference render receipts separately;
    # never add them to the main pilot success denominator.
    for failure in failures:
        job_id = failure.get("job_id")
        failed_at = timestamp(failure.get("at")) or 0
        main = by_id.get(job_id)
        later_media = bool(main and main["status"] == "media_success" and (timestamp(main.get("media_finished_at")) or 0) >= failed_at)
        later_renders = [(path, value) for path, value in receipts.get(job_id, [])
                         if value.get("status") == "completed" and value.get("success") is True
                         and (timestamp(value.get("finished_at")) or 0) >= failed_at]
        latest_success = max(later_renders, key=lambda item: timestamp(item[1].get("finished_at")) or 0) if later_renders else None
        reference_success = bool(job_id and job_id.startswith("ref_") and latest_success)
        failure.update(later_media_success=later_media if main else None,
                       later_render_success=bool(latest_success), resolved_afterward=later_media or reference_success,
                       resolution_kind="main_media_success" if later_media else "reference_png_render_success" if reference_success else "not_proven",
                       resolution_receipt=str(latest_success[0]) if latest_success else None)
    stage_values = defaultdict(list)
    for row in output:
        for name, seconds in row["timing"]["preparation_stages"].items():
            stage_values[name].append(seconds)
    success = [row for row in output if row["status"] == "media_success"]
    comparisons = []
    for a, b, axis in PAIRS:
        left, right = by_id.get(f"train_node_{a:06d}"), by_id.get(f"train_node_{b:06d}")
        if not left or not right:
            continue
        changed = [key for key in set(left["state"]) | set(right["state"]) if left["state"].get(key) != right["state"].get(key)]
        comparisons.append({"from": left["job_id"], "to": right["job_id"], "intended_axis": axis, "state_changed_keys": sorted(changed),
                            "state_single_intended_axis": changed == [axis], "from_status": left["status"], "to_status": right["status"],
                            "from_scene_reused": left["scene_reused"], "to_scene_reused": right["scene_reused"],
                            "from_prepare_seconds": left["timing"]["preparation_seconds"], "to_prepare_seconds": right["timing"]["preparation_seconds"],
                            "from_render_seconds": left["timing"]["actual_render_seconds"], "to_render_seconds": right["timing"]["actual_render_seconds"],
                            "from_stage_sum_seconds": left["timing"]["reconstructed_stage_sum_seconds"], "to_stage_sum_seconds": right["timing"]["reconstructed_stage_sum_seconds"],
                            "interpretation": "state pair comparison only; cache/scene reuse/run order differ, not a controlled hardware or per-axis timing benchmark"})
    interruption = read(run / "INTERRUPTION_TEST.json", errors)
    interruption_result = None
    if interruption:
        interrupted = by_id.get(interruption.get("job_id"), {})
        latest = interrupted.get("latest_render", {})
        interruption_result = {"record": interruption, "observed_raw_frame_count_now": interrupted.get("raw_frame_count"),
                               "render_completed_after_stop": latest.get("status") == "completed" and (timestamp(latest.get("finished_at")) or 0) > (timestamp(interruption.get("at")) or float("inf")),
                               "resume_render_log_events": interrupted.get("resume_render", []), "driver_reused_render": interrupted.get("latest_driver_reused_render"),
                               "media_success_now": interrupted.get("status") == "media_success",
                               "proven_chain": bool(latest.get("status") == "completed" and interrupted.get("raw_frame_count") == 300
                                   and interrupted.get("resume_render") and interrupted.get("status") == "media_success"
                                   and interruption.get("ue_untouched") is True and 0 < interruption.get("frame_count_at_stop", 0) < 300
                                   and (timestamp(latest.get("finished_at")) or 0) > (timestamp(interruption.get("at")) or float("inf"))
                                   and Path(latest.get("file", "")).name == Path(interruption.get("receipt", "missing")).name)}
    warm = [r for r in success if r["scene_reused"] is True and r["timing"]["reconstructed_stage_sum_seconds"] is not None]
    warm_times = [r["timing"]["reconstructed_stage_sum_seconds"] for r in warm]
    total_count = main_count + action_ref_count
    prediction = {"main_video_count": main_count, "action_reference_video_count": action_ref_count, "total_videos": total_count,
                  "basis": "observed successful same-scene reused stage sums; omit first scene-load/cold samples; no separate shader-time measurement",
                  "sample_job_ids": [r["job_id"] for r in warm], "observed_seconds_range": [min(warm_times), max(warm_times)] if warm_times else None,
                  "main_serial_hours_range": [main_count * min(warm_times) / 3600, main_count * max(warm_times) / 3600] if warm_times else None,
                  "main_plus_action_refs_serial_hours_range": [total_count * min(warm_times) / 3600, total_count * max(warm_times) / 3600] if warm_times else None,
                  "raw_storage_bytes_range": [total_count * min(r["raw_bytes"] for r in success), total_count * max(r["raw_bytes"] for r in success)] if success else None,
                  "mp4_storage_bytes_range": [total_count * min(r["video_bytes"] for r in success), total_count * max(r["video_bytes"] for r in success)] if success else None,
                  "limits": "scenario range only, not a forecast/confidence interval; excludes one-time shader/engine startup, upload/DDC, failures, polling/transport gaps and references with different render workloads. Server GPU/Linux/build differ; do not transfer local timing or divide linearly by GPU count."}
    report = {"schema": "dataset_render_pilot_report_v11_v1", "generated_at": started, "run_root": str(run),
              "status": "complete_receipt_snapshot" if len(success) == len(jobs) else "partial_in_progress_snapshot",
              "pilot_jobs": len(jobs), "successful_media": len(success), "status_counts": dict(Counter(r["status"] for r in output)),
              "coverage_planned": {field: dict(Counter(str(r[field]) for r in output)) for field in ("sex", "orientation", "scene")},
              "coverage_successful": {field: dict(Counter(str(r[field]) for r in success)) for field in ("sex", "orientation", "scene")},
              "stage_seconds_statistics": {"preparation_detail": {key: stats(value) for key, value in stage_values.items()},
                                           **{field: stats(r["timing"][field] for r in output) for field in ("preparation_seconds", "actual_render_seconds", "reconstructed_stage_sum_seconds")},
                                           "encode": stats(r["timing"]["encoder"].get("encode_seconds") for r in output),
                                           "input_check": stats(r["timing"]["encoder"].get("input_check_seconds") for r in output),
                                           "media_verification": stats(r["timing"]["encoder"].get("verification_seconds") for r in output)},
              "scene_reuse_groups": {str(value): {"jobs": [r["job_id"] for r in output if r["scene_reused"] is value],
                                                 "preparation_seconds": stats(r["timing"]["preparation_seconds"] for r in output if r["scene_reused"] is value)} for value in (False, True)},
              "gpu_sampling": gpu_summary(samples), "comparisons": comparisons, "interruption_test": interruption_result,
              "failure_and_repair_evidence": failures, "repair_interpretation": "Historical failures followed by success show recovery; precise code changes are not inferred from timing. Raw RGB/RGBA compatibility policy is preserved in encoding receipts.",
              "documented_compatibility_repairs": {"rgba_encoder": (read(run / "OFFLINE_VALIDATION.json", errors) or {}).get("rgba_encoder"),
                                                   "media_alpha_policies": sorted({r["encoding"].get("alpha_policy", "unspecified") for r in output if r.get("encoding")})},
              "dataset_scenarios": prediction, "jobs": output, "read_errors": errors,
              "limits": ["Snapshot can be rerun while jobs continue; not visual acceptance", "No rehash/decode in report; encoder receipts carry existing verification", "Different cold/warm cache, shader state and execution order prevent a strict controlled per-axis/hardware benchmark", "Driver attempt logs may be overwritten; original MRQ and preparation receipts take precedence"]}
    return report


def number(value):
    return "—" if value is None else f"{value:.2f}"


def markdown(report):
    lines = ["# v11 本地渲染小样报告", "", f"生成时间：{report['generated_at']}。当前 **{report['successful_media']}/{report['pilot_jobs']} 条成片具有成功编码校验回执且文件存在**；状态：`{report['status']}`。未完成条目保留原状态，可重复运行更新。", "",
             "耗时主要取准备回执、MRQ提交到结束时间、编码回执；续跑覆盖的driver_attempt不作为原始总耗时。成片校验结论来自已有全解码回执，本次报告只核对文件存在与当前作业规格，不重新解码或哈希。", "", "## 每条作业", "",
             "|节点|性别/方向|状态|场景复用|准备s|MRQ实际s|编码s|阶段合计s|PNG数|原始GiB|MP4 MiB|PIE网格|", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in report["jobs"]:
        timing = row["timing"]
        lines.append(f"|{row['node_id']}|{row['sex']}/{row['orientation']}|{row['status']}|{row['scene_reused']}|{number(timing['preparation_seconds'])}|{number(timing['actual_render_seconds'])}|{number(timing['encoder'].get('encode_seconds'))}|{number(timing['reconstructed_stage_sum_seconds'])}|{row['raw_frame_count']}|{row['raw_bytes']/1024**3:.2f}|{row['video_bytes']/1024**2:.1f}|{row['runtime_readback']['status']}|")
    lines += ["", "成功样本覆盖：" + json.dumps(report["coverage_successful"], ensure_ascii=False) + "。", "",
              "详细地图、身份/服装/发型、实际PIE组件网格、leader、可见性、所有MRQ尝试及编码字段保存在 `PILOT_REPORT.json`。PIE网格一致不代表画面、动作曲线或发色已经通过人工验收。", "", "## 准备细分与缓存", "", "|阶段|样本数|最小s|中位数s|最大s|", "|---|---:|---:|---:|---:|"]
    for key, value in report["stage_seconds_statistics"]["preparation_detail"].items():
        lines.append(f"|{key}|{value['n']}|{number(value.get('min'))}|{number(value.get('median'))}|{number(value.get('max'))}|")
    for key, value in report["scene_reuse_groups"].items():
        stat = value["preparation_seconds"]
        lines += ["", f"scene_reused={key}：{len(value['jobs'])}条，准备耗时范围 {number(stat.get('min'))}–{number(stat.get('max'))} 秒。"]
    lines += ["", "## 成对变化观察", "", "|节点对|预期轴|实际state变化|MRQ秒|准备秒|", "|---|---|---|---|---|"]
    for pair in report["comparisons"]:
        left, right = pair["from"].split("_")[-1], pair["to"].split("_")[-1]
        lines.append(f"|{int(left)}→{int(right)}|{pair['intended_axis']}|{', '.join(pair['state_changed_keys'])}|{number(pair['from_render_seconds'])}→{number(pair['to_render_seconds'])}|{number(pair['from_prepare_seconds'])}→{number(pair['to_prepare_seconds'])}|")
    lines += ["", "这些是数据状态的成对变化，不是严格单变量硬件基准。场景缓存、材质/着色器首次加载、运行顺序不同；不能将两条耗时差直接归因为某个编辑轴。", "", "## 中断恢复", ""]
    interruption = report.get("interruption_test")
    if interruption:
        record = interruption["record"]
        lines += [f"记录 `{record.get('job_id')}` 在 {record.get('frame_count_at_stop')} 帧时停止外部驱动，UE未停止。当前帧数 {interruption['observed_raw_frame_count_now']}，停止后完成渲染：{interruption['render_completed_after_stop']}；resume_render日志 {len(interruption['resume_render_log_events'])}条，成片成功：{interruption['media_success_now']}。", "", f"完整证据链成立：**{interruption['proven_chain']}**。"]
    else:
        lines += ["尚无中断测试记录。"]
    lines += ["", "## GPU采样", ""]
    gpu = report["gpu_sampling"]
    if gpu["samples"]:
        lines += [f"{gpu['samples']}个采样点，覆盖 {gpu['sample_window_seconds']/60:.1f}分钟；采样峰值显存 {gpu['peak_used_mib']:.0f}MiB、GPU利用率 {gpu['peak_gpu_percent']:.0f}%、功率 {gpu['peak_power_w']:.1f}W。采样不是全程覆盖，也不保证捕获瞬时峰值。"]
    else:
        lines += ["尚无可解析GPU采样。"]
    lines += ["", "## 失败与修复证据", "", f"保留 {len(report['failure_and_repair_evidence'])}条历史失败/错误证据。详细错误、来源与之后是否已有成功成片见JSON。失败后成功可以证明恢复，不能单凭报告推断具体代码修复。", ""]
    for failure in report["failure_and_repair_evidence"][:12]:
        text = str(failure.get("error") or failure.get("errors") or failure.get("status"))[:260].replace("\n", " ")
        lines.append(f"- {failure.get('job_id') or '未绑定作业'} / {failure.get('classification', failure['kind'])}：{text}；后续成功恢复：{failure.get('resolved_afterward')}（{failure.get('resolution_kind')}）。")
    lines += ["", "参考PNG的历史错误单独查询其成功渲染回执判断恢复；参考任务不计入上面的12条主视频成功数。正在重渲染的参考原型仍需以最新图片和回执验收，历史恢复记录不代表新版本已接受。"]
    if report["documented_compatibility_repairs"].get("rgba_encoder"):
        lines += ["", "编码兼容修复有独立离线验证记录：UE输出可为RGBA PNG，编码先丢弃alpha再做BT.709有限范围转换。原始帧与成片保留，具体输入通道和策略写入媒体回执；此项不等同于完整画面验收。"]
    lines += ["", "## 数据规模情景范围", ""]
    prediction = report["dataset_scenarios"]
    if prediction["main_plus_action_refs_serial_hours_range"]:
        lo, hi = prediction["main_plus_action_refs_serial_hours_range"]
        lines += [f"{prediction['main_video_count']}条主视频 + {prediction['action_reference_video_count']}条动作参考，共{prediction['total_videos']}条。按已成功的同场景复用样本阶段合计，单机串行约 **{lo:.1f}–{hi:.1f}小时**。", "", "此范围只作本地负载情景估算：剔除首次场景加载样本；首次着色器/引擎启动未单独测量，额外成本未计入，也未包含轮询/传输间隔。服务器GPU、Linux和插件不同，不能直接套用本地速度；动作参考若采用不同负载也不适用。", ""]
        for label, key in (("保留全部原始PNG", "raw_storage_bytes_range"), ("MP4", "mp4_storage_bytes_range")):
            bounds = prediction.get(key)
            if bounds:
                lines.append(f"- {label}按样本大小外推：{bounds[0]/1024**3:.1f}–{bounds[1]/1024**3:.1f}GiB；非精确存储承诺。")
    else:
        lines += ["同场景复用成功样本不足，暂不生成耗时范围。"]
    lines += ["", f"重跑：`python 00_engine/scripts/dataset/report_render_pilot_v11.py --run-root \"{report['run_root']}\"`。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=WORKSPACE / "00_engine/outputs/dataset_render_pilot_20261023_v1")
    parser.add_argument("--main-count", type=int, default=7203)
    parser.add_argument("--action-reference-count", type=int, default=809)
    args = parser.parse_args(argv)
    report = build(args.run_root.resolve(), args.main_count, args.action_reference_count)
    for name, content in (("PILOT_REPORT.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n"), ("PILOT_REPORT.md", markdown(report))):
        temporary = args.run_root / (name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(args.run_root / name)
    print(json.dumps({key: report[key] for key in ("status", "pilot_jobs", "successful_media", "status_counts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
