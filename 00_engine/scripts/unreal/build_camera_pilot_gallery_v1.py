"""Build a local read-only camera-video gallery; never run UE/server/browser.

Consumes camera_pilot_delivery_manifest_v1, or adapts a camera proposal via
--plan. File presence means playable, never visual approval. Standard library
only. Output is exactly <run>/gallery/index.html; media stay under <run>.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import quote

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
LABELS = {
    'static_front':'正面全身', 'static_three_quarter':'前侧全身', 'static_side':'侧面全身',
    'static_rear':'背侧全身', 'static_back':'背面全身', 'static_high':'俯视全身',
    'static_low':'仰视全身', 'static_upper':'上半身', 'static_close':'面部近景', 'static_head':'面部近景',
    'static_wide':'环境远景', 'dolly_in':'推近', 'dolly_out':'拉远',
    'zoom_in':'变焦拉近', 'zoom_out':'变焦拉远', 'follow_front':'前方跟拍',
    'follow_side':'侧面跟拍', 'follow_back':'后方跟拍', 'follow_rear':'后方跟拍', 'orbit_arc':'弧线环绕',
    'orbit_60':'60° 环绕', 'orbit_120':'120° 环绕', 'orbit_180':'180° 环绕', 'orbit_360':'360° 完整环绕',
    'orbit_full':'完整环绕', 'pan_follow':'固定机位转向跟随', 'pan':'固定机位转向跟随',
}
MOTION_LABELS = {'001':'摆臂转身','002':'调整站姿','003':'弯腰伸展','007':'四周张望',
    '008':'向前行走','009':'摆姿','017':'打喷嚏','018':'好奇探看','019':'思考','020':'扶额',
    '022':'举拳庆祝','023':'挥手','024':'鞠躬','029':'甩头转身','030':'舒展舞步',
    '032':'随乐舞动','033':'欢呼跳跃','034':'起跑','035':'边走边思考','036':'模特步行'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def manifest_from_plan(plan_path, run_root=RUN):
    """Return a draft dict. Root can add verified render receipts before build."""
    plan = read(plan_path)
    if plan.get('unified_duration_seconds') != 10 or not isinstance(plan.get('shots'), list):
        raise ValueError('Expected uniform ten-second shot plan')
    clips = []
    for shot in plan['shots']:
        shot_id = shot['shot_id']
        match = re.search(r'motion_cand_(\d+)', shot.get('clip_id', ''))
        motion = MOTION_LABELS.get(match.group(1), shot.get('clip_id', '未标注动作')) if match else shot.get('motion_label', '未标注动作')
        motion = shot.get('motion_label', motion)
        if shot['family'] not in ('static','dynamic','zoom','dolly','pan','follow','orbit'):
            raise ValueError('Unknown planned camera family')
        clips.append({'shot_id': shot_id, 'shot_type': shot['shot_type'], 'family': 'static' if shot['family']=='static' else 'dynamic',
            'camera_label': shot.get('camera_label', LABELS.get(shot['shot_type'], shot['shot_type'])),
            'motion_label': motion, 'sex': shot['sex'], 'duration_seconds': 10,
            'render_status': 'pending', 'review_status': 'pending',
            'video': 'videos/' + shot_id + '.mp4', 'poster': 'videos/' + shot_id + '.jpg',
            'trajectory_sha256': shot.get('trajectory_sha256'),
            'geometry_status': shot.get('status', 'unknown')})
    return {'schema':'camera_pilot_delivery_manifest_v1', 'title':'相机视角 · 十秒视频审查',
            'unified_duration_seconds':10, 'clips':clips}


def media_info(value, run_root, suffixes):
    if value is None:
        return {'url':None, 'exists':False}
    if not isinstance(value, str) or not value or '://' in value:
        raise ValueError('Media must be a local path within this run')
    root = Path(run_root).resolve()
    path = Path(value)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in suffixes:
        raise ValueError('Unsupported or escaped media path: ' + value)
    if suffixes == {'.mp4'} and not path.is_relative_to(root / 'videos'):
        raise ValueError('Videos must remain in the run videos directory')
    relative = os.path.relpath(path, root / 'gallery').replace('\\', '/')
    return {'url':quote(relative, safe='/.-_'), 'exists':path.is_file() and path.stat().st_size > 0}


def normalize_manifest(manifest, run_root):
    if manifest.get('schema') != 'camera_pilot_delivery_manifest_v1' or manifest.get('unified_duration_seconds') != 10:
        raise ValueError('Expected confirmed uniform ten-second gallery manifest')
    rows, seen = [], set()
    clips = manifest.get('clips')
    if not isinstance(clips, list) or not clips:
        raise ValueError('Nonempty clip list required')
    for clip in clips:
        key = clip.get('shot_id')
        if not isinstance(key,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,120}',key) or key in seen:
            raise ValueError('Unique safe shot_id required')
        seen.add(key)
        if clip.get('family') not in ('static','dynamic') or clip.get('sex') not in ('female','male'):
            raise ValueError('Expected static/dynamic family and female/male sex')
        duration = clip.get('duration_seconds')
        if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration != 10:
            raise ValueError('Gallery entries must target exactly ten seconds')
        trajectory = clip.get('trajectory_sha256')
        if trajectory is not None and not re.fullmatch('[a-fA-F0-9]{64}',trajectory):
            raise ValueError('Trajectory SHA must be 64 hex characters')
        video = media_info(clip.get('video'), run_root, {'.mp4'})
        poster = media_info(clip.get('poster'), run_root, {'.png','.jpg','.jpeg','.webp'})
        render = clip.get('render_status','pending')
        if render not in ('pending','rendered','render_failed','excluded'):
            raise ValueError('Unknown render status; geometry pass is not render completion')
        actual = clip.get('measured_duration_seconds')
        if actual is not None and (isinstance(actual,bool) or not isinstance(actual,(int,float)) or not math.isfinite(actual) or actual <= 0):
            raise ValueError('Invalid measured duration')
        duration_ok = actual is not None and abs(actual-10) <= .05
        review = clip.get('review_status','pending')
        if review not in ('pending','accepted','issue'):
            raise ValueError('Unknown human review status')
        # The generator cannot turn geometry/render success into user approval.
        if review != 'pending' and not clip.get('review_evidence'):
            raise ValueError('Human review state requires explicit evidence')
        playable = video['exists'] and render not in ('render_failed','excluded')
        if render == 'excluded':
            status = '暂不纳入'
        elif render == 'render_failed':
            status = '渲染未完成'
        elif not video['exists']:
            status = '等待视频'
        elif actual is not None and not duration_ok:
            status = '时长需检查'
        elif review == 'accepted':
            status = '已记录人工接受'
        elif review == 'issue':
            status = '已记录问题'
        else:
            status = '待人工审查'
        rows.append({'id':key,'family':clip['family'],'shot_type':clip.get('shot_type','unknown'),'camera':str(clip.get('camera_label') or LABELS.get(clip.get('shot_type'),clip.get('shot_type','未标注镜头'))),
            'motion':str(clip.get('motion_label','未标注动作')),'sex':'女性' if clip['sex']=='female' else '男性',
            'duration_label':'10秒' if duration_ok else '目标10秒', 'measured_duration_seconds':actual,
            'status':status,'playable':playable,'video':video['url'] if playable else None,
            'poster':poster['url'] if poster['exists'] else None,'trajectory':trajectory,
            'note':str(clip.get('note','')), 'render_status':render,'review_status':review})
    return rows


def build(manifest_path, run_root=RUN):
    manifest = read(manifest_path) if not isinstance(manifest_path,dict) else manifest_path
    rows = normalize_manifest(manifest, run_root)
    title = html.escape(str(manifest.get('title','相机视角 · 十秒视频审查')))
    data = json.dumps(rows,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template = Path(__file__).with_name('camera_pilot_gallery_v2.html').read_text(encoding='utf-8')
    output = template.replace('__TITLE__',title).replace('__DATA__',data).replace('__COUNT__',str(len(rows))).replace('__READY__',str(sum(r['playable'] for r in rows)))
    path = Path(run_root).resolve()/'gallery/index.html'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(output,encoding='utf-8')
    return {'index':str(path),'clips':len(rows),'playable':sum(r['playable'] for r in rows),
            'awaiting_video':sum(not r['playable'] for r in rows),'human_review_inferred':False}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--manifest', type=Path)
    source.add_argument('--plan', type=Path)
    parser.add_argument('--run-root',type=Path,default=RUN)
    args = parser.parse_args()
    manifest = args.manifest if args.manifest else manifest_from_plan(args.plan,args.run_root)
    print(json.dumps(build(manifest,args.run_root),ensure_ascii=False))


if __name__ == '__main__':
    main()
