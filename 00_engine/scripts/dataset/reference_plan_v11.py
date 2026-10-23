"""Offline full v11 reference plan, preserving original reference IDs/views/groups.

Scene carriers retain adopted main job IDs/states. All other carriers are labeled
synthetic reference-only jobs. No UE import, candidate edits, or media claims.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import random
from pathlib import Path

import render_plan_v11 as base

DEFAULT_MAIN = "00_engine/outputs/dataset_texture_quality_20261023_v1/corrected/main_jobs.json"
DEFAULT_OUT = "00_engine/outputs/dataset_reference_production_20261023_v1"
IDENTITY_HAIR_POOL = {"female": ("HAIR_HB1_05", "HAIR_HB1_11"),
                      "male": ("HAIR_HB3_01", "HAIR_HB1_13")}
IDENTITY_SELECTION_SALT = "identity_white_two_hairs_20261023_v2"


def motion_carrier_note(config_path, out, count):
    if config_path:
        link = os.path.relpath(config_path, out).replace("\\", "/")
        carrier = f"男女固定载体的身份、服装、鞋、发型及颜色以当前[{Path(config_path).name}]({link})为唯一配置依据，不在本页硬编码资产组合"
    else:
        carrier = "男女固定载体尚未配置，动作任务明确阻塞，不以任意目标人物代替"
    return f"- 动作{count}项只使用原要求的组合和原production10资产。{carrier}。相机取对应既有orientation-specific binding，phase0、rate1，禁止再次慢放、循环或补hold。"


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def clone(value): return copy.deepcopy(value)


def scene_key(job):
    s = job["state"]
    return (s["site"], s["action"], s["camera"], s["sex"], s["aspect"])


def appearance(state, catalog):
    sex = catalog["sexes"][state["sex"]]
    identity = next(x for x in sex["identities"] if x["id"] == state["identity"])
    if state.get("hair"):
        hair = next(x for x in sex["hairs"] if x["hair_id"] == state["hair"])
        hair_record = {"hair_id": state["hair"], "fit": clone(hair["fit"]), "color": state["hair_color"]}
    else:
        hair_record = {"hair_id": None, "fit": {"meshes": []}, "color": "original"}
    wardrobe = state["wardrobe"]
    assets = {x["asset_id"]: x for x in base.walk(sex) if x.get("asset_id") and x.get("mesh_paths")}
    ids = list(wardrobe.get("slot_choices", {}).values()) + wardrobe.get("optional_asset_ids", [])
    if wardrobe.get("family_id"):
        family = next(x for x in sex["families"] if x["family_id"] == wardrobe["family_id"])
        group = next(x for x in family["groups"] if x["group_id"] == wardrobe["group_id"])
        ids += [x["asset_id"] if isinstance(x, dict) else x for x in group.get("required_assets", [])]
        ids += group.get("lock_required_asset_ids", [])
    if wardrobe.get("shared_shoe_id"): ids.append(wardrobe["shared_shoe_id"])
    return {"identity": {"character_id": state["identity"], "skeleton": identity["skeleton"], "meshes": clone(identity["meshes"])},
            "hair": hair_record, "wardrobe_assets": [{k: clone(assets[a][k]) for k in ("asset_id", "label", "slot", "mesh_paths") if k in assets[a]} for a in dict.fromkeys(ids)]}


def paths(job_id, clip=False):
    result = {"frames": f"jobs/{job_id}/frames", "receipt": f"jobs/{job_id}/media_receipt.json",
              "media": f"jobs/{job_id}/video.mp4" if clip else f"jobs/{job_id}/frames/frame_0000.png"}
    if clip: result["video"] = result["media"]
    return result


def carrier(source, job_id, role, overrides, catalog):
    job = clone(source)
    job.update(job_id=job_id, source_main_job_id=source["job_id"], source_split=source["split"],
               source_node_id=source["node_id"], reference_carrier=True, carrier_role=role,
               state_role="synthetic_reference_carrier_not_an_adopted_dataset_node", status="planned_not_rendered")
    job["state"].update(clone(overrides))
    job["appearance"] = appearance(job["state"], catalog)
    job["paths"] = paths(job_id, clip=True)
    # The descriptor remains source lineage. Canonical workers create a neutral
    # world and MUST NOT use the inherited source map/site transform as a stage.
    job["stage_policy"] = "neutral_stage; inherited site descriptor is lineage only"
    return job


def freeze_motion_config(config, sex, jobs_by_id, by_identity):
    if not config or sex not in config: return None
    value = config[sex]
    selection = value.get("selection")
    source_id = value.get("source_job_id")
    if source_id:
        source = jobs_by_id[source_id]
    elif selection:
        source = by_identity[selection["character_id"]][0]
    else:
        raise ValueError("Motion carrier requires source_job_id or a full selection: " + sex)
    if source["state"]["sex"] != sex: raise ValueError("Motion carrier source sex mismatch")
    overrides = {k: clone(source["state"][k]) for k in ("identity", "hair", "hair_color", "wardrobe")}
    if selection:
        if selection.get("sex", sex) != sex or selection.get("face_id", "none") != "none" or selection.get("eye_color", "original") != "original":
            raise ValueError("Motion carrier requires matching sex, face none and original eyes")
        overrides.update(identity=selection["character_id"], hair=selection["choice"].get("hair_id"),
                         hair_color=selection["hair_color"], wardrobe=clone(selection["choice"]))
    return {"source_job_id": source["job_id"], "overrides": overrides, "selection": clone(selection)}


def expand_identity_portraits(result, catalog, hair_pool=None):
    """Expand logical identity demands without changing the adopted graph/links.

    A selection is keyed by a step occurrence, including its original IDs, so
    reordering links or re-running the plan never changes a step's choice.
    """
    hair_pool = hair_pool or IDENTITY_HAIR_POOL
    carriers = {j["job_id"]: j for j in result["carriers"]}
    bindings = {b["reference_id"]: b for b in result["bindings"]}
    static, pools = [], []
    for original in result["static"]:
        if original["reference_kind"] == "hair":
            original["garments_present"] = False
        if original["reference_kind"] != "identity":
            static.append(original)
            continue
        old_carrier = carriers.pop(original["source_job_id"])
        sex = old_carrier["state"]["sex"]
        hairs = list(hair_pool[sex])
        if len(hairs) < 2 or len(set(hairs)) != len(hairs):
            raise ValueError("Identity hair pool requires at least two distinct hairstyles")
        available = {h["hair_id"] for h in catalog["sexes"][sex]["hairs"]}
        if not set(hairs).issubset(available):
            raise ValueError("Identity hair pool contains incompatible hairstyles: " + sex)
        pair_seed = int(canonical_hash([IDENTITY_SELECTION_SALT, original["target_identity"], "hair_pair"])[:16], 16)
        pair = random.Random(pair_seed).sample(hairs, 2)
        pool = {"identity": original["target_identity"], "sex": sex,
                "logical_reference_id": original["reference_id"], "hair_color": "silver_white",
                "hair_pair_seed": pair_seed, "variants": []}
        for index, hair_id in enumerate(pair, 1):
            rid = original["reference_id"] if index == 1 else "ref_" + canonical_hash([original["reference_id"], "identity_variant_2"])[:24]
            cid = old_carrier["job_id"] + f"_portrait_{index}"
            source = clone(old_carrier)
            source["job_id"] = cid
            source["state"].update(hair=hair_id, hair_color="silver_white")
            source["state"]["wardrobe"]["hair_id"] = hair_id
            source["appearance"] = appearance(source["state"], catalog)
            source["paths"] = paths(cid, clip=True)
            carriers[cid] = source
            job = clone(original)
            job.update(job_id=rid, reference_id=rid, logical_reference_id=original["reference_id"],
                       identity_variant=index, hair_id=hair_id, hair_color="silver_white", source_job_id=cid,
                       source_job_sha256=hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(),
                       garments_present=False, framing_policy="tight_face_no_neck_or_shoulders",
                       shoulders_present=False, neck_present=False, paths=paths(rid))
            static.append(job)
            binding = clone(bindings[original["reference_id"]])
            binding.update(reference_id=rid, job_id=rid, source_job_id=cid,
                           logical_reference_id=original["reference_id"], identity_variant=index,
                           media_path=job["paths"]["media"])
            # Keep the original binding available while creating the second.
            bindings[rid] = binding
            pool["variants"].append({"reference_id": rid, "job_id": rid, "identity_variant": index,
                                     "hair_id": hair_id, "hair_color": "silver_white"})
        pools.append(pool)
    by_logical = {p["logical_reference_id"]: p for p in pools}
    effective = []
    for link in result["reference_links"]:
        target = clone(link)
        if link.get("axis") == "identity":
            selected = []
            for rid in link["reference_ids"]:
                pool = by_logical[rid]
                seed = int(canonical_hash([IDENTITY_SELECTION_SALT, link])[:16], 16)
                variant = random.Random(seed).choice(pool["variants"])
                selected.append(variant["reference_id"])
                target["identity_reference_selection"] = {
                    "logical_reference_id": rid, "identity": pool["identity"],
                    "selection_seed": seed, "algorithm": "python_random_choice_v1",
                    "selected_reference_id": variant["reference_id"],
                    "identity_variant": variant["identity_variant"], "hair_id": variant["hair_id"]}
            if len(selected) != 1:
                raise ValueError("Each identity-edit step requires exactly one identity reference")
            target["original_reference_ids"] = clone(link["reference_ids"])
            target["reference_ids"] = selected
        effective.append(target)
    result.update(carriers=list(carriers.values()), static=static, bindings=list(bindings.values()),
                  identity_reference_pools=pools, effective_reference_links=effective,
                  identity_hair_pool=clone(hair_pool))
    return result


def apply_shared_hair_framing(result, catalog, clothing):
    """Use one head-relative camera policy and one simple wardrobe per sex."""
    if not clothing:
        raise ValueError("Shared hair framing requires explicit per-sex clothing choices")
    carriers = {j["job_id"]: j for j in result["carriers"]}
    changed = set()
    for job in result["static"]:
        if job["reference_kind"] != "hair": continue
        source = carriers[job["source_job_id"]]
        sex = source["state"]["sex"]
        choice = clone(clothing[sex]["choice"])
        domain = catalog["sexes"][sex]
        family = next(f for f in domain["families"] if f["family_id"] == choice["family_id"])
        group = next(g for g in family["groups"] if g["group_id"] == choice["group_id"])
        missing = set(group["slot_options"]) - set(choice["slot_choices"])
        if missing: raise ValueError("Hair carrier clothing is missing required slots: " + ", ".join(sorted(missing)))
        for slot, aid in choice["slot_choices"].items():
            allowed = {a["asset_id"] for a in group["slot_options"].get(slot, [])}
            if aid not in allowed: raise ValueError("Incompatible hair carrier clothing: " + sex + "/" + slot)
        if not (choice["slot_choices"].get("shirts") or choice["slot_choices"].get("full_body")):
            raise ValueError("Hair carrier clothing needs a covering top")
        choice["hair_id"] = job["hair_id"]
        if source["job_id"] not in changed:
            source["state"].update(wardrobe=choice, hair=job["hair_id"], hair_color="black")
            source["appearance"] = appearance(source["state"], catalog)
            changed.add(source["job_id"])
        job.update(framing_policy="shared_head_shoulders", garments_present=True, neutral_garment_color=True,
                   source_job_sha256=hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest())
    result["hair_carrier_clothing"] = clone(clothing)
    return result


def build_plan(main_jobs, manifest, profile, catalog, motion_carriers=None, identity_portrait_variants=False, identity_hair_pool=None,
               shared_hair_framing=False, hair_carrier_clothing=None, adaptive_hair_framing=False):
    if shared_hair_framing and adaptive_hair_framing:
        raise ValueError("Shared and adaptive hair framing are mutually exclusive")
    requirements = manifest["requirements"]
    ids = [r["id"] for r in requirements]
    if len(ids) != len(set(ids)): raise ValueError("Duplicate original reference IDs")
    by_id, by_identity, by_asset, by_scene, by_motion = {}, {}, {}, {}, {}
    for job in main_jobs:
        by_id[job["job_id"]] = job
        by_identity.setdefault(job["state"]["identity"], []).append(job)
        for asset in job["appearance"]["wardrobe_assets"]: by_asset.setdefault(asset["asset_id"], []).append(job)
        by_scene.setdefault(scene_key(job), []).append(job)
        s = job["state"]
        by_motion.setdefault((s["action"], s["camera"], s["sex"], s["aspect"]), []).append(job)
    fixed = {sex: freeze_motion_config(motion_carriers, sex, by_id, by_identity) for sex in ("female", "male")}
    carriers, static, motion, bindings = {}, [], [], []
    for req in requirements:
        rid, kind = req["id"], req["kind"]
        job = {"job_id": rid, "reference_id": rid, "requirement_kind": kind,
               "reference_kind": "garment" if kind == "wardrobe_piece" else kind,
               "source_jobs_path": "carrier_jobs.json", "main_jobs_path": "carrier_jobs.json",
               "requirement_key": clone(req["key"]), "fps": 30, "frames": 1,
               "status": "planned_not_rendered", "view": req.get("view"),
               "source_manifest_status": req.get("status"), "formal_reference_id_binding": True}
        cid = None
        if kind == "scene":
            aspect = req["key"]["symbolic_aspect"]
            key = (req["site_id"], req["action_id"], req["camera_id"], req["sex"], aspect)
            source = by_scene[key][0]; cid = source["job_id"]
            carriers.setdefault(cid, clone(source))
            job.update(width=source["width"], height=source["height"], stage="source_scene_without_character",
                       site=clone(source["site"]), camera_binding=clone(source["camera_binding"]),
                       exact_initial_camera_policy="prepare exact source main sequence; read frame-zero keys; remove character/followers on owned copy",
                       person_present=False, source_main_job_id=source["job_id"])
        elif kind == "identity":
            source = by_identity[req["identity"]][0]
            cid = "ref_carrier_identity_" + req["identity"]
            carriers.setdefault(cid, carrier(source, cid, kind, {}, catalog))
            job.update(target_identity=req["identity"], hair_id=source["state"]["hair"], render_view="front",
                       width=1024, height=1024, stage="neutral_static", face_id="none", pose_policy="static_imported_reference_pose")
        elif kind == "hair":
            source = next(x for x in by_identity[req["carrier_identity"]] if x["state"]["sex"] == req["carrier_sex"])
            cid = "ref_carrier_hair_" + canonical_hash([req["hair_id"], req["carrier_identity"], req["carrier_sex"]])[:20]
            carriers.setdefault(cid, carrier(source, cid, kind, {"hair": req["hair_id"], "hair_color": "black"}, catalog))
            expected = {x["path"] for x in req["hair_fit"]["meshes"]}
            actual = {x["path"] for x in carriers[cid]["appearance"]["hair"]["fit"]["meshes"]}
            if expected != actual: raise ValueError("Hair fit differs from original demand: " + rid)
            job.update(target_identity=req["carrier_identity"], carrier_identity=req["carrier_identity"],
                       carrier_sex=req["carrier_sex"], hair_id=req["hair_id"], hair_color="black", render_view=req["view"],
                       width=1024, height=1024, stage="neutral_static", face_id="none", pose_policy="static_imported_reference_pose")
        elif kind == "wardrobe_piece":
            source = by_asset[req["asset_id"]][0]
            actual = next(a for a in source["appearance"]["wardrobe_assets"] if a["asset_id"] == req["asset_id"])
            if set(actual["mesh_paths"]) != set(req["mesh_paths"]): raise ValueError("Item mesh set differs: " + rid)
            cid = "ref_carrier_garment_" + canonical_hash(req["asset_id"])[:20]
            carriers.setdefault(cid, carrier(source, cid, "garment", {}, catalog))
            job.update(asset_id=req["asset_id"], slot=req["slot"], mesh_paths=clone(req["mesh_paths"]),
                       width=1024, height=1024, stage="neutral_static", body_present=False, render_view=req["view"],
                       actual_item_is_all_listed_meshes=True, preserve_3d_shape=True)
        elif kind == "motion":
            aspect = req["key"]["symbolic_aspect"]
            key = (req["action_id"], req["camera_id"], req["sex"], aspect)
            source = by_motion[key][0]
            job.update(action_id=req["action_id"], camera_id=req["camera_id"], sex=req["sex"], aspect=aspect,
                       width=profile["resolution"][aspect]["width"], height=profile["resolution"][aspect]["height"],
                       fps=30, frames=300, duration_seconds=10, phase_seconds=0.0, play_rate=1.0,
                       stage="neutral_motion", motion=clone(source["motion"]), camera_binding=clone(source["camera_binding"]),
                       clock_binding="same existing production10 baked clip; start0 rate1 30fps 300frames; no retiming")
            if source["motion"]["animation"] != req["available_target_sex_action_variant"]["production10"]["asset"]:
                raise ValueError("Motion demand differs from main production10 clip: " + rid)
            frozen = fixed[req["sex"]]
            if frozen:
                cid = "ref_carrier_motion_" + rid.removeprefix("ref_")
                carriers[cid] = carrier(source, cid, kind, frozen["overrides"], catalog)
                carriers[cid]["fixed_carrier_source_job_id"] = frozen["source_job_id"]
                job.update(carrier_identity=frozen["overrides"]["identity"], carrier_status="fixed_selection_configured")
            else:
                job.update(status="blocked_carrier_selection_pending", carrier_identity=None, carrier_status="pending_explicit_female_male_selection")
        else:
            raise ValueError("Unknown original requirement kind: " + kind)
        job["source_job_id"] = cid
        job["source_job_sha256"] = hashlib.sha256(json.dumps(carriers[cid], sort_keys=True).encode()).hexdigest() if cid else None
        job["paths"] = paths(rid, clip=kind == "motion")
        (motion if kind == "motion" else static).append(job)
        bindings.append({"reference_id": rid, "job_id": rid, "kind": kind, "source_job_id": cid,
                         "job_manifest": "motion_reference_jobs.json" if kind == "motion" else "static_reference_jobs.json",
                         "media_path": job["paths"]["media"], "status": job["status"]})
    known = set(ids)
    for link in manifest["reference_links"]:
        if not set(link["reference_ids"]).issubset(known): raise ValueError("Step refers to an unknown reference ID")
    for pool in manifest["hair_reference_pools"]:
        variants = pool["variants"]
        if len(variants) != 2 or len({v["carrier_identity"] for v in variants}) != 2:
            raise ValueError("Existing hair group must retain two distinct carriers")
        for variant in variants:
            if not set(variant["reference_ids"]).issubset(known): raise ValueError("Hair group reference missing")
    result = {"carriers": list(carriers.values()), "static": static, "motion": motion, "bindings": bindings,
            "hair_reference_pools": clone(manifest["hair_reference_pools"]), "reference_links": clone(manifest["reference_links"]),
            "motion_carriers": fixed}
    if identity_portrait_variants: result = expand_identity_portraits(result, catalog, identity_hair_pool)
    if shared_hair_framing or adaptive_hair_framing:
        result = apply_shared_hair_framing(result, catalog, hair_carrier_clothing)
    if adaptive_hair_framing:
        for job in result["static"]:
            if job["reference_kind"] == "hair": job["framing_policy"] = "adaptive_complete_hair"
    return result


def motion_pilot(jobs):
    selected = []
    preferred_actions = ("MOTION_CAND_001", "ACT_M06_CHEER_HANDS_STEP_DANCE", "ACT_F03_AUDIENCE_01", "MOTION_CAND_020")
    for sex, aspect, moving in (("female", "landscape", False), ("male", "landscape", False),
                                ("female", "portrait", False), ("male", "portrait", True)):
        cameras = ("orbit_120", "orbit_360", "dolly_out_front", "dolly_in_front") if moving else ("front_full",)
        candidates = [j for j in jobs if j["status"] == "planned_not_rendered" and j["sex"] == sex and j["aspect"] == aspect and j["camera_id"] in cameras]
        if not candidates:
            if any(j["status"].startswith("blocked") for j in jobs): return []
            raise ValueError("Cannot choose demanded motion pilot: " + sex + "/" + aspect)
        selected.append(min(candidates, key=lambda j: (cameras.index(j["camera_id"]),
            preferred_actions.index(j["action_id"]) if j["action_id"] in preferred_actions else len(preferred_actions), j["job_id"])))
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-jobs", default=DEFAULT_MAIN)
    parser.add_argument("--candidate-root", default=base.DEFAULT_CANDIDATE)
    parser.add_argument("--profile", default=base.DEFAULT_PROFILE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--motion-carriers", help="JSON {female:{source_job_id,selection?},male:{...}}")
    parser.add_argument("--identity-portrait-variants", action="store_true", help="Two white-haired portraits per logical identity; deterministic per-step selection")
    framing_group = parser.add_mutually_exclusive_group()
    framing_group.add_argument("--shared-hair-framing", action="store_true", help="One head-relative hair camera policy for both sexes and fixed simple clothes")
    framing_group.add_argument("--adaptive-hair-framing", action="store_true", help="Fit actual complete hair bounds; short styles closer, long styles farther; simple gray clothes")
    parser.add_argument("--hair-carrier-clothing", help="JSON {female:{choice:...},male:{choice:...}} for shared hair framing")
    args = parser.parse_args(argv)
    if (args.shared_hair_framing or args.adaptive_hair_framing) and not args.hair_carrier_clothing:
        parser.error("Hair framing requires --hair-carrier-clothing")
    main_path, candidate, profile_path, out = map(base.local_path, (args.main_jobs, args.candidate_root, args.profile, args.out))
    manifest_path = candidate / "reference_manifest.json"
    manifest, profile = base.read_json(manifest_path), base.read_json(profile_path)
    catalog_path = base.local_path(next(x["path"] for x in manifest["inputs"] if base.portable_path(x["path"]).endswith("/catalog.json")))
    config_path = base.local_path(args.motion_carriers) if args.motion_carriers else None
    config = base.read_json(config_path) if config_path else None
    clothing_path = base.local_path(args.hair_carrier_clothing) if args.hair_carrier_clothing else None
    clothing = base.read_json(clothing_path) if clothing_path else None
    main_doc = base.read_json(main_path)
    result = build_plan(main_doc["jobs"], manifest, profile, base.read_json(catalog_path), config, args.identity_portrait_variants,
                        shared_hair_framing=args.shared_hair_framing, hair_carrier_clothing=clothing,
                        adaptive_hair_framing=args.adaptive_hair_framing)
    source_paths = [main_path, manifest_path, profile_path, catalog_path] + ([config_path] if config_path else []) + ([clothing_path] if clothing_path else [])
    common = {"schema": "dataset_reference_jobs_v11_v1", "path_base": "workspace", "output_path_base": "run_root",
              "offline_only": True, "media_generated": False, "source_manifest_unchanged": True,
              "static_presentation": profile.get("static_reference_presentation"),
              "sources": [{"path": base.portable_path(p), "sha256": base.sha256(p)} for p in source_paths]}
    if args.identity_portrait_variants:
        common["static_presentation"] = clone(common["static_presentation"] or {})
        common["static_presentation"].update(identity="two_white_different_hairstyles_tight_face_no_neck_or_shoulders; select_one_per_step",
                                              identity_garments_present=False, hair_garments_present=False,
                                              changes_to_existing_reference_views_or_counts=True)
    if args.shared_hair_framing or args.adaptive_hair_framing:
        common["static_presentation"] = clone(common["static_presentation"] or {})
        common["static_presentation"].update(hair="shared_head_shoulders_camera_parameters_both_sexes; most_hair_visible_not_forced_longest_complete; fixed_simple_gray_clothes",
                                              hair_garments_present=True, hair_neutral_garment_color=True)
        if args.adaptive_hair_framing:
            common["static_presentation"]["hair"] = "adaptive_complete_hair_bounds; short_closer_long_farther; fixed_simple_gray_clothes"
    if (args.identity_portrait_variants or args.shared_hair_framing or args.adaptive_hair_framing) and out.exists() and any(out.glob("*reference*jobs.json")):
        raise ValueError("Reference variant output already contains a plan; choose a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    def save(name, value): (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save("carrier_jobs.json", {**common, "schema": "dataset_render_jobs_v11_v1", "profile": profile, "job_count": len(result["carriers"]), "jobs": result["carriers"]})
    for name, key in (("static_reference_jobs.json", "static"), ("motion_reference_jobs.json", "motion")):
        save(name, {**common, "job_count": len(result[key]), "jobs": result[key]})
    all_jobs = result["static"] + result["motion"]
    save("reference_jobs.json", {**common, "job_count": len(all_jobs), "jobs": all_jobs})
    pilots = motion_pilot(result["motion"])
    save("motion_pilot_jobs.json", {**common, "job_count": len(pilots), "jobs": pilots,
         "selection_note": "demanded original IDs only; female/male x landscape/portrait; three front_full and one moving camera"})
    save("reference_bindings.json", {**common, "schema": "dataset_reference_bindings_v11_v1", "requirements": result["bindings"],
         "hair_reference_pools": result["hair_reference_pools"], "reference_links": result["reference_links"],
         **({k: result[k] for k in ("identity_reference_pools", "effective_reference_links", "identity_hair_pool")} if args.identity_portrait_variants else {}),
         "selection_policy": "use effective_reference_links for identity variants; reference_links retain source provenance; retain whole hair groups" if args.identity_portrait_variants else "retain original per-step IDs and whole hair group selection; do not select independent front/back carriers"})
    summary = {"schema": "dataset_reference_plan_summary_v11_v1", "original_reference_requirements": len(manifest["requirements"]),
               "static_images": len(result["static"]), "motion_clips": len(result["motion"]), "carrier_jobs": len(result["carriers"]),
               "motion_blocked": sum(j["status"].startswith("blocked") for j in result["motion"]),
               "original_reference_ids_preserved": True, "original_views_and_counts_preserved": True,
               "original_step_reference_bindings_preserved": True, "hair_carrier_groups": len(result["hair_reference_pools"]),
               "motion_carriers": result["motion_carriers"], "media_generated": False}
    if args.identity_portrait_variants:
        summary.update(identity_logical_requirements=len(result["identity_reference_pools"]),
                       identity_portraits=2 * len(result["identity_reference_pools"]),
                       total_reference_jobs=len(all_jobs), original_views_and_counts_preserved=False,
                       original_step_reference_bindings_preserved_as_provenance=True,
                       effective_identity_bindings="reference_bindings.json:effective_reference_links",
                       identity_selection_salt=IDENTITY_SELECTION_SALT)
        pilot = [j for j in result["static"] if j["reference_kind"] == "identity" and j["target_identity"] in ("CFD40_WF_002", "CFD40_AM_001")]
        pilot += [j for j in result["static"] if j["reference_id"] in
                  ("ref_0a619fb87cbf9d044a250173", "ref_ffda7f1e0282c093be77ae72")]
        save("portrait_pilot_jobs.json", {**common, "job_count": len(pilot), "jobs": pilot})
        save("identity_reference_pools.json", {**common, "identity_reference_pools": result["identity_reference_pools"]})
    if args.shared_hair_framing or args.adaptive_hair_framing:
        summary.update(hair_framing_policy="adaptive_complete_hair" if args.adaptive_hair_framing else "shared_head_shoulders", hair_reference_images=sum(j["reference_kind"] == "hair" for j in result["static"]),
                       hair_carrier_clothing_config=base.portable_path(clothing_path), hair_garments_present=True, hair_neutral_garment_color=True)
        hair_pilot = [j for j in result["static"] if j["reference_kind"] == "hair" and
                      ((j["carrier_identity"] == "CFD40_BM_001" and j["hair_id"] == "HAIR_HB3_02") or
                       (j["carrier_identity"] == "CFD40_LF_003" and j["hair_id"] == "HAIR_HB2_04"))]
        save("hair_framing_pilot_jobs.json", {**common, "job_count": len(hair_pilot), "jobs": hair_pilot,
             "selection_note": "adaptive complete hair, short closer long farther; simple gray clothes; male/female front/back" if args.adaptive_hair_framing else "same camera parameters for both sexes; male/female same-carrier front/back"})
    save("PLAN_SUMMARY.json", summary)
    readme = out / "PLAN_README.md"
    if args.identity_portrait_variants:
        readme.write_text(f"# 身份双发型参考离线计划\n\n本轮只写新目录；原配置图、主作业、原参考清单及旧运行不改写。尚未生成媒体。\n\n"
            f"- 总任务{len(all_jobs)}：静态{len(result['static'])}（其中身份{summary['identity_portraits']}，对应{summary['identity_logical_requirements']}人），动作{len(result['motion'])}；载体{len(result['carriers'])}。\n"
            "- 每人两种不同既有发型，统一正式白色silver_white。女性复用Large bun／Top knot long ponytail，男性复用Back-swept Top／Top knot samurai；不要求人物之间发型组合唯一。仅依据目录标签选择低遮脸候选，最终遮挡与构图待小样确认。\n"
            "- 身份任务garments_present=false、framing_policy=tight_face_no_neck_or_shoulders；头发任务garments_present=false，保持原黑色、两个载体和相机。渲染器需消费这些字段。\n"
            "- reference_bindings.json的reference_links逐项保留原来源；训练消费effective_reference_links，每条身份边只选一图，记录selection_seed和原reference_ids。非身份链接逐项保持。identity_reference_pools把原逻辑需求ID映射到两图，第一图沿用原ID，第二图稳定派生。\n"
            "- portrait_pilot_jobs.json含两位人物各两图，以及旧小样同一载体同款头发前后图。carrier_jobs.json在本目录，静态与动作任务source_jobs_path均相对本目录。\n"
            + motion_carrier_note(config_path, out, len(result["motion"]))
            + "\n\n重建时必须选择尚无计划的新输出目录，命令：\n\n```powershell\npython 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --motion-carriers 00_engine/outputs/dataset_reference_portraits_20261023_v2/motion_carriers.json --out 00_engine/outputs/dataset_reference_portraits_20261023_v2_rebuild\n```\n", encoding="utf-8")
    elif readme.is_file():
        note = motion_carrier_note(config_path, out, len(result["motion"]))
        lines = readme.read_text(encoding="utf-8").splitlines()
        readme.write_text("\n".join(note if line.startswith("- 动作") and "production10资产" in line else line for line in lines) + "\n", encoding="utf-8")
    if args.shared_hair_framing:
        text = readme.read_text(encoding="utf-8") if readme.is_file() else "# 发型统一构图离线计划\n"
        text = text.replace("头发任务garments_present=false，保持原黑色、两个载体和相机", "头发任务采用下方v3统一构图规则，保持原黑色和两个载体")
        text += ("\n## v3 发型统一构图\n\n发型任务framing_policy=shared_head_shoulders、garments_present=true、neutral_garment_color=true。男女相同头部相对相机参数，展示大部分发型（包括多数长发），不以最长发型完整入镜为硬条件；前后视角延续。简单衣物固定到各性别hair_carrier_clothing.json，灰色仅由拍摄副本覆盖材质，不改源几何。身份80图和809动作任务延续v2。hair_framing_pilot_jobs.json为男女各前后共4图，未生成媒体。\n\n"
                 "```powershell\npython 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --shared-hair-framing --hair-carrier-clothing 00_engine/outputs/dataset_reference_hair_framing_20261023_v3/hair_carrier_clothing.json --motion-carriers 00_engine/outputs/dataset_reference_hair_framing_20261023_v3/motion_carriers.json --out 00_engine/outputs/dataset_reference_hair_framing_20261023_v3_rebuild\n```\n")
        readme.write_text(text, encoding="utf-8")
    if args.adaptive_hair_framing:
        text = readme.read_text(encoding="utf-8") if readme.is_file() else "# 发型自适应构图离线计划\n"
        text = text.replace("头发任务garments_present=false，保持原黑色、两个载体和相机", "头发任务采用下方v4自适应构图，保持原黑色与两个载体")
        text += ("\n## v4 发型自适应完整取景\n\n112发型任务framing_policy=adaptive_complete_hair、garments_present=true、neutral_garment_color=true。相机以实际头发边界和紧凑头部代理自适应：短发靠近头部，长发后退保证完整，FOV28°、边距1.12，不设100cm距离下限；简单灰衣物延续v3合法配置。身份80图、809动作、所有参考ID与链接保持。hair_framing_pilot_jobs.json含男女各前后共4图，未生成媒体。\n\n"
                 "```powershell\npython 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --adaptive-hair-framing --hair-carrier-clothing 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/hair_carrier_clothing.json --motion-carriers 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/motion_carriers.json --out 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4_rebuild\n```\n")
        readme.write_text(text, encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "motion_carriers"}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
