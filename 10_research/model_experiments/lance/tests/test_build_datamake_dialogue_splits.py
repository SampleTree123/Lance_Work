from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq
import yaml


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "build_datamake_dialogue_splits.py"
)
SPEC = importlib.util.spec_from_file_location("datamake_dialogue_splits", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_release(root: Path, chain_count: int = 10):
    videos = root / "videos"
    videos.mkdir()
    chains = []
    for index in range(chain_count):
        paths = [f"videos/{index}_{position}.mp4" for position in range(3)]
        for relative_path in paths:
            (root / relative_path).write_bytes(relative_path.encode("ascii"))
        chains.append(
            {
                "chain_id": f"chain_{index:02d}",
                "edit_length": 2,
                "package_scope": "unit_test",
                "initial_video": paths[0],
                "final_video": paths[2],
                "turns": [
                    {
                        "round": round_index,
                        "turn_id": f"turn_{index}_{round_index}",
                        "edit_axis": "outfit_id",
                        "video_in": paths[round_index - 1],
                        "video_out": paths[round_index],
                        "prompt": {"en": f"Edit chain {index} round {round_index}."},
                    }
                    for round_index in (1, 2)
                ],
            }
        )
    chains_path = root / "chains.json"
    chains_path.write_text(json.dumps(chains), encoding="utf-8")
    manifest = {
        "status": "released",
        "counts": {"chains": chain_count, "turns": chain_count * 2},
        "files": {
            "chains.json": {"sha256": MODULE.BUILDER.sha256_file(chains_path)}
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return chains_path, chains


class BuildDataMakeDialogueSplitsTest(unittest.TestCase):
    def test_hash_split_is_independent_of_source_order(self):
        chains = [{"chain_id": f"c{index}"} for index in range(10)]
        counts = {"train": 6, "validation": 2, "test": 2}
        forward = MODULE.deterministic_split(chains, counts, seed=2026)
        reverse = MODULE.deterministic_split(list(reversed(chains)), counts, seed=2026)

        self.assertEqual(
            {
                name: [chain["chain_id"] for chain in subset]
                for name, subset in forward.items()
            },
            {
                name: [chain["chain_id"] for chain in subset]
                for name, subset in reverse.items()
            },
        )

    def test_builds_disjoint_prefix_complete_path_referenced_splits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chains_path, chains = write_release(root)
            output_dir = root / "formal_splits"
            result = MODULE.build_splits(
                chains_path=chains_path,
                package_root=root,
                output_dir=output_dir,
                counts={"train": 6, "validation": 2, "test": 2},
                seed=2026,
                languages=["en"],
                row_group_size=4,
                train_parquet_shards=4,
            )

            self.assertTrue(all(result["audit"].values()))
            self.assertEqual(result["source_chain_count"], 10)
            self.assertEqual(result["source_sample_count"], 20)
            self.assertEqual(
                {name: item["chain_count"] for name, item in result["splits"].items()},
                {"train": 6, "validation": 2, "test": 2},
            )
            self.assertEqual(
                {name: item["sample_count"] for name, item in result["splits"].items()},
                {"train": 12, "validation": 4, "test": 4},
            )
            self.assertEqual(
                result["training_math"]["global_batch_size_4_train_steps_ceil"],
                3,
            )

            source_ids = {chain["chain_id"] for chain in chains}
            seen_chain_ids = set()
            seen_sample_ids = set()
            for split_name in MODULE.SPLIT_ORDER:
                split_dir = output_dir / split_name
                parquet_paths = sorted(split_dir.glob("datamake_multiturn*.parquet"))
                expected_shards = 4 if split_name == "train" else 1
                self.assertEqual(len(parquet_paths), expected_shards)
                table = pq.read_table(parquet_paths)
                rows = table.to_pylist()
                row_chain_ids = {row["chain_id"] for row in rows}
                row_sample_ids = {row["sample_id"] for row in rows}
                self.assertTrue(seen_chain_ids.isdisjoint(row_chain_ids))
                self.assertTrue(seen_sample_ids.isdisjoint(row_sample_ids))
                seen_chain_ids.update(row_chain_ids)
                seen_sample_ids.update(row_sample_ids)
                config = yaml.safe_load(
                    (split_dir / "lance_dataset.yaml").read_text()
                )
                dataset = config["D1"]["datamake_multiturn_v2v_local"]
                self.assertEqual(dataset["media_root"], str(root.resolve()))
                self.assertFalse(dataset["raw_bytes_input"])
                self.assertEqual(
                    len(dataset["dataset_names"]["datamake_multiturn"]["data_dir"]),
                    expected_shards,
                )

            self.assertEqual(seen_chain_ids, source_ids)
            self.assertEqual(len(seen_sample_ids), 20)

    def test_rejects_nonreleased_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chains_path, _ = write_release(root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["status"] = "candidate"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must be released"):
                MODULE.build_splits(
                    chains_path=chains_path,
                    package_root=root,
                    output_dir=root / "formal_splits",
                    counts={"train": 6, "validation": 2, "test": 2},
                    seed=2026,
                    languages=["en"],
                    row_group_size=4,
                    train_parquet_shards=4,
                )


if __name__ == "__main__":
    unittest.main()
