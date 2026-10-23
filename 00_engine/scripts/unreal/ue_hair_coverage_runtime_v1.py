"""Shared hair coverage correction after formal slot/color assembly.

Keep meshes, color presets and shading parameters unchanged. Only restore the
HB1_01 opacity binding and the clip threshold required by CC's signed dither.
"""
import hashlib,json

VERSION='hair_coverage_v1'
ROOT='/Game/DataMake/Appearance/Materials/HairCoverageV1'
SHADER_ROOTS={
 '/Game/CC_Shaders/HairShader/RL_Hair_Specular',
 '/Game/DataMake/Appearance/Materials/NeutralHairTrialsV1/M_Hair_NeutralBase_v1',
}


def _color_parent(u,material):
 """Remove only our own coverage layers, retaining the selected color parent."""
 seen=set()
 while isinstance(material,u.MaterialInstanceConstant):
  path=material.get_path_name()
  if not path.split('.',1)[0].startswith(ROOT+'/'):break
  if not u.EditorAssetLibrary.get_metadata_tag(material,'DM_HairCoverage'):break
  if path in seen:raise RuntimeError('Cyclic hair coverage material parent')
  seen.add(path)
  material=material.get_editor_property('parent')
 return material


def _supported_shader(u,material):
 """Do not change ornament shaders merely exposing an Opacity Map parameter."""
 seen=set()
 while isinstance(material,u.MaterialInstanceConstant):
  path=material.get_path_name()
  if path in seen:raise RuntimeError('Cyclic hair material parent')
  seen.add(path)
  material=material.get_editor_property('parent')
 return material is not None and material.get_path_name().split('.',1)[0] in SHADER_ROOTS

def apply(u,components):
 lib=u.MaterialEditingLibrary;rows=[]
 for name,c in components.items():
  mesh=c.get_skeletal_mesh_asset()
  if not name.startswith('HairPart') or mesh is None:continue
  for i,slot in enumerate(mesh.get_editor_property('materials')):
   original=slot.material_interface;parent=_color_parent(u,c.get_material(i))
   if not isinstance(original,u.MaterialInstanceConstant) or not isinstance(parent,u.MaterialInstanceConstant):continue
   if not _supported_shader(u,parent):continue
   if 'Opacity Map' not in {str(n) for n in lib.get_texture_parameter_names(parent)}:continue
   source=original.get_path_name();fix_base='/HB1_01/' in source and original.get_name().startswith('MI_Hair134_')
   opacity=source.split('/Materials/')[0]+'/Textures/T_Hair134_Transparency_Pbr_Opacity' if fix_base else None
   # CC DitherTemporalAA = alpha + (mod5 + noise)/6 - .5.
   # Its zero-alpha maximum is 1/3; .15 admits transparent card rectangles.
   # Hair134's JPEG has border values up to 25/255, requiring >.4314.
   clip=.44 if fix_base else .34
   spec=json.dumps({'version':VERSION,'parent':parent.get_path_name(),'source':source,'opacity':opacity,'clip':clip},sort_keys=True)
   target=ROOT+'/MI_'+hashlib.sha256(spec.encode()).hexdigest()[:20]
   m=u.load_asset(target)
   if m is None:
    folder,label=target.rsplit('/',1)
    m=u.AssetToolsHelpers.get_asset_tools().create_asset(label,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(m,parent)
    props=m.get_editor_property('base_property_overrides')
    props.set_editor_property('override_opacity_mask_clip_value',True)
    props.set_editor_property('opacity_mask_clip_value',clip)
    m.set_editor_property('base_property_overrides',props)
    if opacity:
     texture=u.load_asset(opacity)
     if texture is None:raise RuntimeError('HB1_01 matching opacity texture is missing')
     lib.set_material_instance_texture_parameter_value(m,'Opacity Map',texture)
    lib.update_material_instance(m)
    u.EditorAssetLibrary.set_metadata_tag(m,'DM_HairCoverage',spec)
    if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Cannot save hair coverage correction')
   c.set_material(i,m)
   rows.append({'component':name,'slot':i,'source':source,'color_parent':parent.get_path_name(),
                'material':m.get_path_name(),'clip':clip,'opacity_repaired':opacity})
 return {'version':VERSION,'bindings':rows,'source_assets_modified':False}
