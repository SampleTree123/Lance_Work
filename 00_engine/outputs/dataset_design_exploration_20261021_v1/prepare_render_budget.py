"""Offline planning arithmetic and catalog counts; never imports Unreal.

Lifecycle: experimental. Owner: DATASET_DESIGN_EXPLORATION_20261021.md.
Run from any directory; all generated outputs remain beside this script.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def main():
    inventory = read(RUN / "inventory/normalized_inventory.json")
    appearance = read(RUN / "inventory/appearance_catalog.json")
    motion_path = ROOT / "00_engine/assets/character_creator/production_motion_library_20261017_v1.json"
    motions = [m for m in read(motion_path)["motions"]
               if m["motion_id"] in inventory["actions"]]
    garments, shoes = {}, {}
    for sex in ("female", "male"):
        garments[sex] = sorted({a for p in appearance["presets_by_sex"][sex]
                               for a in p["canonical_choice"]["family_asset_ids"]})
        shoes[sex] = sorted({p["choice"]["shared_shoe_id"]
                            for p in appearance["presets_by_sex"][sex]
                            if p["choice"]["shared_shoe_id"]})
    all_hair = {r["hair_id"] for rows in appearance["hairs_by_sex"].values() for r in rows}
    summary = {
        "status": "read_only_inventory_not_visual_acceptance",
        "identities": len(inventory["identities"]),
        "identity_sexes": dict(Counter(r["sex"] for r in inventory["identities"])),
        "active_semantic_motions": len(inventory["actions"]),
        "motion_sex_variants": sum(len(v) for v in inventory["action_sexes"].values()),
        "camera_presets": len(inventory["cameras"]),
        "aspects": inventory["aspects"],
        "hair_colors": inventory["hair_colors"],
        "hair_catalog_entries": {k: len(v) for k, v in appearance["hairs_by_sex"].items()},
        "unique_hair_ids": len(all_hair),
        "outfit_presets": {k: len(v) for k, v in appearance["presets_by_sex"].items()},
        "preset_referenced_family_asset_ids": {k: len(v) for k, v in garments.items()},
        "preset_referenced_shared_shoes": {k: len(v) for k, v in shoes.items()},
        "garment_count_caveat": "Registry IDs can be bundles/material variants; not all independent garment edits.",
        "production10_rule_counts": dict(Counter(m["production10"]["rule"] for m in motions)),
        "production10_status_caveat": "Contract timing only, not proof every production bake/render has passed.",
        "motion_source": {"path": str(motion_path),
                          "sha256": hashlib.sha256(motion_path.read_bytes()).hexdigest()},
    }
    write(RUN / "inventory/summary.json", summary)

    # No bitrate, time-per-frame, AA count, resolution or duration is frozen here.
    candidates = []
    for duration in (5, 10):
        for fps in (24, 30):
            for width, height in ((1280, 720), (1920, 1080), (2560, 1440)):
                frames = 3000 * duration * fps
                candidates.append({
                    "main_video_nodes": 3000, "duration_seconds": duration, "fps": fps,
                    "width": width, "height": height, "output_frames": frames,
                    "uncompressed_rgb8_decimal_gb": frames * width * height * 3 / 1e9,
                    "compressed_main_decimal_gb_if_measured_Mbps": {
                        str(mbps): 3000 * duration * mbps / 8 / 1000
                        for mbps in (8, 16, 32)},
                    "frame_only_gpu_hours_if_measured_seconds_per_frame": {
                        str(t): frames * t / 3600 for t in (0.1, 0.5, 1.0)},
                })
    budget = {
        "status": "scenario_arithmetic_not_benchmark",
        "budget_scope_requires_user_decision": True,
        "default": "3000 main graph nodes; additional reference videos/images counted separately.",
        "main_only_candidates": candidates,
        "per_job_known_policy": {"engine_warmup_frames": 120, "render_warmup_samples": 32},
        "warmup_arithmetic": {
            "if_one_job_per_main_node_engine_warmup_frames": 3000 * 120,
            "if_one_job_per_main_node_render_warmup_samples": 3000 * 32,
            "warning": "Engine ticks and render samples differ from output frames; never sum as equivalent cost.",
        },
        "total_time_formula": "sum(load_and_setup_j + warmup_j + output_frames_j * measured_seconds_per_frame_j + encode_j)",
        "total_video_count_formula": "unique(main_video_keys union reference_video_keys)",
        "reference_count_policy": "Deduplicate actual sampled edge requests, do not multiply full catalogs.",
        "storage_exclusions": ["reference media", "temporary frame sequences", "depth/masks if later chosen",
                               "asset backups", "render retry space"],
    }
    write(RUN / "render_budget_scenarios.json", budget)
    assert summary["identities"] == 40 and summary["active_semantic_motions"] == 25
    assert summary["unique_hair_ids"] == 28
    assert len(candidates) == 12
    print(json.dumps({"counts": summary, "budget_scenarios": len(candidates)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
