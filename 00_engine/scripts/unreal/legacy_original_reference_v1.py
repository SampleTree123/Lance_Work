"""Validated prior source-sex media fallback; SCENE_CAMERA_SEQUENCE §12."""
import copy,json
from pathlib import Path

CLOCK=('source_start_seconds','source_end_seconds','source_body_play_rate','duration_seconds','fps','frame_count')
NOTE='原性别先用此前已审样片：同一动作窗口和速度，构图可能不同，仅检查姿态兼容；不计入本轮1270条渲染。'

def load_references(run,cross_clips):
    from build_camera_alignment_gallery_v1 import validate,local_file,digest
    run=Path(run);root=run/'references/legacy_original';path=root/'index_v1.json';result=[];pending=[]
    if not path.exists():return result,pending
    try:
        index=json.loads(path.read_text(encoding='utf-8-sig'));assert index['schema']=='legacy_original_review_references_v1'
        cp=local_file(run,index['candidate']['path']);assert digest(cp)==index['candidate']['sha256']
        candidates={x['motion_id']:x for x in json.loads(cp.read_text(encoding='utf-8-sig'))['records']}
    except (ValueError,KeyError,AssertionError,OSError) as e:return [],[{'reason':'此前参考来源未验证：'+str(e)}]
    seen=set()
    for record in index['references']:
        mid=record.get('motion_id')
        try:
            assert mid not in seen;seen.add(mid)
            candidate=candidates[mid];sex=record['sex'];assert sex==candidate['original_sex']
            cross=next(x for x in cross_clips if x['motion_id']==mid and x['sex']!=sex)
            contract=record['playback_contract'];assert contract==candidate['accepted_playback_contract']==cross['playback_contract']
            clip=copy.deepcopy(record['clip']);expected=candidate['variants'][sex]['review_video']
            assert clip['motion_id']==mid and clip['sex']==sex and clip['id']==expected['shot_id']
            assert clip['video_sha256']==expected['video']['sha256'] and clip['verification_receipt_sha256']==expected['receipt']['sha256']
            assert clip['duration_seconds']==contract['duration_seconds'] and clip['fps']==contract['fps'] and clip['decoded_frames']==contract['frame_count']
            for item in record['copied_files']:assert digest(local_file(root,item['path']))==item['sha256']
            checked=validate(dict(schema='camera_motion_scene_alignment_review_v1',motions=[{'id':mid}],cameras=[{'id':clip['camera_id']}],clips=[clip],scenes=[]),root)['clips'][0]
            assert checked['playable'];prefix='references/legacy_original/'
            for field in ('video','poster','verification_receipt'):
                if checked.get(field):checked[field]=prefix+checked[field]
            checked.update(reference_kind='prior_accepted_original_sex',not_current_render=True,note=NOTE,playback_contract=contract)
            result.append(checked)
        except (ValueError,KeyError,AssertionError,OSError,StopIteration) as e:
            pending.append(dict(motion_id=mid,reason='此前参考未验证，继续等待本轮样片：'+str(e)))
    return result,pending
