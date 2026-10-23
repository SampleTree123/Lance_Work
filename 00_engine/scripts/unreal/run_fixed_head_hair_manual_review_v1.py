"""Interactive fixed-head hair review: two reference characters, no captures."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

import formal_wardrobe_registry_v1 as formal

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO = SCRIPT_ROOT.parents[2]
RUN = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_manual_review_20261005_v1"
WORKER = SCRIPT_ROOT / "ue_fixed_head_hair_manual_review_v1.py"
REMOTE = SCRIPT_ROOT / "ue_remote_exec.py"
LEVEL = "/Game/DataMake/Validation/FixedHeadHair/L_DM_FixedHeadHair_ManualReview_v001"
MARKER = "DM_FIXED_HEAD_HAIR_MANUAL_REVIEW="
CONSOLE_PYTHON = (str(Path(sys.executable).with_name("python.exe"))
                  if Path(sys.executable).name.lower() == "pythonw.exe" else sys.executable)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def execute(mode, index=1, view="front", sex="both"):
    worker = str(WORKER.resolve())
    command = "; ".join([
        f"DM_FHMR_MODE={mode!r}", f"DM_FHMR_INDEX={index!r}",
        f"DM_FHMR_VIEW={view!r}", f"DM_FHMR_SEX={sex!r}", f"__file__={worker!r}",
        "DM_FHMR_HAIR_ID=None",
        f"exec(compile(open({worker!r}, encoding='utf-8').read(), {worker!r}, 'exec'), globals())",
    ])
    result = subprocess.run([CONSOLE_PYTHON, str(REMOTE), "--project", "datatry_02",
                             "--command", command, "--discovery-timeout", "20"],
                            cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=180,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-2500:])
    outer = json.loads(result.stdout)
    reply = outer.get("command_result") or {}
    if not reply.get("success"):
        raise RuntimeError(str(reply)[-2500:])
    for output in reversed(reply.get("output") or []):
        line = output.get("output", "")
        if MARKER in line:
            value = json.loads(line.split(MARKER, 1)[1].strip())
            if value.get("success") is not True:
                raise RuntimeError(str(value))
            if mode in ("show", "view") and value.get("viewport_refresh_pending"):
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    current = read(RUN / "current_case.json")
                    if (current.get("hair_id") == value["hair_id"]
                            and current.get("view") == view and current.get("sex") == sex
                            and not current.get("viewport_refresh_pending", True)):
                        return current
                    time.sleep(.1)
                raise RuntimeError("UE 视口刷新未完成，请检查编辑器是否有阻塞弹窗。")
            return value
    raise RuntimeError("UE 未返回审查结果，请确认关卡和 Python 远程执行正常。")


def panel(initial_index=None):
    import tkinter as tk
    from tkinter import messagebox, ttk

    # Historical 40-style / 80-fit review, independent of the reviewed pool.
    registry_path = formal.MATERIAL_REPAIR_REGISTRY
    registry = formal.read_registry(registry_path)
    hairs = sorted(registry["hair_assets"], key=lambda item: item["hair_id"])
    if len(hairs) != 40 or any(set(h.get("fit_variants", {})) != {"female", "male"} for h in hairs):
        raise RuntimeError("需要完整的 40 款男女双版本发型索引。")
    registry_sha = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    current_path = RUN / "current_case.json"
    index = initial_index or (read(current_path).get("index", 1) if current_path.exists() else 1)
    index = max(1, min(len(hairs), index))
    root = tk.Tk()
    root.title("固定头型发型审查 · 男女适配")
    root.geometry("800x560")
    root.minsize(720, 510)
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="逐款检查同一发型的男女版本，可分别放大观察。", font=("Microsoft YaHei UI", 12)).pack(anchor="w")
    selector = ttk.Combobox(frame, state="readonly", values=[
        f"{i:02d} / 40   {h['hair_id']} · {h['display_name']}" for i, h in enumerate(hairs, 1)])
    selector.pack(fill="x", pady=(12, 8))
    selector.current(index - 1)
    controls = []
    selection_line = tk.StringVar()
    ttk.Label(frame, textvariable=selection_line, wraplength=730).pack(anchor="w", pady=4)
    status = tk.StringVar(value="正在连接 UE…")
    ttk.Label(frame, textvariable=status, wraplength=730).pack(anchor="w", pady=8)
    note = tk.StringVar()
    target = ["both"]
    view = ["front"]
    loaded = [None]
    busy = [False]
    closing = [False]
    inbox = queue.Queue()

    def update_line():
        hair = hairs[selector.current()]
        category = {"male": "男性", "female": "女性", "both": "男女通用"}[hair["sex"]]
        selection_line.set(f"使用分类：{category}。本界面展示两个适配版本，审查不改变原使用分类。")

    def enable(value):
        selector.configure(state="readonly" if value else "disabled")
        for button in controls:
            button.configure(state="normal" if value else "disabled")

    def submit(mode, new_index=None, new_view=None, new_target=None):
        if busy[0]:
            return
        if new_index is not None:
            selector.current(max(0, min(len(hairs) - 1, new_index - 1)))
        if new_view is not None:
            view[0] = new_view
        if new_target is not None:
            target[0] = new_target
        selected = selector.current() + 1
        update_line()
        busy[0] = True
        enable(False)
        status.set("正在更新 UE…" if mode != "restore" else "正在恢复编辑器设置…")
        requested_view, requested_target = view[0], target[0]

        def work():
            try:
                reply = execute(mode, selected, requested_view, requested_target)
                if mode != "restore" and reply.get("hair_id") != hairs[selected - 1]["hair_id"]:
                    raise RuntimeError("UE 当前发型与面板选择不一致。")
                inbox.put((mode, selected, reply, None))
            except Exception as exc:
                inbox.put((mode, selected, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll():
        try:
            mode, selected, result, error = inbox.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        busy[0] = False
        enable(True)
        if error:
            if mode == "restore" and closing[0]:
                write(RUN / "restore_error.json", {"error": error, "note": "Panel closed; UE settings restoration could not be confirmed."})
                root.destroy()
                return
            closing[0] = False
            status.set("未完成：" + error[:250])
            messagebox.showerror("发型审查", error)
        elif mode == "restore" and closing[0]:
            root.destroy()
            return
        else:
            loaded[0] = selected
            names = {"front": "正面", "side": "侧面", "back": "背面", "threequarter": "斜侧面"}
            sexes = {"both": "男女同屏", "female": "女性放大", "male": "男性放大"}
            status.set(f"已加载 {selected:02d}/40 · {names[view[0]]} · {sexes[target[0]]}。请在 UE 中观察。")
            write(RUN / "panel_state.json", {"index": selected, "hair_id": hairs[selected - 1]["hair_id"],
                  "view": view[0], "sex": target[0], "registry_sha256": registry_sha,
                  "updated_at": datetime.now(timezone.utc).isoformat()})
        root.after(100, poll)

    def button(row, text, action):
        value = ttk.Button(row, text=text, command=action)
        value.pack(side="left", padx=(0, 8), pady=4)
        controls.append(value)

    navigation = ttk.Frame(frame)
    navigation.pack(fill="x", pady=4)
    button(navigation, "上一款", lambda: submit("show", selector.current()))
    button(navigation, "重新加载", lambda: submit("show"))
    button(navigation, "下一款", lambda: submit("show", selector.current() + 2))
    angles = ttk.Frame(frame)
    angles.pack(fill="x", pady=4)
    for label, value in (("正面", "front"), ("侧面", "side"), ("背面", "back"), ("斜侧面", "threequarter")):
        button(angles, label, lambda v=value: submit("view", new_view=v))
    focus = ttk.Frame(frame)
    focus.pack(fill="x", pady=4)
    for label, value in (("男女同屏", "both"), ("女性放大", "female"), ("男性放大", "male")):
        button(focus, label, lambda v=value: submit("view", new_target=v))
    ttk.Separator(frame).pack(fill="x", pady=8)
    ttk.Label(frame, text="可选：记录结论；也可以检查后直接在对话中告诉我。问题备注：").pack(anchor="w")
    ttk.Entry(frame, textvariable=note).pack(fill="x", pady=4)

    def record(sex, outcome):
        selected = selector.current() + 1
        if busy[0] or loaded[0] != selected:
            messagebox.showinfo("审查记录", "请等待当前发型加载完成。")
            return
        if hashlib.sha256(registry_path.read_bytes()).hexdigest() != registry_sha:
            messagebox.showerror("审查记录", "资产索引已变化，请重新打开面板。")
            return
        path = RUN / "manual_review.json"
        document = read(path) if path.exists() else {"schema_version": 1, "level": LEVEL,
            "registry": str(registry_path), "registry_sha256": registry_sha, "decisions": {}}
        if document.get("registry_sha256") != registry_sha:
            messagebox.showerror("审查记录", "已有记录属于另一版索引，不能覆盖。")
            return
        hair = hairs[selected - 1]
        document["decisions"].setdefault(hair["hair_id"], {})[sex] = {
            "status": outcome, "note": note.get().strip(), "index": selected,
            "recorded_at": datetime.now(timezone.utc).isoformat()}
        write(path, document)
        status.set(f"已记录 {hair['hair_id']} 的{'女性' if sex == 'female' else '男性'}版本：{'正常' if outcome == 'accepted' else '有问题'}。")
    records = ttk.Frame(frame)
    records.pack(fill="x")
    for label, sex, result in (("女性正常", "female", "accepted"), ("女性有问题", "female", "issue"),
                               ("男性正常", "male", "accepted"), ("男性有问题", "male", "issue")):
        button(records, label, lambda s=sex, r=result: record(s, r))
    selector.bind("<<ComboboxSelected>>", lambda _event: submit("show"))

    def close():
        if busy[0]:
            messagebox.showinfo("发型审查", "请等待当前操作完成，再关闭面板。")
            return
        closing[0] = True
        submit("restore")
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.after(250, lambda: submit("show"))
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("panel", "show", "view", "status", "restore"), default="panel")
    parser.add_argument("--hair-index", type=int)
    parser.add_argument("--view", choices=("front", "side", "back", "threequarter"), default="front")
    parser.add_argument("--sex", choices=("both", "female", "male"), default="both")
    args = parser.parse_args()
    if args.hair_index is not None and not 1 <= args.hair_index <= 40:
        parser.error("--hair-index 必须为 1..40")
    if args.action == "panel":
        panel(args.hair_index)
    else:
        print(json.dumps(execute(args.action, args.hair_index or 1, args.view, args.sex), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write(RUN / "panel_error.json", {"error": str(exc), "at": datetime.now(timezone.utc).isoformat()})
        raise
