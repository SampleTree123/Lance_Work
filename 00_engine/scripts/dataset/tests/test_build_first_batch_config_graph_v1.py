import hashlib
import importlib.util
import json
from pathlib import Path
import sys
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


def make_source(chain_total=400):
    assets = [
        asset("f02_average", "bodyfit", "female"),
        asset("m02_average", "bodyfit", "male"),
        asset("happy", "expression"),
        asset("angry", "expression"),
        asset("sad", "expression"),
        asset("scene_one", "scene"),
        asset("camera_medium", "camera"),
        asset("camera_full_body", "camera"),
        asset("lighting_one", "lighting"),
        asset("anchor_one", "anchor"),
    ]
    looks = []
    actions_by_sex = {}
    for sex, bodyfit, prefix in (
        ("female", "f02_average", "f"),
        ("male", "m02_average", "m"),
    ):
        identities = [f"identity_{prefix}{index}" for index in range(1, 5)]
        outfits = [f"outfit_{prefix}{index}" for index in range(1, 5)]
        actions = [f"action_{prefix}{index}" for index in range(1, 7)]
        actions_by_sex[sex] = actions
        assets.extend(asset(item, "identity", sex) for item in identities)
        assets.extend(asset(item, "outfit", sex) for item in outfits)
        assets.extend(
            asset(
                item,
                "action",
                sex,
                {"root_motion_policy": "in_place", "face_policy": "replaceable"},
            )
            for item in actions
        )
        for index, identity_id in enumerate(identities):
            for outfit_id in (outfits[index], outfits[(index + 1) % 4]):
                looks.append(
                    {
                        "look_id": f"look_{prefix}_{identity_id[-1]}_{outfit_id[-1]}",
                        "sex": sex,
                        "bodyfit_id": bodyfit,
                        "identity_id": identity_id,
                        "outfit_id": outfit_id,
                    }
                )
    return {
        "schema_version": "first_batch_graph_source_v1",
        "batch_id": "fixture_batch_v1",
        "status": "frozen",
        "assets": assets,
        "looks": looks,
        "actions_by_sex": actions_by_sex,
        "expression_roles": {
            "happy": "happy",
            "angry": "angry",
            "sad": "sad",
        },
        "scene_binding": {
            "scene_id": "scene_one",
            "lighting_id": "lighting_one",
            "anchor_id": "anchor_one",
            "camera_ids": {
                "medium": "camera_medium",
                "full_body": "camera_full_body",
            },
        },
        "render_profile": {
            "render_profile_id": "render_720p_3s_v1",
            "fps": 24,
            "duration_frames": 72,
            "resolution": {"width": 1280, "height": 720},
            "sequence_asset": "/Game/DataMake/Sequences/LS_FirstBatch",
            "seed": 0,
        },
        "chain_plan": {
            "length_counts": {
                "3": chain_total // 4,
                "4": chain_total // 2,
                "5": chain_total // 4,
            },
            "class_ratios": {
                "progressive": 0.70,
                "rollback": 0.20,
                "closed_cycle": 0.10,
            },
            "sampling_seed": 20260820,
        },
    }


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class FirstBatchConfigGraphTests(unittest.TestCase):
    def build(self, root, source=None):
        source = source or make_source()
        root.mkdir(parents=True, exist_ok=True)
        source_path = root / "source.json"
        source_path.write_text(json.dumps(source), encoding="utf-8")
        output = root / "output"
        report = SUBJECT.build_graph(source_path, output)
        return output, report

    def test_builds_384_nodes_and_requested_chains(self):
        with tempfile.TemporaryDirectory() as raw:
            output, report = self.build(Path(raw))
            self.assertEqual(384, report["counts"]["nodes"])
            self.assertEqual(400, report["counts"]["chains"])
            self.assertEqual(384, report["counts"]["render_jobs"])
            self.assertEqual(
                {"3": 100, "4": 200, "5": 100},
                {str(key): value for key, value in report["chain_report"]["length_counts"].items()},
            )
            self.assertEqual(
                {"closed_cycle": 40, "progressive": 280, "rollback": 80},
                report["chain_report"]["class_counts"],
            )
            self.assertEqual(384, len(read_jsonl(output / "nodes.jsonl")))

    def test_full_4000_chain_target_and_axis_coverage(self):
        with tempfile.TemporaryDirectory() as raw:
            output, report = self.build(Path(raw), make_source(chain_total=4000))
            chain_report = report["chain_report"]
            self.assertEqual(4000, report["counts"]["chains"])
            self.assertEqual(
                {"closed_cycle": 400, "progressive": 2800, "rollback": 800},
                chain_report["class_counts"],
            )
            self.assertTrue(
                all(value >= 0.10 for value in chain_report["axis_shares"].values())
            )
            self.assertGreaterEqual(chain_report["axis_shares"]["E1"], 0.15)
            self.assertGreaterEqual(chain_report["axis_shares"]["E2"], 0.15)
            self.assertEqual(4000, len(read_jsonl(output / "chains.jsonl")))

    def test_all_edges_are_atomic_and_have_inverses(self):
        with tempfile.TemporaryDirectory() as raw:
            output, _ = self.build(Path(raw))
            nodes = {item["node_id"]: item for item in read_jsonl(output / "nodes.jsonl")}
            edges = read_jsonl(output / "edges.jsonl")
            edge_ids = {item["edge_id"] for item in edges}
            for edge in edges:
                SUBJECT.validate_atomic_edge(edge, nodes)
                self.assertIn(edge["inverse_edge_id"], edge_ids)

    def test_chain_classes_obey_path_contracts(self):
        with tempfile.TemporaryDirectory() as raw:
            output, _ = self.build(Path(raw))
            chains = read_jsonl(output / "chains.jsonl")
            for chain in chains:
                nodes = chain["node_ids"]
                self.assertEqual(len(chain["edge_ids"]) + 1, len(nodes))
                if chain["chain_class"] == "progressive":
                    self.assertEqual(len(nodes), len(set(nodes)))
                elif chain["chain_class"] == "rollback":
                    self.assertLess(len(set(nodes)), len(nodes))
                    self.assertNotEqual(nodes[0], nodes[-1])
                else:
                    self.assertEqual(nodes[0], nodes[-1])

    def test_same_source_produces_identical_node_edge_and_chain_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = make_source()
            first, _ = self.build(root / "first", source)
            second, _ = self.build(root / "second", source)
            for name in ("nodes.jsonl", "edges.jsonl", "chains.jsonl", "render_jobs.jsonl"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_rejects_unfrozen_or_absolute_asset_references(self):
        with tempfile.TemporaryDirectory() as raw:
            source = make_source()
            source["status"] = "draft"
            with self.assertRaises(SUBJECT.ConfigGraphError):
                self.build(Path(raw) / "draft", source)
            source = make_source()
            source["assets"][0]["source_ref"] = r"D:\private\asset.ccProject"
            with self.assertRaises(SUBJECT.ConfigGraphError):
                self.build(Path(raw) / "absolute", source)


if __name__ == "__main__":
    unittest.main()
