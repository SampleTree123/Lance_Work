"""Normal-only input provenance, paired SDK reads, strict other channels and rollback."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_probe_refresh_skin_normal_restore_v1 as probe
import cc_repair_headshot_support_materials_v1 as geometry
import cc_refresh_material_pixels_v1 as original
import cc_refresh_eyelash_probe_v2 as roots
import cc_refresh_selected_lash_pixels_v1 as scope
import cc_probe_refresh_skin_material_readonly_v1 as channels
import cc_skin_detail_experiment_v1 as exporter
import cc_skingen_controls_v1 as ui

ROOT=Path(__file__).resolve().parents[4]
LIB=ROOT/'00_engine/scripts/character_creator/runtime_staging/character_refresh_20261018_v1/LM002_skin_normal_restore_library_v1.json'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def record(p):return dict(path=str(Path(p).resolve()),sha256=digest(p))
class ActualImage:
    def __init__(self,path):self.image=Image.open(path)
    def isNull(self):return False
    def width(self):return self.image.width
    def height(self):return self.image.height


def test_actual_same_case_four_maps_and_proven_Normal_signature_validate_without_sdk():
    config=read(LIB)['refresh_skin_normal_restore']
    api=types.SimpleNamespace(sha256_file=digest,read_json=read,QtGui=types.SimpleNamespace(QImage=ActualImage))
    assert set(probe.validate_inputs(config,api))==probe.SKINS
    wrong=copy.deepcopy(config);wrong['skin_normal_maps']['Std_Skin_Head']=config['skin_normal_maps']['Std_Skin_Body']
    with pytest.raises(ValueError,match='exact own after_skin'):probe.validate_inputs(wrong,api)
    wrong=copy.deepcopy(config);wrong['selected_skin']['sha256']='0'*64
    with pytest.raises(ValueError,match='lineage'):probe.validate_inputs(wrong,api)


def row(material,mesh='CC_Base_Body',owner='avatar'):
    return dict(owner=owner,mesh=mesh,material=material,properties={},shader_parameters={},component_source='unit',textures={},missing_textures={c:dict(reason='sdk_empty_image')for c,_ in channels.CHANNELS})
def tex(path='fixture',sha='same'):
    return dict(path=path,sha256=sha,width=2048,height=2048,file_decoded=True)


def test_only_four_skin_normal_bump_pair_may_change_other_Normal_and_shininess_strict(monkeypatch):
    before=dict(pixel_capture_complete=True,materials=[row('Std_Skin_Head'),row('Eye','CC_Base_Eye'),row('Tongue','CC_Base_Tongue')])
    after=copy.deepcopy(before);after['materials'][0]['textures']['bump']=tex()
    assert probe.pixel_compare(before,after,None,True)['passed']
    assert not probe.pixel_compare(before,after,None)['passed']
    for material_index,channel in [(1,'normal'),(2,'bump'),(0,'shininess'),(0,'diffuse')]:
        wrong=copy.deepcopy(after);wrong['materials'][material_index]['textures'][channel]=tex()
        assert not probe.pixel_compare(before,wrong,None,True)['passed']
    assert probe.pixel_compare(after,copy.deepcopy(after),None)['passed']


def test_proven_Normal_write_Bump_readback_is_honest_not_fabricated_direct_Normal(monkeypatch):
    monkeypatch.setattr(geometry,'compare_png_images',lambda *args:dict(rgba_pixels_equal=True))
    rows=[row(m)for m in probe.SKINS]
    for r in rows:r['textures']['bump']=tex()
    result=probe.verify_restored_maps(dict(materials=rows),{m:tex()for m in probe.SKINS},None)
    assert all(r['readbacks']['bump']['available']and not r['readbacks']['normal']['available']for r in result.values())
    rows[0]['textures'].clear()
    with pytest.raises(ValueError,match='no actual decoded'):probe.verify_restored_maps(dict(materials=rows),{m:tex()for m in probe.SKINS},None)


@pytest.mark.parametrize('change_other',[False,True])
def test_exact_four_Normal_writes_save_reload_and_always_restore_source(tmp_path,monkeypatch,change_other):
    source=tmp_path/'source.ccProject';source.write_bytes(b'unit source')
    maps={}
    for i,m in enumerate(sorted(probe.SKINS)):
        path=tmp_path/(m+'.png');path.write_bytes(('unit normal_'+str(i)).encode());maps[m]=dict(record(path),width=2048,height=2048)
    config=dict(character_id='CFD40_LM_002',source_project=record(source),geometry_snapshot=str(tmp_path/'geometry.json'),baseline_pixel_materials=str(tmp_path/'baseline.json'))
    write=lambda value,p:Path(p).write_text(json.dumps(value),encoding='utf-8')
    write(dict(geometry={}),config['geometry_snapshot']);write({},config['baseline_pixel_materials'])
    config['geometry_snapshot']=record(config['geometry_snapshot']);config['baseline_pixel_materials']=record(config['baseline_pixel_materials'])
    monkeypatch.setattr(probe,'validate_inputs',lambda *args:maps);monkeypatch.setattr(roots,'RUN_ROOT',str(tmp_path))
    state=dict(maps={},changed=False);saved={};calls=[]
    class Component:
        def LoadImageToTexture(self,mesh,material,constant,path):
            assert mesh=='CC_Base_Body'and constant==23 and material in probe.SKINS
            calls.append((mesh,material,constant,path));state['maps'][material]=maps[material]
            if change_other:state['changed']=True
            return True
    component=Component();avatar=types.SimpleNamespace(GetMaterialComponent=lambda:component,GetSubdivMeshLevel=lambda:0)
    def save(path):Path(path).write_bytes(b'unit saved');saved[str(path)]=copy.deepcopy(state);return True
    def load(path,label):
        if Path(path).name=='immutable_assembled_source.ccProject':state.update(maps={},changed=False)
        else:state.update(copy.deepcopy(saved[str(path)]))
        return {},{}
    R=types.SimpleNamespace(EMaterialTextureChannel_Normal=23,RScene=types.SimpleNamespace(GetAvatars=lambda:[avatar],SelectObject=lambda a:None),RFileIO=types.SimpleNamespace(SaveProject=save))
    for _,enum in channels.CHANNELS:
        if not hasattr(R,enum):setattr(R,enum,object())
    class DummyImage:
        def isNull(self):return False
        def width(self):return 2048
        def height(self):return 2048
    api=types.SimpleNamespace(RLPy=R,sha256_file=digest,read_json=read,write_json=write,bodyfit_freeze_file_record=record,checked=lambda label,status:status,
        load_file_with_optional_undo_warning=load,_transform_data=lambda value:{},capture_eye_integrity_state=lambda a:{},capture_eye_part_morph_weights=lambda a:[],compare_neutral_eye_states=lambda *a,**kw:dict(matches=True),
        render_preview=lambda path:Path(path).write_bytes(b'unit image'),QtGui=types.SimpleNamespace(QImage=lambda path:DummyImage()),QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(allWidgets=lambda:[])),MATERIAL_TEXTURE_CHANNELS=list(channels.CHANNELS))
    monkeypatch.setattr(geometry,'capture_geometry',lambda *a,**kw:{})
    monkeypatch.setattr(geometry,'compare_geometry',lambda *a:dict(passed=True))
    monkeypatch.setattr(geometry,'compare_png_images',lambda *a:dict(rgba_pixels_equal=True))
    monkeypatch.setattr(original,'compare_pixels',lambda *a:dict(passed=True))
    body=lambda *a,**kw:dict(local=[[0.,0.,0.]]*14164,world=[[0.,0.,0.]]*14164,working_subdivision_level=0,scene_explicitly_settled=False)
    monkeypatch.setitem(sys.modules,'cc_capture_assembly_geometry_v1',types.SimpleNamespace(capture_body_snapshot=body))
    widget=types.SimpleNamespace(text=lambda:'Activate Editor',isChecked=lambda:False)
    monkeypatch.setattr(ui,'unique_widget',lambda *a:widget);monkeypatch.setattr(ui,'widget_record',lambda w:{})
    base=tmp_path/'diffuse.png';base.write_bytes(b'unit diffuse')
    def capture(a,destination,scoped):
        Path(destination).mkdir();rows=[row(m)for m in probe.SKINS]+[row('Std_Eyelash')]+[row(m,m)for m in original.SUPPORT_MESHES]+[row(m,m)for m in scope.NEW_MESHES]
        for r in rows:
            r['textures']['diffuse']=dict(record(base),width=2048,height=2048)
            if r['material']in state['maps']:r['textures']['bump']=state['maps'][r['material']]
            if state['changed']and r['mesh']=='CC_Base_Tongue':r['textures']['normal']=tex()
        result=dict(materials=rows,observation_errors=[]);write(result,Path(destination)/'materials.json');return result
    monkeypatch.setattr(exporter,'capture_materials',capture)
    result=probe.run({'refresh_skin_normal_restore':config},str(tmp_path/'probe'),lambda s:None,api)
    assert len(calls)==4 and {x[1]for x in calls}==probe.SKINS
    assert result['source_unchanged']and result['restored_source']and state['maps']=={}and not state['changed']
    assert result['success']is(not change_other)and not result['accepted_final']and not result['complete_export_verified']
    if change_other:assert 'Protected material pixels changed'in result['error']['message']
