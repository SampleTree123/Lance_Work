import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "verify_first_batch_delivery_v1.py"
SPEC = importlib.util.spec_from_file_location("first_batch_delivery_verifier", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(root):
    dataset = root / "dataset_v1"
    video_records = []
    for index, node_id in enumerate(("n_node00000001", "n_node00000002"), start=1):
        path = dataset / "videos" / f"{index}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture-video-{index}".encode())
        video_records.append(
            {
                "index": index,
                "path": f"videos/{index}.mp4",
                "node_id": node_id,
                "config_sha256": hashlib.sha256(node_id.encode()).hexdigest(),
                "look_id": f"look_{index}",
                "render_profile_id": "render_v1",
                "config": {"identity_id": f"identity_{index}"},
                "media": {
                    "container": "mp4",
                    "codec": "h264",
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "width": 16,
                    "height": 16,
                    "fps": 30,
                    "frames": 2,
                    "duration_seconds": 2 / 30,
                },
                "source": {},
            }
        )
    chain = {
        "schema_version": SUBJECT.CHAIN_SCHEMA_VERSION,
        "dataset_id": "dataset_v1",
        "batch_id": "batch_v1",
        "package_scope": "fixture",
        "chain_id": "c_chain00000001",
        "compatibility_domain_id": "fixture",
        "chain_policy": "fixture",
        "edit_length": 1,
        "semantic_facts": {},
        "initial_video": "videos/1.mp4",
        "final_video": "videos/2.mp4",
        "video_sequence": [
            {"position": 0, "node_id": "n_node00000001", "path": "videos/1.mp4"},
            {"position": 1, "node_id": "n_node00000002", "path": "videos/2.mp4"},
        ],
        "turns": [
            {
                "round": 1,
                "turn_id": "t_turn00000001",
                "edge_id": "e_edge00000001",
                "edge_type": "E1",
                "edit_axis": "identity_id",
                "change": {"before": "identity_1", "after": "identity_2"},
                "source_node_id": "n_node00000001",
                "target_node_id": "n_node00000002",
                "video_in": "videos/1.mp4",
                "prompt": {"en": "Change the person.", "zh-CN": "更换人物。"},
                "standalone_prompt": {"en": "Use another person.", "zh-CN": "使用另一个人物。"},
                "grounding": None,
                "video_out": "videos/2.mp4",
                "quality_flags": {
                    "atomic": True,
                    "contains_internal_id": False,
                    "language_complete": True,
                    "paired_media_required": True,
                },
            }
        ],
    }
    chains_path = dataset / "chains.json"
    write_json(chains_path, [chain])
    simple_chains = [
        {
            "chain_index": 1,
            "chain_id": "c_chain00000001",
            "turns": [
                {
                    "input_video": "videos/1.mp4",
                    "instruction": {"en": "Change the person.", "zh-CN": "更换人物。"},
                    "output_video": "videos/2.mp4",
                }
            ],
        }
    ]
    simple_chains_path = dataset / "chains_simple.json"
    write_json(simple_chains_path, simple_chains)
    manifest = {
        "schema_version": SUBJECT.MANIFEST_SCHEMA_VERSION,
        "dataset_id": "dataset_v1",
        "batch_id": "batch_v1",
        "package_scope": "fixture",
        "status": "package_candidate_pending_release_qa",
        "counts": {"videos": 2, "chains": 1, "turns": 1},
        "checks": {"fixture": True},
        "files": {
            "chains.json": {"bytes": chains_path.stat().st_size, "sha256": sha256(chains_path)},
            "chains_simple.json": {
                "bytes": simple_chains_path.stat().st_size,
                "sha256": sha256(simple_chains_path),
            },
            "videos": video_records,
        },
        "chain_ids": ["c_chain00000001"],
    }
    write_json(dataset / "manifest.json", manifest)
    return dataset


def probe_result():
    return {
        "codec": "h264",
        "width": 16,
        "height": 16,
        "fps": 30.0,
        "frames": 2,
        "duration_seconds": 2 / 30,
    }


class FirstBatchDeliveryVerifierTests(unittest.TestCase):
    def test_verifies_self_contained_package(self):
        with tempfile.TemporaryDirectory() as raw:
            dataset = make_fixture(Path(raw))
            with mock.patch.object(SUBJECT, "probe_video", return_value=probe_result()):
                report = SUBJECT.verify_delivery(
                    dataset_root=dataset,
                    strict_first_batch=False,
                    workers=2,
                )
            self.assertEqual("passed", report["status"])
            self.assertEqual({"videos": 2, "chains": 1, "turns": 1, "referenced_videos": 2}, report["counts"])
            self.assertTrue(all(report["checks"].values()))

    def test_rejects_video_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as raw:
            dataset = make_fixture(Path(raw))
            (dataset / "videos" / "2.mp4").write_bytes(b"changed")
            with mock.patch.object(SUBJECT, "probe_video", return_value=probe_result()):
                with self.assertRaises(SUBJECT.VerificationError):
                    SUBJECT.verify_delivery(
                        dataset_root=dataset,
                        strict_first_batch=False,
                    )

    def test_rejects_turn_media_discontinuity(self):
        with tempfile.TemporaryDirectory() as raw:
            dataset = make_fixture(Path(raw))
            chains_path = dataset / "chains.json"
            chains = json.loads(chains_path.read_text(encoding="utf-8"))
            chains[0]["turns"][0]["video_out"] = "videos/1.mp4"
            write_json(chains_path, chains)
            manifest_path = dataset / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["chains.json"] = {
                "bytes": chains_path.stat().st_size,
                "sha256": sha256(chains_path),
            }
            write_json(manifest_path, manifest)
            with mock.patch.object(SUBJECT, "probe_video", return_value=probe_result()):
                with self.assertRaises(SUBJECT.VerificationError):
                    SUBJECT.verify_delivery(
                        dataset_root=dataset,
                        strict_first_batch=False,
                    )

    def test_rejects_nonsequential_simple_chain_index(self):
        with tempfile.TemporaryDirectory() as raw:
            dataset = make_fixture(Path(raw))
            simple_path = dataset / "chains_simple.json"
            simple = json.loads(simple_path.read_text(encoding="utf-8"))
            simple[0]["chain_index"] = 2
            write_json(simple_path, simple)
            manifest_path = dataset / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["chains_simple.json"] = {
                "bytes": simple_path.stat().st_size,
                "sha256": sha256(simple_path),
            }
            write_json(manifest_path, manifest)
            with mock.patch.object(SUBJECT, "probe_video", return_value=probe_result()):
                with self.assertRaises(SUBJECT.VerificationError):
                    SUBJECT.verify_delivery(
                        dataset_root=dataset,
                        strict_first_batch=False,
                    )


if __name__ == "__main__":
    unittest.main()
