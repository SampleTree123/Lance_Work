import importlib.util,json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('encoder',Path(__file__).parents[1]/'encode_camera_pilot_v1.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def test_png_fingerprint_detects_changed_frame(tmp_path):
 for i in range(300):(tmp_path/f'frame_{i:04d}.png').write_bytes(str(i).encode())
 _,records,before=e.png_evidence(tmp_path)
 assert len(records)==300
 (tmp_path/'frame_0149.png').write_bytes(b'changed')
 assert e.png_evidence(tmp_path)[2]!=before
 (tmp_path/'frame_0300.png').write_bytes(b'extra')
 with pytest.raises(ValueError,match='Missing/extra'):e.png_evidence(tmp_path)

def test_resume_requires_pins_and_decodes_again(tmp_path,monkeypatch):
 video=tmp_path/'a.mp4';video.write_bytes(b'video');calls=[]
 decoded={'decoded_frames':300,'fps':30,'measured_duration_seconds':10,'dimensions':[1280,720]}
 monkeypatch.setattr(e,'decode_video',lambda *args:calls.append(args) or decoded)
 expected={'attempt':'one','png_sequence_sha256':'abc','render_receipt_sha256':'xyz'}
 receipt={'schema':'camera_pilot_encoded_shot_v1','status':'encoded_verified',**expected,'video_sha256':e.sha(video),'decode':decoded}
 assert e.verify_resume(receipt,expected,video,1280,720)==decoded and len(calls)==1
 with pytest.raises(ValueError,match='binding differs'):e.verify_resume(receipt,{**expected,'png_sequence_sha256':'other'},video,1280,720)
 video.write_bytes(b'altered')
 with pytest.raises(ValueError,match='pin differs'):e.verify_resume(receipt,expected,video,1280,720)

def test_orphan_video_is_preserved_and_rejected(tmp_path,monkeypatch):
 monkeypatch.setattr(e,'RUN',tmp_path)
 (tmp_path/'render_receipts').mkdir();(tmp_path/'videos').mkdir()
 receipt={'success':True,'status':'completed','render_contract':{'width':1280,'height':720,'fps':30,'frame_count':300,'duration_seconds':10},'jobs':[{'shot_id':'shot','map':'map','sequence':'seq'}]}
 (tmp_path/'render_receipts'/'one.json').write_text(json.dumps(receipt),encoding='utf-8')
 video=tmp_path/'videos'/'shot.mp4';video.write_bytes(b'keep')
 monkeypatch.setattr(e,'png_evidence',lambda _:([tmp_path/'unused'],[],'source'))
 with pytest.raises(ValueError,match='no verification receipt'):e.process('one')
 assert video.read_bytes()==b'keep'

def test_dense_contacts_cover_motion_and_closeups_only():
 for name in ['cam_04_zoom_in','cam_13_follow_front','cam_18_orbit_60','cam_29_pan','cam_03_static_head','cam_02_static_upper']:assert e.needs_dense_contact(name)
 assert not e.needs_dense_contact('cam_01_static_front')

@pytest.mark.parametrize('value',['../outside','x/y','','a.b'])
def test_unsafe_attempt_rejected(value):
 with pytest.raises(ValueError):e.identifier(value)
