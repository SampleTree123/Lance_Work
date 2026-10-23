"""Small offline fixtures for reference IDs, carriers, shoes and fixed clocks."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("tested_reference_plan_v11", SCRIPTS / "reference_plan_v11.py")
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


def fixture():
    catalog = {"sexes": {}}
    jobs = []
    for sex, identities, hairs in (("female", ("F1", "F2"), ("H1", "H2")), ("male", ("M1",), ("HM",))):
        mesh = lambda x: "/Game/" + x + "." + x
        asset = {"asset_id": sex + "_shirt", "slot": "shirts", "mesh_paths": [mesh(sex + "_shirt")]}
        shoe = {"asset_id": sex + "_shoe", "mesh_paths": [mesh(sex + "_shoe")]}
        domain = {"identities": [{"id": i, "skeleton": mesh(sex + "_skeleton"), "meshes": [{"path": mesh(i), "role": "body"}]} for i in identities],
                  "hairs": [{"hair_id": h, "fit": {"meshes": [{"path": mesh(h)}]}} for h in hairs],
                  "families": [{"family_id": sex + "_family", "groups": [{"group_id": "default", "slot_options": {"shirts": [asset]}, "required_assets": []}]}],
                  "shared_shoes": [shoe]}
        catalog["sexes"][sex] = domain
        for identity in identities:
            state = {"sex": sex, "identity": identity, "hair": hairs[0], "hair_color": "gold", "site": "S", "action": "A", "camera": "front_full", "aspect": "landscape",
                     "wardrobe": {"family_id": sex + "_family", "group_id": "default", "slot_choices": {"shirts": asset["asset_id"]}, "optional_asset_ids": [], "shared_shoe_id": shoe["asset_id"], "hair_id": None}}
            jid = f"train_node_{len(jobs):06d}"
            jobs.append({"job_id": jid, "split": "train", "node_id": len(jobs), "state": state,
                         "site": {"site_id": "S", "map": "/Game/S", "position": {"x": 0, "y": 0, "z": 0}, "yaw": 0},
                         "appearance": M.appearance(state, catalog), "camera_binding": {"shot_id": sex + "_A_front", "plan_path": "camera_plan.json"},
                         "motion": {"animation": mesh(sex + "_A"), "action_id": "A", "fps": 30, "frames": 300, "play_rate": 1, "start_frame": 0},
                         "width": 1920, "height": 1080, "fps": 30, "frames": 300})
    refs = [{"id": "ref_identity", "kind": "identity", "key": {}, "identity": "F1", "view": "front_face"}]
    variants = []
    for person in ("F1", "F2"):
        group = []
        for view in ("front", "back"):
            rid = "ref_hair_" + person + "_" + view; group.append(rid)
            refs.append({"id": rid, "kind": "hair", "key": {}, "hair_id": "H2", "carrier_identity": person,
                         "carrier_sex": "female", "hair_fit": {"meshes": [{"path": "/Game/H2.H2"}]}, "view": view})
        variants.append({"carrier_identity": person, "reference_ids": group, "views": ["front", "back"]})
    for view in ("front", "back"):
        refs.append({"id": "ref_shoe_" + view, "kind": "wardrobe_piece", "key": {}, "asset_id": "female_shoe", "slot": "shoes", "mesh_paths": ["/Game/female_shoe.female_shoe"], "view": view})
    refs.append({"id": "ref_scene", "kind": "scene", "key": {"symbolic_aspect": "landscape"}, "site_id": "S", "action_id": "A", "camera_id": "front_full", "sex": "female"})
    refs.append({"id": "ref_motion", "kind": "motion", "key": {"symbolic_aspect": "landscape"}, "action_id": "A", "camera_id": "front_full", "sex": "male",
                 "available_target_sex_action_variant": {"production10": {"asset": "/Game/male_A.male_A"}}})
    manifest = {"requirements": refs, "hair_reference_pools": [{"variants": variants}], "reference_links": [{"reference_ids": [r["id"] for r in refs]}]}
    profile = {"resolution": {"landscape": {"width": 1920, "height": 1080}, "portrait": {"width": 1080, "height": 1920}}}
    config = {"male": {"source_job_id": "train_node_000002"}}
    return jobs, manifest, profile, catalog, config


class Tests(unittest.TestCase):
    def test_shared_hair_framing_changes_only_hair_jobs_and_carriers(self):
        jobs, manifest, profile, catalog, config = fixture()
        args = (jobs, manifest, profile, catalog, config)
        before = copy.deepcopy(args)
        baseline = M.build_plan(*args, identity_portrait_variants=True, identity_hair_pool={"female": ["H1", "H2"]})
        clothing = {"female": {"choice": copy.deepcopy(jobs[0]["state"]["wardrobe"])}}
        result = M.build_plan(*args, identity_portrait_variants=True, identity_hair_pool={"female": ["H1", "H2"]},
                              shared_hair_framing=True, hair_carrier_clothing=clothing)
        self.assertEqual(args, before)
        self.assertEqual(result["bindings"], baseline["bindings"])
        self.assertEqual(result["reference_links"], baseline["reference_links"])
        self.assertEqual(result["effective_reference_links"], baseline["effective_reference_links"])
        self.assertEqual(result["motion"], baseline["motion"])
        self.assertEqual([j for j in result["static"] if j["reference_kind"] != "hair"],
                         [j for j in baseline["static"] if j["reference_kind"] != "hair"])
        carriers = {j["job_id"]: j for j in result["carriers"]}
        for job in result["static"]:
            if job["reference_kind"] != "hair": continue
            self.assertEqual(job["framing_policy"], "shared_head_shoulders")
            self.assertTrue(job["garments_present"] and job["neutral_garment_color"])
            source = carriers[job["source_job_id"]]
            self.assertEqual(source["state"]["hair"], source["state"]["wardrobe"]["hair_id"])
            self.assertEqual(source["appearance"]["hair"]["color"], "black")
            self.assertEqual(job["source_job_sha256"], hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest())
        adaptive = M.build_plan(*args, identity_portrait_variants=True, identity_hair_pool={"female": ["H1", "H2"]},
                                adaptive_hair_framing=True, hair_carrier_clothing=clothing)
        self.assertEqual(adaptive["carriers"], result["carriers"])
        self.assertEqual(adaptive["effective_reference_links"], result["effective_reference_links"])
        for adaptive_job, shared_job in zip(adaptive["static"], result["static"]):
            expected = copy.deepcopy(shared_job)
            if expected["reference_kind"] == "hair": expected["framing_policy"] = "adaptive_complete_hair"
            self.assertEqual(adaptive_job, expected)
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            M.build_plan(*args, shared_hair_framing=True, adaptive_hair_framing=True, hair_carrier_clothing=clothing)
        with self.assertRaisesRegex(ValueError, "explicit"):
            M.build_plan(*args, shared_hair_framing=True)
        clothing["female"]["choice"]["slot_choices"]["shirts"] = "not_in_group"
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            M.build_plan(*args, shared_hair_framing=True, hair_carrier_clothing=clothing)
        clothing["female"]["choice"] = copy.deepcopy(jobs[0]["state"]["wardrobe"])
        catalog["sexes"]["female"]["families"][0]["groups"][0]["slot_options"]["coats"] = []
        with self.assertRaisesRegex(ValueError, "missing required slots: coats"):
            M.build_plan(*args, shared_hair_framing=True, hair_carrier_clothing=clothing)

    def test_identity_pool_white_distinct_hairs_consistent_carriers_and_step_selection(self):
        jobs, manifest, profile, catalog, config = fixture()
        manifest["reference_links"] = [
            {"axis": "identity", "split": "train", "session_id": "one", "edit_round": 1, "reference_ids": ["ref_identity"]},
            {"axis": "identity", "split": "train", "session_id": "two", "edit_round": 1, "reference_ids": ["ref_identity"]},
            {"axis": "hair", "reference_ids": ["ref_hair_F1_front", "ref_hair_F1_back"]}]
        args = (jobs, manifest, profile, catalog, config)
        before = copy.deepcopy(args)
        result = M.build_plan(*args, identity_portrait_variants=True, identity_hair_pool={"female": ["H1", "H2"]})
        self.assertEqual(args, before)  # All adopted input states/graph bindings remain untouched.
        self.assertEqual(len(result["static"]), 9)
        pool = result["identity_reference_pools"][0]
        self.assertEqual({v["hair_id"] for v in pool["variants"]}, {"H1", "H2"})
        self.assertEqual(pool["logical_reference_id"], "ref_identity")
        self.assertIn("ref_identity", [v["reference_id"] for v in pool["variants"]])
        carriers = {j["job_id"]: j for j in result["carriers"]}
        for job in result["static"]:
            if job["reference_kind"] == "identity":
                source = carriers[job["source_job_id"]]
                self.assertEqual(source["state"]["identity"], "F1")
                self.assertEqual(source["state"]["hair"], job["hair_id"])
                self.assertEqual(source["state"]["wardrobe"]["hair_id"], job["hair_id"])
                self.assertEqual(source["state"]["hair_color"], "silver_white")
                self.assertEqual(source["appearance"]["hair"]["color"], "silver_white")
                self.assertFalse(job["garments_present"])
                self.assertEqual(job["framing_policy"], "tight_face_no_neck_or_shoulders")
        self.assertEqual(result["reference_links"], manifest["reference_links"])
        self.assertEqual(result["effective_reference_links"][-1], manifest["reference_links"][-1])
        valid = {v["reference_id"] for v in pool["variants"]}
        for link in result["effective_reference_links"][:2]:
            self.assertEqual(len(link["reference_ids"]), 1)
            self.assertIn(link["reference_ids"][0], valid)
            self.assertIsInstance(link["identity_reference_selection"]["selection_seed"], int)
        reordered = copy.deepcopy(manifest)
        reordered["reference_links"].reverse()
        again = M.build_plan(jobs, reordered, profile, catalog, config, True, {"female": ["H1", "H2"]})
        self.assertEqual(result["effective_reference_links"], list(reversed(again["effective_reference_links"])))
        baseline = M.build_plan(*args)
        self.assertEqual(result["motion"], baseline["motion"])
        self.assertEqual(result["hair_reference_pools"], baseline["hair_reference_pools"])
        self.assertEqual([b for b in result["bindings"] if b["kind"] != "identity"],
                         [b for b in baseline["bindings"] if b["kind"] != "identity"])

    def test_identity_pool_rejects_duplicate_or_incompatible_hairs(self):
        args = fixture()
        for pool in (["H1", "H1"], ["H1", "missing"]):
            with self.assertRaises(ValueError):
                M.build_plan(*args, identity_portrait_variants=True, identity_hair_pool={"female": pool})

    def test_ids_views_hair_whole_groups_shoes_and_source_hashes(self):
        args = fixture(); before = copy.deepcopy(args)
        result = M.build_plan(*args)
        self.assertEqual(len(result["static"]), 8)
        self.assertEqual(len(result["motion"]), 1)
        self.assertEqual(args, before)
        all_refs = result["static"] + result["motion"]
        self.assertEqual({j["reference_id"] for j in all_refs}, {r["id"] for r in args[1]["requirements"]})
        self.assertEqual(result["hair_reference_pools"], args[1]["hair_reference_pools"])
        self.assertEqual(result["reference_links"], args[1]["reference_links"])
        carriers = {j["job_id"]: j for j in result["carriers"]}
        for job in all_refs:
            expected = hashlib.sha256(json.dumps(carriers[job["source_job_id"]], sort_keys=True).encode()).hexdigest()
            self.assertEqual(job["source_job_sha256"], expected)
        scene = next(j for j in all_refs if j["reference_kind"] == "scene")
        self.assertEqual(scene["source_job_id"], "train_node_000000")
        self.assertEqual(carriers[scene["source_job_id"]], args[0][0])
        hair = [j for j in all_refs if j["reference_kind"] == "hair"]
        self.assertEqual(len({j["source_job_id"] for j in hair}), 2)
        for job in hair:
            self.assertEqual(carriers[job["source_job_id"]]["state"]["hair"], "H2")
            self.assertEqual(carriers[job["source_job_id"]]["state"]["hair_color"], "black")
        self.assertTrue(all(j["slot"] == "shoes" for j in all_refs if j["reference_kind"] == "garment"))
        motion = result["motion"][0]
        self.assertEqual((motion["fps"], motion["frames"], motion["phase_seconds"], motion["play_rate"]), (30, 300, 0, 1))

    def test_missing_motion_selection_is_blocked_and_bad_link_rejected(self):
        jobs, manifest, profile, catalog, config = fixture()
        result = M.build_plan(jobs, manifest, profile, catalog)
        self.assertEqual(result["motion"][0]["status"], "blocked_carrier_selection_pending")
        self.assertIsNone(result["motion"][0]["source_job_id"])
        manifest["reference_links"][0]["reference_ids"].append("ref_missing")
        with self.assertRaisesRegex(ValueError, "unknown reference"):
            M.build_plan(jobs, manifest, profile, catalog, config)

    def test_motion_fixed_selection_rebuilds_appearance(self):
        jobs, manifest, profile, catalog, config = fixture()
        config["male"]["selection"] = {"character_id": "M1", "sex": "male", "choice": jobs[2]["state"]["wardrobe"], "hair_color": "black", "face_id": "none"}
        config["male"]["selection"]["choice"]["hair_id"] = "HM"
        result = M.build_plan(jobs, manifest, profile, catalog, config)
        job = next(j for j in result["carriers"] if j.get("carrier_role") == "motion")
        self.assertEqual(job["state"]["identity"], "M1")
        self.assertEqual(job["appearance"]["hair"]["color"], "black")
        config["male"]["selection"]["sex"] = "female"
        with self.assertRaisesRegex(ValueError, "matching sex"):
            M.build_plan(jobs, manifest, profile, catalog, config)


if __name__ == "__main__": unittest.main()
