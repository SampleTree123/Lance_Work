import copy
import json
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_refresh_selected_lash_pixels_v1 as pixels
import cc_skin_detail_experiment_v1 as exporter


def row(mesh,material='M',owner='avatar',sha='same'):
    return dict(owner=owner,mesh=mesh,material=material,properties={},shader_parameters={},component_source='fixture',
        textures={'diffuse':dict(path='fixture',sha256=sha,width=2,height=2,file_decoded=True)},missing_textures={})


def test_exact_new_mesh_scope_preserves_original_and_rejects_name_lookalikes():
    component=pixels.Component(types.SimpleNamespace(GetMaterialNames=lambda m:['Actual_Material']))
    assert component.GetMaterialNames('Lash_Low_Bushy')==['Actual_Material']
    assert component.GetMaterialNames('CC_Base_Eye')==['Actual_Material']
    assert component.GetMaterialNames('Lash_Low_Bushy_extra')==[]


def test_only_selected_lash_can_change_and_final_all_pixels_are_strict(monkeypatch):
    before=dict(pixel_capture_complete=True,materials=[row('CC_Base_Body','Std_Skin_Head'),row('CC_Base_Body','Std_Eyelash'),row('CC_Base_Eye')])
    after=copy.deepcopy(before);after['materials'][1]['textures']['diffuse']['sha256']='selected_lash'
    after['materials'] += [row(n,owner='avatar/GetAvatarParts:'+n)for n in pixels.NEW_MESHES]
    api=types.SimpleNamespace()
    assert pixels.compare_nonlash(before,after,api)['passed']
    assert pixels.compare_all(after,copy.deepcopy(after),api)['passed']
    import cc_repair_headshot_support_materials_v1 as images
    monkeypatch.setattr(images,'compare_png_images',lambda *a:dict(rgba_pixels_equal=False))
    wrong=copy.deepcopy(after);wrong['materials'][0]['textures']['diffuse']['sha256']='skin_changed'
    assert not pixels.compare_nonlash(before,wrong,api)['passed']
    wrong=copy.deepcopy(after);wrong['materials'][-1]['textures']['diffuse']['sha256']='new_lash_changed_on_reload'
    assert not pixels.compare_all(after,wrong,api)['passed']
    missing=copy.deepcopy(after);missing['materials']=[r for r in missing['materials']if r['mesh']!='CC_Base_Eye']
    assert not pixels.compare_nonlash(before,missing,api)['passed']


@pytest.mark.parametrize('omit_new',[False,True])
def test_capture_requires_actual_decoded_pixels_for_both_new_meshes(tmp_path,monkeypatch,omit_new):
    def capture(a,dest,api):
        Path(dest).mkdir()
        rows=[row('CC_Base_Body',m)for m in pixels.original.SKINS|{'Std_Eyelash'}]
        rows += [row(m)for m in pixels.original.EYE_SUPPORT_MESHES|{'CC_Base_Tongue'}]
        rows += [row(m)for m in sorted(pixels.NEW_MESHES)[:1 if omit_new else 2]]
        for i,r in enumerate(rows):
            path=Path(dest)/(str(i)+'.png');path.write_bytes(b'actual_saved_image_'+str(i).encode())
            r['textures']['diffuse'].update(path=str(path),sha256='sha'+str(i))
        result=dict(materials=rows,observation_errors=[])
        (Path(dest)/'materials.json').write_text(json.dumps(result));return result
    monkeypatch.setattr(exporter,'capture_materials',capture)
    monkeypatch.setattr(pixels.original,'object_record',lambda *a:None)
    image=types.SimpleNamespace(isNull=lambda:False,width=lambda:2,height=lambda:2)
    api=types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[(n,n)for n in pixels.original.CHANNELS],QtGui=types.SimpleNamespace(QImage=lambda p:image),
        sha256_file=lambda p:'fixture',write_json=lambda v,p:Path(p).write_text(json.dumps(v)))
    result=pixels.capture(None,str(tmp_path),'actual',api,True)
    assert result['pixel_capture_complete']is(not omit_new)
    assert result['material_writes']is False
