import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_first_batch_prompt_layer_v1.py"
CATALOG = ROOT / "prompt_catalog_first_batch_v1.json"
SPEC = importlib.util.spec_from_file_location("first_batch_prompt_layer", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path, values):
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
        encoding="utf-8",
    )


def node(node_id, identity, outfit, action="act_f01_sexy_dance"):
    config = {
        "sex": "female",
        "bodyfit_id": "f02_average",
        "identity_id": identity,
        "outfit_id": outfit,
        "action_id": action,
        "expression_id": "happy",
        "scene_id": "scene_one",
        "camera_id": "near",
        "lighting_id": "lighting_one",
        "anchor_id": "anchor_one",
        "frame_start": 0,
        "duration_frames": 150,
        "fps": 30,
        "resolution": {"width": 2560, "height": 1440},
        "seed": 0,
    }
    return {
        "node_id": node_id,
        "compatibility_domain_id": "female_v1",
        "config": config,
        "config_sha256": "0" * 64,
        "expected_media_uri": f"media/nodes/{node_id}/video.mp4",
    }


def edge(edge_id, source, target, edge_type, field, before, after):
    return {
        "edge_id": edge_id,
        "source_node_id": source,
        "target_node_id": target,
        "compatibility_domain_id": "female_v1",
        "edge_type": edge_type,
        "edit_axis": field,
        "before_value": before,
        "after_value": after,
        "changed_fields": [f"config.{field}"],
    }


def chain(chain_id, node_ids, edge_ids, edge_types, facts=None):
    facts = facts or {}
    return {
        "chain_id": chain_id,
        "chain_policy": "freeform_walk",
        "compatibility_domain_id": "female_v1",
        "edit_length": len(edge_ids),
        "node_ids": node_ids,
        "edge_ids": edge_ids,
        "edge_types": edge_types,
        "edge_axes": [SUBJECT.EDIT_FIELDS[item][0] for item in edge_types],
        "is_semantic_shortest": facts.get("is_semantic_shortest", False),
        "has_repeated_axis": facts.get("has_repeated_axis", False),
        "has_consecutive_same_axis": facts.get("has_consecutive_same_axis", False),
        "has_rollback": facts.get("has_rollback", False),
        "returns_to_start": facts.get("returns_to_start", False),
    }


