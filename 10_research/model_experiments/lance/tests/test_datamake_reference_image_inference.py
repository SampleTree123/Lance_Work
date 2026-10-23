"""Reference images must not change edit-source selection or become VAE targets."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import unittest
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lance"))
sys.path.insert(0, str(ROOT / "scripts"))

from multiturn.conversation import Conversation, ContentItem, Turn, TurnAction
from multiturn.sequence_builder import MultiTurnSequenceBuilder
from data.datamake_reference_image import REFERENCE_IMAGE_PROMPT
from data.dataset_base import DataConfig
from build_multiturn_conversation import build_video_edit_conversation

ASSERT = unittest.TestCase()


def make_builder():
    return MultiTurnSequenceBuilder(
        tokenizer=None, data_args=None, model_args=None, training_args=None,
        new_token_ids={"bos_token_id": 1, "eos_token_id": 2,
                       "start_of_image": 3, "end_of_image": 4, "image_token_id": 5},
        dataset_config=SimpleNamespace(resolution="video_480p", max_duration=6),
    )


def test_turn_reference_roundtrip_and_legacy_absence():
    old = {"role": "user", "action": "edit_video", "content": [{"type": "text", "value": "edit"}]}
    assert Turn.from_dict(old).to_dict() == old
    raw = dict(old, reference_image="shirt.png")
    turn = Turn.from_dict(raw)
    assert turn.to_dict() == raw
    assert turn.visual_items == []
    assert turn.joined_text() == "edit"


def test_rejects_non_single_reference():
    for reference in ([], ["a.png"], {}, 3, "", "  "):
        with ASSERT.assertRaisesRegex(ValueError, "reference_image"):
            Turn(role="user", reference_image=reference)


def test_reference_not_allowed_on_assistant_or_other_action():
    with ASSERT.assertRaisesRegex(ValueError, "user"):
        Turn(role="assistant", reference_image="a.png")
    with ASSERT.assertRaisesRegex(ValueError, "edit_video"):
        Turn(role="user", action=TurnAction.GENERATE_IMAGE, reference_image="a.png")


def test_reference_never_overrides_latest_video_source():
    builder = make_builder()
    v0 = ContentItem("video", "v0.mp4")
    v1 = ContentItem("video", "v1.mp4")
    history = [Turn("user", [v0], reference_image="r0.png"), Turn("assistant", [v1]),
               Turn("user", [ContentItem("text", "next")], action=TurnAction.EDIT_VIDEO,
                    reference_image="r1.png")]
    assert builder._latest_visual_item(history) is v1
    assert builder._latest_visual_item([history[-1]]) is None


def test_context_mixed_reference_and_plain_turns_no_video_reader_or_vae():
    builder = make_builder()
    builder.sample = builder.set_sequence_status()
    # Small real patches, independent of production resize presets.
    builder.vit_transform = lambda frames: torch.ones(3, len(frames), 28, 28)
    builder.data_config.vit_patch_size = 14
    builder.data_config.vit_patch_size_temporal = 2
    builder.data_config.text_template = True
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "reference.png"
        Image.new("RGB", (30, 40), "blue").save(path)
        turns = [Turn("user", [ContentItem("text", "change clothes")], reference_image=str(path)),
                 Turn("user", [ContentItem("text", "move camera")])]
        grids, sizes = [], []
        with patch.object(builder, "get_video_tensor_online", side_effect=AssertionError("video read")), \
             patch.object(builder, "process_vae_video", side_effect=AssertionError("VAE reference")):
            messages, types, counts, vae = builder._collect_context(turns, None, grids, sizes)
    assert types == ["vit_video"]
    assert counts == [1]
    assert grids == [[1, 2, 2]]
    assert sizes == [] and vae is None
    assert messages[0]["content"] == [
        {"type": "text", "text": REFERENCE_IMAGE_PROMPT}, {"type": "video"},
        {"type": "text", "text": "change clothes"},
    ]
    assert messages[1]["content"] == [{"type": "text", "text": "move camera"}]
    assert builder.sample["vae_video_tensors"] == []
    assert len(builder.sample["vit_video_tensors"]) == 1


def test_builder_optional_references_are_aligned_per_turn():
    payload = build_video_edit_conversation(Path("source.mp4"), ["shirt", "camera"], ["shirt.png", None])
    conv = Conversation.from_dict(payload)
    assert conv.turns[0].reference_image == "shirt.png"
    assert conv.turns[1].reference_image is None
    assert len(conv.turns[0].visual_items) == 1
    assert "reference_image" not in payload["turns"][1]
    with ASSERT.assertRaisesRegex(ValueError, "one path/null"):
        build_video_edit_conversation(Path("v.mp4"), ["a", "b"], ["r.png"])


def test_reference_is_not_a_valid_video_edit_source():
    builder = make_builder()
    conversation = Conversation([Turn("user", [ContentItem("text", "change clothes")],
                                      TurnAction.EDIT_VIDEO, reference_image="ref.png")])
    with patch.object(builder, "_collect_context", return_value=([], [], [], None)):
        with ASSERT.assertRaisesRegex(ValueError, "visual source"):
            builder.build(conversation, 0)


def test_complete_inference_pack_has_reference_only_in_vit_and_preserves_target():
    class Tokenizer:
        def __call__(self, text, add_special_tokens=False):
            specials = {"<|vision_start|>": 1001, "<|video_pad|>": 1002,
                        "<|image_pad|>": 1003, "<|vision_end|>": 1004}
            ids, cursor = [], 0
            while cursor < len(text):
                for token, value in specials.items():
                    if text.startswith(token, cursor):
                        ids.append(value)
                        cursor += len(token)
                        break
                else:
                    ids.append(ord(text[cursor]) + 10)
                    cursor += 1
            return {"input_ids": ids}

    builder = make_builder()
    builder.tokenizer = Tokenizer()
    builder.data_config = DataConfig()
    builder.data_config.text_template = True
    builder.vit_transform = lambda frames: torch.ones(3, len(frames), 28, 28)

    def read_video(path, vision_stream, **kwargs):
        assert path == "source.mp4"
        return torch.zeros(3, 2, 28, 28) if vision_stream == "vit_video" else torch.zeros(3, 5, 32, 32)

    with tempfile.TemporaryDirectory() as folder:
        reference = Path(folder) / "shirt.png"
        Image.new("RGB", (28, 28), "blue").save(reference)
        plain = Conversation.from_dict(build_video_edit_conversation(Path("source.mp4"), ["change shirt"]))
        with_ref = Conversation.from_dict(build_video_edit_conversation(
            Path("source.mp4"), ["change shirt"], [str(reference)]))
        with patch.object(builder, "get_video_tensor_online", side_effect=read_video):
            old = builder.build(plain, 0)
            new = builder.build(with_ref, 0)
    assert new["vit_video_grid_thw"].tolist() == [[1, 2, 2], [1, 2, 2]]
    assert new["vae_video_grid_thw"].tolist() == old["vae_video_grid_thw"].tolist()
    assert new["video_grid_thw"].tolist() == [[[1, 2, 2], [2, 4, 4], [1, 2, 2], [2, 4, 4]]]
    assert new["mse_loss_indexes"].numel() == old["mse_loss_indexes"].numel() == 8
    assert new["packed_vae_token_indexes"].numel() == old["packed_vae_token_indexes"].numel() == 16
    assert new["packed_vit_token_indexes"].numel() == 2
    assert new["video_sizes"].tolist() == old["video_sizes"].tolist() == [[5, 32, 32], [5, 32, 32]]
    assert sum(new["split_lens"]) == new["sample_lens"][0]
    assert len(new["sample_modality"]) == new["sample_lens"][0]
    assert not set(new["packed_vit_token_indexes"].tolist()) & set(new["mse_loss_indexes"].tolist())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value) for name, value in globals().items()
                              if name.startswith("test_") and callable(value))


if __name__ == "__main__":
    unittest.main()
