"""Reject blank probe captures; this is not garment fit or production approval."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def image_content(image):
    rgb = image.convert("RGB")
    gray = rgb.convert("L")
    histogram = gray.histogram()
    nonblack = sum(histogram[16:])
    stats = ImageStat.Stat(gray)
    valid = nonblack >= 1000 and stats.stddev[0] >= 3.0
    return {"size": list(rgb.size), "grayscale_mean": stats.mean[0],
            "grayscale_stddev": stats.stddev[0], "pixels_above_15": nonblack,
            "pixel_content_valid": valid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    output = args.root / "pixel_validation.json"
    if output.exists():
        raise FileExistsError(output)
    images, rows = {}, {}
    for subject in ("baseline", "derivative"):
        for view in ("front", "back"):
            key = f"{subject}_{view}"
            source = args.root / f"{key}.png"
            images[key] = Image.open(source).convert("RGB")
            rows[key] = {**image_content(images[key]), "path": str(source.resolve()),
                         "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    pairs = {}
    for view in ("front", "back"):
        a, b = images[f"baseline_{view}"], images[f"derivative_{view}"]
        same_size = a.size == b.size
        valid = same_size and all(rows[f"{subject}_{view}"]["pixel_content_valid"]
                                  for subject in ("baseline", "derivative"))
        pairs[view] = {"comparison_meaningful": valid, "same_size": same_size,
                       "rgb_mean_absolute_difference": ImageStat.Stat(ImageChops.difference(a, b)).mean if same_size else None}
    result = {"schema_version": 1, "pixel_content_valid": all(v["comparison_meaningful"] for v in pairs.values()),
              "images": rows, "pairs": pairs, "runtime_approved": False}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pixel_content_valid": result["pixel_content_valid"], "report": str(output)}))
    return 0 if result["pixel_content_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
