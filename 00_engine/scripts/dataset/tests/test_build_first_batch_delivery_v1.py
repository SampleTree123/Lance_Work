import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_first_batch_delivery_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_delivery", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node(node_id, value):
    config = {
        "identity_id": value,
        "outfit_id": "outfit_a",
        "action_id": "action_a",
        "camera_id": "near",
    }
    return {
        "node_id": node_id,
        "config": config,
        "config_sha256": hashlib.sha256(node_id.encode()).hexdigest(),
        "look_id": f"look_{value}",
        "render_profile_id": "render_v1",
    }


def chain(chain_id, node_ids):
    return {
        "chain_id": chain_id,
        "chain_policy": "progressive_shortest",
        "compatibility_domain_id": "fixture",
        "edit_length": len(node_ids) - 1,
        "node_ids": node_ids,
        "is_semantic_shortest": True,
        "has_repeated_axis": False,
        "has_consecutive_same_axis": False,
        "has_rollback": False,
        "returns_to_start": False,
    }


def turn(chain_id, turn_id, round_index, source, target):
    return {
        "turn_id": turn_id,
        "chain_id": chain_id,
        "round": round_index,
        "source_node_id": source,
        "target_node_id": target,
        "edge_id": f"edge_{turn_id}",
        "edge_type": "E1",
        "edit_axis": "identity_id",
        "before_value": source,
        "after_value": target,
        "prompt": {
            "dialogue": {"en": f"Change to {target}.", "zh-CN": f"改为{target}。"},
            "standalone": {"en": f"Use {target}.", "zh-CN": f"使用{target}。"},
        },
        "grounding": {"mode": "fixture"},
        "quality_flags": {
            "atomic": True,
            "contains_internal_id": False,
            "language_complete": True,
            "paired_media_required": True,
        },
    }


def make_fixture(root):
    graph = root / "graph"
    prompt = graph / "text"
    run = root / "run"
    nodes = [node("n_c", "c"), node("n_a", "a"), node("n_b", "b")]
    chains = [chain("chain_2", ["n_b", "n_c"]), chain("chain_1", ["n_a", "n_b"])]
    turns = [
        turn("chain_1", "turn_1", 1, "n_a", "n_b"),
        turn("chain_2", "turn_2", 1, "n_b", "n_c"),
    ]
    dialogs = [
        {"chain_id": "chain_1", "edit_length": 1, "turn_ids": ["turn_1"]},
        {"chain_id": "chain_2", "edit_length": 1, "turn_ids": ["turn_2"]},
    ]
    write_json(
        graph / "source_manifest.json",
        {
            "source_manifest_id": "source_v1",
            "batch_id": "batch_v1",
            "status": "frozen",
        },
    )
    write_jsonl(graph / "nodes.jsonl", nodes)
    write_jsonl(graph / "chains.jsonl", chains)
    write_json(
        prompt / "prompt_manifest.json",
        {
            "status": "passed",
            "prompt_layer_version": "text_v1",
            "graph_source": {
                "source_manifest_sha256": sha256(graph / "source_manifest.json"),
                "nodes_sha256": sha256(graph / "nodes.jsonl"),
                "chains_sha256": sha256(graph / "chains.jsonl"),
            },
        },
    )
    write_jsonl(prompt / "dialogs.jsonl", dialogs)
    write_jsonl(prompt / "turns.jsonl", turns)
    write_json(run / "manifest.json", {"run_id": "run_v1"})
    records = []
    for item in nodes:
        node_id = item["node_id"]
        media = run / "media" / "nodes" / node_id / "video.mp4"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(f"video:{node_id}".encode())
        sidecar = media.with_name("sidecar.json")
        sidecar_value = {
            "status": "accepted",
            "node_id": node_id,
            "ground_truth": {
                "config": item["config"],
                "config_sha256": item["config_sha256"],
            },
            "media": {"sha256": sha256(media)},
            "accepted_at_utc": "2026-08-29T00:00:00+00:00",
        }
        write_json(sidecar, sidecar_value)
        records.append(
            {
                "node_id": node_id,
                "config_sha256": item["config_sha256"],
                "path": str(media.relative_to(run)),
                "sidecar": str(sidecar.relative_to(run)),
                "container": "mp4",
                "codec": "h264",
                "bytes": media.stat().st_size,
                "sha256": sha256(media),
                "width": 16,
                "height": 16,
                "fps": 30,
                "frames": 2,
                "duration_seconds": 2 / 30,
            }
        )
    write_json(run / "media_manifest.json", {"records": records})
    return graph, prompt, run


