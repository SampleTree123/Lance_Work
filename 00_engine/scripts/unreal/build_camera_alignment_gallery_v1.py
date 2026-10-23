"""Independent camera calibration/cross-sex/scene-import review publisher.

Owner: SCENE_CAMERA_SEQUENCE §12. Input comes from actual media verification
receipts; unverified rows remain visible but never acquire video URLs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_motion_scene_alignment_20261012_v1'
LEGACY_LABELS = S.parent / 'dataset/prompt_catalog_first_batch_v1.json'
CAMERA_ORDER = (
    'front_full','front_three_quarter_full','side_full','rear_three_quarter_full','back_full',
    'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper',
    'front_head','high_full','low_full','orbit_360','orbit_120',
    'dolly_in_front','dolly_in_side','dolly_in_back',
    'dolly_out_front','dolly_out_side','dolly_out_back')

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def local_file(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or re.match(r'^[A-Za-z]:',relative):
        raise ValueError('Require relative media path')
    target=(root/relative).resolve()
    target.relative_to(root.resolve())
    if not target.is_file():raise FileNotFoundError(target)
    return target

def presentation(data):
    """Display-only names/order; never rewrites a camera plan or motion ID."""
    ranks={name:i for i,name in enumerate(CAMERA_ORDER)}
    data['cameras']=sorted(data.get('cameras',[]),key=lambda c:(ranks.get(c['id'],len(ranks)),c['id']))
    ids=[c['id'] for c in data['cameras']]
    data['default_camera_id']='front_full' if 'front_full' in ids else next(iter(ids),'')
    legacy=[m for m in data.get('motions',[]) if m['id'].startswith('ACT_')]
    if legacy:
        labels=json.loads(LEGACY_LABELS.read_text(encoding='utf-8-sig'))['labels']['action']
        for motion in legacy:
            label=labels[motion['id'].lower()]['zh-CN']
            sex=motion.get('source_sex') or ('female' if motion['id'].startswith('ACT_F') else 'male')
            if sex not in ('female','male'):raise ValueError('Unknown legacy source sex')
            motion.setdefault('source_label',motion.get('label',motion['id']))
            motion['label']=label+'（原'+('女性' if sex=='female' else '男性')+'动作）'
        data['display_label_source']={'path':str(LEGACY_LABELS),'sha256':digest(LEGACY_LABELS),
                                      'field':'labels.action.<lowercase_action_id>.zh-CN',
                                      'scope':'display names only; historical production settings are not imported'}
    return data

def validate(data,run):
    if data.get('schema')!='camera_motion_scene_alignment_review_v1':raise ValueError('Unknown schema')
    for key in ('motions','cameras','clips','scenes'):
        data.setdefault(key,[])
        ids=[r['id'] for r in data[key]]
        if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',x) for x in ids):
            raise ValueError('Duplicate or unsafe IDs: '+key)
    motions={r['id'] for r in data['motions']};cameras={r['id'] for r in data['cameras']}
    tuples=set()
    for clip in data['clips']:
        if clip['section'] not in ('cameras','cross_sex') or clip['motion_id'] not in motions or clip['camera_id'] not in cameras:
            raise ValueError('Unknown clip dimensions: '+clip['id'])
        if clip.get('sex') not in ('male','female') or clip.get('orientation') not in ('landscape','portrait'):
            raise ValueError('Require sex/orientation: '+clip['id'])
        key=tuple(clip[k] for k in ('section','motion_id','camera_id','sex','orientation'))
        if key in tuples:raise ValueError('Duplicate combination: '+clip['id'])
        tuples.add(key)
        clip['playable']=False;clip['human_acceptance']='pending'
        risk=clip.get('visual_risk')
        if risk:
            if risk.get('shot_id')!=clip['id'] or risk.get('level') not in ('review','priority_review') or risk.get('visual_acceptance')!='pending_not_passed':
                raise ValueError('Visual warning must match this shot and remain unaccepted')
            if not all(isinstance(risk.get(k),str) and risk[k] for k in ('title','message_zh','duration_note_zh')):
                raise ValueError('Visual warning needs human-readable scope')
            for time in risk.get('attention_seconds',[]):
                if isinstance(time,bool) or not isinstance(time,(int,float)) or not math.isfinite(time) or time<0 or time>clip.get('duration_seconds',math.inf)+.05:
                    raise ValueError('Visual attention time outside clip')
            clip['visual_status']='pending_not_passed'
        else:clip['visual_status']='pending_review'
        if type(clip.get('scale_exception',False)) is not bool:raise ValueError('Exception must be boolean')
        if clip.get('scale_exception') and not clip.get('scale_exception_reason'):raise ValueError('Scale exception needs an explanation')
        if clip.get('verification_status')!='encoded_verified':
            clip.pop('video',None);clip.pop('poster',None)
            continue
        duration,fps,count=(clip[k] for k in ('duration_seconds','fps','decoded_frames'))
        if not all(not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in (duration,fps,count)):
            raise ValueError('Invalid media timing')
        if int(count)!=count or abs(count/fps-duration)>1/fps+.001:raise ValueError('Decoded length differs')
        dims=(clip['width'],clip['height'])
        if dims not in ((1280,720),(720,1280)):raise ValueError('Unexpected review resolution')
        if clip['orientation']!=('portrait' if dims[1]>dims[0] else 'landscape'):raise ValueError('Orientation mismatch')
        media=local_file(run,clip['video'])
        if media.suffix.lower()!='.mp4' or digest(media)!=clip['video_sha256']:raise ValueError('Media SHA mismatch: '+clip['id'])
        receipt_path=local_file(run,clip['verification_receipt'])
        if digest(receipt_path)!=clip['verification_receipt_sha256']:raise ValueError('Receipt SHA mismatch')
        receipt=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
        if receipt.get('schema')!='motion_scene_encoded_shot_v1' or receipt.get('status')!='encoded_verified':raise ValueError('Receipt is not fully encoded/verified')
        for key,expected in [('shot_id',clip['id']),('video',clip['video']),('video_sha256',clip['video_sha256']),('width',dims[0]),('height',dims[1]),('expected_frames',count)]:
            if receipt.get(key)!=expected:raise ValueError('Receipt metadata differs: '+key)
        decoded=receipt['decode']
        if decoded.get('ffmpeg_full_decode_success') is not True or decoded.get('ffmpeg_full_decode_frames')!=count or decoded.get('decoded_frames')!=count or decoded.get('dimensions')!=list(dims) or abs(decoded['fps']-fps)>1e-8 or abs(decoded['measured_duration_seconds']-duration)>1e-6:
            raise ValueError('Receipt full-decode metadata differs')
        clip['video']=media.relative_to(run).as_posix()
        if clip.get('poster'):clip['poster']=local_file(run,clip['poster']).relative_to(run).as_posix()
        clip['playable']=True
    index={c['id']:c for c in data['clips']}
    for clip in data['clips']:
        if clip.get('reference_clip_id'):
            ref=index.get(clip['reference_clip_id'])
            if not ref or clip['section']!='cross_sex' or ref['section']!='cameras' or ref['motion_id']!=clip['motion_id'] or ref['sex']==clip['sex']:
                raise ValueError('Cross-sex reference must be same action / opposite sex')
    scene_statuses={'imported_verified','copied_pending_ue','already_present','failed','incomplete','pending'}
    for scene in data['scenes']:
        if scene.get('status') not in scene_statuses:raise ValueError('Unknown scene status')
    if (Path(run)/'references/legacy_original/index_v1.json').exists() and any(c['section']=='cross_sex' for c in data['clips']):
        from legacy_original_reference_v1 import load_references
        data['original_sex_references'],data['original_sex_reference_pending']=load_references(run,[c for c in data['clips'] if c['section']=='cross_sex'])
    data.update(playable_count=sum(c['playable'] for c in data['clips']),human_acceptance='pending',
                visual_risk_count=sum(bool(c.get('visual_risk')) for c in data['clips']),
                priority_visual_risk_count=sum(c.get('visual_risk',{}).get('level')=='priority_review' for c in data['clips']))
    return data

def build(run=RUN):
    run=Path(run).resolve();source=run/'review_gallery_input_v1.json'
    data=presentation(validate(json.loads(source.read_text(encoding='utf-8-sig')),run))
    data['input_sha256']=digest(source)
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    gallery=run/'gallery';gallery.mkdir(exist_ok=True)
    html=(S/'camera_alignment_gallery_v1.html').read_text(encoding='utf-8').replace('__DATA__',encoded)
    tmp=gallery/'index.html.partial';tmp.write_text(html,encoding='utf-8');tmp.replace(gallery/'index.html')
    (gallery/'打开相机校对审查.cmd').write_text('@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "'+str(S/'open_camera_alignment_gallery_v1.py')+'" --run-root "'+str(run)+'" %*\nif errorlevel 1 pause\n',encoding='utf-8')
    (run/'review_delivery_manifest_v1.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'index':str(gallery/'index.html'),'clips':len(data['clips']),'playable':data['playable_count'],'human_acceptance':'pending'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-root',type=Path,default=RUN)
    print(json.dumps(build(parser.parse_args().run_root),ensure_ascii=False))
