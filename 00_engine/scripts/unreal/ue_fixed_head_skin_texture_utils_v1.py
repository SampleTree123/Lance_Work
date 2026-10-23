"""Exact-source skin imports with fresh TextureFactory resources and one shader.

No top-level Unreal dependency or mutation. The historical function name stays
compatible; it now imports both Diffuse and Normal and binds four unified skin
instances. It never duplicates the possibly broken Interchange texture resource.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

SKIN_SLOTS={"Std_Skin_Head_Pbr","Std_Skin_Body_Pbr","Std_Skin_Arm_Pbr","Std_Skin_Leg_Pbr"}
SKIN_ROLES=("Head","Body","Arm","Leg")


def build_skin_source_plan(mesh_path,slot_names,cc_materials,json_path):
    """Pure semantic plan: exact CC declarations, bounded output, source hashes."""
    package=mesh_path.split(".",1)[0]
    if not package.startswith("/Game/DataMake/CharacterFactory/FixedHeadHair_"):
        raise ValueError("Skin setup only supports independent fixed-head batch assets")
    directory=package.rsplit("/",1)[0]
    if "/Shared/" not in directory or not directory.endswith("/CombinedBase"):
        raise ValueError("Skin source imports must stay inside the combined-base directory")
    json_path=Path(json_path).resolve()
    if not json_path.is_file():raise FileNotFoundError(json_path)
    ordered=[slot for slot in slot_names if slot in SKIN_SLOTS]
    if len(ordered)!=4 or set(ordered)!=SKIN_SLOTS:
        raise ValueError("Expected exactly four distinct CC skin slots")
    rows=[]
    for role in SKIN_ROLES:
        name="Std_Skin_"+role+"_Pbr"
        source=cc_materials.get(name)
        if not isinstance(source,dict):raise ValueError("No exact CC JSON skin material "+name)
        row={"slot":name,"role":role,"textures":{}}
        for channel,kind in (("Base Color","Diffuse"),("Normal","Normal")):
            declaration=source.get("Textures",{}).get(channel,{})
            relative=declaration.get("Texture Path")
            if not relative:raise ValueError("Missing exact skin "+channel+" declaration for "+name)
            physical=(json_path.parent/relative).resolve()
            if not physical.is_relative_to(json_path.parent):raise ValueError("Texture path escapes this exported base "+name)
            if not physical.is_file():raise FileNotFoundError(physical)
            digest=hashlib.sha256(physical.read_bytes()).hexdigest()
            row["textures"][kind]={"source_file":str(physical),"sha256":digest,"bytes":physical.stat().st_size,
                "srgb":kind!="Normal","compression":"TC_NORMALMAP" if kind=="Normal" else "TC_DEFAULT",
                "sampler":"NORMAL" if kind=="Normal" else "COLOR"}
        rows.append(row)
    fingerprint=hashlib.sha256(json.dumps({"mesh":mesh_path,"rows":rows,"roughness":.6,"specular":.35},sort_keys=True).encode()).hexdigest()
    root=directory+"/SkinSource_v1/S_"+fingerprint[:16]
    for row in rows:
        row["material"]=root+"/Materials/MI_Skin_"+row["role"]+"_Source_v1"
        for kind,record in row["textures"].items():
            record["asset"]=root+"/Textures/T_"+row["role"]+"_"+kind+"_"+record["sha256"][:12]
    return {"schema_version":1,"mesh":mesh_path,"root":root,"source_fingerprint":fingerprint,
        "source_json":str(json_path),"source_json_sha256":hashlib.sha256(json_path.read_bytes()).hexdigest(),
        "parent":root+"/Materials/M_UnifiedSkin_Source_v1","rows":rows,
        "graph":{"shading_model":"DEFAULT_LIT","blend_mode":"OPAQUE","connections":{
            "BASE_COLOR":"Base Color Map.RGB","NORMAL":"Normal Map.RGB",
            "ROUGHNESS":"DM Skin Roughness","SPECULAR":"DM Skin Specular"},
            "scalars":{"DM Skin Roughness":.6,"DM Skin Specular":.35},
            "color_correction":False,"source_color_pixels_unchanged":True}}


def configure_normal_texture(texture,save=True,never_stream=None):
    import unreal
    if not isinstance(texture,unreal.Texture2D):raise TypeError("Expected Texture2D")
    before={"srgb":texture.get_editor_property("srgb"),"compression_settings":str(texture.get_editor_property("compression_settings")),"lod_group":str(texture.get_editor_property("lod_group"))}
    values={"srgb":False,"compression_settings":unreal.TextureCompressionSettings.TC_NORMALMAP,"lod_group":unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP,"flip_green_channel":False}
    if never_stream is not None:values["never_stream"]=bool(never_stream)
    texture.set_editor_properties(values)
    if save and not unreal.EditorAssetLibrary.save_loaded_asset(texture,only_if_is_dirty=False):raise RuntimeError("Could not save skin Normal texture")
    after={"srgb":texture.get_editor_property("srgb"),"compression_settings":str(texture.get_editor_property("compression_settings")),"lod_group":str(texture.get_editor_property("lod_group"))}
    if after["srgb"] or "TC_NORMALMAP" not in after["compression_settings"]:raise RuntimeError("Normal setup readback failed")
    return {"texture":texture.get_path_name(),"before":before,"after":after}


def _fresh_texture(record,save):
    import unreal
    source=Path(record["source_file"])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=record["sha256"]:raise RuntimeError("Skin source changed during import")
    target=record["asset"];texture=unreal.load_asset(target);created=texture is None
    normal=record["compression"]=="TC_NORMALMAP"
    compression=unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT
    group=unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if normal else unreal.TextureGroup.TEXTUREGROUP_CHARACTER
    if created:
        folder,name=target.rsplit("/",1);factory=unreal.TextureFactory()
        factory.set_editor_properties({"compression_settings":compression,"lod_group":group,"defer_compression":False,"create_material":False})
        task=unreal.AssetImportTask();task.set_editor_properties({"filename":str(source),"destination_path":folder,"destination_name":name,
            "automated":True,"save":False,"replace_existing":False,"factory":factory})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=unreal.load_asset(target)
    if not isinstance(texture,unreal.Texture2D):raise RuntimeError("Fresh skin TextureFactory import failed "+target)
    data=texture.get_editor_property("asset_import_data")
    imported=[Path(p).resolve() for p in data.extract_filenames()] if data else []
    if source.resolve() not in imported:raise RuntimeError("Existing hashed texture has different physical source "+target)
    stored_hash=unreal.EditorAssetLibrary.get_metadata_tag(texture,"DM_Source_SHA256")
    if not created and stored_hash and str(stored_hash)!=record["sha256"]:
        raise RuntimeError("Existing skin texture source fingerprint changed "+target)
    if not created and not stored_hash and record["sha256"][:12] not in target:
        raise RuntimeError("Existing skin texture has no source hash provenance "+target)
    unreal.EditorAssetLibrary.set_metadata_tag(texture,"DM_Source_SHA256",record["sha256"])
    texture.set_editor_properties({"srgb":not normal,"compression_settings":compression,"lod_group":group,"never_stream":True,"flip_green_channel":False})
    if save and not unreal.EditorAssetLibrary.save_loaded_asset(texture,only_if_is_dirty=False):raise RuntimeError("Cannot save fresh skin texture")
    if texture.get_editor_property("srgb") != (not normal) or texture.get_editor_property("compression_settings")!=compression:
        raise RuntimeError("Fresh source texture semantic readback failed")
    return texture,{**record,"texture":texture.get_path_name(),"created":created,"factory":"TextureFactory","resource_duplicated":False}


def import_physical_skin_texture(source_path,destination,is_normal,save=True):
    """Shared explicit physical-source TextureFactory API for repair callers."""
    source=Path(source_path).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    if not destination.startswith("/Game/DataMake/CharacterFactory/"):
        raise ValueError("Physical skin texture destination outside factory asset root")
    record={"source_file":str(source),"sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "bytes":source.stat().st_size,"asset":destination,"srgb":not is_normal,
        "compression":"TC_NORMALMAP" if is_normal else "TC_DEFAULT",
        "sampler":"NORMAL" if is_normal else "COLOR"}
    return _fresh_texture(record,save)


def _unified_parent(plan,defaults,save):
    import unreal
    lib=unreal.MaterialEditingLibrary;target=plan["parent"];material=unreal.load_asset(target)
    if material is None:
        folder,name=target.rsplit("/",1)
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
        material.set_editor_properties({"blend_mode":unreal.BlendMode.BLEND_OPAQUE,"shading_model":unreal.MaterialShadingModel.MSM_DEFAULT_LIT,"used_with_skeletal_mesh":True})
        for kind,parameter,sampler,prop,y in [
            ("Diffuse","Base Color Map",unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,unreal.MaterialProperty.MP_BASE_COLOR,0),
            ("Normal","Normal Map",unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,unreal.MaterialProperty.MP_NORMAL,300)]:
            node=lib.create_material_expression(material,unreal.MaterialExpressionTextureSampleParameter2D,0,y)
            node.set_editor_properties({"parameter_name":parameter,"texture":defaults[kind],"sampler_type":sampler})
            if not lib.connect_material_property(node,"RGB",prop):raise RuntimeError("Unified skin texture graph connection failed")
        for name,value,prop,y in [("DM Skin Roughness",.6,unreal.MaterialProperty.MP_ROUGHNESS,300),("DM Skin Specular",.35,unreal.MaterialProperty.MP_SPECULAR,500)]:
            node=lib.create_material_expression(material,unreal.MaterialExpressionScalarParameter,700,y)
            node.set_editor_properties({"parameter_name":name,"default_value":value})
            if not lib.connect_material_property(node,"",prop):raise RuntimeError("Unified skin scalar graph connection failed")
        lib.recompile_material(material)
    if not isinstance(material,unreal.Material):raise RuntimeError("Wrong unified skin parent class")
    if material.get_editor_property("shading_model")!=unreal.MaterialShadingModel.MSM_DEFAULT_LIT:raise RuntimeError("Unified skin parent shading changed")
    for parameter,prop in [("Base Color Map",unreal.MaterialProperty.MP_BASE_COLOR),("Normal Map",unreal.MaterialProperty.MP_NORMAL)]:
        node=lib.get_material_property_input_node(material,prop)
        if not isinstance(node,unreal.MaterialExpressionTextureSampleParameter2D) or str(node.get_editor_property("parameter_name"))!=parameter:
            raise RuntimeError("Unified skin parent graph differs from direct source contract")
    if save and not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError("Cannot save unified skin parent")
    return material


def configure_imported_skin_normals(mesh,cc_materials,json_path,save=True):
    """Compatible call site, now fresh exact-source textures and 4 unified MIs."""
    import unreal
    lib=unreal.MaterialEditingLibrary
    slots=list(mesh.get_editor_property("materials"))
    plan=build_skin_source_plan(mesh.get_path_name(),[str(s.get_editor_property("material_slot_name")) for s in slots],cc_materials,json_path)
    textures={};evidence={}
    for row in plan["rows"]:
        for kind,record in row["textures"].items():
            texture,entry=_fresh_texture(record,save);textures[(row["slot"],kind)]=texture;evidence[(row["slot"],kind)]=entry
    defaults={kind:textures[("Std_Skin_Head_Pbr",kind)] for kind in ("Diffuse","Normal")}
    parent=_unified_parent(plan,defaults,save);records=[];instances={}
    for row in plan["rows"]:
        target=row["material"];material=unreal.load_asset(target)
        if material is None:
            folder,name=target.rsplit("/",1)
            material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        if not isinstance(material,unreal.MaterialInstanceConstant):raise RuntimeError("Wrong unified skin instance class")
        lib.set_material_instance_parent(material,parent);lib.clear_all_material_instance_parameters(material)
        for kind,parameter in (("Diffuse","Base Color Map"),("Normal","Normal Map")):
            texture=textures[(row["slot"],kind)];lib.set_material_instance_texture_parameter_value(material,parameter,texture)
            actual=lib.get_material_instance_texture_parameter_value(material,parameter)
            if actual is None or actual.get_path_name()!=texture.get_path_name():raise RuntimeError("Skin source map setter readback failed")
        for parameter,value in plan["graph"]["scalars"].items():
            lib.set_material_instance_scalar_parameter_value(material,parameter,value)
            if abs(lib.get_material_instance_scalar_parameter_value(material,parameter)-value)>1e-5:raise RuntimeError("Skin scalar readback failed")
        lib.update_material_instance(material)
        if save and not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError("Cannot save unified skin instance")
        instances[row["slot"]]=material
    for slot in slots:
        name=str(slot.get_editor_property("material_slot_name"))
        if name not in instances:continue
        before=slot.get_editor_property("material_interface");material=instances[name]
        slot.set_editor_property("material_interface",material)
        records.append({"slot":name,"old_material":before.get_path_name() if before else None,"material":material.get_path_name(),
            "parent":parent.get_path_name(),"source_fingerprint":plan["source_fingerprint"],"json_path":plan["source_json"],
            "source_json_sha256":plan["source_json_sha256"],"normal":evidence[(name,"Normal")],"diffuse":evidence[(name,"Diffuse")],
            "graph":plan["graph"],"geometry_unchanged":True,"other_material_slots_unchanged":True})
    mesh.set_editor_property("materials",slots)
    if save and not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):raise RuntimeError("Cannot save unified source skin bindings")
    return records
