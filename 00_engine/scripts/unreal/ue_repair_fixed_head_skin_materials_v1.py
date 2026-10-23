"""Copy-based fixed-head skin repair; execute via existing UE Python bridge.

DM_SKIN_REPAIR_MODE=build|preview|apply|rollback|status
DM_SKIN_CORRECTION_STRENGTH=0|1 (historical HQ preview A/B, default 0).
Default unified path uses source RGB directly and has no color correction graph.
No CC geometry, source texture, index or completed import report is changed.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import unreal

REPO=Path(r'D:\UE\Lance_Work')
RUN=REPO/'00_engine/outputs/unreal_character_import/fixed_head_material_repair_20261005_v1'
ROOT='/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/Shared/SkinRepair_v1'
OLD='/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/Shared'
LIB=unreal.MaterialEditingLibrary
STRENGTH=float(globals().get('DM_SKIN_CORRECTION_STRENGTH',0.))
MODE=globals().get('DM_SKIN_REPAIR_MODE','preview')
VARIANT=globals().get('DM_SKIN_SHADER_VARIANT','unified')
if VARIANT=='unified':STRENGTH=0.
ROLES=['Head','Body','Arm','Leg']

def path(asset):return asset.get_path_name() if asset else None

def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Save failed '+path(asset))

def copy(source,target):
    if not target.startswith(ROOT+'/'):raise RuntimeError('Out of repair root')
    found=unreal.load_asset(target)
    if found:return found
    asset=unreal.EditorAssetLibrary.duplicate_asset(source,target)
    if not asset:raise RuntimeError('Duplicate failed '+source)
    return asset

def write(name,data):
    RUN.mkdir(parents=True,exist_ok=True)
    (RUN/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def import_control(row):
    source=Path(row['control_path'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=row['control_sha256']:raise RuntimeError('Control SHA mismatch')
    destination=ROOT+'/'+row['sex'].title()+'/Textures/T_NeckLinearDelta_R06_WrappedUV'
    texture=unreal.load_asset(destination)
    if texture is None:
        task=unreal.AssetImportTask();folder,name=destination.rsplit('/',1)
        task.set_editor_properties({'filename':str(source),'destination_path':folder,'destination_name':name,'automated':True,'save':False,'replace_existing':False})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=unreal.load_asset(destination)
    if not isinstance(texture,unreal.Texture2D):raise RuntimeError('Control texture import failed')
    texture.set_editor_properties({'srgb':False,'compression_settings':unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,'lod_group':unreal.TextureGroup.TEXTUREGROUP_UI,'never_stream':True})
    save(texture);return texture

def import_physical_skin(sex,role,kind):
    """Use original PNG bytes and a new factory-created texture resource.

    Duplicated female Head Normal read correct properties but sampled as (1,1,0)
    on GPU. Never reuse its platform data or change original imported textures.
    """
    source=Path(r'D:\UE\exports\character_creator\fixed_head_hair_20261004_v1\bases')/sex/('CC_FIXED_HEAD_'+sex.upper()+'.fbm')/('Std_Skin_'+role+'_Pbr_'+kind+'.png')
    if not source.exists():raise RuntimeError('Physical skin source missing '+str(source))
    target=ROOT+'/'+sex.title()+'/Textures/T_Physical_'+role+'_'+kind+'_v1'
    texture=unreal.load_asset(target)
    is_normal=kind=='Normal'
    compression=unreal.TextureCompressionSettings.TC_NORMALMAP if is_normal else unreal.TextureCompressionSettings.TC_DEFAULT
    group=unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if is_normal else unreal.TextureGroup.TEXTUREGROUP_CHARACTER
    if texture is None:
        folder,name=target.rsplit('/',1);factory=unreal.TextureFactory()
        factory.set_editor_properties({'compression_settings':compression,'lod_group':group,'defer_compression':False,'create_material':False})
        task=unreal.AssetImportTask()
        task.set_editor_properties({'filename':str(source),'destination_path':folder,'destination_name':name,'automated':True,'save':False,'replace_existing':False,'factory':factory})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=unreal.load_asset(target)
    if not isinstance(texture,unreal.Texture2D):raise RuntimeError('Physical skin import failed '+target)
    texture.set_editor_properties({'srgb':not is_normal,'compression_settings':compression,'lod_group':group,'never_stream':True,'flip_green_channel':False})
    save(texture);return texture,{'file':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'factory':'TextureFactory','created_from_source_not_duplicate':True}

def parent_material(default_control):
    material=copy('/Game/CC_Shaders/SkinShader/RL_HQSkin',ROOT+'/Materials/M_HQSkin_NeckContinuity_v2')
    if material.get_editor_property('use_material_attributes'):raise RuntimeError('Unexpected attribute-based skin shader')
    existing={str(n) for n in LIB.get_scalar_parameter_names(material)}
    if 'DM Neck Correction Strength' not in existing:
        base=LIB.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
        base_output=LIB.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_BASE_COLOR)
        if base is None:raise RuntimeError('HQ skin has no base color input')
        def expression(cls,x,y):return LIB.create_material_expression(material,cls,x,y)
        tex=expression(unreal.MaterialExpressionTextureSampleParameter2D,1600,600);tex.set_editor_properties({'parameter_name':'DM Neck Linear Delta','texture':default_control,'sampler_type':unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR})
        subtract=expression(unreal.MaterialExpressionSubtract,1850,600);subtract.set_editor_property('const_b',128/255)
        scale=expression(unreal.MaterialExpressionMultiply,2050,600);scale.set_editor_property('const_b',255*.5/127)
        strength=expression(unreal.MaterialExpressionScalarParameter,2050,850);strength.set_editor_properties({'parameter_name':'DM Neck Correction Strength','default_value':0.})
        amount=expression(unreal.MaterialExpressionMultiply,2250,600)
        add=expression(unreal.MaterialExpressionAdd,2450,400)
        saturate=expression(unreal.MaterialExpressionSaturate,2650,400)
        for a,output,b,input_name in [(tex,'RGB',subtract,'A'),(subtract,'',scale,'A'),(scale,'',amount,'A'),(strength,'',amount,'B'),(base,base_output,add,'A'),(amount,'',add,'B'),(add,'',saturate,'Input')]:
            names=[str(x) for x in LIB.get_material_expression_input_names(b)]
            if input_name not in names and len(names)==1:input_name=names[0]
            if not LIB.connect_material_expressions(a,output,b,input_name):raise RuntimeError('Could not wire correction '+input_name+'; available='+str(names))
        if not LIB.connect_material_property(saturate,'',unreal.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Could not bind corrected basecolor')
        LIB.recompile_material(material);save(material)
    node=LIB.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(node,unreal.MaterialExpressionSaturate):raise RuntimeError('Partial correction parent: BaseColor output is not expected Saturate')
    return material

def unified_parent(default_control=None):
    """Bounded common skin response: keep source detail without HQ branches."""
    target=ROOT+'/Materials/M_UnifiedSkin_PhysicalSource_v1'
    material=unreal.load_asset(target)
    if material is not None:return material
    folder,name=target.rsplit('/',1)
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    material.set_editor_properties({'blend_mode':unreal.BlendMode.BLEND_OPAQUE,'shading_model':unreal.MaterialShadingModel.MSM_DEFAULT_LIT,'used_with_skeletal_mesh':True})
    def expression(cls,x,y):return LIB.create_material_expression(material,cls,x,y)
    diffuse=expression(unreal.MaterialExpressionTextureSampleParameter2D,0,0)
    diffuse.set_editor_properties({'parameter_name':'Base Color Map','texture':unreal.load_asset('/Engine/EngineResources/DefaultTexture'),'sampler_type':unreal.MaterialSamplerType.SAMPLERTYPE_COLOR})
    normal=expression(unreal.MaterialExpressionTextureSampleParameter2D,0,300)
    normal.set_editor_properties({'parameter_name':'Normal Map','texture':unreal.load_asset('/Game/CC_Shaders/SkinShader/Textures/Share/Normal_Default'),'sampler_type':unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL})
    for node,out,prop in [(diffuse,'RGB',unreal.MaterialProperty.MP_BASE_COLOR),(normal,'RGB',unreal.MaterialProperty.MP_NORMAL)]:
        if not LIB.connect_material_property(node,out,prop):raise RuntimeError('Unified skin property connection failed')
    for name,value,prop,y in [('DM Skin Roughness',.6,unreal.MaterialProperty.MP_ROUGHNESS,300),('DM Skin Specular',.35,unreal.MaterialProperty.MP_SPECULAR,500)]:
        node=expression(unreal.MaterialExpressionScalarParameter,800,y);node.set_editor_properties({'parameter_name':name,'default_value':value});LIB.connect_material_property(node,'',prop)
    LIB.recompile_material(material);save(material);return material

def sources(sex):
    base='CC_FIXED_HEAD_'+sex.upper()
    source=Path(r'D:\UE\exports\character_creator\fixed_head_hair_20261004_v1\bases')/sex/(base+'.json')
    document=json.loads(source.read_text(encoding='utf-8-sig'))
    found={}
    def walk(v):
        if isinstance(v,dict):
            for k,item in v.items():
                if k.startswith('Std_Skin_') and isinstance(item,dict) and 'Textures' in item:found[k]=item
                else:walk(item)
        elif isinstance(v,list):
            for item in v:walk(item)
    walk(document);return found

def mapping(name):
    source=Path(r'D:\UE\projects\datatry_02\Plugins\RLPlugin\Source\RLPlugin\Private\RLShaderData.h')
    text=source.read_text(encoding='utf-8-sig');block=text.split('g_k'+name+'Map =',1)[1].split('};',1)[0]
    return dict(re.findall(r'^\s*\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}',block,re.M))

def set_texture(material,name,texture):
    LIB.set_material_instance_texture_parameter_value(material,name,texture)
    if path(LIB.get_material_instance_texture_parameter_value(material,name))!=path(texture):raise RuntimeError('Texture parameter readback failed '+name)

def build():
    controls=[]
    control_by_sex={}
    if VARIANT=='hq':
        controls=json.loads((RUN/'skin_controls/skin_seam_controls.json').read_text())['controls']
        control_by_sex={row['sex']:import_control(row) for row in controls}
    if VARIANT not in ['hq','unified']:raise RuntimeError('Unknown skin variant')
    parent=unified_parent() if VARIANT=='unified' else parent_material(control_by_sex['female']);rows=[]
    for sex in ['female','male']:
        title=sex.title();ref=('F02','F','CC_MOD_F_BASE_UE58') if sex=='female' else ('M02','M','CC_MOD_M_BASE_UE58')
        template_root=f'/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/{ref[0]}_Average/Cases/{ref[1]}_BASE/FullReference/Materials/{ref[2]}'
        cc=sources(sex)
        for role in ROLES:
            name='Std_Skin_'+role+'_Pbr';template_path=template_root+'/'+name+'_HQ_Inst'
            template=unreal.load_asset(template_path)
            if not isinstance(template,unreal.MaterialInstanceConstant):raise RuntimeError('Skin template missing '+template_path)
            if VARIANT=='unified':
                target=ROOT+'/'+title+'/Materials/MI_Skin_'+role+'_UnifiedFresh_v1'
                material=unreal.load_asset(target)
                if material is None:
                    folder,instance_name=target.rsplit('/',1)
                    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(instance_name,folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
                LIB.clear_all_material_instance_parameters(material)
            else:
                material=copy(template_path,ROOT+'/'+title+'/Materials/MI_Skin_'+role)
                for field in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']:
                    material.set_editor_property(field,template.get_editor_property(field))
            LIB.set_material_instance_parent(material,parent)
            normal,normal_source=import_physical_skin(sex,role,'Normal')
            diffuse,diffuse_source=import_physical_skin(sex,role,'Diffuse')
            set_texture(material,'Base Color Map',diffuse);set_texture(material,'Normal Map',normal)
            if VARIANT=='hq':set_texture(material,'DM Neck Linear Delta',control_by_sex[sex])
            scalar_names={str(x) for x in LIB.get_scalar_parameter_names(material)}
            mapped={};unmapped=[]
            shader_map=mapping('Head' if role=='Head' else 'Skin')
            variables=cc[name].get('Custom Shader',{}).get('Variable',{})
            for source_name,target_name in shader_map.items():
                value=variables.get(source_name)
                if isinstance(value,(float,int)) and target_name in scalar_names:
                    LIB.set_material_instance_scalar_parameter_value(material,target_name,float(value));mapped[target_name]=float(value)
                elif value is not None and not isinstance(value,list):unmapped.append({'source':source_name,'target':target_name,'reason':'Not a scalar or parameter absent; copied accepted template/default'})
            if VARIANT=='hq':LIB.set_material_instance_scalar_parameter_value(material,'DM Neck Correction Strength',STRENGTH if role=='Head' else 0.)
            # Avoid carrying old character-specific second-face/wrinkle blends.
            for key in ['BaseColor_Blend2_Strength','NormalMap_Blend_Strength']:
                if key in scalar_names:LIB.set_material_instance_scalar_parameter_value(material,key,0.)
            LIB.update_material_instance(material);save(material)
            rows.append({'sex':sex,'role':role,'slot':name,'material':path(material),'template':None if VARIANT=='unified' else path(template),'template_reference_only':path(template) if VARIANT=='unified' else None,'instance_created_fresh':VARIANT=='unified','shader_variant':VARIANT,'parent':path(parent),'parent_shading_model':str(parent.get_editor_property('shading_model')),'normal_copy':path(normal),'normal_physical_source':normal_source,'diffuse_physical_source':diffuse_source,'normal_srgb':normal.get_editor_property('srgb'),'normal_compression':str(normal.get_editor_property('compression_settings')),'source_diffuse':path(diffuse),'mapped_source_scalars':mapped,'unmapped_source_scalars':unmapped,'correction_strength':STRENGTH if role=='Head' else 0.})
    result={'success':True,'mode':'build','variant':VARIANT,'shader_variant':VARIANT,'parent':path(parent),'parent_shading_model':str(parent.get_editor_property('shading_model')),'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows,'controls':controls,'correction_required':False,'source_color_boundary_nonblocking':True,'numeric_delta_graph_present':VARIANT=='hq','original_normal_assets_unchanged':True,'original_diffuse_pixels_unchanged':True,'geometry_unchanged':True,'at_utc':datetime.now(timezone.utc).isoformat()};write('skin_build.json',result);return result

def actors():
    return {a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}

def bind(preview):
    record=build();lookup={(r['sex'],r['slot']):r for r in record['rows']};backpath=RUN/('skin_actor_backup.json' if preview else 'skin_mesh_backup.json')
    backup=json.loads(backpath.read_text()) if backpath.exists() else {'rows':[]}
    if preview:
        actor_map=actors();targets=[]
        for sex in ['female','male']:
            name='DM_FHMR_'+sex.title()+'_Body';actor=actor_map.get(name)
            if actor is None:raise RuntimeError('Open manual review map before skin preview: '+name)
            component=actor.get_editor_property('skeletal_mesh_component');targets.append((sex,component,component.get_editor_property('skeletal_mesh_asset')))
    else:
        targets=[(sex,None,unreal.load_asset(OLD+'/'+sex.title()+'/CombinedBase/CC_FIXED_HEAD_'+sex.upper())) for sex in ['female','male']]
    changed=[]
    for sex,component,mesh in targets:
        slots=list(mesh.get_editor_property('materials'))
        if not any(r['sex']==sex for r in backup['rows']):
            backup['rows'].append({'sex':sex,'mesh':path(mesh),'materials':[path(s.get_editor_property('material_interface')) for s in slots],'overrides':[path(m) for m in component.get_editor_property('override_materials')] if component else None})
            write(backpath.name,backup)
        for i,slot in enumerate(slots):
            key=(sex,str(slot.get_editor_property('material_slot_name')))
            if key not in lookup:continue
            material=unreal.load_asset(lookup[key]['material'])
            if preview:component.set_material(i,material)
            else:slot.set_editor_property('material_interface',material)
            changed.append({'sex':sex,'mesh':path(mesh),'index':i,'slot':key[1],'material':path(material)})
        if not preview:mesh.set_editor_property('materials',slots);save(mesh)
    result={'success':True,'mode':'preview' if preview else 'apply','changed_slots':changed,'correction_strength':STRENGTH,'backup':str(backpath),'at_utc':datetime.now(timezone.utc).isoformat()};write('skin_'+result['mode']+'.json',result);return result

def rollback():
    restored=[];actor_map=actors()
    for name in ['skin_mesh_backup.json','skin_actor_backup.json']:
        p=RUN/name
        if not p.exists():continue
        for row in json.loads(p.read_text())['rows']:
            if name=='skin_actor_backup.json':
                actor=actor_map.get('DM_FHMR_'+row['sex'].title()+'_Body')
                if actor:actor.get_editor_property('skeletal_mesh_component').set_editor_property('override_materials',[unreal.load_asset(x) if x else None for x in row['overrides']])
            else:
                mesh=unreal.load_asset(row['mesh']);slots=list(mesh.get_editor_property('materials'))
                for slot,pth in zip(slots,row['materials']):slot.set_editor_property('material_interface',unreal.load_asset(pth) if pth else None)
                mesh.set_editor_property('materials',slots);save(mesh)
            restored.append({'kind':name,'sex':row['sex']})
    result={'success':True,'mode':'rollback','restored':restored};write('skin_rollback.json',result);return result

def debug(mode):
    rows=json.loads((RUN/'skin_build.json').read_text())['rows'];changes=[]
    for row in rows:
        material=unreal.load_asset(row['material'])
        if row.get('template'):
            template=unreal.load_asset(row['template'])
            material.set_editor_property('scalar_parameter_values',template.get_editor_property('scalar_parameter_values'))
        # Restore precisely the build-time source scalars before each debug.
        for name,val in row['mapped_source_scalars'].items():LIB.set_material_instance_scalar_parameter_value(material,name,val)
        scalar_names={str(x) for x in LIB.get_scalar_parameter_names(material)}
        overrides={'DM Neck Correction Strength':0. if mode=='debug_uncorrected' else (1. if row['role']=='Head' else 0.)}
        if mode=='debug_surface':
            overrides.update({'Normal/Bump Strength':0.,'MicroNormal Strength':0.,'Head Specular':.5,'Specular':.5,'Min SSS':0.,'Max SSS':0.})
        if mode=='debug_head_normal' and row['role']=='Head':
            overrides.update({'Normal/Bump Strength':0.,'MicroNormal Strength':0.})
        if mode=='debug_flat_texture':
            texture=unreal.load_asset('/Game/CC_Shaders/SkinShader/Textures/Share/Normal_Default') if row['role']=='Head' else unreal.load_asset(row['normal_copy'])
            set_texture(material,'Normal Map',texture)
        for name,val in overrides.items():
            if name in scalar_names:LIB.set_material_instance_scalar_parameter_value(material,name,val)
        LIB.update_material_instance(material);save(material);changes.append({'sex':row['sex'],'role':row['role'],'overrides':overrides})
    result={'success':True,'mode':mode,'changes':changes,'scope':'Temporary copied repair instances only; no body mesh binding or geometry changes'};write('skin_'+mode+'.json',result);return result

def main():
    if not 0<=STRENGTH<=1:raise RuntimeError('Correction strength must be within 0..1')
    if MODE=='build':return build()
    if MODE in ('preview','apply'):return bind(MODE=='preview')
    if MODE=='rollback':return rollback()
    if MODE in ['debug_uncorrected','debug_head_normal','debug_flat_texture','debug_surface']:return debug(MODE)
    if MODE=='status':return json.loads((RUN/'skin_build.json').read_text())
    raise RuntimeError('Unknown skin repair mode')

print('DM_FIXED_HEAD_SKIN_REPAIR='+json.dumps(main(),ensure_ascii=False,default=str))
