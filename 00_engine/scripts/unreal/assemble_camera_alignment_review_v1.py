"""Publish only verified calibration media and explicit scene import outcomes. SCENE_CAMERA_SEQUENCE §12."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
from encode_motion_scene_pilot_v1 import read, sha, object_sha, owned, atomic_json

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/camera_motion_scene_alignment_20261012_v1')


def visual_risks(run, shot_ids, filename='smoke_visual_risks_for_review_v2.json'):
    path=run/filename
    if not path.exists():return {},None
    report=read(path)
    if report.get('schema')!='camera_review_visual_risks_v1' or report.get('automatic_visual_pass') is not False:
        raise ValueError('Unknown or automatically accepted visual-risk report')
    result={}
    for item in report['items']:
        sid=item['shot_id']
        if sid not in shot_ids or sid in result:raise ValueError('Unknown or duplicate visual-risk shot')
        if item.get('visual_acceptance')!='pending_not_passed' or item.get('level') not in ('review','priority_review'):
            raise ValueError('Visual risk must remain explicitly unaccepted')
        result[sid]=item
    return result,dict(path=str(path),sha256=sha(path))


def cross_visual_risks(run, shot_ids):
    path=run/'legacy_cross_sex_visual_audit_v1.json'
    if not path.exists():return {},None
    report=read(path)
    if report.get('schema')!='legacy_cross_sex_visual_audit_v1':raise ValueError('Unknown cross-sex visual audit')
    proof=report['media_validation'];media=owned(run,run/proof['path'])
    if proof.get('success') is not True or sha(media)!=proof['sha256']:raise ValueError('Cross-sex visual audit media proof changed')
    result={}
    for item in report['risks']:
        sid=item['shot_id']
        if sid not in shot_ids or sid in result:raise ValueError('Unknown or duplicate cross-sex risk shot')
        if item['type']!='outfit_pose_compatibility':raise ValueError('Unknown cross-sex visual risk')
        result[sid]=dict(shot_id=sid,level='review',visual_acceptance='pending_not_passed',
            type=item['type'],title='动作与服装搭配待审',message_zh=item['message_zh']+' '+item['recommendation_zh'],
            duration_note_zh='这是抽样时刻的服装表现，不代表跨性别骨骼转换失败，也不代表全部服装已检查。',
            attention_seconds=[item['time_seconds']],evidence_frame=item['frame'])
    return result,dict(path=str(path),sha256=sha(path))


def scene_index(run, scene_index_path=None):
    if scene_index_path is None:
        path=run/'scenes/gallery_scene_index_v1.json'
        if not path.exists():return [],None
        from scene_path_relocation_v1 import build_current_index
        return build_current_index(path)['scenes'],None
    path=Path(scene_index_path).resolve()
    data=read(path)
    if data.get('schema')!='gallery_scene_index_relocated_v2' or data.get('camera_render_started') is not False:
        raise ValueError('Explicit scene index must be the verified relocated v2 index')
    expected={'relocated_scene_roots':24,'relocated_scene_maps':74,'shared_starter_maps':3,
              'effective_gallery_maps':77,'display_cards':24,'retired_duplicate_worlds':1}
    if data.get('effective_map_counts')!=expected:
        raise ValueError('Relocated scene index requires all24 roots/74 scene maps')
    for key in ('source_index','relocation_registry','global_relocation_proof'):
        pin=data[key]
        if sha(Path(pin['path']))!=pin['sha256']:
            raise ValueError('Explicit scene index provenance changed: '+key)
    proof=read(Path(data['global_relocation_proof']['path']))
    if (proof.get('schema')!='final_registry_and_reference_check_v1' or proof.get('success') is not True
            or proof.get('scene_root_count')!=24 or proof.get('map_count')!=74
            or proof.get('stale_scene_dependencies')!=[] or proof.get('camera_render_started') is not False
            or proof.get('registry_sha256')!=data['relocation_registry']['sha256']):
        raise ValueError('Explicit scene index requires the successful global relocation proof')
    from scene_path_relocation_v1 import read_overlay
    overlay=read_overlay(Path(data['relocation_registry']['path']))
    if len(overlay['mappings'])!=24 or any(r.get('status')!='verified' for r in overlay['mappings']):
        raise ValueError('Explicit scene index requires the complete verified overlay')
    scenes=data['scenes'];maps=[p for r in scenes for p in r['all_maps']]
    if (len(scenes)!=24 or len(maps)!=len(set(maps)) or len(maps)!=77
            or any(not set(r['maps']).issubset(r['all_maps']) for r in scenes)):
        raise ValueError('Explicit scene index full map coverage changed')
    return scenes,dict(path=str(path),sha256=sha(path))


def assemble(run=RUN, scene_index_path=None):
    run = Path(run).resolve()
    plan_paths = [run / 'camera_trial_plan_v2.json']
    extra = run / 'legacy_cross_sex_camera_plan_v1.json'
    if extra.exists():
        plan_paths.append(extra)
    shots = {}
    for path in plan_paths:
        for shot in read(path)['shots']:
            sid = shot['shot_id']
            if sid in shots:
                raise ValueError('Duplicate calibration shot: ' + sid)
            shots[sid] = shot
    media = {}
    for path in sorted(run.glob('media_validation_*.json')):
        report = read(path)
        if report.get('schema') != 'motion_scene_media_validation_v1' or report.get('success') is not True:
            continue
        for row in report['videos']:
            sid = row['shot_id']
            if sid not in shots:
                continue
            rp = owned(run, run / row['verification_receipt'])
            if sha(rp) != row['verification_receipt_sha256']:
                raise ValueError('Changed media receipt: ' + sid)
            receipt = read(rp)
            if (receipt.get('status') != 'encoded_verified' or receipt['shot_id'] != sid
                    or receipt['shot_plan_sha256'] != object_sha(shots[sid])
                    or receipt['video_sha256'] != row['video_sha256']):
                raise ValueError('Video source binding differs: ' + sid)
            if sid in media and media[sid] != row:
                raise ValueError('Conflicting verified media: ' + sid)
            media[sid] = row
    risks,risk_source=visual_risks(run,set(shots))
    cross_risks,cross_source=cross_visual_risks(run,set(shots))
    batch_risks,batch_source=visual_risks(run,set(shots),'first_batch_visual_risks_for_review_v1.json')
    for extra_risks in (cross_risks,batch_risks):
        if set(risks)&set(extra_risks):raise ValueError('Duplicate visual risk across sources')
        risks.update(extra_risks)
    motions, cameras, clips = {}, {}, []
    for sid, shot in shots.items():
        cross = shot.get('group') == 'legacy_cross_sex'
        mid = shot['motion_id']
        if mid not in motions or not cross:
            motions[mid] = dict(id=mid,label=shot['motion_label'],source_sex=shot['sex'],
                output_duration_seconds=shot['duration_seconds'])
        cameras[shot['camera_id']] = dict(id=shot['camera_id'],label=shot['camera_label'])
        calibration = shot.get('calibration', {})
        depth_exception = shot.get('closeup_depth_exception')
        exception = shot.get('scale_exception') or depth_exception
        exception_note = ''
        if isinstance(exception,dict):
            base = exception['baseline_endpoint_distances_cm'][0] / 100
            adjusted = exception['adjusted_endpoint_distances_cm'][0] / 100
            if depth_exception:
                exception_note = f'近景中身体会过于接近镜头，距离由 {base:.2f} 米调整为 {adjusted:.2f} 米，保留最小拍摄空间；仍请检查局部裁切。'
            else:
                exception_note = f'此动作在公共距离下会有身体部位出画，镜头距离由 {base:.2f} 米调整为 {adjusted:.2f} 米，以容纳动作幅度。'
        row = dict(id=sid,section='cross_sex' if cross else 'cameras',motion_id=mid,
            camera_id=shot['camera_id'],sex=shot['sex'],orientation=shot['orientation'],
            width=shot['width'],height=shot['height'],duration_seconds=shot['duration_seconds'],
            fps=shot['fps'],verification_status='pending',
            scale_exception=bool(exception or calibration.get('scale_exception',False)),
            scale_exception_reason=exception_note or shot.get('scale_exception_reason',calibration.get('scale_exception_reason','')))
        if sid in media:
            for key in ('video','video_sha256','poster','decoded_frames','verification_status',
                        'verification_receipt','verification_receipt_sha256'):
                row[key] = media[sid][key]
        else:
            row['note'] = '正在生成；完成编码和检查后开放播放。'
        row['visual_status']='pending_not_passed' if sid in risks else 'pending_review'
        if sid in risks:row['visual_risk']=risks[sid]
        if cross:
            from legacy_original_reference_v1 import CLOCK
            row['playback_contract']={key:shot[key] for key in CLOCK}
            refs = [s['shot_id'] for s in shots.values() if s['motion_id']==mid
                    and s.get('group')!='legacy_cross_sex' and s['camera_id']=='front_full'
                    and s['orientation']=='landscape']
            if len(refs)==1:
                row['reference_clip_id']=refs[0]
        clips.append(row)
    scenes,scene_source=scene_index(run,scene_index_path)
    data=dict(schema='camera_motion_scene_alignment_review_v1',motions=list(motions.values()),
        cameras=list(cameras.values()),clips=clips,scenes=scenes,
        updated_at=datetime.now(timezone.utc).isoformat(),human_acceptance='pending',
        camera_policy='多数动作使用统一人物尺度；大幅度动作需要拉远时单独标注。近景允许已有约定的局部裁切。',
        summary_notes=['在空白场景对照各动作的同类镜头。身体动作沿用已确认窗口和速度。',
                       '场景本轮只导入与加载检查，尚未选择拍摄点位。'],
        source_plans=[dict(path=str(p),sha256=sha(p)) for p in plan_paths])
    if risk_source:data['visual_risk_source']=risk_source
    if scene_source:data['scene_index_source']=scene_source
    data['visual_risk_sources']=[source for source in (risk_source,cross_source,batch_source) if source]
    atomic_json(run/'review_gallery_input_v1.json',data)
    from build_camera_alignment_gallery_v1 import build
    return build(run)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,default=RUN)
    parser.add_argument('--scene-index',type=Path,help='Use the complete verified relocated v2 display index')
    args=parser.parse_args()
    print(assemble(args.run,args.scene_index))
