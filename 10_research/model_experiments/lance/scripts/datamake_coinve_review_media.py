"""Reuse the training paired-window sampler for inference and preview only.

Training source files remain unchanged. Owner: ../training_integration.md.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys


def sampled_frames(path, crop):
    import decord
    from PIL import Image

    lance = Path(__file__).resolve().parents[1] / "lance"
    if str(lance) not in sys.path:
        sys.path.insert(0, str(lance))
    from data.datasets_factory.dataset_datamake_mixed_v2v_local import CROP_POLICY, crop_frame_indices
    if crop["policy"] != CROP_POLICY:
        raise ValueError("Unsupported paired crop policy")
    reader = decord.VideoReader(str(path), ctx=decord.cpu(0), num_threads=1)
    fps = float(reader.get_avg_fps())
    indices = crop_frame_indices(len(reader), fps, crop["start_seconds"], crop["duration_seconds"])
    frames = [Image.fromarray(frame) for frame in reader.get_batch(indices).asnumpy()]
    return frames, {"original_path": str(path), "native_fps": fps, "indices": indices,
                    "start_seconds": crop["start_seconds"], "duration_seconds": crop["duration_seconds"],
                    "sampled_frames": len(frames), "sample_fps": 12}


@contextmanager
def paired_input(builder, case):
    """Override only this case's source decoding, never load the target into inference."""
    crop = case.get("paired_crop")
    if crop is None:
        yield
        return
    import torch

    original = builder.get_video_tensor_online
    had_override = "get_video_tensor_online" in builder.__dict__
    cached = []
    def read(media_url, vision_stream, worker_id=0, element_dtype="image"):
        if str(media_url) != crop["path"] or element_dtype != "video":
            raise ValueError("Single-turn CoinVE inference must decode only its source")
        if not cached:
            frames, evidence = sampled_frames(media_url, crop)
            cached.extend(frames)
            case["paired_input_sampling"] = evidence
        builder.vision_stream = vision_stream
        if vision_stream == "vae_video":
            return builder.transform(cached)
        if vision_stream == "vit_video":
            value = builder.vit_transform(cached)
            if value.shape[1] % 2:
                value = torch.cat([value, value[:, -1:]], dim=1)
            return value
        raise ValueError(f"Unknown vision stream: {vision_stream}")
    builder.get_video_tensor_online = read
    try:
        yield
    finally:
        if had_override:
            builder.get_video_tensor_online = original
        else:
            del builder.get_video_tensor_online


def sampled_preview(path, crop, run, original_sha256):
    """Write a small browser-compatible visualization; inference reads original frames."""
    import imageio_ffmpeg
    import numpy as np
    from PIL import Image

    key = hashlib.sha256(json.dumps({"sha256": original_sha256, "crop": crop}, sort_keys=True).encode()).hexdigest()[:16]
    output = run / "references" / f"{key}_sampled.mp4"
    evidence_path = output.with_suffix(".json")
    if output.is_file() and evidence_path.is_file():
        return output, json.loads(evidence_path.read_text())
    frames, evidence = sampled_frames(path, crop)
    w, h = frames[0].size
    scale = min(640 / w, 360 / h, 1.)
    size = (max(2, int(w * scale) // 2 * 2), max(2, int(h * scale) // 2 * 2))
    temp = output.with_name(output.stem + ".tmp.mp4")
    writer = imageio_ffmpeg.write_frames(str(temp), size, fps=12, codec="libx264", pix_fmt_out="yuv420p",
                                        macro_block_size=2, output_params=["-crf", "18", "-threads", "2", "-movflags", "+faststart"])
    writer.send(None)
    try:
        for frame in frames:
            writer.send(np.asarray(frame.resize(size, Image.Resampling.LANCZOS)))
    finally:
        writer.close()
    temp.replace(output)
    evidence.update({"original_sha256": original_sha256, "preview_size": list(size),
                     "preview_only_not_inference_input": True})
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    return output, evidence