def make_graph(root):
    root.mkdir(parents=True)
    nodes = [
        node("n0", "f_id01", "f_o01"),
        node("n1", "f_id02", "f_o01"),
        node("n2", "f_id02", "f_o02"),
    ]
    edges = [
        edge("e01", "n0", "n1", "E1", "identity_id", "f_id01", "f_id02"),
        edge("e10", "n1", "n0", "E1", "identity_id", "f_id02", "f_id01"),
        edge("e12", "n1", "n2", "E2", "outfit_id", "f_o01", "f_o02"),
    ]
    chains = [
        chain("c_direct", ["n0", "n1", "n2"], ["e01", "e12"], ["E1", "E2"]),
        chain(
            "c_rollback",
            ["n0", "n1", "n0"],
            ["e01", "e10"],
            ["E1", "E1"],
            {
                "has_repeated_axis": True,
                "has_consecutive_same_axis": True,
                "has_rollback": True,
                "returns_to_start": True,
            },
        ),
    ]
    write_json(root / "source_manifest.json", {"source_manifest_id": "fixture_source"})
    write_jsonl(root / "nodes.jsonl", nodes)
    write_jsonl(root / "edges.jsonl", edges)
    write_jsonl(root / "chains.jsonl", chains)
    return nodes, edges, chains


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class FirstBatchPromptLayerTests(unittest.TestCase):
    def build(self, root, catalog=CATALOG):
        graph = root / "graph"
        make_graph(graph)
        output = root / "text"
        report = SUBJECT.build_prompt_layer(
            graph, catalog, output, strict_first_batch=False
        )
        return graph, output, report

    def test_builds_bilingual_video_prompt_video_turns(self):
        with tempfile.TemporaryDirectory() as raw:
            _, output, report = self.build(Path(raw))
            turns = read_jsonl(output / "turns.jsonl")
            dialogs = read_jsonl(output / "dialogs.jsonl")
            self.assertEqual(4, report["counts"]["turns"])
            self.assertEqual(2, report["counts"]["dialogs"])
            self.assertEqual(4, len(turns))
            self.assertEqual(2, len(dialogs))
            self.assertTrue((output / "prompt_review.json").is_file())
            self.assertTrue((output / "PROMPT_REVIEW.md").is_file())
            self.assertTrue((output / "identity_descriptions.json").is_file())
            self.assertTrue((output / "IDENTITY_DESCRIPTION_REVIEW.md").is_file())
            self.assertEqual(8, report["counts"]["identity_descriptions"])
            for turn in turns:
                self.assertTrue(turn["video_in_uri"].endswith("video.mp4"))
                self.assertTrue(turn["video_out_uri"].endswith("video.mp4"))
                self.assertEqual(
                    {"zh-CN", "en"}, set(turn["prompt"]["dialogue"])
                )
                self.assertEqual(
                    {"zh-CN", "en"}, set(turn["prompt"]["standalone"])
                )
                for mode in ("dialogue", "standalone"):
                    for text in turn["prompt"][mode].values():
                        self.assertIsNone(SUBJECT.INTERNAL_ID_PATTERN.search(text))
                self.assertTrue(turn["quality_flags"]["atomic"])

    def test_rollback_has_contextual_and_standalone_forms(self):
        with tempfile.TemporaryDirectory() as raw:
            _, output, _ = self.build(Path(raw))
            rollback = next(
                turn
                for turn in read_jsonl(output / "turns.jsonl")
                if turn["chain_id"] == "c_rollback" and turn["round"] == 2
            )
            self.assertEqual("initial_state", rollback["history_reference"]["kind"])
            self.assertTrue(
                rollback["prompt"]["template_ids"]["dialogue.zh-CN"].startswith(
                    "restore_initial_zh-CN_"
                )
            )
            self.assertTrue(
                rollback["prompt"]["template_ids"]["dialogue.en"].startswith(
                    "restore_initial_en_"
                )
            )
            target = read_json(CATALOG)["labels"]["identity"]["f_id01"]["zh-CN"]
            self.assertIn(target, rollback["prompt"]["standalone"]["zh-CN"])
            self.assertTrue(
                rollback["prompt"]["template_ids"]["standalone.zh-CN"].startswith(
                    "e1_direct_zh-CN_"
                )
            )

    def test_identity_turn_declares_description_and_paired_target_grounding(self):
        with tempfile.TemporaryDirectory() as raw:
            _, output, _ = self.build(Path(raw))
            identity_turn = next(
                turn for turn in read_jsonl(output / "turns.jsonl") if turn["edge_type"] == "E1"
            )
            self.assertEqual(
                "visible_description_and_paired_target_video",
                identity_turn["grounding"]["mode"],
            )
            self.assertEqual(
                "identity_specific_visible_description",
                identity_turn["grounding"]["target_specificity"],
            )
            self.assertEqual(3, len(identity_turn["grounding"]["reference_image_uris"]))
            self.assertEqual(
                "first_batch_identity_descriptions_zh_en_v1_20260824",
                identity_turn["grounding"]["description_catalog_version"],
            )

    def test_identity_descriptions_are_unique_and_match_prompt_labels(self):
        catalog = read_json(CATALOG)
        descriptions = catalog["identity_description_catalog"]["identities"]
        labels = catalog["labels"]["identity"]
        self.assertEqual(set(labels), set(descriptions))
        for language in ("zh-CN", "en"):
            targets = [
                descriptions[identity_id]["prompt_target"][language]
                for identity_id in sorted(descriptions)
            ]
            self.assertEqual(len(targets), len(set(targets)))
            for identity_id in descriptions:
                self.assertEqual(
                    labels[identity_id][language],
                    descriptions[identity_id]["prompt_target"][language],
                )

    def test_same_inputs_produce_identical_turns_and_dialogs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, first, _ = self.build(root / "first")
            _, second, _ = self.build(root / "second")
            self.assertEqual((first / "turns.jsonl").read_bytes(), (second / "turns.jsonl").read_bytes())
            self.assertEqual((first / "dialogs.jsonl").read_bytes(), (second / "dialogs.jsonl").read_bytes())

    def test_rejects_non_atomic_turn(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            graph = root / "graph"
            make_graph(graph)
            nodes = read_jsonl(graph / "nodes.jsonl")
            nodes[1]["config"]["outfit_id"] = "f_o02"
            write_jsonl(graph / "nodes.jsonl", nodes)
            with self.assertRaises(SUBJECT.PromptLayerError):
                SUBJECT.build_prompt_layer(
                    graph, CATALOG, root / "text", strict_first_batch=False
                )


if __name__ == "__main__":
    unittest.main()
