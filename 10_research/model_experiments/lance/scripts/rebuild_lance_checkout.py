#!/usr/bin/env python3
"""Recreate or verify the pinned upstream + reviewed DataMake patch.

Owner: ../training_integration.md. Never overwrites an existing checkout.
Model weights and datasets remain outside the source tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "patches/current/source_lock.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(destination, *args):
    return subprocess.check_output(["git", "-C", str(destination), *args], text=True).strip()


def verify(destination, lock, official_only=False):
    actual = git(destination, "rev-parse", "HEAD")
    if actual != lock["upstream_commit"]:
        raise ValueError(f"Unexpected upstream commit: {actual}")
    if official_only:
        if git(destination, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Official-only checkout is not clean")
    else:
        for name, expected in lock["adapted_files_sha256"].items():
            path = destination / name
            if not path.is_file() or sha256(path) != expected:
                raise ValueError(f"Source lock mismatch: {name}")
        changed = set(git(destination, "diff", "HEAD", "--name-only").splitlines())
        added = set(git(destination, "ls-files", "--others", "--exclude-standard").splitlines())
        unexpected = (changed | added) - set(lock["adapted_files_sha256"]) - {"downloads"}
        if unexpected:
            raise ValueError(f"Unrecorded source changes: {sorted(unexpected)}")
        for name in lock["retired_trainers"]:
            if (destination / name).exists():
                raise ValueError(f"Retired trainer reintroduced: {name}")
    return {"status": "passed", "upstream_commit": actual,
            "official_only": official_only, "destination": str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "lance")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--official-only", action="store_true",
                        help="Create clean official code without DataMake modifications")
    args = parser.parse_args()
    destination = args.destination.absolute()
    lock = json.loads(LOCK.read_text())
    patch = LOCK.parent / lock["patch_file"]
    if sha256(patch) != lock["patch_sha256"]:
        raise ValueError("Reviewed patch checksum mismatch")
    if args.verify_only:
        print(json.dumps(verify(destination, lock, args.official_only), indent=2))
        return
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing path: {destination}")
    # A failed checkout remains inspectable; never delete a pre-existing path.
    destination.mkdir(parents=True)
    git(destination, "init", "--quiet")
    git(destination, "remote", "add", "origin", lock["upstream_url"])
    git(destination, "fetch", "--depth=1", "origin", lock["upstream_commit"])
    git(destination, "checkout", "--detach", "--quiet", "FETCH_HEAD")
    if not args.official_only:
        git(destination, "apply", "--check", str(patch))
        git(destination, "apply", str(patch))
        (destination / "downloads").symlink_to(os.path.relpath(ROOT / "models/Lance", destination))
    print(json.dumps(verify(destination, lock, args.official_only), indent=2))


if __name__ == "__main__":
    main()
