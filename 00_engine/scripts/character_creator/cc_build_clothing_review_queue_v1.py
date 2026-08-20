"""Build a fillable human-review queue for the date-filtered clothing library."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = (
    SCRIPT_ROOT.parents[1]
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "clothing_date_reorganization"
    / "reorg_20260811_v1"
)
DEFAULT_MANIFEST = ARTIFACT_ROOT / "manifest.json"
DEFAULT_COPY_MAP = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_2022plus_sorted/COPY_MAP.json"
)
DEFAULT_OUTPUT_DIR = ARTIFACT_ROOT / "human_review"
DEFAULT_PUBLISH_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_2022plus_sorted"
)
V2_ARTIFACT_ROOT = ARTIFACT_ROOT.parent / "reorg_20260811_v2_newest50"
V2_MANIFEST = V2_ARTIFACT_ROOT / "manifest.json"
V2_PUBLISH_ROOT = Path(
    "D:/BaiduNetdiskDownload/\u4eba\u7269\u548c\u670d\u88c5_newest50pct_sorted"
)
V2_COPY_MAP = V2_PUBLISH_ROOT / "COPY_MAP.json"
V2_OUTPUT_DIR = V2_ARTIFACT_ROOT / "human_review"


def write_queue(
    manifest_path: Path,
    copy_map_path: Path,
    output_dir: Path,
    queue_id: str,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    copy_map = json.loads(copy_map_path.read_text(encoding="utf-8"))
    destinations = {row["package_id"]: row["destination"] for row in copy_map}
    packages = [
        package
        for package in manifest["logical_packages"]
        if package["classification"] in {"accepted", "date_unknown"}
    ]
    packages.sort(
        key=lambda package: (
            package["classification"] != "accepted",
            package["logical_sex"],
            package["label"].casefold(),
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "review_order",
        "queue",
        "sex",
        "package_name",
        "result_relative_path",
        "source_type",
        "cc_asset_count",
        "earliest_asset_date",
        "latest_asset_date",
        "duplicate_source_count",
        "review_status",
        "complete_author_look",
        "load_result",
        "generation_popup",
        "visible_clipping",
        "recommended_policy",
        "notes",
    ]
    csv_path = output_dir / f"clothing_human_review_queue_{queue_id}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, package in enumerate(packages, start=1):
            writer.writerow(
                {
                    "review_order": index,
                    "queue": (
                        "01_accepted_first"
                        if package["classification"] == "accepted"
                        else "02_date_unknown_secondary"
                    ),
                    "sex": package["logical_sex"],
                    "package_name": package["label"],
                    "result_relative_path": destinations[package["package_id"]],
                    "source_type": package["source_type"],
                    "cc_asset_count": package["cc_asset_count"],
                    "earliest_asset_date": package["earliest_asset_date"] or "",
                    "latest_asset_date": package["latest_asset_date"] or "",
                    "duplicate_source_count": package["duplicate_source_count"],
                    "review_status": "pending",
                    "complete_author_look": "",
                    "load_result": "",
                    "generation_popup": "",
                    "visible_clipping": "",
                    "recommended_policy": "",
                    "notes": "",
                }
            )

    summary = manifest["summary"]
    accepted_count = summary["logical_counts_by_classification"].get("accepted", 0)
    unknown_count = summary["logical_counts_by_classification"].get("date_unknown", 0)
    excluded_label = (
        "_older_half"
        if manifest.get("classification_policy") == "newest-half-per-sex"
        else "_outdated"
    )
    excluded_count = summary["logical_counts_by_classification"].get(
        "older_half", summary["logical_counts_by_classification"].get("outdated", 0)
    )
    matrix = summary["logical_matrix"]
    accepted_parts = ", ".join(
        f"{sex} {matrix.get(sex, {}).get('accepted', 0)}"
        for sex in ("female", "male", "both")
    )
    guide = output_dir / "人工审查说明.md"
    guide.write_text(
        "# Character Creator 服装人工审查说明\n\n"
        "## 审查顺序\n\n"
        f"1. 先审查三个性别根下的直接条目，共 {accepted_count} 个（{accepted_parts}）。\n"
        f"2. 主队列完成后，再决定是否审查 `_date_unknown` 中的 {unknown_count} 个包。\n"
        f"3. `{excluded_label}` 中 {excluded_count} 个包默认不进入本轮人工审查。\n\n"
        "## 每包记录\n\n"
        "- 是否能正常解压、显示并载入 CC；\n"
        "- 是否提供完整作者 Look，以及包含哪些衣服、鞋、帽子和附件；\n"
        "- 是否出现代际转换弹窗，选择了 `Keep Cloth Shape` 还是 `Fit Body Shape`；\n"
        "- 在作者角色和平均 BodyFit 上是否有明显静态穿模；\n"
        "- 建议保持整套锁定、受限同包替换，还是拒绝；\n"
        "- 暂时不要把不同来源包的 Shirt/Coat 任意组合。\n\n"
        f"填写 `{csv_path.name}` 的空白列即可。\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--copy-map", type=Path, default=DEFAULT_COPY_MAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--publish-root", type=Path, default=DEFAULT_PUBLISH_ROOT)
    parser.add_argument("--queue-id", default="20260811_v1")
    parser.add_argument(
        "--profile", choices=("cutoff-v1", "newest50-v2"), default="cutoff-v1"
    )
    parser.add_argument("--publish", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.profile == "newest50-v2":
        if args.manifest == DEFAULT_MANIFEST:
            args.manifest = V2_MANIFEST
        if args.copy_map == DEFAULT_COPY_MAP:
            args.copy_map = V2_COPY_MAP
        if args.output_dir == DEFAULT_OUTPUT_DIR:
            args.output_dir = V2_OUTPUT_DIR
        if args.publish_root == DEFAULT_PUBLISH_ROOT:
            args.publish_root = V2_PUBLISH_ROOT
        if args.queue_id == "20260811_v1":
            args.queue_id = "20260811_v2_newest50"
    write_queue(args.manifest, args.copy_map, args.output_dir, args.queue_id)
    if args.publish:
        args.publish_root.mkdir(parents=True, exist_ok=True)
        for path in args.output_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, args.publish_root / path.name)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
