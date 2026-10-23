"""Focused safety, exact morph differences and import-option contract tests."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

PATH = Path(__file__).resolve().parents[1]/'ue_import_complete_character_skeleton_pilot_v1.py'
SPEC = importlib.util.spec_from_file_location('complete_character_import',PATH)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)


def test_scope_does_not_allow_production_assets_or_prefix_collision():
    SUBJECT.guard(SUBJECT.UE_ROOT+'/Male/Mesh.Mesh')
    for bad in ['/Game/Other/Mesh',SUBJECT.UE_ROOT+'Extra/Mesh',SUBJECT.UE_ROOT]:
        with pytest.raises(ValueError):
            SUBJECT.guard(bad)


def test_witness_directory_defaults_unchanged_and_traversal_rejected_before_io(monkeypatch):
    assert SUBJECT.WITNESS_SUBDIR == 'MaterialWitness'
    assert SUBJECT.WITNESS_AUTOMATED is True
    for bad in ('../Old', '/Game/Other', 'Sub/Other', 'Sub\\Other', '', None):
        monkeypatch.setattr(SUBJECT, 'WITNESS_SUBDIR', bad)
        with pytest.raises(ValueError, match='safe single asset directory'):
            SUBJECT.main('nonexistent-manifest.json')


def test_split_directory_rejects_traversal_before_io(monkeypatch):
    assert SUBJECT.SPLIT_SUBDIR == 'Meshes'
    for bad in ('../Old', '/Game/Other', 'Sub/Other', 'Sub\\Other', '', None):
        monkeypatch.setattr(SUBJECT, 'SPLIT_SUBDIR', bad)
        with pytest.raises(ValueError, match='safe single asset directory'):
            SUBJECT.main('nonexistent-manifest.json')


def test_pending_recovery_routes_only_split_to_new_directory_and_completed_cannot_move(tmp_path, monkeypatch):
    import hashlib
    import json
    case = {'character_id':'BM001','sex':'male','expected_meshes':[]}
    manifest = tmp_path/'manifest.json'
    SUBJECT.write(manifest, {'schema_version':1,'cases':[case]})
    signature = hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
    state = tmp_path/'BM001/import_state.json'
    SUBJECT.write(state, {'input_fingerprint':signature,'status':'pending'})
    monkeypatch.setattr(SUBJECT, 'REPORT_ROOT', tmp_path)
    monkeypatch.setattr(SUBJECT, 'REQUIRED_CASE_SEXES', ('male',))
    monkeypatch.setattr(SUBJECT, 'SPLIT_SUBDIR', 'MeshesRecovery20261007')
    monkeypatch.setattr(SUBJECT, 'unreal', SimpleNamespace(SkeletalMesh=type('SkeletalMesh',(),{}),
        SystemLibrary=SimpleNamespace(get_engine_version=lambda:'test')))
    monkeypatch.setattr(SUBJECT, 'assets', lambda root:[])
    monkeypatch.setattr(SUBJECT, 'source_record', lambda *args:{'path':'source','sha256':'locked'})
    calls = []
    monkeypatch.setattr(SUBJECT, 'import_witness', lambda fbx,root:calls.append(('witness',root)))
    monkeypatch.setattr(SUBJECT, 'configure_exact_source_normal_textures', lambda *args:None)
    def split(fbx,root):
        calls.append(('split',root))
        raise RuntimeError('bounded test stop before import')
    monkeypatch.setattr(SUBJECT, 'import_split', split)
    with pytest.raises(RuntimeError, match='bounded test stop'):
        SUBJECT.main(manifest)
    assert calls == [('witness',SUBJECT.UE_ROOT+'/BM001/MaterialWitness'),
                     ('split',SUBJECT.UE_ROOT+'/BM001/MeshesRecovery20261007')]
    assert SUBJECT.read(state)['status'] == 'pending'
    assert SUBJECT.read(tmp_path/'BM001/import_audit.json')['split_root'].endswith('/MeshesRecovery20261007')
    SUBJECT.write(state, {'input_fingerprint':signature,'status':'audited'})
    calls.clear()
    with pytest.raises(ValueError,match='Completed import split directory'):
        SUBJECT.main(manifest)
    assert not calls


@pytest.mark.parametrize('witness_material', (None, 'OtherMaterial', 'Std_Tongue_Pbr'))
def test_witness_materials_are_required_before_split_import(tmp_path, monkeypatch, witness_material):
    import hashlib
    import json
    case = {'character_id':'LM002','sex':'male','expected_meshes':[
        {'source_name':'CC_Base_Tongue','expected_materials':['Std_Tongue_Pbr']}]}
    manifest = tmp_path/'manifest.json'
    SUBJECT.write(manifest, {'schema_version':1,'cases':[case]})
    state = tmp_path/'LM002/import_state.json'
    signature = hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
    SUBJECT.write(state, {'input_fingerprint':signature,'status':'pending'})
    monkeypatch.setattr(SUBJECT, 'REPORT_ROOT', tmp_path)
    monkeypatch.setattr(SUBJECT, 'REQUIRED_CASE_SEXES', ('male',))
    class SkeletalMesh(Properties):
        pass
    material = SimpleNamespace(get_path_name=lambda:'/Game/Witness/TongueHQ.TongueHQ')
    witnesses = [] if witness_material is None else [SkeletalMesh(materials=[Properties(
        material_interface=material,material_slot_name=witness_material,
        imported_material_slot_name=witness_material)])]
    monkeypatch.setattr(SUBJECT, 'unreal', SimpleNamespace(SkeletalMesh=SkeletalMesh,
        SystemLibrary=SimpleNamespace(get_engine_version=lambda:'test')))
    monkeypatch.setattr(SUBJECT, 'source_record', lambda *args:{'path':'source','sha256':'locked'})
    monkeypatch.setattr(SUBJECT, 'assets', lambda root:witnesses)
    monkeypatch.setattr(SUBJECT, 'import_witness', lambda *args:{'cancelled':witness_material is None})
    monkeypatch.setattr(SUBJECT, 'configure_exact_source_normal_textures', lambda *args:None)
    calls = []
    def split(fbx,root):
        calls.append(root)
        raise RuntimeError('normal split path reached')
    monkeypatch.setattr(SUBJECT, 'import_split', split)
    valid = witness_material == 'Std_Tongue_Pbr'
    message = 'normal split path reached' if valid else 'No unique exact Auto Setup material for Std_Tongue_Pbr'
    with pytest.raises(RuntimeError,match=message):
        SUBJECT.main(manifest)
    assert calls == ([SUBJECT.UE_ROOT+'/LM002/Meshes'] if valid else [])
    report = SUBJECT.read(tmp_path/'LM002/import_audit.json')
    assert report['success'] is False and message in report['error']
    assert report['source'] == {'path':'source','sha256':'locked'}
    assert report['auto_setup_json'] == {'path':'source','sha256':'locked'}
    assert SUBJECT.read(state)['status'] == 'pending'


def test_morph_report_exposes_loss_and_only_normalizes_exact_mesh_prefix():
    result = SUBJECT.morph_comparison(['Smile','Blink','Lip_Open'],['CC_Base_Body__Smile','Blink','WrongBody_Lip_Open'],'CC_Base_Body')
    assert result['missing']==['Lip_Open']
    assert result['unexpected']==['WrongBody_Lip_Open']
    assert result['all_source_names_present'] is False
    assert 'Unclassified' in result['missing_reason']


def test_all_morph_names_preserved_and_collision_not_hidden():
    result = SUBJECT.morph_comparison(['Blink','Smile'],['Blink','CC_Base_Body_Smile'],'CC_Base_Body')
    assert result['all_source_names_present'] and not result['missing']
    duplicate = SUBJECT.morph_comparison(['Blink'],['Blink','CC_Base_Body_Blink'],'CC_Base_Body')
    assert duplicate['normalized_collisions']==1 and duplicate['imported_count']==2
    assert SUBJECT.morph_comparison(['Blink'],['cc_base_body__Blink'],'CC_Base_Body')['all_source_names_present']


def test_observed_space_sanitation_has_exact_bidirectional_source_mapping():
    source = ['TL Center Lower Depth L','EO Outer Depth R']
    imported = ['TL_Center_Lower_Depth_L','CC_Base_TearLine__EO_Outer_Depth_R']
    result = SUBJECT.morph_comparison(source,imported,'CC_Base_TearLine')
    assert result['all_source_names_present']
    assert result['missing']==[] and result['unexpected']==[]
    assert result['source_to_imported']==dict(zip(source,imported))
    assert result['imported_to_source']==dict(zip(imported,source))


def test_space_sanitation_source_collision_cannot_claim_full_preservation():
    result = SUBJECT.morph_comparison(['A B','A_B'],['A_B'],'Body')
    assert result['source_normalization_collisions']=={'A_B':['A B','A_B']}
    assert result['all_source_names_present'] is False
    assert result['source_to_imported']=={} and result['imported_to_source']=={}


def test_space_or_prefix_imported_collision_cannot_claim_full_preservation():
    result = SUBJECT.morph_comparison(['A B'],['A_B','Body__A_B'],'Body')
    assert result['actual_normalization_collisions']=={'A_B':['A_B','Body__A_B']}
    assert result['all_source_names_present'] is False
    assert result['source_to_imported']=={} and result['imported_to_source']=={}


def test_sources_must_have_locked_sha(tmp_path):
    fbx = tmp_path/'input.fbx'
    fbx.write_bytes(b'full character')
    case = {'fbx':{'path':str(fbx),'sha256':SUBJECT.sha(fbx)}}
    assert SUBJECT.source_record(case,'fbx')['sha256']==SUBJECT.sha(fbx)
    fbx.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Changed source'):
        SUBJECT.source_record(case,'fbx')


class Properties:
    def __init__(self,**values): self.values=values
    def set_editor_properties(self,values): self.values.update(values)
    def set_editor_property(self,key,value): self.values[key]=value
    def get_editor_property(self,key): return self.values[key]


def test_import_options_keep_full_rig_and_all_morph_without_animation(monkeypatch):
    mesh,common,normals = Properties(),Properties(),Properties()
    texture,animation = Properties(),Properties()
    material = Properties(texture_pipeline=texture)
    pipeline = Properties(mesh_pipeline=mesh,common_skeletal_meshes_and_animations_properties=common,
        common_meshes_properties=normals,animation_pipeline=animation,material_pipeline=material)
    monkeypatch.setattr(SUBJECT,'unreal',SimpleNamespace(
        InterchangeCombineSkeletalMeshesBehavior=SimpleNamespace(DO_NOT_COMBINE='DO_NOT_COMBINE'),
        InterchangeSkeletalMeshContentType=SimpleNamespace(ALL='ALL')))
    SUBJECT.configure_split(pipeline)
    assert mesh.values['import_morph_targets'] is True
    assert mesh.values['morph_threshold_position']==0.0
    assert mesh.values['skeletal_mesh_import_content_type']=='ALL'
    assert mesh.values['combine_skeletal_meshes_behavior']=='DO_NOT_COMBINE'
    assert mesh.values['update_skeleton_reference_pose'] is False
    assert common.values['use_t0_as_ref_pose'] is False
    assert common.values['skeleton'] is None and common.values['try_auto_select_skeleton'] is False
    assert animation.values['import_animations'] is False and mesh.values['create_physics_asset'] is False
    assert normals.values=={'recompute_normals':True,'recompute_tangents':True,
        'convert_statics_in_bone_hierarchy_to_skeletals':True}


def test_explicit_shared_skeleton_preserves_reference_pose_controls(monkeypatch):
    class Skeleton:
        pass
    shared = Skeleton()
    mesh,common,normals = Properties(),Properties(),Properties()
    pipeline = Properties(mesh_pipeline=mesh,common_skeletal_meshes_and_animations_properties=common,
        common_meshes_properties=normals,animation_pipeline=Properties(),
        material_pipeline=Properties(texture_pipeline=Properties()))
    monkeypatch.setattr(SUBJECT,'SHARED_SKELETON_PATH','/Game/Probe/Shared/Female')
    monkeypatch.setattr(SUBJECT,'unreal',SimpleNamespace(Skeleton=Skeleton,load_asset=lambda path:shared,
        InterchangeCombineSkeletalMeshesBehavior=SimpleNamespace(DO_NOT_COMBINE='DO_NOT_COMBINE'),
        InterchangeSkeletalMeshContentType=SimpleNamespace(ALL='ALL')))
    SUBJECT.configure_split(pipeline)
    assert common.values['skeleton'] is shared
    assert common.values['try_auto_select_skeleton'] is False
    assert common.values['use_t0_as_ref_pose'] is False
    assert mesh.values['update_skeleton_reference_pose'] is False
    assert mesh.values['import_morph_targets'] is True


def test_shared_reference_reader_uses_skeleton_pose_without_unexposed_properties(monkeypatch):
    class Skeleton:
        pass
    pose = object()  # Deliberately has no get_editor_property; UE AnimPose hides these.
    transform = SimpleNamespace(translation=SimpleNamespace(x=1.,y=2.,z=3.),
        rotation=SimpleNamespace(x=0.,y=0.,z=0.,w=1.),scale3d=SimpleNamespace(x=1.,y=1.,z=1.))
    extensions = SimpleNamespace(get_reference_pose=lambda skeleton:pose,
        get_bone_names=lambda value:['root'],get_ref_bone_pose=lambda value,name,space:transform)
    monkeypatch.setattr(SUBJECT,'unreal',SimpleNamespace(Skeleton=Skeleton,
        AnimPoseExtensions=extensions,AnimPoseSpaces=SimpleNamespace(LOCAL='LOCAL')))
    before = SUBJECT.skeleton_reference_inventory(Skeleton())
    assert before[0]['translation_cm'] == [1.,2.,3.]
    assert 'parent' not in before[0]
    transform.translation.x = 2.
    assert SUBJECT.skeleton_reference_inventory(Skeleton()) != before
