"""Check native derivative evidence without weakening geometry or skin comparisons."""
from pathlib import Path
import argparse
import hashlib
import json
import math

MATRIX_TOLERANCE = 1e-10


def compare(left, right, path=()):
    errors, rounded = [], []
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        pairs = ((left[k], right[k], path + (str(k),)) for k in left)
    elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        pairs = ((a, b, path + (str(i),)) for i, (a, b) in enumerate(zip(left, right)))
    else:
        if any(isinstance(x, float) and not math.isfinite(x) for x in (left, right)):
            return ["/".join(path) + ": nonfinite"], []
        if type(left) is type(right) and left == right:
            return [], []
        numeric = all(type(x) in (float, int) for x in (left, right))
        if numeric and len(path) >= 2 and path[-2] in {"transform", "link_transform", "global"}:
            delta = abs(left - right)
            if delta <= MATRIX_TOLERANCE:
                return [], [{"path": "/".join(path), "absolute_delta": delta}]
        return ["/".join(path) + ": mismatch"], []
    for a, b, p in pairs:
        e, r = compare(a, b, p)
        errors.extend(e)
        rounded.extend(r)
    return errors, rounded


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--native-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    case = next(c for c in manifest["cases"] if c["case_id"] == args.case_id)
    native = json.loads(args.native_report.read_text(encoding="utf-8"))
    source = Path(native["source"])
    derived = Path(native["output"])
    if source.resolve() != Path(case["export"]["fbx"]["path"]).resolve():
        raise ValueError("Native source differs from manifest")
    if digest(source) != case["export"]["fbx"]["sha256"]:
        raise ValueError("Original export changed")
    if derived.resolve() == source.resolve():
        raise ValueError("Derivative must not be the original")
    errors, rounded = compare(native["before_export"], native["after_reload"])
    if not native["before_export"]["meshes"]:
        errors.append("Empty selected geometry")
    result = {"schema_version": 1, "case_id": args.case_id, "success": not errors,
              "native_report": str(args.native_report.resolve()), "native_report_sha256": digest(args.native_report),
              "source": str(source), "source_sha256": digest(source),
              "derivative": str(derived), "derivative_sha256": digest(derived),
              "matrix_absolute_tolerance": MATRIX_TOLERANCE, "matrix_rounding": rounded,
              "errors": errors, "runtime_approved": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"success": not errors, "errors": errors[:5], "matrix_rounding_count": len(rounded)}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
