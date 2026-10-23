"""Current neutral-base hair dyes; original texture assets stay intact.

The historical filename is retained for runtime pins and saved-source compatibility.
"""
from __future__ import annotations
import hashlib,json,types,struct
import hair_eye_color_runtime_v1 as original
import scene_site_hair_color_trials_v1 as palette

TRIALS={'black_neutral_v1':'black','blue_neutral_v1':'blue','pink_neutral_v1':'pink'}
SHADER='/Game/DataMake/Appearance/Materials/NeutralHairTrialsV1/M_Hair_NeutralBase_v1'
OWNER='DM_NeutralHairTrialSpec'
SOFT_SPECULAR_SCALE=.75
SOFT_ROUGHNESS_INCREMENT=.06

def soft_reflection_scalars(values):
    """Reduce source specular by 25%, gently broaden highlights, no tint changes."""
    result=dict(values)
    for name in ('Specular Multiplier','Roughness Multiplier'):
        if name not in values:raise RuntimeError('Hair source lacks reflection parameter: '+name)
    result['Specular Multiplier']=values['Specular Multiplier']*SOFT_SPECULAR_SCALE
    roughness=values['Roughness Multiplier']
    result['Roughness Multiplier']=roughness+min(SOFT_ROUGHNESS_INCREMENT,max(0.,1.-roughness))
    for name in ('Specular Multiplier','Roughness Multiplier'):
        result[name]=struct.unpack('f',struct.pack('f',result[name]))[0]
    return result

def snapshot(lib,source):
    return {
        'scalar':{str(n):lib.get_material_instance_scalar_parameter_value(source,n) for n in lib.get_scalar_parameter_names(source)},
        'vector':{str(n):original._rgba(lib.get_material_instance_vector_parameter_value(source,n)) for n in lib.get_vector_parameter_names(source)},
        'texture':{str(n):original._path(lib.get_material_instance_texture_parameter_value(source,n)) for n in lib.get_texture_parameter_names(source)},
        'static':{str(n):lib.get_material_instance_static_switch_parameter_value(source,n) for n in lib.get_static_switch_parameter_names(source)},
    }

def material(row,asset_root,slot,soft_reflection=False):
    if row['kind'] != 'hair':
        return original._material(row,asset_root,slot)
    u=original._ue();lib=u.MaterialEditingLibrary
    source=row['source'];base=row['preset'];shader=u.load_asset(SHADER)
    if shader is None or str(u.EditorAssetLibrary.get_metadata_tag(shader,'DM_NeutralHairTrial'))!='v1':
        raise RuntimeError('Neutral hair trial shader is missing or incomplete')
    expected=snapshot(lib,source)
    for name,value in palette.NEUTRAL_SCALAR_OVERRIDES.get(base,{}).items():
        if name not in expected['scalar']:
            raise RuntimeError('Hair source lacks white midtone parameter: '+name)
        expected['scalar'][name]=struct.unpack('f',struct.pack('f',value))[0]
    expected['vector']['Base Color Tint']=[struct.unpack('f',struct.pack('f',x))[0] for x in palette.NEUTRAL_TINTS[base]]
    specification={'version':2,'method':palette.NEUTRAL_METHOD,'source':original._path(source),'source_sha256':row['source_sha256'],
        'shader_sha256':original._sha(original.package_file(SHADER)), 'base_preset':base,'effective_parameters':expected}
    if soft_reflection:
        expected['scalar']=soft_reflection_scalars(expected['scalar'])
        specification['reflection_method']=palette.SOFT_REFLECTION_METHOD
    spec=json.dumps(specification,sort_keys=True)
    key=hashlib.sha256(spec.encode()).hexdigest()[:20]
    path=asset_root+'/NeutralHairTrialsV1/Instances/MI_'+base+'_'+key
    created=False
    if u.EditorAssetLibrary.does_asset_exist(path):
        instance=u.load_asset(path)
        if str(u.EditorAssetLibrary.get_metadata_tag(instance,OWNER))!=spec:
            raise RuntimeError('Incomplete or mismatched neutral hair trial instance: '+path)
    else:
        instance=u.EditorAssetLibrary.duplicate_asset(source.get_path_name().split('.')[0],path)
        if not isinstance(instance,u.MaterialInstanceConstant):raise RuntimeError('Trial instance duplication failed')
        lib.set_material_instance_parent(instance,shader)
        for name,value in expected['scalar'].items():lib.set_material_instance_scalar_parameter_value(instance,name,value)
        for name,value in expected['vector'].items():lib.set_material_instance_vector_parameter_value(instance,name,u.LinearColor(*value))
        for name,value in expected['texture'].items():lib.set_material_instance_texture_parameter_value(instance,name,u.load_asset(value) if value else None)
        for name,value in expected['static'].items():lib.set_material_instance_static_switch_parameter_value(instance,name,value)
        lib.update_material_instance(instance)
        if snapshot(lib,instance)!=expected:raise RuntimeError('Neutral trial changed parameters beyond the intended tint')
        u.EditorAssetLibrary.set_metadata_tag(instance,OWNER,spec)
        if not u.EditorAssetLibrary.save_loaded_asset(instance,False):raise RuntimeError('Trial material save failed')
        created=True
    if original._path(instance.get_editor_property('parent'))!=original._path(shader) or snapshot(lib,instance)!=expected:
        raise RuntimeError('Neutral trial parameter inheritance no longer matches source')
    return instance,expected['vector']['Base Color Tint'],created

def apply(request,components,slot,asset_root):
    requested=request['hair_color']
    canonical=palette.canonical_color(requested)
    soft_reflection=canonical in palette.SOFT_REFLECTION_COLORS
    base=palette.SOFT_REFLECTION_COLORS.get(canonical,canonical)
    if canonical == palette.LEGACY_SILVER_ID:
        result=original.apply(dict(request,hair_color='silver_white'),components,slot,asset_root)
        result.update(hair_color=canonical,requested_hair_color=requested,base_preset='silver_white',
                      hair_color_method='legacy_chestnut_base_v1',neutral_base_trial=False,
                      desaturation_fraction=0.,palette_parameters_unchanged=True,
                      scope='current_scene_appearance_legacy_silver_comparison')
        return result
    if base != 'original' and base not in palette.NEUTRAL_TINTS:
        raise ValueError('Unknown neutral hair color: '+str(requested))
    mapped=dict(request,hair_color=base)
    # Reuse the original slot classification, protected-source hashing, binding
    # checks and rollback, replacing only the derived material factory privately.
    factory=(lambda row,root,index: material(row,root,index,True)) if soft_reflection else material
    worker=types.FunctionType(original.apply.__code__,dict(original.apply.__globals__,_material=factory),
                              original.apply.__name__,original.apply.__defaults__,original.apply.__closure__)
    result=worker(mapped,components,slot,asset_root)
    result.update(hair_color=canonical,requested_hair_color=requested,base_preset=base,
                  neutral_base_trial=soft_reflection,hair_color_method=palette.NEUTRAL_METHOD,
                  desaturation_fraction=1. if canonical != 'original' else 0.,
                  palette_parameters_unchanged=False,scope='current_scene_appearance')
    if soft_reflection:result['reflection_method']=palette.SOFT_REFLECTION_METHOD
    return result
