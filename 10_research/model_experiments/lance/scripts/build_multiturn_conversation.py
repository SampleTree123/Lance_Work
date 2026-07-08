#!/usr/bin/env python3
"""Build a Lance multi-turn conversation JSON for quick smoke tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_prompt_lines(path: Path) -> list[str]:
    prompts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            prompts.append(line)
    return prompts


def resolve_file(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    resolved = resolved.resolve()
    if not resolved.is_file():
        raise SystemExit(f"file not found: {resolved}")
    return resolved


def load_prompts(args: argparse.Namespace) -> list[str]:
    if args.prompt and args.prompts_file:
        raise SystemExit("use --prompt or --prompts-file, not both")
    if args.prompts_file:
        prompts = read_prompt_lines(resolve_file(args.prompts_file))
    else:
        prompts = [p.strip() for p in (args.prompt or []) if p.strip()]
    if not prompts:
        raise SystemExit("no prompts provided")
    return prompts


def build_video_edit_conversation(video: Path, prompts: list[str]) -> dict:
    turns = []
    for idx, prompt in enumerate(prompts):
        content = [{"type": "text", "value": prompt}]
        if idx == 0:
            content.insert(0, {"type": "video", "value": str(video)})
        turns.append(
            {
                "role": "user",
                "action": "edit_video",
                "content": content,
            }
        )
    return {
        "system_prompt": None,
        "turns": turns,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Initial source video.")
    parser.add_argument("--prompt", action="append", default=[], help="One edit prompt. Repeat for multiple turns.")
    parser.add_argument("--prompts-file", help="Prompt file; one non-empty non-comment line per turn.")
    parser.add_argument("--output", required=True, help="Output conversation JSON path.")
    args = parser.parse_args()

    video = resolve_file(args.video)
    prompts = load_prompts(args)
    payload = build_video_edit_conversation(video, prompts)

    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
