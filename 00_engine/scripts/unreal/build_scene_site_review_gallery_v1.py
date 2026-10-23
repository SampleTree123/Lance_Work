"""Publish the independent scene-site pilot review. Owner: SCENE_CAMERA_SEQUENCE §17.

Offline only. Reuses existing full-decode evidence without decoding media again;
only matching verified receipts and unchanged media receive playable URLs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

S = Path(__file__).resolve().parent
RUN = S.parents[1] / "outputs/scene_site_review_20261014_v1"
SCENES = {"gas_station": "沙漠加油站", "parking": "停车场"}
LIMITATIONS = [
    "本页仅展示两个点位的必要样片，不代表全部 1260 组合已经拍摄或获人工接受。",
    "自动检查使用离散骨点、身体和相机代理及可见性碰撞通道；不能保证发型、服装、完整网格或无碰撞物体均无遮挡。",
    "报告只记录检查时的场景；网页不会实时读取 UE，点位、场景或输入改变后需要重新检查。",
    "视频通过编码与完整解码核验只说明媒体有效，构图、穿模和遮挡仍需人工审看。",
]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def local_file(run, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or re.match(r"^[A-Za-z]:", relative):
        raise ValueError("媒体路径必须是本次输出目录内的相对路径")
    path = (run / relative).resolve()
    path.relative_to(run.resolve())
    if not path.is_file():
        raise FileNotFoundError("文件尚未生成：" + relative)
    return path


def same_point(first, second):
    return all(first.get(k) == second.get(k) for k in ("site_id", "map", "position", "yaw"))


def verified_media(run, row, shot, report, plan):
    """Require unchanged encoder evidence, matching frozen shot and full decode."""
    if row.get("verification_status") != "encoded_verified":
        raise ValueError("媒体尚未完成编码验证")
    pin = {"path": str(plan.resolve()), "sha256": digest(plan)}
    if pin not in report.get("source_plans", []):
        raise ValueError("媒体报告没有绑定当前试拍计划")
    video = local_file(run, row["video"])
    poster = local_file(run, row["poster"])
    receipt_path = local_file(run, row["verification_receipt"])
    if video.suffix.lower() != ".mp4" or poster.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("媒体格式不正确")
    for path, expected in ((video, row["video_sha256"]), (poster, row["poster_sha256"]),
                           (receipt_path, row["verification_receipt_sha256"])):
        if digest(path) != expected:
            raise ValueError("文件与验证回执不一致：" + path.name)
    receipt = read(receipt_path)
    if receipt.get("schema") != "motion_scene_encoded_shot_v1" or receipt.get("status") != "encoded_verified":
        raise ValueError("编码回执尚未验证")
    expected = {"shot_id": shot["shot_id"], "shot_plan_sha256": object_sha(shot), "video": row["video"],
                "video_sha256": row["video_sha256"], "width": shot["width"], "height": shot["height"],
                "expected_frames": shot["frame_count"], "render_receipt_sha256": report["render_receipt_sha256"]}
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("媒体回执与当前镜头、画幅或渲染记录不匹配")
    decoded = receipt.get("decode") or {}
    count, fps, duration = shot["frame_count"], shot["fps"], shot["duration_seconds"]
    if (not all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in (count, fps, duration))
            or int(count) != count or abs(count / fps - duration) > 1e-6
            or decoded.get("ffmpeg_full_decode_success") is not True
            or decoded.get("ffmpeg_full_decode_frames") != count or decoded.get("decoded_frames") != count
            or decoded.get("dimensions") != [shot["width"], shot["height"]]
            or abs(decoded.get("fps", 0) - fps) > 1e-8
            or abs(decoded.get("measured_duration_seconds", 0) - duration) > 1e-6
            or row.get("decoded_frames") != count or row.get("width") != shot["width"]
            or row.get("height") != shot["height"]):
        raise ValueError("完整解码回执的帧数、时长或画幅不匹配")
    if shot["orientation"] != ("portrait" if shot["height"] > shot["width"] else "landscape"):
        raise ValueError("计划画幅方向不一致")
    return {"video": video.relative_to(run).as_posix(), "poster": poster.relative_to(run).as_posix(),
            "video_sha256": row["video_sha256"], "poster_sha256": row["poster_sha256"],
            "verification_receipt": receipt_path.relative_to(run).as_posix(),
            "verification_receipt_sha256": row["verification_receipt_sha256"], "decoded_frames": count,
            "verification_status": "encoded_verified", "playable": True}


def compact_report(report, site, path, run):
    return {"path": str(path.relative_to(run)), "sha256": digest(path), "status": report.get("status", "unknown"),
            "point_match": same_point(report.get("site", {}), site), "scope": report.get("scope"),
            "summary": report.get("summary", {}), "coverage": report.get("coverage", {}),
            "sampling": report.get("sampling", ""), "limitations": report.get("limitations") or LIMITATIONS[1:3],
            "issues": report.get("issues") or [], "error": report.get("error"), "human_acceptance": "pending"}


def latest_site_plans(run):
    """One current plan per site; old plans remain untouched for provenance."""
    grouped = {}
    for path in sorted((run / "pilot_plans").glob("*.json")):
        document = read(path)
        if document.get("schema") != "scene_site_review_pilot_plan_v1":
            continue
        site_id = document["site"]["site_id"]
        revision = tuple(int(n) for n in re.findall(r"\d+", str(document.get("revision", "")))) or (-1,)
        rank = (revision, path.stat().st_mtime_ns, path.name)
        grouped.setdefault(site_id, []).append((rank, path, document))
    selected, superseded = [], []
    for rows in grouped.values():
        rows.sort(key=lambda row: row[0])
        selected.append((rows[-1][1], rows[-1][2]))
        superseded.extend(row[1].relative_to(run).as_posix() for row in rows[:-1])
    return sorted(selected, key=lambda row: row[0].name), sorted(superseded)


def build(run=RUN):
    run = Path(run).resolve()
    plans, shots, clips, scenes, warnings = [], {}, {}, {}, []
    reports = [(p, read(p)) for p in sorted((run / "reports").glob("*.json"), key=lambda p: p.stat().st_mtime)]
    selected_plans, superseded_paths = latest_site_plans(run)
    for path, document in selected_plans:
        site, scene_id = document["site"], document["scene_id"]
        plan_id = path.stem
        site_pin = document.get("site_pin") or {}
        site_record, record_path = None, None
        if site_pin.get("path"):
            record_path = Path(site_pin["path"]).resolve()
            try:
                record_path.relative_to(run)
                if digest(record_path) == site_pin.get("sha256"):
                    site_record = read(record_path)
                else:
                    warnings.append({"plan_id": plan_id, "message": "保存点位已改变；本页保留试拍计划冻结的位置。"})
            except (OSError, ValueError):
                warnings.append({"plan_id": plan_id, "message": "试拍计划对应的保存点位不可读取。"})
        related = [(p, r) for p, r in reports if r.get("site", {}).get("site_id") == site["site_id"]]
        selected_report, selected_path = None, None
        if site_record and isinstance(site_record.get("report"), dict):
            selected_report, selected_path = site_record["report"], record_path
        elif related:
            exact = [(p, r) for p, r in related if same_point(r.get("site", {}), site)]
            selected_path, selected_report = (exact or related)[-1]
        plan_row = {"id": plan_id, "scene_id": scene_id, "revision": str(document.get("revision", "v1")),
                    "site": site, "plan": {"path": path.relative_to(run).as_posix(), "sha256": digest(path)},
                    "report": compact_report(selected_report, site, selected_path, run) if selected_report else None,
                    "human_acceptance": "pending"}
        plans.append(plan_row)
        scenes[scene_id] = {"id": scene_id, "label": SCENES.get(scene_id, site.get("name") or scene_id)}
        for shot in document["shots"]:
            sid = shot["shot_id"]
            if sid in shots:
                raise ValueError("试拍镜头编号重复：" + sid)
            shots[sid] = (shot, path)
            clips[sid] = {"id": sid, "plan_id": plan_id, "scene_id": scene_id, "site_id": site["site_id"],
                          "motion_id": shot["motion_id"], "motion_label": shot.get("motion_label", shot["motion_id"]),
                          "camera_id": shot["camera_id"], "camera_label": shot.get("camera_label", shot["camera_id"]),
                          "orientation": shot["orientation"], "width": shot["width"], "height": shot["height"],
                          "duration_seconds": shot["duration_seconds"], "fps": shot["fps"],
                          "source_frozen_shot_id": shot.get("source_frozen_shot_id"),
                          "verification_status": "pending", "playable": False, "human_acceptance": "pending"}
    for path in sorted(run.glob("media_validation_*.json")):
        report = read(path)
        if report.get("schema") != "motion_scene_media_validation_v1" or report.get("success") is not True:
            continue
        for row in report.get("videos", []):
            sid = row.get("shot_id")
            if sid not in shots or row.get("verification_status") != "encoded_verified":
                continue
            shot, plan_path = shots[sid]
            try:
                media = verified_media(run, row, shot, report, plan_path)
                if clips[sid]["playable"] and clips[sid]["video_sha256"] != media["video_sha256"]:
                    raise ValueError("同一镜头存在不同的已验证媒体")
                clips[sid].update(media)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append({"shot_id": sid, "source": path.name, "message": str(exc)})
                if not clips[sid]["playable"]:
                    clips[sid].update(verification_status="blocked", verification_error=str(exc))
    candidate = run / "scene_candidate_recommendation_v1.json"
    if candidate.is_file():
        for row in read(candidate).get("candidates", []):
            scene_id = row["scene_id"]
            scenes.setdefault(scene_id, {"id": scene_id, "label": SCENES.get(scene_id, scene_id)})
    data = {"schema": "scene_site_review_gallery_v1", "review_run_id": run.name,
            "updated_at": datetime.now(timezone.utc).isoformat(), "scenes": list(scenes.values()),
            "plans": plans, "clips": list(clips.values()), "playable_count": sum(c["playable"] for c in clips.values()),
            "pending_count": sum(not c["playable"] for c in clips.values()), "warnings": warnings,
            "active_plan_paths": [p.relative_to(run).as_posix() for p, _ in selected_plans],
            "superseded_plan_paths": superseded_paths,
            "plan_selection_policy": "One plan per site_id: greatest numeric revision components, then modification time in nanoseconds, then filename; media must match the selected plan exactly.",
            "limitations": LIMITATIONS, "human_acceptance": "pending", "ue_accessed_by_builder": False}
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    gallery = run / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    temporary = gallery / "index.html.partial"
    temporary.write_text(HTML.replace("__DATA__", encoded), encoding="utf-8")
    temporary.replace(gallery / "index.html")
    write(run / "review_delivery_manifest_v1.json", data)
    return {"index": str(gallery / "index.html"), "clips": len(clips), "playable": data["playable_count"],
            "pending": data["pending_count"], "warnings": len(warnings), "superseded_plans": len(superseded_paths),
            "human_acceptance": "pending"}


HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>场景拍摄点 · 必要样片审查</title><style>
:root{font-family:system-ui,"Microsoft YaHei UI",sans-serif;color:#e7edf2;background:#0e141c;color-scheme:dark}*{box-sizing:border-box}body{margin:0}main{max-width:1440px;margin:auto;padding:28px}h1{font-size:27px;margin:0 0 8px}h2{font-size:18px;margin:0 0 12px}p{line-height:1.65;margin:8px 0}.muted{color:#a5b4c3}.badge{display:inline-block;padding:5px 10px;background:#243445;border-radius:14px;font-size:13px}.controls{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}label{display:flex;flex-direction:column;gap:6px;font-size:13px;color:#b8c7d5}select,button{font:inherit;padding:9px 11px;border:1px solid #3c5063;border-radius:8px;background:#182431;color:#eef5fa}select{max-width:300px}button{cursor:pointer}button:hover{border-color:#74b9df}button:disabled{opacity:.45;cursor:default}.layout{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(300px,1fr);gap:18px}.card{border:1px solid #293b4d;border-radius:14px;background:#131e29;padding:18px;margin-bottom:18px}.stage{background:#080d12;min-height:390px;display:flex;align-items:center;justify-content:center;border-radius:10px;overflow:hidden}video{display:block;max-width:100%;max-height:650px;width:100%;background:#080d12}.pending{text-align:center;padding:45px 25px;color:#bed0df}.alert{border-left:3px solid #e4ba68;padding:8px 12px;background:#302b20;border-radius:4px;font-size:14px}.issue{padding:13px 0;border-top:1px solid #293b4d}.issue p{margin:3px 0}.issue button{padding:5px 9px;font-size:13px;margin-top:5px}.issues{max-height:480px;overflow:auto}.facts{font-size:14px;overflow-wrap:anywhere}.scope{font-size:14px;color:#d2dfeb}details summary{cursor:pointer;color:#b9d6e9}li{line-height:1.65;margin:5px 0}a{color:#99cef1}.foot{margin-top:18px;font-size:13px}@media(max-width:900px){main{padding:18px}.layout{grid-template-columns:1fr}.stage{min-height:260px}select{max-width:100%}}
</style></head><body><main>
<header><h1>场景拍摄点 · 必要样片审查</h1><p class="muted">检查地面、人物空间与相机遮挡。加油站和停车场分别审看，全部结果仍待人工确认。</p><span class="badge" id="counts"></span></header>
<div class="controls"><label>场景<select id="scene"></select></label><label>点位版本<select id="plan"></select></label><label>动作<select id="motion"></select></label><label>镜头<select id="camera"></select></label><label>画幅<select id="aspect"></select></label></div>
<div class="layout"><section><div class="card"><h2 id="clipTitle">样片尚未生成</h2><div class="stage" id="stage"></div><p class="muted" id="clipNote"></p><p class="alert">媒体核验通过不等于画面通过。请留意脚底、身体穿入、遮挡与相机穿墙。</p></div>
<div class="card"><h2>点位与检查记录</h2><div id="site" class="facts"></div><p id="reportStatus" class="alert"></p><p id="scope" class="scope"></p><details><summary>查看检测局限</summary><ul id="limits"></ul></details></div></section>
<aside><div class="card"><h2 id="issueTitle">自动检查的问题与提醒</h2><p class="muted">有对应样片时可跳到问题时间；其余组合请在 UE 面板定位。</p><div class="issues" id="issues"></div></div><div class="card"><h2>发布说明</h2><p id="publishNote" class="muted"></p><details id="warningBox"><summary>查看未发布原因</summary><ul id="warnings"></ul></details></div></aside></div>
<p class="muted foot" id="updated"></p></main><script id="reviewData" type="application/json">__DATA__</script><script>
'use strict';const D=JSON.parse(document.getElementById('reviewData').textContent),$=id=>document.getElementById(id);let active=null,activePlan=null;
const aspectName=x=>x==='portrait'?'竖屏':'横屏';const add=(tag,text,host,cls)=>{let e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;host.append(e);return e};
function options(id,rows,old){let box=$(id);box.replaceChildren();for(let r of rows){let o=document.createElement('option');o.value=r.id;o.textContent=r.label;box.append(o)}if(rows.some(x=>x.id===old))box.value=old;box.disabled=!rows.length}
function distinct(rows,key,label){return [...new Map(rows.map(r=>[r[key],{id:r[key],label:r[label]||r[key]}])).values()]}
function candidates(){return D.clips.filter(c=>c.plan_id===$('plan').value)}
function changeScene(){let rows=D.plans.filter(p=>p.scene_id===$('scene').value);options('plan',rows.map(p=>({id:p.id,label:(p.site.name||p.site.site_id)+' · '+p.revision})));if(rows.length)$('plan').value=rows[rows.length-1].id;changePlan()}
function changePlan(){let rows=candidates();options('motion',distinct(rows,'motion_id','motion_label'));changeMotion();renderReport()}
function changeMotion(){let rows=candidates().filter(c=>c.motion_id===$('motion').value);options('camera',distinct(rows,'camera_id','camera_label'),$('camera').value);changeCamera()}
function changeCamera(){let rows=candidates().filter(c=>c.motion_id===$('motion').value&&c.camera_id===$('camera').value);options('aspect',distinct(rows,'orientation','orientation').map(r=>({id:r.id,label:aspectName(r.id)})),$('aspect').value);showClip()}
function mediaUrl(p){return '../'+p.split('/').map(encodeURIComponent).join('/')}
function showClip(seek){let rows=candidates().filter(c=>c.motion_id===$('motion').value&&c.camera_id===$('camera').value&&c.orientation===$('aspect').value);active=rows[0]||null;$('stage').replaceChildren();if(!active){$('clipTitle').textContent='样片计划尚未就绪';add('div','这个场景尚无必要样片计划，等待拍摄准备。',$('stage'),'pending');$('clipNote').textContent='尚无可播放资源。';return}
$('clipTitle').textContent=active.motion_label+' · '+active.camera_label+' · '+aspectName(active.orientation);if(!active.playable){add('div',active.verification_status==='blocked'?'验证受阻：'+active.verification_error:'待生成：视频完成核验后才会出现。',$('stage'),'pending');$('clipNote').textContent='当前组合没有已验证的视频，未发布播放地址。';return}
let video=document.createElement('video');video.controls=true;video.preload='metadata';video.playsInline=true;video.src=mediaUrl(active.video);video.poster=mediaUrl(active.poster);video.addEventListener('error',()=>{$('clipNote').textContent='视频载入失败，请检查服务器和媒体文件；本页不会自动换用其他样片。'});if(Number.isFinite(seek))video.addEventListener('loadedmetadata',()=>{video.currentTime=Math.min(Math.max(0,seek),Number.isFinite(video.duration)?video.duration:seek)},{once:true});$('stage').append(video);$('clipNote').textContent=`已核验编码与完整解码 · ${active.duration_seconds.toFixed(2)} 秒 · ${active.width} × ${active.height} · 人工审查待确认`}
function scopeLabel(scope){if(!scope)return '检查范围尚未记录';if(scope.kind==='all')return `范围：全部 ${scope.combinations} 个组合`;let s=scope.selection||{};return `范围：仅当前组合（${s.action_id||''} / ${s.camera_id||''} / ${aspectName(s.aspect)}），不代表全量检查`}
function jump(issue){let c=candidates().find(c=>c.motion_id===issue.action_id&&c.camera_id===issue.camera_id&&c.orientation===issue.aspect);if(!c)return;$('motion').value=c.motion_id;changeMotion();$('camera').value=c.camera_id;changeCamera();$('aspect').value=c.orientation;showClip(Number(issue.time_seconds));$('stage').scrollIntoView({behavior:'smooth',block:'center'})}
function renderReport(){activePlan=D.plans.find(p=>p.id===$('plan').value)||null;let site=$('site'),issues=$('issues');site.replaceChildren();issues.replaceChildren();$('limits').replaceChildren();$('issueTitle').textContent='自动检查的问题与提醒';let report=activePlan?.report;for(let text of [...new Set([...D.limitations,...(report?.limitations||[])])])add('li',text,$('limits'));if(!activePlan){add('p','尚无保存点位与检测记录。',site);$('reportStatus').textContent='等待建立点位并实际检查。';$('scope').textContent='';return}
let s=activePlan.site,p=s.position||{};add('p',(s.name||s.site_id)+` · 坐标 (${p.x}, ${p.y}, ${p.z}) 厘米 · 朝向 ${s.yaw}°`,site);add('p','场景：'+s.map,site,'muted');if(!report){$('reportStatus').textContent='尚无点位检查报告；没有问题记录不代表已通过。';$('scope').textContent='';add('p','等待实际检查结果。',issues,'muted');return}
const names={complete:'本次检查已完成',completed:'本次检查已完成',stale:'检查已过期',cancelled:'检查已取消',failed:'检查失败',running:'检查未完成'};let status=names[report.status]||'检查状态：'+report.status;if(!report.point_match)status+='；报告属于不同位置，仅作历史参考';if(report.status==='complete'&&report.point_match)status+='；网页不实时确认 UE 场景是否改变';$('reportStatus').textContent=status+(report.error?'。'+report.error:'')+'。仍待人工审看。';let sum=report.summary||{};$('scope').textContent=scopeLabel(report.scope)+` · 完成 ${sum.checked_items||0} / ${sum.total_items||0} 个离散检查项`;$('issueTitle').textContent=`自动检查的问题与提醒（${report.issues.length}）`;if(!report.issues.length)add('p',report.status==='complete'?'本次采样没有记录问题；仍需审看样片。':'检查未有效完成，暂未记录问题。',issues,'muted');for(let issue of report.issues){let box=add('div','',issues,'issue');add('p',issue.message||issue.kind,box);add('p',`${issue.action_id||''} · ${issue.camera_id||''} · ${aspectName(issue.aspect)} · ${Number(issue.time_seconds||0).toFixed(2)} 秒`,box,'muted');let target=candidates().find(c=>c.motion_id===issue.action_id&&c.camera_id===issue.camera_id&&c.orientation===issue.aspect);if(target?.playable){let b=add('button','跳到样片对应时间',box);b.type='button';b.addEventListener('click',()=>jump(issue))}else add('p',target?'此问题组合的样片待生成。':'此问题组合不在本轮必要样片中，可在 UE 面板定位。',box,'muted')}}
for(let [id,fn]of [['scene',changeScene],['plan',changePlan],['motion',changeMotion],['camera',changeCamera],['aspect',showClip]])$(id).addEventListener('change',()=>fn());options('scene',D.scenes);$('counts').textContent=`已核验可播放 ${D.playable_count} / ${D.clips.length} 条 · ${D.pending_count>0?'其余待完成':'本轮样片已齐'}`;$('publishNote').textContent='仅发布与试拍计划、编码回执和文件校验一致的视频及海报；本页复用既有完整解码回执，不重复解码。';$('warningBox').hidden=!D.warnings.length;for(let w of D.warnings)add('li',(w.shot_id||w.plan_id||'')+'：'+w.message,$('warnings'));$('updated').textContent='页面构建于 '+D.updated_at+' · 静态审查快照 · 人工接受状态：待确认';changeScene();
</script></body></html>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=RUN)
    print(json.dumps(build(parser.parse_args().run_root), ensure_ascii=False))
