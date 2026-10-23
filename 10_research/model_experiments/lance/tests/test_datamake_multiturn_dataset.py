from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
import random
from types import MethodType, SimpleNamespace
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import torch


LANCE_ROOT = Path(__file__).parents[1] / "lance"
sys.path.insert(0, str(LANCE_ROOT))

from data.datasets_factory.dataset_datamake_multiturn_v2v_local import (  # noqa: E402
    DataMakeMultiTurnV2VLocalIterableDataset,
)
from data.datasets_factory.datamake_online_rollout_turn import (  # noqa: E402
    process_online_rollout_row,
)
from data.base_mm_parquet_dataset import BaseMMParquetDataset  # noqa: E402
from data.datasets_factory.dataset_x2v_interleave_local import (  # noqa: E402
    X2VInterleaveLocalIterableDataset,
)


class TinyTokenizer:
    SPECIALS = {
        "<|vision_start|>": 1001,
        "<|video_pad|>": 1002,
        "<|image_pad|>": 1003,
        "<|vision_end|>": 1004,
    }

    def __call__(self, text, add_special_tokens=False):
        ids = []
        cursor = 0
        while cursor < len(text):
            matched = False
            for token, token_id in self.SPECIALS.items():
                if text.startswith(token, cursor):
                    ids.append(token_id)
                    cursor += len(token)
                    matched = True
                    break
            if not matched:
                ids.append(ord(text[cursor]) + 10)
                cursor += 1
        return {"input_ids": ids}


class Logger:
    def info(self, message):
        pass

    def warning(self, message):
        raise AssertionError(message)


def make_dataset(tmp_path: Path):
    dataset = DataMakeMultiTurnV2VLocalIterableDataset.__new__(
        DataMakeMultiTurnV2VLocalIterableDataset
    )
    dataset.media_root = str(tmp_path)
    dataset.dataset_type = dataset.DATASET_TYPE
    dataset.data_config = {
        "text_cond_dropout_prob": 0.0,
        "vit_cond_dropout_prob": 0.0,
    }
    dataset.vision_cond_type = ["vit", "vae_Nsplit"]
    dataset.L_video_group = 1000
    dataset.random_choose_group = False
    dataset.tokenizer = TinyTokenizer()
    dataset.dataset_name = "datamake_multiturn_v2v_local"
    dataset.logger = Logger()

    def fake_get_video_tensor(
        self,
        media_bytes,
        vision_stream,
        worker_id=0,
        element_dtype="video",
        raw_bytes_input=True,
    ):
        token_count = 5 if vision_stream == "vit_video" else 7
        return SimpleNamespace(stream=vision_stream, payload=media_bytes), token_count, None

    dataset.get_video_tensor = MethodType(fake_get_video_tensor, dataset)
    dataset.vit_transform = lambda frames: torch.zeros(3, len(frames), 8, 8)

    def fake_vision_token_count(self, tensor):
        return int(tensor.shape[1] * tensor.shape[2] * tensor.shape[3])

    dataset.vision_token_count = MethodType(fake_vision_token_count, dataset)
    return dataset


def write_videos(tmp_path: Path, count: int):
    videos = tmp_path / "videos"
    videos.mkdir()
    for index in range(count):
        (videos / f"{index}.mp4").write_bytes(f"video-{index}".encode("ascii"))