class FirstBatchDeliveryTests(unittest.TestCase):
    def test_builds_numbered_videos_and_bilingual_chains(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            graph, prompt, run = make_fixture(root)
            output = root / "dataset_v1"
            manifest = SUBJECT.build_delivery(
                graph_dir=graph,
                prompt_dir=prompt,
                render_run_root=run,
                output_dir=output,
                dataset_id="dataset_v1",
                package_scope="fixture",
                materialization_mode="copy",
                strict_first_batch=False,
            )
            self.assertEqual(["1.mp4", "2.mp4", "3.mp4"], sorted(path.name for path in (output / "videos").iterdir()))
            self.assertEqual(3, manifest["counts"]["videos"])
            self.assertEqual(2, manifest["counts"]["chains"])
            self.assertEqual(2, manifest["counts"]["turns"])
            self.assertTrue(all(manifest["checks"].values()))
            self.assertEqual(
                ["n_a", "n_b", "n_c"],
                [record["node_id"] for record in manifest["files"]["videos"]],
            )
            chains = json.loads((output / "chains.json").read_text(encoding="utf-8"))
            self.assertEqual("videos/1.mp4", chains[0]["initial_video"])
            self.assertEqual("videos/2.mp4", chains[0]["final_video"])
            self.assertEqual({"en", "zh-CN"}, set(chains[0]["turns"][0]["prompt"]))
            self.assertEqual({"en", "zh-CN"}, set(chains[0]["turns"][0]["standalone_prompt"]))
            simple_chains = json.loads(
                (output / "chains_simple.json").read_text(encoding="utf-8")
            )
            self.assertEqual([1, 2], [chain["chain_index"] for chain in simple_chains])
            self.assertEqual(chains[0]["chain_id"], simple_chains[0]["chain_id"])
            self.assertEqual(
                {
                    "input_video": "videos/1.mp4",
                    "instruction": chains[0]["turns"][0]["prompt"],
                    "output_video": "videos/2.mp4",
                },
                simple_chains[0]["turns"][0],
            )
            self.assertEqual(
                manifest["files"]["chains_simple.json"]["sha256"],
                sha256(output / "chains_simple.json"),
            )

    def test_selected_chain_packages_only_required_endpoints(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            graph, prompt, run = make_fixture(root)
            output = root / "sample"
            manifest = SUBJECT.build_delivery(
                graph_dir=graph,
                prompt_dir=prompt,
                render_run_root=run,
                output_dir=output,
                dataset_id="dataset_v1",
                package_scope="sample",
                selected_chain_ids=["chain_2"],
                materialization_mode="copy",
            )
            self.assertEqual("sample", manifest["status"])
            self.assertEqual(2, manifest["counts"]["videos"])
            self.assertEqual(["n_b", "n_c"], [item["node_id"] for item in manifest["files"]["videos"]])

    def test_rejects_missing_accepted_media(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            graph, prompt, run = make_fixture(root)
            media_manifest = json.loads((run / "media_manifest.json").read_text())
            media_manifest["records"] = [
                item for item in media_manifest["records"] if item["node_id"] != "n_c"
            ]
            write_json(run / "media_manifest.json", media_manifest)
            with self.assertRaises(SUBJECT.DeliveryError):
                SUBJECT.build_delivery(
                    graph_dir=graph,
                    prompt_dir=prompt,
                    render_run_root=run,
                    output_dir=root / "delivery",
                    dataset_id="dataset_v1",
                    package_scope="fixture",
                    materialization_mode="copy",
                    strict_first_batch=False,
                )


if __name__ == "__main__":
    unittest.main()
