"""Explicit opt-in entrypoint; never changes the old CFD40 launcher/pointer.

Pass --motion-catalog and --face-registry before the ordinary review arguments.
Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
"""
from pathlib import Path
import argparse
import sys
import motion_library_review_adapter_v1 as adapter


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--motion-catalog', type=Path, required=True)
    parser.add_argument('--face-registry', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    app = adapter.controller(adapter.extension.source(args.motion_catalog), adapter.extension.source(args.face_registry))
    sys.argv = [sys.argv[0]] + remaining
    app.main()


if __name__ == '__main__':
    main()
