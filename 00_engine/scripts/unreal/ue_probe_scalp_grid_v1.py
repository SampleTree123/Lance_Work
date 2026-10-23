"""Diagnose scalp grid artifacts with transient per-component controls only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ue_hair_sex_fit_review_v1 as review

ROOT = Path(globals().get("DM_SGP_ROOT", str(review.REVIEW_ROOT / "rendering_repair_v2/scalp_grid_diagnostic_20260930_v1/verified_controls"))).resolve()
CASES = globals().get("DM_SGP_CASES", [(4, "front"), (6, "front"), (15, "front_left")])
ALL_MODES = ("baseline", "scalp_hidden", "hair_cards_hidden", "hair_shadows_off", "scalp_force_opaque")
MODES = tuple(globals().get("DM_SGP_MODES", ALL_MODES))
INCLUDE_HAIRLINE = bool(globals().get("DM_SGP_INCLUDE_HAIRLINE", False))


def write(name, data):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def shader_audit():
    library = unreal.MaterialEditingLibrary
    parent = unreal.load_asset("/Game/CC_Shaders/HairShader/RL_Hair_Specular")
    root = library.get_material_property_input_node(parent, unreal.MaterialProperty.MP_OPACITY_MASK)
    visited = set()
    records = []
    def walk(node):
        if node is None or node.get_path_name() in visited:
            return
        visited.add(node.get_path_name())
        record = {"class": node.get_class().get_name(), "path": node.get_path_name()}
        if isinstance(node, unreal.MaterialExpressionMaterialFunctionCall):
            function = node.get_editor_property("material_function")
            record["function"] = function.get_path_name() if function else None
        try:
            record["parameter_name"] = str(node.get_editor_property("parameter_name"))
        except Exception:
            pass
        records.append(record)
        for child in library.get_inputs_for_material_expression(parent, node):
            walk(child)
    walk(root)
    write("shader_opacity_graph.json", {"parent": parent.get_path_name(), "opacity_root": root.get_path_name() if root else None,
                                       "nodes": records, "source_assets_modified": False})


def main():
    if not ROOT.is_relative_to(review.REVIEW_ROOT.resolve()):
        raise ValueError("Keep diagnostic evidence inside the hair review Run Root")
    if not MODES or any(mode not in ALL_MODES for mode in MODES):
        raise ValueError("Unknown scalp diagnostic control")
    if any(view not in review.VIEW_YAWS for _, view in CASES):
        raise ValueError("Unknown diagnostic view")
    if getattr(unreal, "_dm_hair_fit_cancel", None) or getattr(unreal, "_dm_scalp_probe_cancel", None):
        raise RuntimeError("Finish the active capture before diagnosing scalp materials")
    if ROOT.exists() and any(ROOT.glob("*.png")):
        raise FileExistsError("Keep the prior diagnostic evidence; select a new versioned run root before recapturing")
    shader_audit()
    review._load_level()
    plan = review._plan()
    rows = json.loads((review.REVIEW_ROOT / "rendering_repair_v2/repair_plan.json").read_text(encoding="utf-8"))["rows"]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera = review._spawn(unreal.SceneCapture2D, review.CAMERA_LOCATION, review.CAMERA_ROTATION, transient=True)
    capture = camera.get_component_by_class(unreal.SceneCaptureComponent2D)
    capture.set_editor_property("capture_every_frame", False)
    capture.set_editor_property("capture_on_movement", False)
    capture.set_editor_property("always_persist_rendering_state", True)
    capture.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property("show_flag_settings", [unreal.EngineShowFlagsSetting(show_flag_name=n, enabled=True)
                                                       for n in ("AntiAliasing", "TemporalAA", "PostProcessing")])
    capture.set_editor_property("fov_angle", 28.0)
    target = unreal.RenderingLibrary.create_render_target2d(world, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8,
                                                            unreal.LinearColor(.18, .18, .18, 1))
    capture.set_editor_property("texture_target", target)
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    previous_throttle = settings.get_editor_property("bThrottleCPUWhenNotForeground")
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    invisible = unreal.Material()
    invisible.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    invisible.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    invisible.set_editor_property("used_with_skeletal_mesh", True)
    zero = unreal.MaterialEditingLibrary.create_material_expression(invisible, unreal.MaterialExpressionConstant)
    zero.set_editor_property("r", 0.)
    unreal.MaterialEditingLibrary.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    unreal.MaterialEditingLibrary.recompile_material(invisible)
    steps = [(review._case(plan, index), view, mode) for index, view in CASES for mode in MODES]
    state = {"index": 0, "prepared": False, "frames": 0, "deadline": 0., "handle": None,
             "completed": [], "error": None}

    def report(done=False):
        write("probe_progress.json", {"done": done, "success": done and state["error"] is None,
                                      "error": state["error"], "completed": state["completed"], "expected": len(steps),
                                      "source_assets_modified": False, "at_utc": datetime.now(timezone.utc).isoformat(),
                                      "include_hairline_coverage": INCLUDE_HAIRLINE})

    def finish(error=None):
        state["error"] = error
        unreal.unregister_slate_post_tick_callback(state["handle"])
        actors.destroy_actor(camera)
        review._remove_body()
        settings.set_editor_property("bThrottleCPUWhenNotForeground", previous_throttle)
        report(True)
        if getattr(unreal, "_dm_scalp_probe_cancel", None) is finish:
            del unreal._dm_scalp_probe_cancel

    def tick(_delta):
        try:
            if state["index"] == len(steps):
                finish()
                return
            case, view, mode = steps[state["index"]]
            if not state["prepared"]:
                body = review._stage(case)
                body.set_actor_rotation(unreal.Rotator(yaw=review.VIEW_YAWS[view]), False)
                scalp_rows = [r for r in rows if r["hair_id"] == case["hair_id"] and
                              (r["slot_name"].lower().startswith("scalp") or
                               INCLUDE_HAIRLINE and r["slot_name"].lower().startswith("hairline"))]
                for comp in body.get_components_by_class(unreal.SkeletalMeshComponent):
                    mesh = comp.get_skeletal_mesh_asset()
                    if mesh is None or not comp.get_name().startswith("HairPart"):
                        continue
                    if mode == "hair_shadows_off":
                        comp.set_editor_property("cast_shadow", False)
                    scalp_indices = {r["slot_index"] for r in scalp_rows if r["mesh"] == mesh.get_path_name()}
                    if mode == "hair_cards_hidden":
                        for index in range(len(mesh.get_editor_property("materials"))):
                            if index not in scalp_indices:
                                comp.set_material(index, invisible)
                    for row in scalp_rows:
                        if mesh.get_path_name() != row["mesh"]:
                            continue
                        if mode == "scalp_hidden":
                            # Use a constant-zero mask: shader opacity parameters can have bypass branches.
                            comp.set_material(row["slot_index"], invisible)
                        elif mode == "scalp_force_opaque":
                            mid = comp.create_dynamic_material_instance(row["slot_index"])
                            mid.set_texture_parameter_value("Opacity Map", unreal.load_asset("/Game/CC_Shaders/SkinShader/Textures/Share/White"))
                capture.set_editor_property("camera_cut_this_frame", True)
                state.update(prepared=True, frames=0, deadline=time.monotonic()+1.)
                return
            state["frames"] += 1
            capture.capture_scene()
            if state["frames"] < 32 or time.monotonic() < state["deadline"]:
                return
            name = f"{case['review_index']:03d}_{case['hair_id']}_{view}_{mode}.png"
            unreal.RenderingLibrary.export_render_target(world, target, str(ROOT), name)
            state["completed"].append(name)
            state["index"] += 1
            state["prepared"] = False
            report()
        except Exception as exc:
            finish(f"{type(exc).__name__}: {exc}")
    report()
    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    unreal._dm_scalp_probe_cancel = finish
    print("SCALP_GRID_PROBE="+json.dumps({"started": True, "steps":len(steps), "root":str(ROOT)}))


main()
