"""Regression checks for semantic skin maps, bounded roots and no color graph."""
import importlib.util
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location("skin_source_utils",Path(__file__).parents[1]/"ue_fixed_head_skin_texture_utils_v1.py")
utils=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(utils)
MESH="/Game/DataMake/CharacterFactory/FixedHeadHair_test_v1/Shared/Female/CombinedBase/Body.Body"


def sources(tmp_path):
    jp=tmp_path/"base.json";jp.write_text("{}")
    cc={}
    for role in utils.SKIN_ROLES:
        diffuse=tmp_path/(role+"_Diffuse.png");diffuse.write_bytes(b"diffuse-"+role.encode())
        normal=tmp_path/(role+"_Normal.png");normal.write_bytes(b"normal-"+role.encode())
        cc["Std_Skin_"+role+"_Pbr"]={"Textures":{"Base Color":{"Texture Path":diffuse.name},"Normal":{"Texture Path":normal.name}}}
    return jp,cc


def test_exact_source_map_semantics_and_direct_graph(tmp_path):
    jp,cc=sources(tmp_path)
    plan=utils.build_skin_source_plan(MESH,["Std_Tongue_Pbr",*utils.SKIN_SLOTS],cc,jp)
    assert len(plan["rows"])==4
    assert len({record["asset"] for row in plan["rows"] for record in row["textures"].values()})==8
    for row in plan["rows"]:
        normal=row["textures"]["Normal"];diffuse=row["textures"]["Diffuse"]
        assert normal["srgb"] is False and normal["compression"]=="TC_NORMALMAP" and normal["sampler"]=="NORMAL"
        assert diffuse["srgb"] is True and diffuse["compression"]=="TC_DEFAULT" and diffuse["sampler"]=="COLOR"
        assert Path(normal["source_file"]).name==row["role"]+"_Normal.png"
        assert Path(diffuse["source_file"]).name==row["role"]+"_Diffuse.png"
        assert normal["sha256"][:12] in normal["asset"]
    assert plan["graph"]["shading_model"]=="DEFAULT_LIT"
    assert plan["graph"]["connections"]=={"BASE_COLOR":"Base Color Map.RGB","NORMAL":"Normal Map.RGB","ROUGHNESS":"DM Skin Roughness","SPECULAR":"DM Skin Specular"}
    assert plan["graph"]["scalars"]=={"DM Skin Roughness":.6,"DM Skin Specular":.35}
    assert plan["graph"]["color_correction"] is False


def test_same_source_is_idempotent_changed_source_gets_new_assets(tmp_path):
    jp,cc=sources(tmp_path)
    a=utils.build_skin_source_plan(MESH,list(utils.SKIN_SLOTS),cc,jp)
    assert a==utils.build_skin_source_plan(MESH,list(utils.SKIN_SLOTS),cc,jp)
    (tmp_path/"Head_Normal.png").write_bytes(b"changed-normal-pixels")
    b=utils.build_skin_source_plan(MESH,list(utils.SKIN_SLOTS),cc,jp)
    assert a["root"]!=b["root"] and a["source_fingerprint"]!=b["source_fingerprint"]
    assert a["rows"][0]["textures"]["Normal"]["asset"]!=b["rows"][0]["textures"]["Normal"]["asset"]


def test_rejects_wrong_root_and_incomplete_skin_layout(tmp_path):
    jp,cc=sources(tmp_path)
    with pytest.raises(ValueError):utils.build_skin_source_plan("/Game/Characters/Body.Body",list(utils.SKIN_SLOTS),cc,jp)
    with pytest.raises(ValueError):utils.build_skin_source_plan(MESH,["Std_Skin_Head_Pbr"]*4,cc,jp)
    del cc["Std_Skin_Head_Pbr"]["Textures"]["Normal"]
    with pytest.raises(ValueError,match="Normal"):utils.build_skin_source_plan(MESH,list(utils.SKIN_SLOTS),cc,jp)


def test_rejects_texture_declaration_outside_exported_base(tmp_path):
    jp,cc=sources(tmp_path)
    cc["Std_Skin_Head_Pbr"]["Textures"]["Normal"]["Texture Path"]="../other_asset.png"
    with pytest.raises(ValueError,match="escapes"):utils.build_skin_source_plan(MESH,list(utils.SKIN_SLOTS),cc,jp)
