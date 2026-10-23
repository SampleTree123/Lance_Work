"""Explicit UE review commands and an on-demand desktop page selector; no monitor."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import time

from modular_outfit_runtime_plan_v2 import read_json, write_json

ROOT = Path(__file__).resolve().parent


def command_payload(plan, action, page=1, start=1, count=10, view="front", playing=False):
    return (f"import sys; sys.path.insert(0, {str(ROOT)!r}); "
            "import importlib; import ue_wardrobe_coverage_review_v1 as w; importlib.reload(w); "
            f"w.run({str(plan.resolve())!r}, action={action!r}, page={page}, start={start}, count={count}, view={view!r}, playing={playing!r})")


def execute(args):
    command = [sys.executable, str(ROOT / "ue_remote_exec.py"), "--project", args.project,
               "--command", command_payload(args.plan, args.action, args.page, args.start, args.count, args.view, args.playing)]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def summarize(plan_path):
    plan = read_json(plan_path)
    digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    expected = {c["review_index"]: c for c in plan["review_selection"]["outfits"]}
    rows = {}
    for path in sorted((plan_path.parent / "assembly").glob("checks_*.json")):
        report = read_json(path)
        if report["plan_sha256"] != digest:
            raise ValueError(f"Stale assembly report: {path}")
        for row in report["rows"]:
            index = row["review_index"]
            if index not in expected or index in rows:
                raise ValueError(f"Unexpected or repeated assembly row: {index}")
            if row["qualified_variant_id"] != expected[index]["qualified_variant_id"]:
                raise ValueError(f"Wrong variant in assembly report: {index}")
            rows[index] = row
    covered = {c["mesh"] for row in rows.values() if row["success"]
               for c in row["application"]["components"] if c["enabled"]}
    required = set(plan["coverage"]["mesh_witnesses"])
    result = {
        "plan_sha256": digest, "expected_outfits": len(expected), "checked_outfits": len(rows),
        "passed_outfits": sum(r["success"] for r in rows.values()),
        "missing_review_indices": sorted(set(expected) - set(rows)),
        "failed_review_indices": sorted(i for i, r in rows.items() if not r["success"]),
        "expected_meshes": len(required), "covered_meshes": len(covered),
        "uncovered_mesh_paths": sorted(required - covered), "unexpected_mesh_paths": sorted(covered - required),
        "visual_acceptance": "pending", "runtime_approved": False,
    }
    result["assembly_checks_complete"] = not any(result[k] for k in (
        "missing_review_indices", "failed_review_indices", "uncovered_mesh_paths", "unexpected_mesh_paths"))
    write_json(plan_path.parent / "assembly_summary.json", result)
    return result


def evaluate_playback_samples(moving, paused):
    errors = []
    expected = {r["actor"] for r in moving[0]["rows"]}
    for sample in moving + paused:
        if {r["actor"] for r in sample["rows"]} != expected:
            errors.append("Review actors changed while sampling")
            return errors
        for row in sample["rows"]:
            for follower in row["followers"]:
                if not follower["leader_is_body"]:
                    errors.append(f"Wrong leader: {row['actor']}:{follower['name']}")
                for bone, point in follower["bones"].items():
                    if bone in row["bones"] and math.dist(point, row["bones"][bone]) > 0.05:
                        errors.append(f"Follower pose mismatch: {row['actor']}:{follower['name']}:{bone}")
    for actor in expected:
        motion = [next(r for r in s["rows"] if r["actor"] == actor) for s in moving]
        stopped = [next(r for r in s["rows"] if r["actor"] == actor) for s in paused]
        if not all(r["playing"] for r in motion) or len({round(r["position"], 4) for r in motion}) < 2:
            errors.append(f"Animation time did not advance: {actor}")
        if not any(math.dist(motion[0]["bones"][bone], r["bones"][bone]) > 0.01
                   for r in motion[1:] for bone in motion[0]["bones"]):
            errors.append(f"Body bones did not move: {actor}")
        if any(r["playing"] for r in stopped) or len({round(r["position"], 4) for r in stopped}) != 1:
            errors.append(f"Animation did not pause: {actor}")
        if any(math.dist(stopped[0]["bones"][bone], r["bones"][bone]) > 0.01
               for r in stopped[1:] for bone in stopped[0]["bones"]):
            errors.append(f"Body bones moved while paused: {actor}")
    return sorted(set(errors))


def verify_playback(args):
    request = argparse.Namespace(**vars(args))
    def call(action, playing=False):
        request.action, request.playing = action, playing
        execute(request)
    def samples(count):
        result = []
        for _ in range(count):
            # Wait outside UE's game thread; never block its animation tick.
            time.sleep(0.7)
            call("sample")
            result.append(read_json(args.plan.parent / "stage" / "playback_sample.json"))
        return result
    try:
        call("view", True)
        moving = samples(3)
        call("view", False)
        paused = samples(2)
        errors = evaluate_playback_samples(moving, paused)
        result = {"plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                  "scope": "current_page_live_time_body_and_follower_bones_play_pause",
                  "moving": moving, "paused": paused, "errors": errors, "success": not errors,
                  "visual_acceptance": "pending"}
        page = read_json(args.plan.parent / "current_page.json")["page"]
        write_json(args.plan.parent / "stage" / f"playback_page_{page:03d}.json", result)
        if errors:
            raise RuntimeError("; ".join(errors))
        return {"success": True, "page": page, "actors": len(moving[0]["rows"])}
    finally:
        call("view", args.playing)


def panel(args):
    import tkinter as tk
    from tkinter import ttk, messagebox
    plan = read_json(args.plan)
    pages = plan["coverage"]["pages"]
    choices = {c["review_index"]: c for c in plan["review_selection"]["outfits"]}
    root = tk.Tk()
    root.title("Wardrobe mesh coverage review")
    root.geometry("850x600")
    root.minsize(700, 500)
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    labels = [f"{p['page']:03d} / {len(pages)}   {p['family_id']}   #{', #'.join(map(str, p['review_indices']))}" for p in pages]
    selector = ttk.Combobox(frame, values=labels, state="readonly", width=90)
    selector.pack(fill="x")
    current = args.plan.parent / "current_page.json"
    selector.current((read_json(current)["page"] if current.exists() else 1) - 1)
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=10)
    details = tk.Text(frame, wrap="word", height=17)
    details.pack(fill="both", expand=True)
    status = tk.StringVar(value="UE stage ready. Select a page and load it.")
    ttk.Label(frame, textvariable=status, wraplength=800).pack(fill="x", pady=8)
    review_id = tk.StringVar()
    review_selector = ttk.Combobox(frame, textvariable=review_id, state="readonly", width=12)
    review_selector.pack(anchor="w")
    note = tk.StringVar()
    ttk.Entry(frame, textvariable=note).pack(fill="x", pady=6)
    decisions_path = args.plan.parent / "manual_review.json"
    digest = hashlib.sha256(args.plan.read_bytes()).hexdigest()

    def display(_event=None):
        indices = pages[selector.current()]["review_indices"]
        review_selector["values"] = [str(i) for i in indices]
        review_selector.current(0)
        lines = []
        for index in indices:
            c = choices[index]
            lines += [f"#{index:03d}  {c['family_display_name']} / {c['group_id']}"]
            lines += [f"  {a['display_name']}\n    {a['source_path']}" for a in c["assets"]]
            lines.append("")
        details.configure(state="normal")
        details.delete("1.0", "end")
        details.insert("1.0", "\n".join(lines))
        details.configure(state="disabled")

    busy = [False]
    loaded_page = [read_json(current)["page"] if current.exists() else None]
    view = tk.StringVar(value="front")
    playing = tk.BooleanVar(value=False)
    preview_state = args.plan.parent / "stage" / "view.json"
    if preview_state.exists():
        saved_view = read_json(preview_state)
        if saved_view.get("page") == loaded_page[0]:
            playing.set(saved_view.get("playing", False))
            view.set(saved_view.get("view", "front"))

    def load(delta=0, view_only=False):
        if busy[0]:
            return
        index = max(0, min(len(pages) - 1, selector.current() + delta))
        if view_only and loaded_page[0] != index + 1:
            messagebox.showwarning("Review", "Load the selected page before changing its view.")
            return
        if not view_only:
            view.set("front")
            playing.set(False)
        requested_view, requested_playing = view.get(), playing.get()
        selector.current(index)
        display()
        busy[0] = True
        status.set(f"Updating UE page {index + 1}...")
        def work():
            try:
                request = argparse.Namespace(**vars(args))
                request.action, request.page = ("view" if view_only else "show"), index + 1
                request.view, request.playing = requested_view, requested_playing
                execute(request)
                root.after(0, lambda: finish(index + 1, None))
            except Exception as exc:
                root.after(0, lambda error=str(exc): finish(None, error))
        threading.Thread(target=work, daemon=True).start()

    def finish(page, error):
        busy[0] = False
        loaded_page[0] = page
        status.set(error or f"UE page {page} loaded. Visual decisions remain manual.")
        if error:
            messagebox.showerror("UE review", error)

    def record(value):
        if busy[0] or loaded_page[0] != selector.current() + 1:
            messagebox.showwarning("Review", "Load this page in UE before recording a decision.")
            return
        if value == "issue" and not note.get().strip():
            messagebox.showwarning("Review", "Enter an issue note first.")
            return
        doc = read_json(decisions_path) if decisions_path.exists() else {"plan_sha256": digest, "decisions": {}}
        if doc["plan_sha256"] != digest:
            raise ValueError("Manual decisions belong to another plan")
        doc["decisions"][review_id.get()] = {"status": value, "note": note.get().strip(),
                                             "at": datetime.now(timezone.utc).isoformat()}
        write_json(decisions_path, doc)
        status.set(f"#{review_id.get()} recorded: {value}")

    ttk.Button(toolbar, text="< Previous", command=lambda: load(-1)).pack(side="left")
    ttk.Button(toolbar, text="Load selected", command=load).pack(side="left", padx=8)
    ttk.Button(toolbar, text="Next >", command=lambda: load(1)).pack(side="left")
    for value in ("front", "side", "back"):
        ttk.Radiobutton(toolbar, text=value.title(), value=value, variable=view,
                        command=lambda: load(view_only=True)).pack(side="left", padx=3)
    ttk.Checkbutton(toolbar, text="Animate", variable=playing,
                    command=lambda: load(view_only=True)).pack(side="left", padx=5)
    actions = ttk.Frame(frame)
    actions.pack(fill="x")
    ttk.Button(actions, text="Accept selected outfit", command=lambda: record("accepted")).pack(side="left")
    ttk.Button(actions, text="Record issue", command=lambda: record("issue")).pack(side="left", padx=8)
    selector.bind("<<ComboboxSelected>>", display)
    def close():
        if busy[0]:
            messagebox.showinfo("Review", "Wait for the current UE command to finish.")
            return
        busy[0] = True
        status.set("Stopping preview and restoring editor settings...")
        def stop():
            try:
                request = argparse.Namespace(**vars(args))
                request.action = "stop"
                execute(request)
                root.after(0, root.destroy)
            except Exception as exc:
                root.after(0, lambda error=str(exc): finish(loaded_page[0], error))
        threading.Thread(target=stop, daemon=True).start()
    root.protocol("WM_DELETE_WINDOW", close)
    display()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--project", default="datatry_02")
    parser.add_argument("--action", choices=("show", "reload", "view", "audit", "summarize", "panel", "sample", "stop", "verify-playback"), default="show")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--view", choices=("front", "side", "back"), default="front")
    parser.add_argument("--playing", action="store_true")
    args = parser.parse_args()
    if args.action == "panel":
        panel(args)
    elif args.action == "summarize":
        print(json.dumps(summarize(args.plan), indent=2))
    elif args.action == "verify-playback":
        print(json.dumps(verify_playback(args), indent=2))
    else:
        print(execute(args))


if __name__ == "__main__":
    main()
