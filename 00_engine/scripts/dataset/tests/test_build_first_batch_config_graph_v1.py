import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_first_batch_config_graph_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_graph", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def fake_hash(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def asset(asset_id, asset_type, sex="unisex", constraints=None):
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "sex_compatibility": sex,
        "source_ref": f"registry://fixture/{asset_id}",
        "content_sha256": fake_hash(asset_id),
        "version": "v1",
        "status": "frozen",
        "constraints": constraints or {},
    }


def make_source():
    assets = [
        asset("f02_average", "bodyfit", "female"),
        asset("m02_average", "bodyfit", "male"),
        asset("happy", "expression"),
        asset("scene_one", "scene"),
        asset("near", "camera"),
        asset("far", "camera"),
        asset("high", "camera"),
        asset("side", "camera"),
        asset("lighting_one", "lighting"),
        asset("anchor_one", "anchor"),
        asset("render_1440p30_5s_v1", "render_profile"),
    ]
    looks = []
    actions_by_sex = {}
    for sex, bodyfit, prefix in (
        ("female", "f02_average", "f"),
        ("male", "m02_average", "m"),
    ):
        identities = [f"identity_{prefix}{index}" for index in range(1, 5)]
        outfits = [f"outfit_{prefix}{index}" for index in range(1, 5)]
        actions = [f"action_{prefix}{index}" for index in range(1, 6)]
        actions_by_sex[sex] = actions
        assets.extend(asset(item, "identity", sex) for item in identities)
        assets.extend(asset(item, "outfit", sex) for item in outfits)
        assets.extend(
            asset(
                item,
                "action",
                sex,
                {
                    "root_motion_policy": "preserve_source_root_motion",
                    "face_policy": "replaceable",
                },
            )
            for item in actions
        )
        for identity_id in identities:
            for outfit_id in outfits:
                looks.append(
                    {
                        "look_id": f"look_{prefix}_{identity_id[-1]}_{outfit_id[-1]}",
                        "sex": sex,
                        "bodyfit_id": bodyfit,
                        "identity_id": identity_id,
                        "outfit_id": outfit_id,
                        "character_blueprint": (
                            f"/Game/Fixture/{sex}/{identity_id}/{outfit_id}/BP_Look"
                        ),
                    }
                )
    return {
        "schema_version": "config_graph_v1",
        "manifest_type": "first_batch_source_manifest",
        "sampling_spec_version": "multi_round_v1_20260824",
        "source_manifest_id": "fixture_source_20260824_v1",
        "batch_id": "fixture_batch_v1",
        "status": "frozen",
        "production_mode": "full_pool",
        "expected_domain_count": 2,
        "expected_nodes": 640,
        "expected_chains": 4000,
        "expected_render_jobs": 640,
        "input_manifest_sha256": fake_hash("fixture_inputs"),
        "assets": assets,
        "looks": looks,
        "actions_by_sex": actions_by_sex,
        "expression_ids": ["happy"],
        "expression_policy": {
            "fixed_expression_id": "happy",
            "editable_feature": False,
            "edit_axis": None,
        },
        "scene_binding": {
            "scene_id": "scene_one",
            "lighting_id": "lighting_one",
            "anchor_id": "anchor_one",
            "camera_ids": {
                "near": "near",
                "far": "far",
                "high": "high",
                "side": "side",
            },
        },
        "render_profile": {
            "render_profile_id": "render_1440p30_5s_v1",
            "fps": 30,
            "frame_start": 0,
            "duration_frames": 150,
            "resolution": {"width": 2560, "height": 1440},
            "sequence_asset": "/Game/DataMake/Sequences/LS_FirstBatch",
            "seed": 0,
        },
        "chain_plan": {
            "quota_matrix": {
                domain: {
                    policy: {str(length): count for length, count in lengths.items()}
                    for policy, lengths in policies.items()
                }
                for domain, policies in SUBJECT.DEFAULT_CHAIN_QUOTAS.items()
            },
            "sampler_seed": 20260824,
            "axis_share_tolerance": 0.02,
        },
    }


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def report_domain_counts(nodes):
    counts = {}
    for node in nodes:
        domain_id = node["compatibility_domain_id"]
        counts[domain_id] = counts.get(domain_id, 0) + 1
    return counts


