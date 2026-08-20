from __future__ import annotations

import argparse
from pathlib import Path

from portal_registry import PortalDataError, register_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and register a visualization run in the local portal."
    )
    parser.add_argument("run_json", type=Path)
    parser.add_argument(
        "--portal-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target, registry = register_run(
            args.run_json,
            args.portal_root,
            replace=args.replace,
        )
    except PortalDataError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"Run: {target}")
    print(f"Registry: {registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
