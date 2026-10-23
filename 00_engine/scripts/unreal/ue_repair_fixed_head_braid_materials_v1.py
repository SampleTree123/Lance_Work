"""Repair source-declared RLHair slots omitted by historical card-only repair.

UE globals: DM_BRAID_REPAIR_MODE=plan|preview|restore_preview|apply|rollback;
DM_BRAID_REPAIR_HAIR_IDS optional list. Preview only overrides visible manual
review actors; apply saves exact mesh slot bindings. Existing materials/textures
are retained. Rollback restores old slots from the durable journal.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import traceback
from datetime import datetime,timezone
from pathlib import Path
import unreal

REPO=Path(__file__).resolve().parents[3]
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0,str(Path(__file__).parent))
from hair_source_shader_v1 import create_material,is_rl_hair,is_ornament_slot,shader_settings

UE_SOURCE_ROOT="/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1"
UE_TARGET_ROOT="/Game/DataMake/CharacterFactory/MaterialRemediation_20261005_v1/Hair"
OUT=REPO/"00_engine/outputs/unreal_character_import/fixed_head_material_repair_20261005_v1/hair"
IMPORT_REPORT=REPO/"00_engine/outputs/unreal_character_import/fixed_head_hair_20261004_v1/import_report.json"
LEGACY_PARENT="/InterchangeAssets/Materials/FBXLegacyPhongSurfaceMaterial.FBXLegacyPhongSurfaceMaterial"
REVIEW_MAP="/Game/DataMake/Validation/FixedHeadHair/L_DM_FixedHeadHair_ManualReview_v001"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    temp.replace(path)


def path(asset):
    return asset.get_path_name() if asset else None


def token(value):
    return re.sub(r"[^A-Za-z0-9_]","_",value).casefold()


def plan():
    result=[]
    imported=read(IMPORT_REPORT)
    for case in imported["records"]:
        jp=Path(case["source_json"]);source=read(jp)
        actor=next(iter(next(iter(source.values()))["Object"].values()))
        by_slot={}
        for mesh in actor["Meshes"].values():
            for slot,material in mesh.get("Materials",{}).items():
                key=token(slot)
                if key in by_slot and by_slot[key]!=material:
                    raise RuntimeError("Ambiguous source slot "+slot)
                by_slot[key]=material
        for mesh in case["meshes"]:
            for index,(slot,binding) in enumerate(zip(mesh["slot_names"],mesh["materials"])):
                # Old report remains immutable. Only legacy source-declared hair
                # becomes a repair target; covered cards and ornaments stay intact.
                if not binding.startswith("/Game/DataMake/CharacterFactory/Hair/"):
                    continue
                cc=by_slot.get(token(slot))
                if cc is None or not is_rl_hair(cc) or is_ornament_slot(slot):
                    continue
                legacy=unreal.load_asset(binding)
                if legacy is None or path(legacy.get_editor_property("parent"))!=LEGACY_PARENT:
                    raise RuntimeError("Historical material parent changed "+binding)
                target=UE_TARGET_ROOT+"/"+case["hair_id"].removeprefix("HAIR_")+"/"+case["sex"].title()
                target+="/Materials/MI_"+re.sub(r"[^A-Za-z0-9_]","_",slot)+"_BraidStrandsV1"
                result.append({"hair_id":case["hair_id"],"sex":case["sex"],"mesh":mesh["path"],"slot_index":index,
                    "slot_name":slot,"before":binding,"target":target,"source_json":str(jp),
                    "source_json_sha256":hashlib.sha256(jp.read_bytes()).hexdigest(),"source_material":cc,
                    "texture_root":target.split("/Materials/",1)[0]+"/Textures","settings":shader_settings(cc)})
    if len(result)!=24 or len({r["hair_id"] for r in result})!=5:
        raise RuntimeError("Unexpected source-declared omitted hair scope "+str(len(result)))
    return result


def validate(row):
    if not row["mesh"].startswith(UE_SOURCE_ROOT+"/Hair/"):
        raise RuntimeError("Mesh outside fixed-head library")
    mesh=unreal.load_asset(row["mesh"])
    if not isinstance(mesh,unreal.SkeletalMesh):
        raise RuntimeError("Missing fixed-head hair mesh")
    slots=list(mesh.get_editor_property("materials"));slot=slots[row["slot_index"]]
    if token(str(slot.get_editor_property("material_slot_name")))!=token(row["slot_name"]):
        raise RuntimeError("Changed slot layout")
    if path(slot.get_editor_property("material_interface")) not in (row["before"],row["target"]+"."+row["target"].rsplit("/",1)[1]):
        raise RuntimeError("Unexpected current material binding")
    return mesh


def restore_preview():
    journal_path=OUT/"hair_preview_journal.json"
    if not journal_path.is_file():
        return {"restored":0}
    journal=read(journal_path);restored=0
    actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors={a.get_path_name():a for a in actor_sub.get_all_level_actors()}
    for rec in journal.get("actors",[]):
        a=all_actors.get(rec["actor"])
        if a is None:
            continue
        c=a.get_component_by_class(unreal.SkeletalMeshComponent)
        if c is None or path(c.get_editor_property("skeletal_mesh"))!=rec["mesh"]:
            continue
        c.set_editor_property("override_materials",[unreal.load_asset(m) if m else None for m in rec["before"]]);restored+=1
    journal["restored_at_utc"]=datetime.now(timezone.utc).isoformat();write(journal_path,journal)
    return {"restored":restored}


def run():
    mode=globals().get("DM_BRAID_REPAIR_MODE","plan")
    selected=set(globals().get("DM_BRAID_REPAIR_HAIR_IDS") or [])
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    result={"mode":mode,"success":False,"at_utc":datetime.now(timezone.utc).isoformat(),"records":[]}
    try:
        if mode=="restore_preview":
            result.update(restore_preview());result["success"]=True
        elif mode=="rollback":
            journal=read(OUT/"hair_apply_journal.json")
            for row in journal["rows"]:
                if selected and row["hair_id"] not in selected:
                    continue
                mesh=validate(row);slots=list(mesh.get_editor_property("materials"))
                slots[row["slot_index"]].set_editor_property("material_interface",unreal.load_asset(row["before"]))
                mesh.set_editor_property("materials",slots)
                if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):
                    raise RuntimeError("Rollback save failed")
                result["records"].append({"mesh":row["mesh"],"slot_index":row["slot_index"],"restored":row["before"]})
            result["success"]=True
        else:
            if mode not in ("plan","preview","apply"):
                raise ValueError("Unsupported braid repair mode")
            rows=plan()
            if selected:
                if selected-set(r["hair_id"] for r in rows):
                    raise ValueError("Unknown braid repair hair ID")
                rows=[r for r in rows if r["hair_id"] in selected]
            if mode=="preview" and not selected:
                raise ValueError("Preview requires an explicit hair ID")
            for row in rows:
                validate(row)
            write(OUT/("hair_plan_"+stamp+".json"),{"rows":rows,"bindings":len(rows)})
            if mode=="plan":
                result.update(success=True,bindings=len(rows),hair_ids=sorted({r["hair_id"] for r in rows}))
            else:
                materials={}
                for row in rows:
                    material,record=create_material(row["source_material"],row["source_json"],row["target"],row["texture_root"],row["slot_name"])
                    materials[(row["mesh"],row["slot_index"])]=material
                    result["records"].append({"mesh":row["mesh"],"slot_index":row["slot_index"],"before":row["before"],"hair_id":row["hair_id"],"sex":row["sex"],**record})
                if mode=="apply":
                    jp=OUT/"hair_apply_journal.json"
                    journal=read(jp) if jp.exists() else {"rows":[]}
                    existing={(r["mesh"],r["slot_index"]) for r in journal["rows"]}
                    journal["rows"].extend(r for r in rows if (r["mesh"],r["slot_index"]) not in existing)
                    write(jp,journal)  # Durable before any mesh rebinding.
                    restore_preview()
                    meshes={r["mesh"]:validate(r) for r in rows}
                    for mp,mesh in meshes.items():
                        slots=list(mesh.get_editor_property("materials"))
                        for row in [r for r in rows if r["mesh"]==mp]:
                            slots[row["slot_index"]].set_editor_property("material_interface",materials[(mp,row["slot_index"])])
                        mesh.set_editor_property("materials",slots)
                        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):
                            raise RuntimeError("Cannot save repaired braid mesh binding")
                else:
                    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
                    if world.get_path_name().split(".",1)[0]!=REVIEW_MAP:
                        raise RuntimeError("Preview only supports the manual review map")
                    restore_preview()
                    changed=[]
                    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
                        if not a.get_actor_label().startswith("DM_FHMR_"):
                            continue
                        c=a.get_component_by_class(unreal.SkeletalMeshComponent)
                        if c is None:
                            continue
                        mp=path(c.get_editor_property("skeletal_mesh"))
                        own=[r for r in rows if r["mesh"]==mp]
                        if not own:
                            continue
                        changed.append({"actor":a.get_path_name(),"mesh":mp,"before":[path(m) for m in c.get_editor_property("override_materials")]})
                        write(OUT/"hair_preview_journal.json",{"actors":changed})
                        for row in own:
                            c.set_material(row["slot_index"],materials[(mp,row["slot_index"])])
                    if not changed:
                        raise RuntimeError("No selected braid meshes currently visible; load the selected hair in manual review first")
                    result["preview_actors"]=len(changed)
                result["success"]=True
    except Exception:
        result["error"]=traceback.format_exc()
    write(OUT/("hair_"+mode+"_"+stamp+".json"),result)
    write(OUT/("hair_"+mode+"_latest.json"),result)
    print("DM_BRAID_REPAIR="+json.dumps({"success":result["success"],"mode":mode,"records":len(result["records"]),"report":str(OUT/("hair_"+mode+"_latest.json")),"error":result.get("error")},ensure_ascii=False))
    if not result["success"]:
        raise RuntimeError("Braid repair failed; inspect precise report")
    return result


if globals().get("DM_BRAID_REPAIR_RUN",True):
    run()
