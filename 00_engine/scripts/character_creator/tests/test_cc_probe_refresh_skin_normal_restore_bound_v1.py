"""Actual female lineage + unchanged private engine + honest image completeness."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_probe_refresh_skin_normal_restore_bound_v1 as bound
import cc_probe_refresh_skin_normal_restore_v1 as public
ROOT=Path(__file__).resolve().parents[4]
LIB=ROOT/'00_engine/scripts/character_creator/runtime_staging/character_refresh_20261018_v1/WF003_skin_normal_restore_library_v1.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):return dict(path=str(p),sha256=sha(p))
class Img:
 def __init__(self,p):self.im=Image.open(p)
 def isNull(self):return False
 def width(self):return self.im.width
 def height(self):return self.im.height
API=types.SimpleNamespace(sha256_file=sha,read_json=read,QtGui=types.SimpleNamespace(QImage=Img))

def test_real_WF_maps_bind_own_v9_recovery_verification_combined_completed_chain():
 c=read(LIB)['refresh_skin_normal_restore_bound']
 assert set(bound.validate_bound(c,API))==bound.SKINS
 assert c['source_project']['sha256']=='fd28fcc3c2db3897fb535495ba721a7fd9102a87f5a1fe1755b1da7b8d100522'
 assert c['skin_normal_maps']['Std_Skin_Head']['sha256']=='35bfcbc13d595ea617f05e56434271196a27e1372100f0ce1149e56c6629b171'


def test_male_map_cannot_substitute_for_female_head():
 c=read(LIB)['refresh_skin_normal_restore_bound'];male=read(LIB.with_name('LM002_skin_normal_restore_library_v1.json'))['refresh_skin_normal_restore']
 c['skin_normal_maps']['Std_Skin_Head']=male['skin_normal_maps']['Std_Skin_Head']
 with pytest.raises(ValueError,match='Own exact after_skin'):bound.validate_bound(c,API)


@pytest.mark.parametrize('what',['verification','runtime'])
def test_failed_recovery_or_runtime_receipt_cannot_authorize(what):
 c=read(LIB)['refresh_skin_normal_restore_bound']
 def altered(p):
  d=read(p)
  if p==c['prelash_report'if what=='verification'else'proven_runtime_report']['path']:d['success']=False
  return d
 api=types.SimpleNamespace(sha256_file=sha,read_json=altered,QtGui=API.QtGui)
 with pytest.raises(ValueError):bound.validate_bound(c,api)


def test_private_adapter_does_not_modify_public_frozen_module_or_source():
 before=sha(bound.ENGINE);original=public.validate_inputs
 private=bound.private_engine();private.validate_inputs=lambda *a:None
 assert public.validate_inputs is original and private is not public
 assert sha(bound.ENGINE)==before==bound.ENGINE_SHA
 assert private.run.__code__.co_code==public.run.__code__.co_code


def test_missing_twice_is_stable_but_never_a_real_normal_image_gate():
 snapshot=dict(pixel_capture_complete=True,materials=[dict(owner='avatar',mesh='CC_Base_Body',material=m,textures={},missing_textures={'bump':dict(reason='sdk_known_warning_image'),'normal':dict(reason='sdk_empty_image')})for m in bound.SKINS])
 assert public.pixel_compare(snapshot,copy.deepcopy(snapshot),None)['passed']
 with pytest.raises(ValueError,match='no actual decoded'):public.verify_restored_maps(snapshot,{m:dict(width=2048,height=2048)for m in bound.SKINS},None)


def test_wrapper_preserves_raw_engine_receipts_and_reports_same_bytes_WF_alias(tmp_path,monkeypatch):
 c=read(LIB)['refresh_skin_normal_restore_bound'];calls=[]
 def engine_run(library,output,log,api):
  assert library['refresh_skin_normal_restore']['character_id']=='CFD40_WF_003'
  calls.append(library);folder=Path(output);folder.mkdir()
  saved=folder/'CANDIDATE_LM002_four_skin_normals_restored.ccProject';saved.write_bytes(b'unit female candidate, legacy engine basename only')
  rp=folder/'skin_normal_restore_report.json';sp=folder/'validation_result.json'
  full=dict(success=True,material_restoration_verified=True,character_id='CFD40_WF_003',saved_project=pin(saved))
  api.write_json(full,rp);api.write_json(dict(success=True),sp)
  return dict(success=True,status='unit_shared_engine_success',source_unchanged=True,restored_source=True,saved_project=pin(saved),report_path=str(rp),summary_path=str(sp))
 fake=types.SimpleNamespace(run=engine_run,validate_inputs=None)
 monkeypatch.setattr(bound,'private_engine',lambda:fake)
 api=types.SimpleNamespace(read_json=read,write_json=lambda v,p:Path(p).write_text(json.dumps(v),encoding='utf-8'),sha256_file=sha,bodyfit_freeze_file_record=pin)
 result=bound.run({'refresh_skin_normal_restore_bound':c},str(tmp_path/'output'),lambda s:None,api)
 assert len(calls)==1 and fake.validate_inputs is bound.validate_bound
 full=read(result['report_path']);raw=read(full['engine_full_report']['path'])
 assert result['saved_project']['path'].endswith('CANDIDATE_WF003_four_skin_normals_restored.ccProject')
 assert result['saved_project']['sha256']==raw['saved_project']['sha256']
 assert Path(raw['saved_project']['path']).exists()and sha(raw['saved_project']['path'])==raw['saved_project']['sha256']
 assert full['engine_summary']['path']!=result['summary_path']and not result['accepted_final']
