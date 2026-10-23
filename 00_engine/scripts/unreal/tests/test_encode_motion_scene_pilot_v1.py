"""Real bundled FFmpeg tests for variable-duration encoding and recovery guards."""
from pathlib import Path
import json
import sys
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import encode_motion_scene_pilot_v1 as encoder


def case(tmp_path,count=9,width=1280,height=720):
    attempt='test_attempt';sid='test_shot'
    folder=tmp_path/'renders'/attempt/sid;folder.mkdir(parents=True)
    for i in range(count):Image.new('RGB',(width,height),(i*11%255,70,100)).save(folder/f'frame_{i:04d}.png')
    receipt={'attempt_id':attempt,'success':True,'status':'completed','output_root':str(folder.parent),'jobs':[{'shot_id':sid,'map':'test-map','sequence':'test-sequence'}],
             'render_contract':{'width':width,'height':height,'fps':30,'frame_counts_by_shot':{sid:count}}}
    (tmp_path/'render_receipts').mkdir()
    (tmp_path/'render_receipts'/f'{attempt}.json').write_text(json.dumps(receipt),encoding='utf-8')
    plan={'shots':[{'shot_id':sid,'width':width,'height':height,'fps':30,'frame_count':count,'duration_seconds':count/30}]}
    (tmp_path/'camera_trial_plan_v1.json').write_text(json.dumps(plan),encoding='utf-8')
    return attempt,sid,receipt,plan


@pytest.mark.parametrize('count,width,height',[(9,1280,720),(17,720,1280)])
def test_actual_encode_full_decode_and_matching_resume(tmp_path,count,width,height):
    attempt,sid,_,_=case(tmp_path,count,width,height)
    report=encoder.process(attempt,run=tmp_path)
    clip=report['videos'][0]
    assert clip['decoded_frames']==count and clip['ffmpeg_full_decode_frames']==count
    assert clip['dimensions']==[width,height] and clip['duration_seconds']==count/30
    assert len(clip['contact_frames'])==20 and clip['contact_frames'][-1]==count-1
    with Image.open(tmp_path/clip['timeline_contact']) as im:
        assert im.size==((1080,1648) if height>width else (1920,976))
    before=(tmp_path/'media_receipts'/f'{sid}.json').read_bytes()
    assert encoder.process(attempt,run=tmp_path)==report
    assert (tmp_path/'media_receipts'/f'{sid}.json').read_bytes()==before
    assert len(list((tmp_path/'renders'/attempt/sid).glob('*.png')))==count


def test_changed_raw_frame_blocks_resume_without_overwriting_video(tmp_path):
    attempt,sid,_,_=case(tmp_path)
    encoder.process(attempt,run=tmp_path)
    video=tmp_path/'videos'/f'{sid}.mp4';before=encoder.sha(video)
    Image.new('RGB',(1280,720),'red').save(tmp_path/'renders'/attempt/sid/'frame_0000.png')
    with pytest.raises(ValueError,match='binding differs'):encoder.process(attempt,run=tmp_path)
    assert encoder.sha(video)==before


def test_failed_attempt_and_mismatched_plan_rejected_before_output(tmp_path):
    attempt,sid,receipt,plan=case(tmp_path)
    receipt['success']=False
    with pytest.raises(ValueError,match='terminal success'):encoder.validate_contract(receipt,{sid:plan['shots'][0]})
    receipt['success']=True;plan['shots'][0]['frame_count']+=1
    with pytest.raises(ValueError,match='mismatch'):encoder.validate_contract(receipt,{sid:plan['shots'][0]})
    assert not (tmp_path/'videos').exists()


def test_missing_frame_rejected(tmp_path):
    attempt,sid,_,_=case(tmp_path)
    (tmp_path/'renders'/attempt/sid/'frame_0005.png').unlink()
    with pytest.raises(ValueError,match='PNG frames'):encoder.process(attempt,run=tmp_path)


def test_unknown_existing_video_is_preserved(tmp_path):
    attempt,sid,_,_=case(tmp_path)
    (tmp_path/'videos').mkdir();video=tmp_path/'videos'/f'{sid}.mp4';video.write_bytes(b'unknown retained bytes')
    with pytest.raises(ValueError,match='lacks verified receipt'):encoder.process(attempt,run=tmp_path)
    assert video.read_bytes()==b'unknown retained bytes'
