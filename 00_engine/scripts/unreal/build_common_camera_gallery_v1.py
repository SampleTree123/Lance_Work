"""Publish the bounded 120-shot common-camera review. Owner: SCENE_CAMERA_SEQUENCE §14.

Reuse the existing receipt/media validator. Pending shots never receive media URLs.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
from build_camera_alignment_gallery_v1 import validate, digest, local_file, CAMERA_ORDER
from encode_motion_scene_pilot_v1 import object_sha

S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/camera_common_presets_20261014_v1'

def build(run=RUN):
    run=Path(run).resolve();source=run/'camera_trial_plan_v2.json'
    plan=json.loads(source.read_text(encoding='utf-8-sig'))
    if plan.get('schema') not in ('camera_common_presets_trial_v1','camera_common_presets_trial_v2'):
        raise ValueError('Expected bounded common-camera trial plan')
    shots={s['shot_id']:s for s in plan['shots']}
    if len(shots)!=120 or len({s['motion_id'] for s in shots.values()})!=3 or len({s['camera_id'] for s in shots.values()})!=20 or any(s['camera_id']=='front_head' for s in shots.values()):
        raise ValueError('Expected 3 actions × 20 cameras × 2 orientations, without face closeup')
    media={}
    for path in sorted(run.glob('media_validation_*.json')):
        report=json.loads(path.read_text(encoding='utf-8-sig'))
        if report.get('schema')!='motion_scene_media_validation_v1' or report.get('success') is not True:
            continue
        for row in report['videos']:
            sid=row['shot_id']
            if sid not in shots:continue
            rp=local_file(run,row['verification_receipt'])
            if digest(rp)!=row['verification_receipt_sha256']:raise ValueError('Changed receipt: '+sid)
            receipt=json.loads(rp.read_text(encoding='utf-8-sig'))
            if receipt.get('shot_plan_sha256')!=object_sha(shots[sid]):raise ValueError('Receipt plan differs: '+sid)
            if sid in media and media[sid]!=row:raise ValueError('Conflicting media: '+sid)
            media[sid]=row
    motions={};cameras={};clips=[]
    for sid,shot in shots.items():
        mid=shot['motion_id'];cid=shot['camera_id']
        motions[mid]={'id':mid,'label':shot['motion_label']}
        cameras[cid]={'id':cid,'label':shot['camera_label']}
        row={key:shot[key] for key in ('motion_id','camera_id','sex','orientation','width','height','duration_seconds','fps')}
        row.update(id=sid,section='cameras',verification_status='pending',
                   common_preset_parameters={**shot.get('common_preset_parameters',{}),
                       'horizontal_fov_degrees':shot['frames'][0]['horizontal_fov_degrees']},
                   tracking_policy=shot.get('tracking_policy',{}),
                   follow_diagnostics=shot.get('follow_diagnostics',{}),
                   framing_diagnostics=shot.get('framing_diagnostics',{}))
        if mid=='MOTION_CAND_003' and cid=='front_upper':
            row['review_notes']={'source':'本轮样片检查','human_acceptance':'pending',
                'message_zh':'深弯腰时主要看到头发和肩背；约4.4–4.8秒起身时可能短暂裁到头部，请重点检查跟随是否自然。',
                'scope':'仅弯腰伸展正面上半身横竖样片，不外推其他视角。'}
        if mid=='MOTION_CAND_030' and cid=='back_upper' and shot['orientation']=='portrait':
            row['review_notes']={'source':'本轮代表帧采样检查','human_acceptance':'pending',
                'message_zh':'约12.2秒的采样画面中躯干靠左边缘、局部出画；下一采样13.4秒已恢复。请实际播放检查跟随与裁切是否合适。',
                'scope':'仅舞蹈竖屏背面上半身样片；这是离散采样，不能据此判断出画持续多久，也不外推其他视角。'}
        if sid in media:
            for key in ('video','video_sha256','poster','decoded_frames','verification_status','verification_receipt','verification_receipt_sha256'):
                if key in media[sid]:row[key]=media[sid][key]
        clips.append(row)
    for cid in cameras:
        for orientation in ('landscape','portrait'):
            values=[c['common_preset_parameters'] for c in clips if c['camera_id']==cid and c['orientation']==orientation]
            if len(values)!=3 or any(v!=values[0] for v in values[1:]):
                raise ValueError('Three actions do not share preset parameters: '+cid+'/'+orientation)
    rank={cid:i for i,cid in enumerate(CAMERA_ORDER)}
    data={'schema':'camera_motion_scene_alignment_review_v1','trial_schema':'camera_common_presets_review_v1',
          'motions':sorted(motions.values(),key=lambda m:({'MOTION_CAND_008':0,'MOTION_CAND_030':1,'MOTION_CAND_003':2}.get(m['id'],3),m['id'])),
          'cameras':sorted(cameras.values(),key=lambda c:rank.get(c['id'],99)),
          'clips':clips,'scenes':[],'updated_at':datetime.now(timezone.utc).isoformat(),
          'plan_sha256':digest(source),'human_acceptance':'pending'}
    data=validate(data,run)
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    gallery=run/'gallery';gallery.mkdir(exist_ok=True)
    html=(S/'common_camera_gallery_v1.html').read_text(encoding='utf-8').replace('__DATA__',encoded)
    target=gallery/'index.html';temporary=gallery/'index.html.partial';temporary.write_text(html,encoding='utf-8');temporary.replace(target)
    manifest=run/'review_delivery_manifest_v1.json';temporary=manifest.with_suffix('.json.partial');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(manifest)
    (gallery/'打开共用镜头审查.cmd').write_text('@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "'+str(S/'open_common_camera_gallery_v1.py')+'" --run-root "'+str(run)+'" %*\nif errorlevel 1 pause\n',encoding='utf-8')
    return {'index':str(target),'clips':len(clips),'playable':data['playable_count'],'human_acceptance':'pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,default=RUN)
    print(json.dumps(build(p.parse_args().run_root),ensure_ascii=False))