class FirstBatchConfigGraphTests(unittest.TestCase):
    def build(self, root, source=None):
        source = source or make_source()
        root.mkdir(parents=True, exist_ok=True)
        source_path = root / "source.json"
        source_path.write_text(json.dumps(source), encoding="utf-8")
        output = root / "output"
        report = SUBJECT.build_graph(source_path, output)
        return output, report

    def test_builds_exact_first_batch_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            output, report = self.build(Path(raw))
            self.assertEqual(640, report["counts"]["nodes"])
            self.assertEqual(8320, report["counts"]["edges"])
            self.assertEqual(4000, report["counts"]["chains"])
            self.assertEqual(640, report["counts"]["render_jobs"])
            self.assertEqual(
                {"3": 1667, "4": 1666, "5": 667},
                {
                    str(key): value
                    for key, value in report["chain_report"]["length_counts"].items()
                },
            )
            self.assertEqual(
                {"freeform_walk": 2000, "progressive_shortest": 2000},
                report["chain_report"]["policy_counts"],
            )
            self.assertEqual(
                {"female_v1": 2000, "male_v1": 2000},
                report["chain_report"]["domain_counts"],
            )
            self.assertEqual(640, report["chain_report"]["referenced_node_count"])
            self.assertEqual(
                {"E1": 3750, "E2": 3750, "E3": 3750, "E7": 3750},
                report["chain_report"]["axis_counts"],
            )
            self.assertEqual(
                {"E1": 0.25, "E2": 0.25, "E3": 0.25, "E7": 0.25},
                report["chain_report"]["axis_shares"],
            )
            self.assertEqual(640, len(read_jsonl(output / "nodes.jsonl")))
            self.assertEqual(4000, len(read_jsonl(output / "chains.jsonl")))

    def test_nodes_domains_and_edges_match_happy_only_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            output, _ = self.build(Path(raw))
            nodes = {item["node_id"]: item for item in read_jsonl(output / "nodes.jsonl")}
            edges = read_jsonl(output / "edges.jsonl")
            domains = read_json(output / "compatibility_domains.json")["domains"]
            self.assertEqual(
                {"female_v1", "male_v1"},
                {item["compatibility_domain_id"] for item in domains},
            )
            self.assertEqual(
                {"happy"},
                {node["config"]["expression_id"] for node in nodes.values()},
            )
            self.assertEqual(
                {"near", "far", "high", "side"},
                {node["config"]["camera_id"] for node in nodes.values()},
            )
            self.assertEqual(
                {"female_v1": 320, "male_v1": 320},
                report_domain_counts(nodes.values()),
            )
            edge_ids = {item["edge_id"] for item in edges}
            for edge in edges:
                SUBJECT.validate_atomic_edge(edge, nodes)
                self.assertIn(edge["inverse_edge_id"], edge_ids)
                self.assertIn(edge["edge_type"], {"E1", "E2", "E3", "E7"})
                self.assertEqual(
                    SUBJECT.EDIT_FIELDS[edge["edge_type"]], edge["edit_axis"]
                )

    def test_chain_policies_and_fact_labels_recompute(self):
        with tempfile.TemporaryDirectory() as raw:
            output, _ = self.build(Path(raw))
            nodes = {item["node_id"]: item for item in read_jsonl(output / "nodes.jsonl")}
            chains = read_jsonl(output / "chains.jsonl")
            for chain in chains:
                facts = SUBJECT.semantic_facts(
                    chain["node_ids"], chain["edge_axes"], nodes
                )
                for key, value in facts.items():
                    self.assertIs(value, chain[key])
                if chain["chain_policy"] == "progressive_shortest":
                    self.assertIn(chain["edit_length"], (3, 4))
                    self.assertEqual(
                        len(chain["edge_axes"]), len(set(chain["edge_axes"]))
                    )
                    self.assertTrue(chain["is_semantic_shortest"])
                    self.assertFalse(chain["has_rollback"])
                    self.assertFalse(chain["returns_to_start"])

    def test_quota_matrix_is_exact_and_freeform_facts_are_reported(self):
        with tempfile.TemporaryDirectory() as raw:
            _, report = self.build(Path(raw))
            quota_counts = report["chain_report"]["quota_counts"]
            self.assertEqual(
                500, quota_counts["female_v1/progressive_shortest/length_3"]
            )
            self.assertEqual(
                500, quota_counts["female_v1/progressive_shortest/length_4"]
            )
            self.assertEqual(334, quota_counts["female_v1/freeform_walk/length_3"])
            self.assertEqual(333, quota_counts["female_v1/freeform_walk/length_4"])
            self.assertEqual(333, quota_counts["female_v1/freeform_walk/length_5"])
            self.assertEqual(333, quota_counts["male_v1/freeform_walk/length_3"])
            self.assertEqual(333, quota_counts["male_v1/freeform_walk/length_4"])
            self.assertEqual(334, quota_counts["male_v1/freeform_walk/length_5"])
            self.assertIn(
                "has_repeated_axis",
                report["chain_report"]["freeform_fact_true_counts"],
            )

    def test_same_source_produces_identical_graph_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = make_source()
            first, _ = self.build(root / "first", source)
            second, _ = self.build(root / "second", source)
            for name in (
                "compatibility_domains.json",
                "nodes.jsonl",
                "edges.jsonl",
                "chains.jsonl",
                "render_jobs.jsonl",
            ):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_rejects_old_contract_and_unportable_asset_reference(self):
        with tempfile.TemporaryDirectory() as raw:
            source = make_source()
            source["expression_ids"] = ["happy", "angry", "sad"]
            with self.assertRaises(SUBJECT.ConfigGraphError):
                self.build(Path(raw) / "old_expression_contract", source)

            source = make_source()
            source["render_profile"]["resolution"] = {"width": 1280, "height": 720}
            with self.assertRaises(SUBJECT.ConfigGraphError):
                self.build(Path(raw) / "old_render_contract", source)

            source = make_source()
            source["assets"][0]["source_ref"] = r"D:\private\asset.ccProject"
            with self.assertRaises(SUBJECT.ConfigGraphError):
                self.build(Path(raw) / "absolute", source)


if __name__ == "__main__":
    unittest.main()
