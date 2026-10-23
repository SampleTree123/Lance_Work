"""Real-model pipeline simulation: zero new responses, two restores, no tolerance waiver."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_probe_delicate_support_restore_v4 as probe
import cc_refresh_prelash_source_chain_v1 as lineage
import cc_refresh_selected_lash_pixels_v1 as selected_pixels
import cc_skingen_controls_v1 as ui
import cc_support_evaluated_inverse_v1 as evaluated
import cc_refresh_eyelash_probe_v2 as lash
import cc_probe_eye_support_identity_v5 as identity
import cc_eye_support_inverse_affine_v1 as eye_inverse
import cc_eye_support_obj_semantics_v1 as semantics
import cc_refresh_eye_support_diagnostic_v1 as queries
import cc_repair_headshot_support_materials_v1 as capture
import cc_compile_character_manifest as compiler


def test_actual_v1_original6_export_is_valid_template_and_not_newlash_uv_proof(tmp_path):
    root=Path(__file__).resolve().parents[4]
    run=root/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/delicate_WF003_support_restore_v1'
    if not run.exists():pytest.skip('Actual v1 export evidence unavailable')
    original=probe.native_group_layouts(run/'original_native_whole_avatar.obj')
    applied=probe.native_group_layouts(run/'applied_native_whole_avatar.obj')
    assert probe.native_template_layouts(applied,original)==original
    sdk=json.loads((run/'applied_rendered_snapshot.json').read_text())
    assert {m['name']for m in sdk['other_meshes']['meshes']} >= probe.NEW_NAMES
    assert not set(applied)&probe.NEW_NAMES
    for name,row in original.items():
        path=tmp_path/(name+'.obj')
        identity.extract_native_group(str(run/'applied_native_whole_avatar.obj'),str(path),name,row['vertex_count'],row['faces'])
        assert probe.uv_attributes_equal(run/('original_native_'+name+'.obj'),path)['passed']
    bad=dict(applied);bad['Unexpected_Mesh']=bad['CC_Base_Eye']
    with pytest.raises(ValueError):probe.native_template_layouts(bad,original)


def test_uv_protection_does_not_relax_skin_or_support_attributes(tmp_path):
    text='g A\nv 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nvn 0 0 1\ns 8\nf 1/1/1 2/2/1 3/3/1\n'
    a=tmp_path/'a.obj';b=tmp_path/'b.obj';a.write_text(text);b.write_text(text.replace('vt 0 0','vt 0.000001 0'))
    assert not probe.uv_attributes_equal(a,b)['passed']


@pytest.mark.parametrize('failure',[None,'nonlash','tearline_nonlinear'])
def test_zero_response_two_restores_or_rollback_without_retry(tmp_path,monkeypatch,failure):
    root=tmp_path/'refresh';root.mkdir();source=root/'source.ccProject';source.write_bytes(b'original')
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rec=lambda p:dict(path=str(p),sha256=sha(p),bytes=Path(p).stat().st_size)
    for k in('RUN_ROOT','CREATION_ROOT','STAGE_ROOT'):monkeypatch.setattr(lash,k,str(root))
    registry=root/'registry.json';registry.write_text('{}');resource=root/'native.obj';resource.write_text('fixture')
    asset=root/'Delicate.ccAvatarPreset';asset.write_bytes(b'asset')
    monkeypatch.setattr(lash,'REGISTRY',str(registry));monkeypatch.setattr(lash,'RESOURCE',str(resource));monkeypatch.setattr(lash,'DELICATE_SHA',sha(asset))
    monkeypatch.setattr(lash,'validate_addition_evidence',lambda *a:{'fixture':True});monkeypatch.setattr(lash,'native_partition',lambda *a:{'native_lash_count':704})
    selected=dict(asset_id=lash.DELICATE_ID,path=str(asset),sha256=sha(asset),application_mode='character_preset_replace',slot='eyelashes')
    monkeypatch.setattr(compiler,'facial_pool',lambda *a:dict({str(i):{}for i in range(8)},**{lash.DELICATE_ID:selected}))
    coords=lambda n:[[float(i)/n,math.sin(i*.3),math.cos(i*.7)]for i in range(n)]
    originals={name:coords(s['vertex_count'])for name,s in probe.SELECTORS.items()}
    state={'applied':False,'low':copy.deepcopy(originals),'high':copy.deepcopy(originals)};calls=[]
    def reset():state.update(applied=False,low=copy.deepcopy(originals),high=copy.deepcopy(originals))
    A=[[.98,0.,0.],[0.,.98,0.],[0.,0.,.98]];b=[.03,-.01,.02]
    def meshrow(owner,name,count,vertices=None,face_count=1,digest='same'):
        return dict(owner=owner,name=name,vertex_count=count,face_count=face_count,faces_sha256=digest,
            vertices=vertices if vertices is not None else [[0.,0.,0.]]*count)
    def body():
        v=[[0.,0.,0.]for _ in range(lash.BODY_COUNT)]
        if state['applied']:
            for i in lash.LASH:v[i][0]=.3
            if failure=='nonlash':v[7000][0]=.001
        return dict(local=v,world=copy.deepcopy(v),working_subdivision_level=0,scene_explicitly_settled=False)
    T=dict(translation=dict(x=0.,y=0.,z=0.),rotation=dict(x=0.,y=0.,z=0.,w=1.))
    def geometry(a,api):
        rows=[meshrow('avatar','CC_Base_Body',lash.BODY_COUNT,body()['local']),meshrow('avatar','CC_Base_Tongue',309),meshrow('avatar','CC_Base_Tongue',1209),
            meshrow('avatar/1:CC_Base_Eye','CC_Base_Eye',648),meshrow('avatar/1:CC_Base_Eye','CC_Base_Eye',2568),
            meshrow('avatar/2:CC_Base_Teeth','CC_Base_Teeth',2642),meshrow('avatar/2:CC_Base_Teeth','CC_Base_Teeth',10092)]
        for name,count,high in [('CC_Base_EyeOcclusion',182,650),('CC_Base_TearLine',190,652)]:
            owner='avatar/'+probe.SELECTORS[name]['part_type']+':'+name
            rows.extend([meshrow(owner,name,count,copy.deepcopy(state['low'][name])),meshrow(owner,name,high,[state['high'][name][i%count][:]for i in range(high)])])
        parts=[dict(owner='avatar',type=t,name=n)for t,n in [('1','CC_Base_Eye'),('2','CC_Base_Teeth'),('5','CC_Base_EyeOcclusion'),('6','CC_Base_TearLine')]]
        if state['applied']:
            for key in lash.DELICATE_ADDITIONS:
                rows.append(meshrow(key[0],key[1],key[2],face_count=key[3],digest=key[4]));parts.append(dict(owner='avatar',type='9',name=key[1]))
        rows.sort(key=lambda x:(x['owner'],x['name'],x['vertex_count'],x['face_count']));parts.sort(key=lambda x:(x['owner'],x['type'],x['name']))
        owners=sorted({'avatar'}|{r['owner']for r in rows});trans=[dict(owner=o,space=s,value=copy.deepcopy(T))for o in owners for s in('local','world')]
        return dict(meshes=rows,parts=parts,owner_transforms=trans,owner_transform_errors=[],working_subdivision=0,expression_count=379)
    monkeypatch.setattr(capture,'capture_geometry',geometry);monkeypatch.setattr(queries,'query_support_levels',lambda a:dict(consistent=True))
    monkeypatch.setitem(sys.modules,'cc_capture_assembly_geometry_v1',types.SimpleNamespace(capture_body_snapshot=lambda *a,**kw:body()))
    class Mesh:
        def __init__(self,name):self.name=name
        def GetName(self):return self.name
        def GetVerticesCount(self):return lash.BODY_COUNT if self.name=='CC_Base_Body'else probe.SELECTORS[self.name]['vertex_count']
        def GetFacesCount(self):return 1
        def GetFace(self,i):return [0,1,2]
        def ReplaceMesh(self,path,option,uv):
            calls.append(self.name);assert uv is False
            W=[list(map(float,line.split()[1:]))for line in Path(path).read_text().splitlines()if line.startswith('v ')]
            P=[[.98*x+b[0],.98*y+b[1],.98*z+b[2]]for x,y,z in W]
            if self.name=='CC_Base_TearLine'and failure=='tearline_nonlinear':P=[[x+.1*x*x,y,z]for x,y,z in P]
            state['low'][self.name]=P;return True
    avatar=types.SimpleNamespace(GetMeshes=lambda all:[Mesh('CC_Base_Body')],GetSubdivMeshLevel=lambda:0)
    monkeypatch.setattr(identity,'resolve_target',lambda a,s:(None,Mesh(s['mesh_name']),[[0,1,2]]))
    monkeypatch.setattr(identity,'target_world',lambda a,s:dict(world=copy.deepcopy(state['low'][s['mesh_name']]),faces=[[0,1,2]],working_subdivision_level=0))
    def layouts(path):
        counts={'CC_Base_Body':lash.BODY_COUNT,'CC_Base_Tongue':309,'CC_Base_Eye':648,'CC_Base_Teeth':2642,'CC_Base_EyeOcclusion':182,'CC_Base_TearLine':190}
        return {name:dict(vertex_count=count,faces=[[0,1,2]])for name,count in counts.items()}
    monkeypatch.setattr(probe,'native_group_layouts',layouts)
    def extract(whole,path,name,count,faces):Path(path).write_text('fixture');return {}
    def parsed(path,name,count,faces):
        points=state['low'].get(name,[[0.,0.,0.]]*count)
        return dict(vertices=copy.deepcopy(points),lines=['v {} {} {}\n'.format(*v)for v in points],uv_normal_material_corner_sha256='same')
    monkeypatch.setattr(identity,'extract_native_group',extract);monkeypatch.setattr(identity,'parse_native_obj',parsed)
    monkeypatch.setattr(probe,'uv_attributes_equal',lambda *a:dict(passed=True));monkeypatch.setattr(semantics,'compare_native_semantics',lambda *a:dict(passed=True))
    model=dict(source_project=rec(source),target=eye_inverse.TARGET,source_files=dict(report=rec(source)),fitter=rec(Path(eye_inverse.__file__)),
        linear_row_vector_3x3=A,translation_cm=b,source_world_cm=originals['CC_Base_EyeOcclusion'],desired_local_cm=originals['CC_Base_EyeOcclusion'],
        observed_v3_local_cm=eye_inverse.map_rows(originals['CC_Base_EyeOcclusion'],A,b),submitted_compensated_input_cm=[[(v[j]-b[j])/.98 for j in range(3)]for v in originals['CC_Base_EyeOcclusion']],
        faces_sha256='same',metrics=dict(rank=4,normalized_design_condition=2.,linear_condition=1.,determinant=.98**3,fit_max_mm=0.,held_out=[dict(maximum_local_error_mm=0.)]),final_protection_limit_mm=.002,origin_limit_mm=.0002)
    mp=root/'model.json';mp.write_text(json.dumps(model));vp=root/'successful_identity.json';vp.write_text(json.dumps(dict(success=True,restored_source=True,source_unchanged=True,source_project=rec(source),inverse_affine_model=rec(mp))))
    def load(path,label):
        if Path(path).name.startswith('immutable'):reset()
        return {},{}
    def apply(*args,**kwargs):
        state['applied']=True
        for name in originals:
            state['low'][name]=[[x+.01,y+.02,z-.01]for x,y,z in originals[name]]
        state['high']=copy.deepcopy(state['low'])
        return avatar,{'steps':[dict(character_preset_verified=True,eye_geometry_preserved=True,eye_support_preserved=True)]}
    def render(path):state['high']=copy.deepcopy(state['low']);Path(path).write_bytes(b'image')
    def save(path):Path(path).write_bytes(b'project');return True
    def export(a,path,flags):Path(path).write_text('whole');return True
    R=types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda:[avatar],SelectObject=lambda a:None),RFileIO=types.SimpleNamespace(SaveProject=save,ExportObjFile=export),EExport3DFileOption_AllClothes=1,EExport3DFileOption_FullBodyPart=2,EReplaceMeshOption_ZUp=0)
    api=types.SimpleNamespace(RLPy=R,sha256_file=sha,bodyfit_freeze_file_record=rec,read_json=lambda p:json.loads(Path(p).read_text()),write_json=lambda v,p:Path(p).write_text(json.dumps(v)),now=lambda:'fixture',
        checked=lambda label,status:status,load_file_with_optional_undo_warning=load,_transform_data=lambda x:{},capture_eye_integrity_state=lambda a:{},capture_eye_part_morph_weights=lambda a:[],compare_neutral_eye_states=lambda *a,**kw:dict(matches=True),apply_appearance_assets=apply,render_preview=render)
    em=dict(source_project=rec(source),verification_implementation=rec(Path(evaluated.__file__)),source_files=dict(v2_report=rec(source)),supports={name:dict(count=len(values),applied_local_cm=[[x+.01,y+.02,z-.01]for x,y,z in values],desired_pre_evaluation_raw_local_cm=values,submitted_corrected_input_cm=[[(v[j]-b[j])/.98 for j in range(3)]for v in values])for name,values in originals.items()})
    ep=root/'evaluated_model.json';ep.write_text(json.dumps(em))
    monkeypatch.setattr(evaluated,'verify_model',lambda m:{'fixture':True});monkeypatch.setattr(evaluated,'verify_pinned_evidence',lambda *a:{'fixture':True})
    config=dict(operation='apply_delicate_to_stable_prelash_fixed_inverse_two_restores',save_current_scene_backup=True,maximum_response_calls=0,maximum_restores_per_support=1,native_template_scope='original6_new_lash_uv_pending_complete_fbx',source_project=rec(source),registry=rec(registry),native_lash_resource=rec(resource),eyelash_asset_id=lash.DELICATE_ID,validated_eye_occlusion_identity=rec(vp),eye_occlusion_inverse_model=rec(mp),evaluated_support_model=rec(ep),original_geometry_anchor=rec(source),strict_material_pixels=True,character_id='CFD40_WF_003')
    sourcepix={'pixel_capture_complete':True,'materials':[]}
    chain=dict(anchor=rec(source),body=body(),native=geometry(avatar,None),pixels=sourcepix)
    monkeypatch.setattr(lineage,'validate',lambda *a:chain)
    monkeypatch.setattr(lineage,'check_loaded',lambda *a:dict(passed=True))
    monkeypatch.setattr(lineage,'check_anchor_eye_origin',lambda *a:dict(passed=True))
    widget=types.SimpleNamespace(text=lambda:'Activate Editor',isChecked=lambda:False)
    monkeypatch.setattr(ui,'unique_widget',lambda *a:widget);monkeypatch.setattr(ui,'widget_record',lambda w:dict(text=w.text(),isChecked=w.isChecked()))
    api.QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(allWidgets=lambda:[]))
    def capture_pixels(a,dest,label,api,require_new):
        target=Path(dest)/('pixels_'+label);target.mkdir();(target/'materials.json').write_text(json.dumps(sourcepix));return sourcepix
    monkeypatch.setattr(selected_pixels,'capture',capture_pixels)
    monkeypatch.setattr(selected_pixels,'compare_all',lambda *a:dict(passed=True))
    monkeypatch.setattr(selected_pixels,'compare_nonlash',lambda *a:dict(passed=True))
    result=probe.run({'refresh_delicate_support_restore':config},str(root/'probe'),lambda s:None,api)
    report=json.loads(Path(result['report_path']).read_text())
    assert result['restored_source']and result['source_unchanged']and not state['applied']
    assert result['success']is(failure is None)
    assert len(calls)==(0 if failure=='nonlash'else 2)
    assert report['additional_calibration_calls']==0 and report['maximum_actual_support_replacements']==2
    assert result['new_lash_UV_verified']is False and result['assembly_accepted']is False
    if failure is None:
        assert all(s['original_protection_passed']for s in report['steps']if not s['pending_restoration_supports'])
        assert report['saved_project']and report['normal_semantic_checks'][-1]['passed']
        assert report['steps'][0]['original_protection_passed']is False
        assert report['lash_upper_bound_registered']is False and report['visual_acceptance']=='pending'
        assert result['material_pixels_verified']is True and result['accepted_final']is False
        assert len(report['eyelash_parts_evidence']['added_parts'])==2
        parts_capture=json.loads(Path(report['eyelash_parts_evidence']['capture']['path']).read_text())
        assert parts_capture['native_snapshot']['sha256']and parts_capture['character_id']=='CFD40_WF_003'
