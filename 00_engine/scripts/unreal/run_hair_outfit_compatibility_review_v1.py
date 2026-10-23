"""Desktop selector for the female hair x outfit compatibility review."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading


ROOT = Path(__file__).resolve().parent
LANCE_ROOT = ROOT.parents[2]
PLAN = (
    LANCE_ROOT / "00_engine" / "outputs" / "unreal_character_import"
    / "current_reviews_20261001_v1" / "hair_outfit_compatibility" / "review_plan.json"
)
REPORT_ROOT = PLAN.parent
REMOTE = ROOT / "ue_remote_exec.py"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def remote_command(mode: str, *, case_index: int | None = None, view: str | None = None) -> str:
    worker = "D:/UE/Lance_Work/00_engine/scripts/unreal/ue_build_hair_outfit_compatibility_review_v1.py"
    assignments = [f"DM_HOC_MODE={mode!r}", f"__file__={worker!r}"]
    if case_index is not None:
        assignments.append(f"DM_HOC_CASE_INDEX={case_index!r}")
    if view is not None:
        assignments.append(f"DM_HOC_VIEW={view!r}")
    assignments.append(
        "exec(compile(open(r%r, encoding='utf-8').read(), r%r, 'exec'), globals())"
        % (worker, worker)
    )
    return "; ".join(assignments)


def execute(mode: str, *, case_index: int | None = None, view: str | None = None):
    command = [
        sys.executable,
        str(REMOTE),
        "--project",
        "datatry_02",
        "--command",
        remote_command(mode, case_index=case_index, view=view),
        "--discovery-timeout",
        "30",
    ]
    result = subprocess.run(command, cwd=str(LANCE_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if result.returncode:
        raise RuntimeError((result.stdout or "") + (result.stderr or ""))
    return result.stdout


def panel():
    import tkinter as tk
    from tkinter import ttk, messagebox

    plan = read(PLAN)
    cases = plan["cases"]
    outfits = {x["outfit_index"]: x for x in plan["outfit_targets"]}
    hairs = {x["hair_index"]: x for x in plan["hair_styles"]}
    labels = [
        f"#{c['review_index']:03d}  {outfits[c['outfit_index']]['display_name']} × {hairs[c['hair_index']]['display_name']}"
        for c in cases
    ]
    current_path = REPORT_ROOT / "current_case.json"
    decision_path = REPORT_ROOT / "manual_review.json"
    digest = hashlib.sha256(PLAN.read_bytes()).hexdigest()
    root = tk.Tk()
    root.title("Hair × Outfit Compatibility Review")
    root.geometry("980x720")
    root.minsize(800, 560)
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    selector = ttk.Combobox(frame, values=labels, state="readonly", width=105)
    selector.pack(fill="x")
    selector.current(max(0, min(len(cases) - 1, (read(current_path).get("review_index", 1) - 1) if current_path.exists() else 0)))
    details = tk.Text(frame, wrap="word", height=24)
    details.pack(fill="both", expand=True, pady=8)
    status = tk.StringVar(value="UE compatibility review ready.")
    ttk.Label(frame, textvariable=status, wraplength=900).pack(fill="x")
    note = tk.StringVar()
    ttk.Entry(frame, textvariable=note).pack(fill="x", pady=6)
    busy = [False]
    loaded = [None]

    def selected_case():
        return cases[selector.current()]

    def display():
        c = selected_case()
        o, h = outfits[c["outfit_index"]], hairs[c["hair_index"]]
        lines = [
            f"Review #{c['review_index']:03d} / {len(cases)}",
            f"Outfit: {o['display_name']} ({o['family_display_name']})",
            f"Source: {o['source_path']}",
            f"UE mesh: {', '.join(o['mesh_paths'])}",
            f"Hair: {h['display_name']} ({h['hair_id']})",
            "Hair meshes:",
            *[f"  - {m['name']}: {m['path']}" for m in h["meshes"]],
            "",
            "检查正面、侧面、背面：头发与服装是否穿模，材质和颜色是否正常。",
        ]
        details.configure(state="normal")
        details.delete("1.0", "end")
        details.insert("1.0", "\n".join(lines))
        details.configure(state="disabled")

    def finish(message=None, error=None):
        busy[0] = False
        if error:
            status.set(str(error))
            messagebox.showerror("UE review", str(error))
        else:
            loaded[0] = selected_case()["review_index"]
            status.set(message or f"Loaded review #{loaded[0]:03d}. Visual decision remains manual.")

    def load_case(delta=0):
        if busy[0]:
            return
        index = max(0, min(len(cases) - 1, selector.current() + delta))
        selector.current(index)
        display()
        case_index = cases[index]["review_index"]
        busy[0] = True
        status.set(f"Loading UE review #{case_index:03d}...")
        def work():
            try:
                execute("show", case_index=case_index)
                root.after(0, lambda: finish())
            except Exception as exc:
                root.after(0, lambda error=str(exc): finish(error=error))
        threading.Thread(target=work, daemon=True).start()

    def view(value):
        if busy[0] or loaded[0] is None:
            messagebox.showwarning("Review", "Load a review case first.")
            return
        busy[0] = True
        status.set(f"Changing view to {value}...")
        def work():
            try:
                execute("view", view=value)
                root.after(0, lambda: finish(f"Review #{loaded[0]:03d}, {value} view loaded."))
            except Exception as exc:
                root.after(0, lambda error=str(exc): finish(error=error))
        threading.Thread(target=work, daemon=True).start()

    def record(value):
        if busy[0] or loaded[0] != selected_case()["review_index"]:
            messagebox.showwarning("Review", "Load the selected case in UE before recording.")
            return
        if value == "issue" and not note.get().strip():
            messagebox.showwarning("Review", "Enter an issue note first.")
            return
        doc = read(decision_path) if decision_path.exists() else {"plan_sha256": digest, "decisions": {}}
        if doc.get("plan_sha256") != digest:
            raise RuntimeError("Manual decisions belong to another plan")
        doc["decisions"][str(loaded[0])] = {
            "review_index": loaded[0], "status": value, "note": note.get().strip(),
            "at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write(decision_path, doc)
        status.set(f"#{loaded[0]:03d} recorded as {value}.")

    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x")
    ttk.Button(toolbar, text="Previous", command=lambda: load_case(-1)).pack(side="left")
    ttk.Button(toolbar, text="Load selected", command=load_case).pack(side="left", padx=8)
    ttk.Button(toolbar, text="Next", command=lambda: load_case(1)).pack(side="left")
    for value in ("front", "side", "back"):
        ttk.Button(toolbar, text=value.title(), command=lambda v=value: view(v)).pack(side="left", padx=3)
    actions = ttk.Frame(frame)
    actions.pack(fill="x", pady=6)
    ttk.Button(actions, text="Accept", command=lambda: record("accepted")).pack(side="left")
    ttk.Button(actions, text="Record issue", command=lambda: record("issue")).pack(side="left", padx=8)
    selector.bind("<<ComboboxSelected>>", lambda _event: display())
    def close():
        if busy[0]:
            messagebox.showinfo("Review", "Wait for the current UE command to finish.")
            return
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    display()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("panel", "show", "view"), default="panel")
    parser.add_argument("--case-index", type=int, default=1)
    parser.add_argument("--view", choices=("front", "side", "back"), default="front")
    args = parser.parse_args()
    if args.action == "panel":
        panel()
    elif args.action == "show":
        print(execute("show", case_index=args.case_index))
    else:
        print(execute("view", view=args.view))


if __name__ == "__main__":
    main()
