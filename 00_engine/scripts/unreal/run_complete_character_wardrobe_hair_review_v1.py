"""Visible review controls for existing complete characters; never launch UE or CC."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
import uuid

from ue_remote_exec import DEFAULT_ENGINE_ROOT, load_remote_execution

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO = SCRIPT_ROOT.parents[2]
ROOT = REPO / "00_engine/outputs/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1"
WORKER = SCRIPT_ROOT / "ue_complete_character_wardrobe_hair_review_v1.py"
LEVEL = "/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001"
MARKER = "DM_CC_WARDROBE_HAIR_REVIEW="
PROJECT = "datatry_02"
DEFAULT_USER = "Macheniek"
COMMAND_TIMEOUT = 120
ACTIONS = ("show", "view", "playback", "sample", "audit", "reload", "restore", "status")
DEFAULT_CASE = {"female_outfit": 1, "male_outfit": 1, "hair_index": 2,
                "action_index": 0, "view": "front", "focus": "both",
                "framing": "full", "playing": False}
REMOTE_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def record_error(exc, stage, trace=None):
    write(ROOT / "controller_error.json", {"at": now(), "pid": os.getpid(),
          "stage": stage, "error_type": type(exc).__name__, "error": str(exc),
          "traceback": trace if trace is not None else traceback.format_exc()})


def load_catalog():
    from complete_character_review_contract_v1 import catalog
    data = catalog()
    for key in ("female_outfits", "male_outfits", "hairs"):
        rows = data[key]
        if not rows or [row["index"] for row in rows] != list(range(1, len(rows) + 1)):
            raise ValueError(f"审查目录索引不连续：{key}。")
    for sex in ("female", "male"):
        rows = data["actions_by_sex"][sex]
        if not rows or [row["index"] for row in rows] != list(range(1, len(rows) + 1)):
            raise ValueError(f"{sex} 身体动作目录索引不连续。")
    if len(data["actions_by_sex"]["female"]) != len(data["actions_by_sex"]["male"]):
        raise ValueError("男女动作目录数量不一致，无法按编号配对。")
    if not data.get("sources"):
        raise ValueError("审查目录缺少来源与哈希。")
    return data


def initial_case(overrides=None):
    case = dict(DEFAULT_CASE)
    current = ROOT / "current_case.json"
    if current.is_file():
        saved = read(current)
        saved = saved.get("request", saved.get("case", saved))
        case.update({key: saved[key] for key in case if key in saved})
    case.update({key: value for key, value in (overrides or {}).items()
                 if key in case and value is not None})
    return case


def validate_request(request, data=None):
    if request.get("action") not in ACTIONS:
        raise ValueError("不支持的审查操作。")
    data = data if data is not None else load_catalog()
    bounds = {"female_outfit": len(data["female_outfits"]),
              "male_outfit": len(data["male_outfits"]), "hair_index": len(data["hairs"]),
              "action_index": len(data["actions_by_sex"]["female"])}
    for key, maximum in bounds.items():
        value = request.get(key)
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f"{key} 必须为 0..{maximum}。")
    for key, choices in (("view", ("front", "side", "back", "threequarter")),
                         ("focus", ("both", "female", "male")), ("framing", ("full", "head"))):
        if request.get(key) not in choices:
            raise ValueError(f"无效的 {key}。")
    if type(request.get("playing")) is not bool:
        raise ValueError("playing 必须为布尔值。")
    return request


def select_node(nodes, node_id=None, pinned=None):
    """Fail closed on missing/stale pins or ambiguity; never switch editor implicitly."""
    selected_id = node_id or (pinned or {}).get("node_id")
    candidates = [node for node in nodes if node.get("project_name") == PROJECT]
    if selected_id:
        candidates = [node for node in candidates if node.get("node_id") == selected_id]
    else:
        candidates = [node for node in candidates if node.get("user") == DEFAULT_USER]
    if len(candidates) != 1:
        reason = "未找到已固定的 UE 实例；确认实例后用 --node-id 指定" if selected_id else "需要唯一的 Macheniek / datatry_02 实例"
        raise RuntimeError(f"{reason}。匹配数量：{len(candidates)}。")
    return candidates[0]


@contextmanager
def command_lock():
    """Serialize threads and prevent concurrent panel/CLI sends from this controller."""
    with REMOTE_LOCK:
        ROOT.mkdir(parents=True, exist_ok=True)
        with (ROOT / "remote.lock").open("a+b") as handle:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise RuntimeError("另一个审查命令尚未完成，请等待后重试。") from exc
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def command_payload(request):
    return (f"import sys, runpy\nsys.path.insert(0, {str(SCRIPT_ROOT)!r})\n"
            f"runpy.run_path({str(WORKER)!r}, run_name='__main__', "
            f"init_globals={{'DM_CC_REVIEW_REQUEST': {request!r}}})")


def parse_reply(reply, request):
    if reply.get("success") is not True:
        raise RuntimeError("UE 执行失败：" + str(reply)[-2500:])
    for item in reversed(reply.get("output") or []):
        output = item.get("output", "")
        if MARKER not in output:
            continue
        result, _ = json.JSONDecoder().raw_decode(output.split(MARKER, 1)[1].lstrip())
        if not isinstance(result, dict):
            raise RuntimeError("审查完成标记不是有效对象。")
        if result.get("success") is not True:
            raise RuntimeError("审查未完成：" + json.dumps(result, ensure_ascii=False)[-2500:])
        if "result_file" in result:
            raw_path = result["result_file"]
            if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
                raise RuntimeError("审查结果文件必须是 replies 目录中的绝对路径。")
            try:
                result_path = Path(raw_path).resolve(strict=True)
                reply_root = (ROOT / "replies").resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise RuntimeError("审查结果文件不存在或无法解析。") from exc
            if (result_path.parent != reply_root or result_path.suffix.lower() != ".json"
                    or not result_path.is_file()):
                raise RuntimeError("审查结果文件必须位于本次审查的 replies 目录内。")
            result = read(result_path)
            if not isinstance(result, dict) or result.get("success") is not True:
                raise RuntimeError("审查未完成：" + json.dumps(result, ensure_ascii=False)[-2500:])
        actual = result.get("request")
        if actual:
            mismatches = [key for key in DEFAULT_CASE if key in actual and actual[key] != request[key]]
            if mismatches:
                raise RuntimeError("UE 返回选择与请求不一致：" + ", ".join(mismatches))
        return result
    raise RuntimeError("UE 未返回本审查工具的完成标记；不会自动重试。")


def execute(request, node_id=None):
    validate_request(request)
    if not WORKER.is_file():
        raise FileNotFoundError(f"审查执行脚本尚未就绪：{WORKER}")
    with command_lock():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        log = ROOT / f"remote_{stamp}_{uuid.uuid4().hex[:8]}.json"
        envelope = {"started_at": now(), "request": request, "success": False}
        remote_module = load_remote_execution(DEFAULT_ENGINE_ROOT.resolve())
        session = remote_module.RemoteExecution()
        session_path = ROOT / "session.json"
        pinned = read(session_path) if session_path.is_file() else None
        try:
            session.start()
            deadline = time.monotonic() + 12
            first_match = None
            last_error = None
            while time.monotonic() < deadline:
                nodes = list(session.remote_nodes)
                try:
                    node = select_node(nodes, node_id, pinned)
                    first_match = first_match or time.monotonic()
                    if time.monotonic() - first_match >= 2:
                        break
                except RuntimeError as exc:
                    first_match, last_error = None, exc
                time.sleep(.2)
            else:
                raise last_error or RuntimeError("UE 远程发现未完成。")
            node = select_node(list(session.remote_nodes), node_id, pinned)
            envelope["node"] = node
            write(session_path, {"node_id": node["node_id"], "project": PROJECT,
                                 "user": node.get("user"), "node": node, "pinned_at": now()})
            session.open_command_connection(node["node_id"])
            # UE's public run_command has no timeout parameter; bound its documented
            # implementation's accepted socket without modifying the engine module.
            channel = session._command_connection._command_channel_socket
            channel.settimeout(COMMAND_TIMEOUT)
            reply = session.run_command(command_payload(request), unattended=True,
                                        exec_mode=remote_module.MODE_EXEC_FILE, raise_on_failure=False)
            envelope["command_result"] = reply
            result = parse_reply(reply, request)
            envelope.update(success=True, result=result)
            return result
        except Exception as exc:
            envelope["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            envelope["finished_at"] = now()
            try:
                session.stop()
            finally:
                write(log, envelope)


def panel(args):
    import tkinter as tk
    from tkinter import ttk

    data = load_catalog()
    sources_sha = digest(data["sources"])
    case = initial_case(vars(args))
    # Restoring a previous case must not unexpectedly restart its last animation.
    case["action_index"] = args.action_index if args.action_index is not None else 0
    case["playing"] = bool(args.playing) and case["action_index"] != 0
    validate_request(dict(case, action="show"), data)
    root = tk.Tk()
    lifecycle = {"pid": os.getpid(), "started_at": now(), "sources_sha256": sources_sha}

    def checkpoint(stage, **details):
        lifecycle.update(stage=stage, updated_at=now(), **details)
        write(ROOT / "panel_lifecycle.json", lifecycle)

    checkpoint("window_created", initial_case=case)
    root.title("完整角色 · 旧服装与发型审查")
    root.geometry("940x710")
    root.minsize(850, 670)
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="在 UE 中检查这两位完整角色的衣服、发型和身体动作。",
              font=("Microsoft YaHei UI", 12)).pack(anchor="w")
    ttk.Label(frame, text="更换选项后自动显示；检查结果单独记录。关闭面板不会关闭 UE。").pack(anchor="w", pady=(4, 10))
    selectors, controls = {}, []
    status = tk.StringVar(value="准备连接用户的 UE 实例…")
    detail = tk.StringVar()
    note = tk.StringVar()
    inbox = queue.Queue()
    state = {"busy": False, "closing": False, "loaded": None, "reply": None}

    def callback_error(exc_type, exc, trace):
        record_error(exc, "tk_callback", "".join(traceback.format_exception(exc_type, exc, trace)))
        checkpoint("callback_failed", error=str(exc))
        status.set("面板操作未完成，错误详情已保存：" + str(exc)[:300])
    root.report_callback_exception = callback_error

    def add_selector(key, label, labels):
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=10).pack(side="left")
        box = ttk.Combobox(row, state="readonly", values=labels)
        box.pack(side="left", fill="x", expand=True)
        box.current(case[key])
        selectors[key] = box
        box.bind("<<ComboboxSelected>>", lambda _event: submit("show"))

    for sex, label in (("female", "女性服装"), ("male", "男性服装")):
        add_selector(sex + "_outfit", label, ["0 · 不穿外层服装"] +
                     [f"{row['index']:02d} · {row['label']}" for row in data[sex + "_outfits"]])
    add_selector("hair_index", "发型", ["0 · 无发型"] +
                 [f"{row['index']:02d} · {row['hair_id']} · {row['display_name']}" for row in data["hairs"]])
    female_actions, male_actions = (data["actions_by_sex"][sex] for sex in ("female", "male"))
    add_selector("action_index", "身体动作", ["0 · 静态姿势"] +
                 [f"{f['index']} · 女：{f['label']}   /   男：{m['label']}"
                  for f, m in zip(female_actions, male_actions)])
    ttk.Label(frame, textvariable=detail, wraplength=880).pack(anchor="w", pady=8)

    def current():
        return dict(case, **{key: box.current() for key, box in selectors.items()})

    def describe():
        selected = current()
        denied = []
        for sex, label in (("female", "女性"), ("male", "男性")):
            index = selected[sex + "_outfit"]
            if index and data[sex + "_outfits"][index - 1].get("hair_deny"):
                denied.append(label)
        hair = data["hairs"][selected["hair_index"] - 1] if selected["hair_index"] else None
        classification = {"female": "女性", "male": "男性", "both": "男女通用"}.get((hair or {}).get("sex"), "")
        parts = [f"发型原使用分类：{classification}；此处可检查两个适配版本。"] if hair else ["当前不装配发型。"]
        if denied and hair:
            parts.append("已选服装禁止独立发型：" + "、".join(denied) + "；以实际装配结果为准。")
        detail.set(" ".join(parts))

    def enabled(value):
        for box in selectors.values():
            box.configure(state="readonly" if value else "disabled")
        for button in controls:
            button.configure(state="normal" if value else "disabled")

    def submit(action, **updates):
        if state["busy"]:
            return
        case.update(updates)
        if selectors["action_index"].current() == 0:
            case["playing"] = False
        request = validate_request(dict(current(), action=action), data)
        describe()
        state["busy"] = True
        enabled(False)
        status.set("正在恢复编辑器设置…" if action == "restore" else "正在更新 UE，请稍候…")
        def work():
            try:
                reply = execute(request, args.node_id)
                inbox.put((request, reply, None))
            except Exception as exc:
                inbox.put((request, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll():
        try:
            request, reply, error = inbox.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        state["busy"] = False
        enabled(not state["closing"])
        if error:
            checkpoint("load_failed", request=request, error=error)
            status.set("未完成：" + error[:420])
            state["loaded"], state["reply"] = None, None
            if request["action"] == "restore" and state["closing"]:
                write(ROOT / "restore_error.json", {"at": now(), "error": error,
                      "note": "Panel closed; UE remains open; CPU restoration not confirmed."})
                root.destroy()
                return
        elif request["action"] == "restore" and state["closing"]:
            root.destroy()
            return
        else:
            checkpoint("ready", request=request, error=None)
            case.update({key: request[key] for key in DEFAULT_CASE})
            state["loaded"], state["reply"] = dict(case), reply
            view_label = {"front": "正面", "side": "侧面", "back": "背面", "threequarter": "斜侧面"}[case["view"]]
            play_label = "播放中" if case["playing"] and case["action_index"] else "静止"
            status.set(f"已显示 · 女装 {case['female_outfit']} / 男装 {case['male_outfit']} · 发型 {case['hair_index']} · {view_label} · {play_label}。请在 UE 中观察。")
            write(ROOT / "panel_state.json", {"pid": os.getpid(), "request": request, "bindings": reply.get("bindings"),
                  "sources": data["sources"], "sources_sha256": sources_sha, "updated_at": now()})
        if state["closing"]:
            submit("restore")
        root.after(100, poll)

    def toolbar(items):
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=3)
        for label, callback in items:
            button = ttk.Button(row, text=label, command=callback)
            button.pack(side="left", padx=(0, 7), pady=2)
            controls.append(button)

    def start_playback():
        if selectors["action_index"].current() == 0:
            selectors["action_index"].current(min(3, len(female_actions)))
        submit("playback", playing=True)

    toolbar([("播放动作", start_playback),
             ("暂停", lambda: submit("playback", playing=False)),
             ("重新显示", lambda: submit("show")), ("重载已保存场景", lambda: submit("reload"))])
    toolbar([(label, lambda v=value: submit("view", view=v)) for label, value in
             (("正面", "front"), ("侧面", "side"), ("背面", "back"), ("斜侧面", "threequarter"))])
    toolbar([(label, lambda v=value: submit("view", focus=v)) for label, value in
             (("男女同屏", "both"), ("女性放大", "female"), ("男性放大", "male"))] +
            [("全身", lambda: submit("view", framing="full")), ("头部", lambda: submit("view", framing="head"))])
    ttk.Label(frame, textvariable=status, wraplength=880).pack(anchor="w", pady=12)
    ttk.Separator(frame).pack(fill="x", pady=8)
    ttk.Label(frame, text="可选：记录当前组合的观察结果，或检查后直接在对话中反馈。").pack(anchor="w")
    ttk.Entry(frame, textvariable=note).pack(fill="x", pady=6)

    def record(sex, outcome):
        selected = current()
        if state["busy"] or state["loaded"] != selected or not state["reply"]:
            status.set("请等待当前组合成功加载后再记录。")
            return
        if state["reply"].get("bindings") is None:
            status.set("当前回执没有实际绑定信息，暂不记录验收。")
            return
        try:
            if digest(load_catalog()["sources"]) != sources_sha:
                raise ValueError("来源索引已变化，请重新打开面板；旧记录保持原样。")
            path = ROOT / "manual_review.json"
            document = read(path) if path.exists() else {"schema_version": 1, "level": LEVEL,
                "scope": "complete_character_existing_wardrobe_hair_review",
                "sources": data["sources"], "sources_sha256": sources_sha, "observations": []}
            if document.get("sources_sha256") != sources_sha:
                raise ValueError("已有记录属于另一版来源，不覆盖其结果。")
            document["observations"].append({"at": now(), "sex": sex, "outcome": outcome,
                "note": note.get().strip(), "request": dict(selected),
                "bindings": state["reply"]["bindings"], "observation_id": uuid.uuid4().hex})
            write(path, document)
            status.set(f"已记录{'女性' if sex == 'female' else '男性'}当前组合：{'正常' if outcome == 'accepted' else '有问题'}。")
        except Exception as exc:
            status.set("记录未完成：" + str(exc))

    toolbar([(label, lambda s=sex, r=outcome: record(s, r)) for label, sex, outcome in
             (("女性正常", "female", "accepted"), ("女性有问题", "female", "issue"),
              ("男性正常", "male", "accepted"), ("男性有问题", "male", "issue"))])

    def close():
        if state["closing"]:
            return
        state["closing"] = True
        checkpoint("closing")
        enabled(False)
        if state["busy"]:
            status.set("等待当前操作完成，然后恢复编辑器设置并关闭面板…")
        else:
            submit("restore")
    root.protocol("WM_DELETE_WINDOW", close)
    describe()
    root.after(100, poll)
    root.after(250, lambda: submit("show"))
    try:
        root.mainloop()
    finally:
        checkpoint("closed")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("panel",) + ACTIONS, default="panel")
    for key in ("female-outfit", "male-outfit", "hair-index", "action-index"):
        parser.add_argument("--" + key, type=int)
    parser.add_argument("--view", choices=("front", "side", "back", "threequarter"))
    parser.add_argument("--focus", choices=("both", "female", "male"))
    parser.add_argument("--framing", choices=("full", "head"))
    parser.add_argument("--playing", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--node-id", help="Explicit running UE node; replaces this tool's saved pin")
    return parser


def main():
    args = build_parser().parse_args()
    if args.action == "panel":
        panel(args)
    else:
        request = dict(initial_case(vars(args)), action=args.action)
        print(json.dumps(execute(request, args.node_id), ensure_ascii=False, default=str))


def entrypoint():
    try:
        main()
    except Exception as exc:
        record_error(exc, "entrypoint")
        raise


if __name__ == "__main__":
    entrypoint()
