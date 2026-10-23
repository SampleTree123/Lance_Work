from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "build_datamake_multiturn_training_data.py"
)
SPEC = importlib.util.spec_from_file_location("datamake_multiturn_builder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_delivery(tmp_path: Path):
    videos = tmp_path / "videos"
    videos.mkdir()
    for name in ("0.mp4", "1.mp4", "2.mp4"):
        (videos / name).write_bytes(name.encode("ascii"))
    chain = {
        "chain_id": "c_test",
        "edit_length": 2,
        "chain_policy": "freeform_walk",
        "initial_video": "videos/0.mp4",
        "final_video": "videos/2.mp4",
        "turns": [
            {
                "round": 1,
                "turn_id": "t1",
                "edit_axis": "outfit_id",
                "video_in": "videos/0.mp4",
                "video_out": "videos/1.mp4",
                "prompt": {"en": "Change the outfit.", "zh-CN": "更换服装。"},
                "standalone_prompt": {
                    "en": "Change only the outfit.",
                    "zh-CN": "仅更换服装。",
                },
            },
            {
                "round": 2,
                "turn_id": "t2",
                "edit_axis": "camera_id",
                "video_in": "videos/1.mp4",
                "video_out": "videos/2.mp4",
                "prompt": {"en": "Move to the side view.", "zh-CN": "切换侧面镜头。"},
                "standalone_prompt": {
                    "en": "Use only the side view.",
                    "zh-CN": "仅使用侧面镜头。",
                },
            },
        ],
    }
    chains_path = tmp_path / "chains.json"
    chains_path.write_text(json.dumps([chain]), encoding="utf-8")
    return chains_path, chain


class BuildDataMakeMultiTurnTrainingDataTest(unittest.TestCase):
    def test_builds_one_prefix_sample_per_target_round(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            chains_path, chain = write_delivery(tmp_path)
            rows = MODULE.build_rows([chain], tmp_path, ["en"], "dialogue")

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["prompts"], ["Change the outfit."])
            self.assertEqual(
                rows[0]["video_paths"], ["videos/0.mp4", "videos/1.mp4"]
            )
            self.assertEqual(
                rows[1]["prompts"],
                ["Change the outfit.", "Move to the side view."],
            )
            self.assertEqual(
                rows[1]["video_paths"],
                ["videos/0.mp4", "videos/1.mp4", "videos/2.mp4"],
            )
            self.assertEqual(len({row["sample_id"] for row in rows}), 2)
            self.assertEqual(MODULE.read_chains(chains_path), [chain])

    def test_rejects_broken_endpoint_reuse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            _, chain = write_delivery(tmp_path)
            chain["turns"][1]["video_in"] = "videos/0.mp4"

            with self.assertRaisesRegex(ValueError, "breaks endpoint reuse"):
                MODULE.build_rows([chain], tmp_path, ["en"], "dialogue")

    def test_standalone_view_is_a_true_single_turn_control(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            _, chain = write_delivery(tmp_path)
            rows = MODULE.build_rows([chain], tmp_path, ["en"], "standalone")

            self.assertEqual(rows[1]["target_round"], 2)
            self.assertEqual(rows[1]["context_length"], 1)
            self.assertEqual(rows[1]["prompts"], ["Use only the side view."])
            self.assertEqual(
                rows[1]["video_paths"], ["videos/1.mp4", "videos/2.mp4"]
            )

    def test_rejects_media_path_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            outside = tmp_path.parent / "outside.mp4"
            outside.write_bytes(b"outside")
            self.addCleanup(outside.unlink, missing_ok=True)

            with self.assertRaisesRegex(ValueError, "escapes package root"):
                MODULE.resolve_package_media(tmp_path, "../outside.mp4")

    def test_generated_yaml_uses_path_references_and_bounded_resolution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            parquet_path = tmp_path / "data.parquet"
            config = MODULE.build_lance_yaml(parquet_path, tmp_path)
            dataset = config["D1"]["datamake_multiturn_v2v_local"]

            self.assertEqual(
                dataset["dataset_type"], "datamake_multiturn_video2video"
            )
            self.assertEqual(dataset["media_root"], str(tmp_path.resolve()))
            self.assertEqual(dataset["video_transform_args"]["resolution"], 480)
            self.assertEqual(
                dataset["vit_video_transform_args"]["resolution"], 448
            )


if __name__ == "__main__":
    unittest.main()
