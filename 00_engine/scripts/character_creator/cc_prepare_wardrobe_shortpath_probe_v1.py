"""Clone one frozen export case to an isolated short destination for diagnosis."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def prepare(source, case_id, destination, output_manifest):
    source, destination, output_manifest = source.resolve(), destination.resolve(), output_manifest.resolve()
    if destination.exists() or output_manifest.exists():
        raise FileExistsError("Probe destination and manifest must be new; preserve existing evidence")
    raw = source.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"))
    cases = [p for p in value["presets"] if p["preset_id"] == case_id]
    if len(cases) != 1:
        raise ValueError("Select exactly one known case")
    case = copy.deepcopy(cases[0])
    previous = copy.deepcopy(case["production_output"])
    original_root = Path(previous["export_root"]).resolve()
    if destination == original_root or original_root in destination.parents or destination in original_root.parents:
        raise ValueError("Probe must be isolated from the original export")
    case["production_output"]["export_root"] = str(destination / "fbx")
    case["production_output"]["project_path"] = str(destination / (previous["export_basename"] + ".ccProject"))
    value["presets"] = [case]
    value["counts"] = {"case_count": 1}
    value["output_root"] = str(destination)
    value["shortpath_probe"] = {
        "source_manifest": str(source), "source_sha256": hashlib.sha256(raw).hexdigest(),
        "original_production_output": previous, "not_production_acceptance": True,
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with output_manifest.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.case_id, args.destination, args.output_manifest)