class DataMakeMultiTurnDatasetTest(unittest.TestCase):
    def test_uses_distributed_resume_aware_iterator(self):
        self.assertIs(
            DataMakeMultiTurnV2VLocalIterableDataset.__iter__,
            BaseMMParquetDataset.__iter__,
        )
        self.assertFalse(
            issubclass(
                DataMakeMultiTurnV2VLocalIterableDataset,
                X2VInterleaveLocalIterableDataset,
            )
        )

    def test_debug_repeat_expands_shards_before_worker_split(self):
        dataset = DataMakeMultiTurnV2VLocalIterableDataset(
            dataset_name="datamake_multiturn_v2v_local",
            tokenizer=None,
            data_dir_list=["tiny.parquet"],
            all_data_paths=["tiny.parquet"],
            local_rank=0,
            world_size=1,
            num_workers=2,
            debug_parquet_repeat=32,
        )

        self.assertEqual(dataset.debug_parquet_repeat, 32)
        self.assertEqual(dataset.data_paths, ["tiny.parquet"] * 32)

        dataset.set_epoch(seed=2026)
        for worker_id in range(2):
            worker_info = SimpleNamespace(id=worker_id, num_workers=2)
            with patch("torch.utils.data.get_worker_info", return_value=worker_info):
                worker_paths, returned_worker_id = dataset.get_data_paths_per_worker()
            self.assertEqual(returned_worker_id, worker_id)
            self.assertEqual(worker_paths, ["tiny.parquet"] * 16)

    def test_eight_shards_assign_one_file_per_rank_worker(self):
        paths = [f"part-{index:05d}.parquet" for index in range(8)]
        assigned = []
        for rank in range(4):
            dataset = DataMakeMultiTurnV2VLocalIterableDataset.__new__(
                DataMakeMultiTurnV2VLocalIterableDataset
            )
            dataset.data_paths = paths
            dataset.local_rank = rank
            dataset.world_size = 4
            dataset.num_workers = 2
            dataset.rng = random.Random()
            dataset.set_epoch(seed=2026)
            self.assertEqual(len(dataset.data_paths_per_rank), 2)

            for worker_id in range(2):
                worker_info = SimpleNamespace(id=worker_id, num_workers=2)
                with patch("torch.utils.data.get_worker_info", return_value=worker_info):
                    worker_paths, returned_worker_id = (
                        dataset.get_data_paths_per_worker()
                    )
                self.assertEqual(returned_worker_id, worker_id)
                self.assertEqual(len(worker_paths), 1)
                assigned.extend(worker_paths)

        self.assertCountEqual(assigned, paths)

    def test_resume_data_status_starts_after_last_completed_row(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            parquet_path = Path(temp_dir) / "part.parquet"
            pq.write_table(
                pa.table({"value": ["first", "second", "third"]}),
                parquet_path,
            )
            dataset = DataMakeMultiTurnV2VLocalIterableDataset.__new__(
                DataMakeMultiTurnV2VLocalIterableDataset
            )
            dataset.data_paths = [str(parquet_path)]
            dataset.local_rank = 0
            dataset.world_size = 1
            dataset.num_workers = 0
            dataset.rng = random.Random()
            dataset.seed = 2026
            dataset.dataset_name = "resume-test"
            dataset.dataset_type = dataset.DATASET_TYPE
            dataset.caption_key = "unused"
            dataset.logger = Logger()
            dataset.data_status = {0: [0, 0, 0]}

            def fake_process_row(
                self,
                row,
                parquet_idx,
                row_group_id,
                row_idx,
                worker_id,
                parquet_file_path,
            ):
                return {"value": row["value"], "row_idx": row_idx}

            dataset._process_row = MethodType(fake_process_row, dataset)
            dataset.set_epoch(seed=2026)

            resumed = next(iter(dataset))

            self.assertEqual(resumed, {"value": "second", "row_idx": 1})

    def test_round_three_uses_all_history_vit_and_only_latest_source_vae(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_videos(tmp_path, 4)
            dataset = make_dataset(tmp_path)
            row = {
                "sample_id": "sample-3",
                "chain_id": "chain",
                "target_round": 3,
                "prompts": ["edit one", "edit two", "edit three"],
                "video_paths": [
                    "videos/0.mp4",
                    "videos/1.mp4",
                    "videos/2.mp4",
                    "videos/3.mp4",
                ],
            }

            sample = dataset._process_row(row, 0, 0, 0, 0, "test.parquet")
            plans = sample["sequence_plan"]

            self.assertEqual(
                [plan["type"] for plan in plans],
                [
                    "vit_video",
                    "vit_video",
                    "vit_video",
                    "vae_video",
                    "vae_video",
                    "text_template",
                ],
            )
            self.assertEqual(
                [plan["loss"] for plan in plans[:-1]], [0, 0, 0, 0, 1]
            )
            self.assertEqual(
                [
                    plan.get("datamake_edit_role")
                    for plan in plans
                    if plan["type"] == "vae_video"
                ],
                ["source", "target"],
            )
            self.assertEqual(len(plans[-1]["spans_index"]), 5)
            self.assertEqual(len(sample["video_tensor_list"]), 5)
            self.assertEqual(sample["N_target"], 1)
            self.assertEqual(sample["sample_task"], "edit")

    def test_round_one_keeps_initial_video_as_direct_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_videos(tmp_path, 2)
            dataset = make_dataset(tmp_path)
            row = {
                "sample_id": "sample-1",
                "chain_id": "chain",
                "target_round": 1,
                "prompts": ["edit one"],
                "video_paths": ["videos/0.mp4", "videos/1.mp4"],
            }

            sample = dataset._process_row(row, 0, 0, 0, 0, "test.parquet")
            plans = sample["sequence_plan"]

            self.assertEqual(
                [plan["type"] for plan in plans],
                ["vit_video", "vae_video", "vae_video", "text_template"],
            )
            self.assertEqual([plan["loss"] for plan in plans[:-1]], [0, 0, 1])
            self.assertEqual(
                [
                    plan.get("datamake_edit_role")
                    for plan in plans
                    if plan["type"] == "vae_video"
                ],
                ["source", "target"],
            )
            self.assertEqual(len(plans[-1]["spans_index"]), 3)

    def test_in_memory_rollouts_replace_history_without_codec_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_videos(tmp_path, 4)
            dataset = make_dataset(tmp_path)
            generated_one = torch.full((3, 6, 8, 8), -0.25, dtype=torch.float16)
            generated_two = torch.full((3, 6, 8, 8), 0.75, dtype=torch.float16)
            row = {
                "sample_id": "sample-online-3",
                "chain_id": "chain",
                "target_round": 3,
                "prompts": ["edit one", "edit two", "edit three"],
                "video_paths": [
                    "videos/0.mp4",
                    "videos/1.mp4",
                    "videos/2.mp4",
                    "videos/3.mp4",
                ],
                "video_inputs": [
                    "videos/0.mp4",
                    generated_one,
                    generated_two,
                    "videos/3.mp4",
                ],
            }

            sample = process_online_rollout_row(
                dataset, row, 0, 0, 0, 0, "memory-row"
            )

            self.assertIsNotNone(sample)
            self.assertEqual(
                [plan["type"] for plan in sample["sequence_plan"]],
                [
                    "vit_video",
                    "vit_video",
                    "vit_video",
                    "vae_video",
                    "vae_video",
                    "text_template",
                ],
            )
            vae_source = sample["video_tensor_list"][3]
            self.assertEqual(vae_source.dtype, torch.float32)
            self.assertTrue(torch.allclose(vae_source, generated_two.float()))
            self.assertNotIsInstance(sample["video_tensor_list"][1], SimpleNamespace)
            self.assertNotIsInstance(sample["video_tensor_list"][2], SimpleNamespace)


if __name__ == "__main__":
    unittest.main()
