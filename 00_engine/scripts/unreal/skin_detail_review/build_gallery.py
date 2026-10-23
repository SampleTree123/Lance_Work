"""Experimental skin comparison gallery. Owner: CHARACTER_RUNTIME.md §3.20.

Consumes an explicit manifest, never searches render directories or assumes a
prepared scene is rendered. Reuses camera-pilot hash and decoded-media checks.
"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from encode_camera_pilot_v1 import atomic_json, decode_video, read, sha

VARIANTS = {"A": "A · 原始皮肤", "B": "B · 补回粗糙度", "C": "C · 更换整套皮肤", "B_micro": "B_micro · 微法线诊断"}
CONTRACT = {"decoded_frames": 300, "fps": 30, "measured_duration_seconds": 10, "dimensions": [1920, 1080]}


def local_file(run, value):
    p = Path(value)
    if p.is_absolute():
        raise ValueError("Media paths must be relative to run root")
    p = (run / p).resolve()
    p.relative_to(run)
    if not p.is_file():
        raise FileNotFoundError(p)
    return p


def build(run, manifest, full_decode=False):
    run = Path(run).resolve()
    manifest = Path(manifest).resolve()
    data = read(manifest)
    if data.get("schema") != "skin_detail_review_v1":
        raise ValueError("Unknown manifest schema")
    characters = data["characters"]
    if {x["sex"] for x in characters} != {"male", "female"} or len(characters) != 2:
        raise ValueError("Exactly one male and one female are required")
    if len({x["id"] for x in characters}) != 2:
        raise ValueError("Duplicate character ID")
    gallery = run / "gallery"
    gallery.mkdir(exist_ok=True)
    for character in characters:
        if character["id"] not in {"CFD40_AF_005", "CFD40_LM_002"}:
            raise ValueError("Unexpected frozen representative")
        photo = character.get("photo")
        if photo:
            source = local_file(run, photo["path"])
            if sha(source) != photo["sha256"]:
                raise ValueError("Source photo hash mismatch")
            character["photo_url"] = "../" + source.relative_to(run).as_posix()
    known = {x["id"] for x in characters}
    clips = {}
    for item in data.get("clips", []):
        key = (item["character_id"], item["framing"], item["variant"])
        if key[0] not in known or key[1] not in ("head", "upper") or key[2] not in VARIANTS or key in clips:
            raise ValueError("Unknown/duplicate comparison slot: " + str(key))
        row = dict(item, playable=False)
        if item.get("status") == "encoded_verified":
            video = local_file(run, item["video"])
            receipt_file = local_file(run, item["receipt"])
            if video.suffix.lower() != ".mp4" or sha(video) != item["video_sha256"] or sha(receipt_file) != item["receipt_sha256"]:
                raise ValueError("Video/receipt hash mismatch")
            receipt = read(receipt_file)
            if receipt.get("status") != "encoded_verified" or receipt.get("video_sha256") != item["video_sha256"]:
                raise ValueError("Receipt has no matching verified video")
            if receipt.get("decode") != CONTRACT:
                raise ValueError("Expected 300 frames, 30 fps, 10 seconds, 1920x1080")
            if full_decode and decode_video(video, 1920, 1080) != CONTRACT:
                raise ValueError("Actual full decode differs")
            row.update(playable=True, video_url="../" + video.relative_to(run).as_posix())
            if item.get("poster"):
                poster = local_file(run, item["poster"])
                if not item.get("poster_sha256") or sha(poster) != item["poster_sha256"]:
                    raise ValueError("Poster hash mismatch")
                row["poster_url"] = "../" + poster.relative_to(run).as_posix()
        else:
            # An unverified path must never leak into the playable page.
            for name in ("video", "poster", "video_url", "poster_url"):
                row.pop(name, None)
            row["reason"] = item.get("reason", "尚未完成或尚未核验")
        clips[key] = row
    variants = ["A", "B", "C"] + (["B_micro"] if any(k[2] == "B_micro" for k in clips) else [])
    for character in characters:
        for framing in ("head", "upper"):
            for variant in variants:
                key = (character["id"], framing, variant)
                clips.setdefault(key, {"character_id":key[0], "framing":key[1], "variant":key[2], "status":"pending", "playable":False, "reason":"尚未提交完成媒体"})
    result = {"characters":characters, "variants":[{"id":v,"label":VARIANTS[v]} for v in variants], "clips":list(clips.values()), "input_sha256":sha(manifest), "playable_count":sum(x["playable"] for x in clips.values()), "human_acceptance":"pending", "contract":CONTRACT}
    encoded = json.dumps(result, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = Path(__file__).with_name("gallery.html").read_text(encoding="utf-8").replace("__DATA__", encoded)
    (gallery / "index.html").write_text(html, encoding="utf-8")
    atomic_json(gallery / "gallery_build_receipt_v1.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--full-decode", action="store_true")
    args = parser.parse_args()
    result = build(args.run_root, args.manifest, args.full_decode)
    print(json.dumps({"playable_count":result["playable_count"], "slots":len(result["clips"]), "html":str(args.run_root / "gallery/index.html")}, ensure_ascii=False))
