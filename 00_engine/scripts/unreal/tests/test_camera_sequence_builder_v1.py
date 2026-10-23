import copy
import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('builder',Path(__file__).parents[1]/'ue_camera_sequence_builder_v1.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def shot():
    rows=[{'t':i/30,'position':[1,2,3],'rotation_pitch_yaw_roll':[10,179+i*.1 if i<10 else -180+(i-10)*.1,5],'horizontal_fov_degrees':35} for i in range(301)]
    return {'status':'geometry_pass','fps':30,'duration_seconds':10,'frame_count':300,'frames':rows[:-1],'endpoint_validation_frame':rows[-1]}

def test_rotation_channel_order_and_unwrap():
    result=b.key_rows(shot())
    assert result[0]['transform']==[1,2,3,5,10,179,1,1,1]
    assert result[10]['transform'][5]==pytest.approx(180)
    assert all(abs(y['transform'][5]-x['transform'][5])<1 for x,y in zip(result,result[1:]))

def test_endpoint_key_not_an_extra_display_frame():
    rows=b.key_rows(shot())
    assert len(rows)==301 and rows[-1]['frame']==300

def test_input_not_modified():
    source=shot();saved=copy.deepcopy(source);b.key_rows(source);assert source==saved

@pytest.mark.parametrize('mutator',[lambda s:s.update(status='unsuitable'),lambda s:s.update(fps=24),lambda s:s.update(duration_seconds=12),lambda s:s['frames'][0].update(t=.1),lambda s:s['frames'][5]['position'].__setitem__(1,float('nan')),lambda s:s['frames'][4].update(horizontal_fov_degrees=180)])
def test_invalid_camera_contract_rejected(mutator):
    source=shot();mutator(source)
    with pytest.raises(ValueError):b.key_rows(source)

def test_owned_new_paths_only():
    class Library:
        @staticmethod
        def does_asset_exist(path): return path.endswith('/Existing')
    class Unreal: EditorAssetLibrary=Library
    assert b.validate_new_path(Unreal,b.ALLOWED_PREFIX+'Sequences/Test')[1]=='Test'
    for path in ['/Game/Other/Test',b.ALLOWED_PREFIX+'../Test',b.ALLOWED_PREFIX+'Existing',b.ALLOWED_PREFIX+'Test.Test']:
        with pytest.raises(ValueError):b.validate_new_path(Unreal,path)

def test_unwrap_holds_orientation_equivalence():
    assert b.unwrap_degrees([170,179,-179,-170])==pytest.approx([170,179,181,190])
