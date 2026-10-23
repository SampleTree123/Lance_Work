from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


LANCE_ROOT = Path(__file__).parents[1] / "lance"
sys.path.insert(0, str(LANCE_ROOT))

from train.train_utils import (  # noqa: E402
    setup_output_paths,
    setup_rank0_logging_and_wandb,
)


class Logger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class WandbTrainingLoggingTest(unittest.TestCase):
    def test_online_run_honors_stable_run_id(self):
        training_args = SimpleNamespace(
            wandb_name="formal-dialogue-run",
            wandb_runid="formal-dialogue-v1",
            wandb_project="datamake_lance",
            wandb_resume="allow",
            wandb_offline=False,
            wandb_dir="/tmp/datamake-wandb-test",
        )
        config_mock = MagicMock()
        with patch("train.train_utils.wandb.init") as init_mock, patch(
            "train.train_utils.wandb.config", config_mock
        ):
            setup_rank0_logging_and_wandb(
                SimpleNamespace(model="test"),
                SimpleNamespace(dataset="test"),
                training_args,
                Logger(),
                global_rank=0,
            )

        init_mock.assert_called_once_with(
            project="datamake_lance",
            name="formal-dialogue-run",
            id="formal-dialogue-v1",
            resume="allow",
            mode="online",
            dir="/tmp/datamake-wandb-test",
        )
        config_mock.update.assert_called_once()
        self.assertTrue(config_mock.update.call_args.kwargs["allow_val_change"])

    def test_online_mode_keeps_local_buffer_under_run_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            training_args = SimpleNamespace(
                outputs_dir=temp_dir,
                wandb_name="formal-dialogue-run",
                wandb_offline=False,
            )
            setup_output_paths(training_args, Logger(), global_rank=0)

            self.assertTrue(Path(training_args.config_dir).is_dir())
            self.assertTrue(Path(training_args.ckpt_dir).is_dir())
            self.assertTrue(Path(training_args.wandb_dir).is_dir())


if __name__ == "__main__":
    unittest.main()
