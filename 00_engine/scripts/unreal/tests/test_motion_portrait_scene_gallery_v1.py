"""Validate pilot review media admission and variable-duration handling."""
import hashlib
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_motion_portrait_scene_gallery_v1 as gallery


def fixture_run(tmp_path, duration=6.0):
    (tmp_path/'videos').mkdir()
    video=tmp_path/'videos/motion.mp4'
    video.write_bytes(b'fixture for admission checks; not a decoded video')
    data={'schema':'motion_portrait_scene_review_v1','motions':[{'id':'walk','label':'行走'}], 'scenes':[], 'clips':[
        {'id':'clip1','section':'motions','motion_id':'walk','camera_id':'front','camera_label':'正面全身','orientation':'landscape',
         'video':'videos/motion.mp4','video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
         'verification_status':'encoded_verified','duration_seconds':duration,'fps':30,'decoded_frames':round(duration*30),'width':1280,'height':720}]}
    return data


def build_data(tmp_path,data):
    (tmp_path/'review_gallery_input_v1.json').write_text(json.dumps(data),encoding='utf-8')
    return gallery.build(tmp_path)


@pytest.mark.parametrize('duration',[3.5,6,10,15.0666666667])
def test_variable_duration_admitted_without_ten_second_assumption(tmp_path,duration):
    result=build_data(tmp_path,fixture_run(tmp_path,duration))
    assert result['playable']==1
    assert result['human_acceptance']=='pending'


def test_changed_video_rejected(tmp_path):
    data=fixture_run(tmp_path)
    (tmp_path/'videos/motion.mp4').write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'): build_data(tmp_path,data)


def test_unverified_media_not_exposed(tmp_path):
    data=fixture_run(tmp_path);data['clips'][0]['verification_status']='rendered'
    assert build_data(tmp_path,data)['playable']==0
    final=json.loads((tmp_path/'review_delivery_manifest_v1.json').read_text(encoding='utf-8'))
    assert 'video' not in final['clips'][0]


def test_path_escape_rejected(tmp_path):
    data=fixture_run(tmp_path);data['clips'][0]['video']='../outside.mp4'
    with pytest.raises(ValueError):build_data(tmp_path,data)


def test_mismatched_timing_rejected(tmp_path):
    data=fixture_run(tmp_path);data['clips'][0]['decoded_frames']=60
    with pytest.raises(ValueError,match='Duration'):build_data(tmp_path,data)


def test_wrong_orientation_rejected(tmp_path):
    data=fixture_run(tmp_path);data['clips'][0]['orientation']='portrait'
    with pytest.raises(ValueError,match='Orientation'):build_data(tmp_path,data)


def test_duplicate_clip_rejected(tmp_path):
    data=fixture_run(tmp_path);data['clips'].append(dict(data['clips'][0]))
    with pytest.raises(ValueError,match='duplicate'):build_data(tmp_path,data)
