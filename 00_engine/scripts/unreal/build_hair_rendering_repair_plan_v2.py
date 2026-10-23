"""Build source-driven hair shader settings without copying another hairstyle's maps."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
EXPORT = Path(r"D:\UE\exports\character_creator\scalp_hair_batch_20260924_v1")
HEADER = Path(r"D:\UE\projects\datatry_02\Plugins\RLPlugin\Source\RLPlugin\Private\RLShaderData.h")


def build():
    old = json.loads((ROOT / "masked_repair_plan.json").read_text(encoding="utf-8"))
    header = HEADER.read_text(encoding="utf-8")
    section = header.split("g_kHairMap =", 1)[1].split("};", 1)[0]
    mapping = dict(re.findall(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}', section))
    mapping.update({"TangentMapFlipGreen": "Flip Tangent Y", "ActiveChangeHairColor": "Activate Hair Color"})
    sources = {}
    rows = []
    for row in old["rows"]:
        hair_id = row["hair_id"]
        if hair_id not in sources:
            source_path = next((EXPORT / (hair_id + "_F") / "fbx").glob("*.json"))
            document = json.loads(source_path.read_text(encoding="utf-8-sig"))
            actor = next(iter(next(iter(document.values()))["Object"].values()))
            materials = {}
            for mesh in actor["Meshes"].values():
                for name, material in mesh.get("Materials", {}).items():
                    key = name.lower()
                    if key in materials and materials[key] != material:
                        raise ValueError("Conflicting source material " + hair_id + " / " + name)
                    materials[key] = material
            sources[hair_id] = (source_path, materials)
        source_path, materials = sources[hair_id]
        source = materials[row["slot_name"].lower()]
        shader = source.get("Custom Shader", {})
        if any(image.get("Texture Path") for image in shader.get("Image", {}).values()):
            raise ValueError("Custom maps need explicit importing: " + hair_id + " / " + row["slot_name"])
        variables = shader.get("Variable", {})
        scalars = {"Increase Opacity Mask Min Value": 0.0, "Alpha Power": 1.0, "Alpha Multiplier": 1.0,
                   "Blend Strength": 0.0, "Glow Strength": 0.0, "Opacity": source.get("Opacity", 1.0),
                   "Opacity Strength": 1.0, "PixelDepthOffset": 0.0,
                   "Specular Strength": variables.get("Specular Strength", 0.0 if not shader else 0.5)}
        vectors = {"Base Color Tint": [value / 255.0 for value in source.get("Diffuse Color", [255.0] * 3)] + [1.0]}
        switches = {"Use Flow Map": False, "Use ORM Map": False, "Use Bump Map": False,
                    "Activate Hair Color": bool(variables.get("ActiveChangeHairColor", 0)),
                    "Flip Tangent Y": bool(variables.get("TangentMapFlipGreen", 0))}
        for cc_name, ue_name in mapping.items():
            if cc_name not in variables or ue_name in switches:
                continue
            value = variables[cc_name]
            if isinstance(value, list):
                vectors[ue_name] = [float(channel) / 255.0 for channel in value] + [1.0]
            else:
                scalars[ue_name] = float(value)
        # Exported base color already contains CC's dye; custom Root/ID maps are absent.
        # Reapplying dye with placeholder masks changes the baked colors a second time.
        switches["Activate Hair Color"] = False
        scalars["Vertex Color Strength"] = 0.0
        # Hair and scalp still share the verified shader; scalp has no dye/flow parameters.
        if not shader:
            scalars.update({"Roughness Multiplier": 1.0, "Specular Multiplier": 0.0, "Scatter": 0.0})
        rows.append({**row, "v2_material": row["new_material"] + "_StrandsV2",
                     "source_json": str(source_path), "scalars": scalars, "vectors": vectors, "switches": switches})
    return {"schema_version": 2, "parent": "/Game/CC_Shaders/HairShader/RL_Hair_Specular.RL_Hair_Specular",
            "source_mapping": str(HEADER), "source_mapping_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(),
            "slot_count": len(rows), "hair_count": len(sources), "rows": rows,
            "no_source_custom_flow_id_root_maps": True, "opacity_clip": 0.15}


if __name__ == "__main__":
    plan = build()
    output = ROOT / "rendering_repair_v2"
    output.mkdir(exist_ok=True)
    (output / "repair_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"hairs": plan["hair_count"], "slots": plan["slot_count"]}))
