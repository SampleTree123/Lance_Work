from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "build_datamake_round_weighted_train.py"
)
SPEC = importlib.util.spec_from_file_location("datamake_round_weighted", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildDataMakeRoundWeightedTrainTest(unittest.TestCase):
    def test_round_five_is_tripled_without_changing_other_rounds(self):
        rows = [
            {"sample_id": f"s{index}", "target_round": round_index}
            for index, round_index in enumerate([1, 2, 3, 4, 5, 5])
        ]
        repeats = {1: 1, 2: 1, 3: 1, 4: 1, 5: 3}

        first = MODULE.expand_and_shuffle_rows(rows, repeats, seed=2041)
        second = MODULE.expand_and_shuffle_rows(list(reversed(rows)), repeats, seed=2041)

        self.assertEqual(
            [row["sampling_instance_id"] for row in first],
            [row["sampling_instance_id"] for row in second],
        )
        per_round = {}
        for row in first:
            per_round[row["target_round"]] = per_round.get(row["target_round"], 0) + 1
        self.assertEqual(per_round, {1: 1, 2: 1, 3: 1, 4: 1, 5: 6})
        self.assertEqual(len({row["sample_id"] for row in first}), 6)
        self.assertEqual(len({row["sampling_instance_id"] for row in first}), 10)

    def test_builder_writes_eight_balanced_shards_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            train = source / "train"
            train.mkdir(parents=True)
            rows = [
                {
                    "sample_id": f"sample_{index:02d}",
                    "chain_id": f"chain_{index:02d}",
                    "target_round": 5 if index < 4 else (index % 4) + 1,
                    "prompts": ["edit"],
                    "video_paths": ["videos/a.mp4", "videos/b.mp4"],
                }
                for index in range(16)
            ]
            parquet = train / "source.parquet"
            pq.write_table(pa.Table.from_pylist(rows), parquet)
            config = {
                "D1": {
                    "datamake_multiturn_v2v_local": {
                        "dataset_names": {
                            "datamake_multiturn": {"data_dir": [str(parquet)]}
                        }
                    }
                }
            }
            config_path = train / "lance_dataset.yaml"
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
            per_round = {}
            for row in rows:
                key = str(row["target_round"])
                per_round[key] = per_round.get(key, 0) + 1
            split_manifest = {
                "splits": {
                    "train": {
                        "chain_count": 16,
                        "sample_count": 16,
                        "samples_per_target_round": per_round,
                        "dataset_config": "train/lance_dataset.yaml",
                        "parquet_files": [
                            {
                                "path": "train/source.parquet",
                                "rows": 16,
                                "sha256": MODULE.sha256_file(parquet),
                            }
                        ],
                    }
                }
            }
            split_path = source / "split_manifest.json"
            split_path.write_text(json.dumps(split_manifest), encoding="utf-8")

            result = MODULE.build_weighted_train(
                source_split_manifest=split_path,
                output_dir=root / "weighted",
                round_repeats={1: 1, 2: 1, 3: 1, 4: 1, 5: 3},
                sampling_seed=2041,
                first_data_seed=2041,
            )

            self.assertEqual(result["source_train_rows"], 16)
            self.assertEqual(result["effective_train_rows"], 24)
            self.assertEqual(result["effective_samples_per_target_round"]["5"], 12)
            self.assertEqual(len(result["parquet_files"]), 8)
            self.assertEqual(sum(item["rows"] for item in result["parquet_files"]), 24)
            self.assertTrue(all(result["audit"].values()))
            weighted_config = yaml.safe_load(
                (root / "weighted/train/lance_dataset.yaml").read_text()
            )
            paths = weighted_config["D1"]["datamake_multiturn_v2v_local"][
                "dataset_names"
            ]["datamake_multiturn"]["data_dir"]
            self.assertEqual(len(paths), 8)


if __name__ == "__main__":
    unittest.main()
