"""中文拍摄点审查面板。只连接现有编辑器；所有 UE 修改由专用 worker 执行。"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
import uuid

import run_complete_character_wardrobe_hair_review_v1 as bridge
import scene_site_catalog_v1 as scene_directory
import scene_site_appearance_v1 as appearance_contract

SCRIPT_ROOT = Path(__file__).resolve().parent
RUN = SCRIPT_ROOT.parents[2] / "00_engine/outputs/scene_site_review_20261014_v1"
WORKER = SCRIPT_ROOT / "ue_primary_saved_site_review_v1.py"
MARKER = "DM_SCENE_SITE_REVIEW="
ACTIONS = {"status", "catalog", "create_site", "capture_site", "update_site", "snap_ground",
           "preview", "overview", "show_ranges", "check_start", "check_all", "poll_check", "cancel_check",
           "save_site", "load_site", "restore", "play", "pause_playback", "stop_playback", "playback_status", "open_scene",
           "set_appearance", "save_appearance", "load_appearance"}
now, read, write = bridge.now, bridge.read, bridge.write


def request(action, **values):
    if action not in ACTIONS:
        raise ValueError("不支持的拍摄点操作。")
    result = {"action": action, "request_id": uuid.uuid4().hex, **values}
    if 'source_mode' in result and result['source_mode'] not in {'full', 'production10'}:
        raise ValueError('请选择完整动作预览或正式10秒预览。')
    if action == "open_scene" and (not isinstance(result.get("map_path"), str)
            or not result['map_path'].startswith('/Game/Scenes/') or any(
                part in {'', '.', '..'} for part in result['map_path'].split('/')[1:])):
        raise ValueError("请选择场景目录中的完整关卡。")
    for key in ("yaw", "time_seconds"):
        if key in result and (type(result[key]) not in (int, float) or not math.isfinite(result[key])):
            raise ValueError("角度和时间必须是有效数字。")
    if "time_seconds" in result and result["time_seconds"] < 0:
        raise ValueError("时间不能小于 0。")
    if "position" in result:
        p = result["position"]
        if not isinstance(p, dict) or set(p) != {"x", "y", "z"} or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in p.values()):
            raise ValueError("点位坐标必须是有效数字。")
    return result


def command_payload(sent):
    # Keep the echoed remote command short, even with thousands of review notes.
    path = RUN / 'requests' / (sent['request_id'] + '.json')
    write(path, sent)
    return (f"import sys, runpy\nsys.path.insert(0, {str(SCRIPT_ROOT)!r})\n"
            f"import json\nfrom pathlib import Path\n"
            f"runpy.run_path({str(WORKER)!r}, run_name='__main__', "
            f"init_globals={{'DM_SCENE_SITE_REVIEW_REQUEST': json.loads(Path({str(path)!r}).read_text(encoding='utf-8-sig'))}})")


def install_complete_reply_receiver(module):
    """TCP chunks are not message boundaries; decode only a complete JSON reply."""
    def receive(connection, expected_type):
        data = bytearray()
        while True:
            part = connection._command_channel_socket.recv(module.DEFAULT_RECEIVE_BUFFER_SIZE)
            if not part:
                raise RuntimeError('UE 回执传输中断；请核对保存文件，不自动重复操作。')
            data.extend(part)
            if len(data) > 64 * 1024 * 1024:
                raise RuntimeError('UE 回执超出大小限制。')
            try:
                json.loads(data.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            message = module._RemoteExecutionMessage(None, None)
            if (message.from_json_bytes(bytes(data)) and
                    message.passes_receive_filter(connection._node_id) and message.type_ == expected_type):
                return message
            raise RuntimeError('UE 回执类型或来源不匹配。')
    module._RemoteExecutionCommandConnection._receive_message = receive


def parse_reply(reply, sent):
    if not isinstance(reply, dict) or reply.get("success") is not True:
        raise RuntimeError("UE 未完成操作；请查看本次输出目录的 remote 日志。")
    markers = [str(row.get("output", "")).split(MARKER, 1)[1]
               for row in reply.get("output", []) if MARKER in str(row.get("output", ""))]
    if len(markers) != 1:
        raise RuntimeError("UE 未返回唯一的拍摄点回执；本次操作不会自动重试。")
    result, _ = json.JSONDecoder().raw_decode(markers[0].lstrip())
    if not isinstance(result, dict):
        raise RuntimeError("UE 返回的拍摄点回执格式错误。")
    if result.get("result_file"):
        path = Path(result["result_file"]).resolve(strict=True)
        if path.parent != (RUN / "replies").resolve() or path.suffix.lower() != ".json":
            raise RuntimeError("UE 回执路径不属于本次拍摄点审查。")
        result = read(path)
    if result.get("success") is not True:
        detail = result.get("error") or result.get("message") or "请查看输出目录的错误记录。"
        raise RuntimeError("操作未完成：" + str(detail))
    if result.get("request_id") not in (None, sent["request_id"]):
        raise RuntimeError("UE 回执与本次操作不匹配。")
    if result.get("action") not in (None, sent["action"]):
        raise RuntimeError("UE 回执的操作类型不匹配。")
    return result


def execute(sent, node_id=None):
    if not WORKER.is_file():
        raise FileNotFoundError("拍摄点执行脚本尚未就绪。")
    with bridge.command_lock():
        record = {"started_at": now(), "request": sent, "success": False}
        session = None
        try:
            module = bridge.load_remote_execution(bridge.DEFAULT_ENGINE_ROOT.resolve())
            install_complete_reply_receiver(module)
            session = module.RemoteExecution()
            session.start()
            pin_path = RUN / "session.json"
            pinned = read(pin_path) if pin_path.is_file() else None
            deadline, last_error, found_at = time.monotonic() + 12, None, None
            while time.monotonic() < deadline:
                try:
                    node = bridge.select_node(list(session.remote_nodes), node_id, pinned)
                    found_at = found_at or time.monotonic()
                    if time.monotonic() - found_at >= .6:
                        break
                except RuntimeError as exc:
                    last_error, found_at = exc, None
                time.sleep(.2)
            else:
                raise last_error or RuntimeError("未发现可用 UE。请先打开 datatry_02。")
            node = bridge.select_node(list(session.remote_nodes), node_id, pinned)
            write(pin_path, {"node_id": node["node_id"], "node": node, "pinned_at": now()})
            record["node"] = node
            session.open_command_connection(node["node_id"])
            session._command_connection._command_channel_socket.settimeout(120)
            reply = session.run_command(command_payload(sent), unattended=True,
                                        exec_mode=module.MODE_EXEC_FILE, raise_on_failure=False)
            record["command_result"] = reply
            result = parse_reply(reply, sent)
            record.update(success=True, result=result)
            return result
        except Exception as exc:
            record["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
            raise
        finally:
            record["finished_at"] = now()
            try:
                if session is not None:
                    session.stop()
            finally:
                write(RUN / "remote" / (sent["request_id"] + ".json"), record)


class CommandQueue:
    """One background worker, no Tk access from the background thread."""
    def __init__(self, executor=execute, node_id=None):
        self.executor, self.node_id = executor, node_id
        self.requests, self.results = queue.Queue(), queue.Queue()
        self.busy = False
        self.thread = threading.Thread(target=self._work, daemon=True)
        self.thread.start()

    def _work(self):
        while True:
            sent = self.requests.get()
            if sent is None:
                return
            try:
                self.results.put((sent, self.executor(sent, self.node_id), None))
            except Exception as exc:
                self.results.put((sent, None, exc))

    def submit(self, sent):
        if self.busy:
            raise RuntimeError("上一个操作尚未完成，请稍候。")
        self.busy = True
        self.requests.put(copy.deepcopy(sent))

    def poll(self):
        try:
            item = self.results.get_nowait()
        except queue.Empty:
            return None
        self.busy = False
        return item


def check_running(state):
    check = state.get("check") or {}
    return check.get("status") in {"running", "pending", "starting", "checking"} or check.get("running") is True


@contextmanager
def panel_lock():
    """A second panel must never drive the same review actor concurrently."""
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / "panel.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0"); handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("拍摄点面板已经打开，请使用现有窗口。") from exc
            try:
                yield
            finally:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def issue_selection(issue):
    """Keep navigation tied to the exact recorded action/camera/time."""
    keys = ("action_id", "camera_id", "aspect", "time_seconds")
    if any(issue.get(k) is None for k in keys):
        raise ValueError("这条问题没有完整的动作、镜头或时间，无法直接跳转。")
    return {k: issue[k] for k in keys}


def combination_key(value):
    return tuple(value.get(k) for k in ("action_id", "camera_id", "aspect"))


def site_signature(state):
    return state.get("review_stamp") or json.dumps({k: state.get(k) for k in ("site_id", "map", "position", "yaw")}, sort_keys=True)


def current_scene_map(state):
    return state.get('current_map') or state.get('map') or ''


def sites_for_scene(catalog, map_path):
    return [row for row in catalog.get('sites', []) if row.get('map') == map_path]


def decision_rows(records):
    """Only explicit human decisions survive; absent combinations stay pending."""
    return [copy.deepcopy(r) for r in records if isinstance(r, dict)
            and r.get("decision") in {"allowed", "excluded"} and all(combination_key(r))]


ISSUE_STATUSES = {"unreviewed": "未审看", "confirmed_problem": "确认有问题", "acceptable": "可接受"}


def issue_key(issue):
    """A report's ordering is not an identity; stable recorded evidence is."""
    value = {key: issue.get(key) for key in
             ("kind", "action_id", "camera_id", "aspect", "time_seconds", "message")}
    if type(value["time_seconds"]) in (int, float):
        value["time_seconds"] = float(value["time_seconds"])
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def issue_review_rows(records):
    if not isinstance(records, dict):
        return {}
    return {key: {"status": value["status"], "note": str(value.get("note", ""))}
            for key, value in records.items() if isinstance(key, str) and isinstance(value, dict)
            and value.get("status") in ISSUE_STATUSES}


def scoped_combinations(catalog, selected, scope, both_aspects=False):
    """Expand bulk decisions to explicit, inspectable per-combination records."""
    motions = [r["id"] for r in catalog.get("motions", [])] if scope == "camera" else [selected["action_id"]]
    cameras = [r["id"] for r in catalog.get("cameras", [])] if scope == "action" else [selected["camera_id"]]
    aspects = ["landscape", "portrait"] if both_aspects else [selected["aspect"]]
    return [{"action_id": motion, "camera_id": camera, "aspect": aspect}
            for motion in motions for camera in cameras for aspect in aspects]


def scope_text(scope):
    if not isinstance(scope, dict):
        return "检查范围：尚未明确"
    if scope.get("kind") == "all":
        return f"检查范围：全部组合（{scope.get('combinations', '?')} 项）"
    if scope.get("kind") == "remaining":
        return f"检查范围：剩余组合（{scope.get('combinations', '?')} 项；排除 {len(scope.get('excluded_combinations') or [])} 项）"
    selected = scope.get("selection") or {}
    aspect = "竖屏" if selected.get("aspect") == "portrait" else "横屏" if selected.get("aspect") == "landscape" else ""
    return "检查范围：仅当前组合  " + " / ".join(str(v) for v in (selected.get("action_id"), selected.get("camera_id"), aspect) if v)


class Panel:
    def __init__(self, root, node_id=None, executor=execute):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk, self.root = tk, ttk, root
        self.manager = CommandQueue(executor, node_id)
        self.state, self.catalog, self.issues = {}, {}, []
        self.closing = False
        self.keep_closing = False
        self.decisions, self.decisions_dirty = [], False
        self.issue_reviews, self.undo_decisions = {}, []
        self.editing_issue = None
        self.setting_note = False
        self.site_form_dirty = False
        self.appearance_dirty = False
        self.appearance_value = None
        self.setting_site_form = False
        self.drafts_path = RUN / "panel_review_drafts.json"
        try:
            self.drafts = read(self.drafts_path) if self.drafts_path.is_file() else {}
            if not isinstance(self.drafts, dict):
                self.drafts = {}
        except (ValueError, OSError):
            self.drafts = {}
        self.playback_poll_paused = False
        self.last_playback_poll = 0.
        self.poll_paused = False
        self.last_poll, self.last_report = 0., None
        self.buttons, self.inputs = [], []
        root.title("场景拍摄点审查")
        root.geometry("1230x960")
        root.minsize(1050, 780)
        outer = ttk.Frame(root); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        page_scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        page_scroll.pack(side="right", fill="y"); canvas.configure(yscrollcommand=page_scroll.set)
        frame = ttk.Frame(canvas, padding=12)
        content = canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(content, width=event.width))
        def scroll_page(event):
            widget = event.widget
            if hasattr(widget, 'winfo_toplevel') and widget.winfo_toplevel() == root and not isinstance(widget, ttk.Treeview):
                canvas.yview_scroll(-int(event.delta / 120), "units")
        root.bind_all("<MouseWheel>", scroll_page, add="+")
        ttk.Label(frame, text="选择并打开场景，再创建拍摄点；移动点位后检查人物和相机需要的空间。", font=("Microsoft YaHei UI", 11)).pack(anchor="w")
        ttk.Label(frame, text="点击“打开所选场景”切换；当前关卡有未保存修改时，先自动保留独立恢复备份。").pack(anchor="w", pady=(2, 0))
        self.status = tk.StringVar(value="正在连接现有 UE…")
        ttk.Label(frame, textvariable=self.status, wraplength=1050).pack(anchor="w", pady=(3, 2))
        self.map_label = tk.StringVar(value="尚未连接 UE")
        ttk.Label(frame, textvariable=self.map_label).pack(anchor="w", pady=(3, 8))

        scenes = ttk.LabelFrame(frame, text="场景目录", padding=8)
        scenes.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(scenes); row.pack(fill="x")
        self.scene_category = tk.StringVar(value="主场景")
        self.scene_category_box = self.combo(row, "显示", self.scene_category, 12,
                                            ["主场景", "全部地图", *[v for k, v in scene_directory.CATEGORY_NAMES.items() if k != 'primary']])
        self.scene_category_box.bind('<<ComboboxSelected>>', lambda _event: self.refresh_scene_choices())
        self.scene_choice = tk.StringVar()
        self.scene_box = self.combo(row, "场景", self.scene_choice, 64)
        self.button(row, "打开所选场景", self.open_scene).pack(side="left", padx=3)
        self.scene_count = tk.StringVar()
        ttk.Label(scenes, textvariable=self.scene_count).pack(anchor="w", pady=(5, 0))

        sites = ttk.LabelFrame(frame, text="1. 拍摄点", padding=8)
        sites.pack(fill="x")
        top = ttk.Frame(sites); top.pack(fill="x")
        self.name = tk.StringVar(value="拍摄点 01")
        ttk.Label(top, text="名称").pack(side="left")
        self.entry(top, self.name, 22).pack(side="left", padx=5)
        self.button(top, "创建拍摄点", lambda: self.send("create_site", name=self.name.get().strip())).pack(side="left", padx=3)
        self.button(top, "读取 UE 点位", lambda: self.send("capture_site")).pack(side="left", padx=3)
        self.button(top, "起点贴地", lambda: self.send("snap_ground")).pack(side="left", padx=3)
        self.button(top, "刷新状态", lambda: self.send("status"), always=True).pack(side="right")
        row = ttk.Frame(sites); row.pack(fill="x", pady=7)
        self.position = {axis: tk.StringVar(value="0") for axis in "xyz"}
        for axis in "xyz":
            ttk.Label(row, text=axis.upper() + " (厘米)").pack(side="left")
            self.entry(row, self.position[axis], 12).pack(side="left", padx=(4, 12))
        ttk.Label(row, text="朝向 (度)").pack(side="left")
        self.yaw = tk.StringVar(value="0")
        self.entry(row, self.yaw, 10).pack(side="left", padx=4)
        self.button(row, "应用位置 / 朝向", self.update_site).pack(side="left", padx=8)
        row = ttk.Frame(sites); row.pack(fill="x")
        self.saved_site = tk.StringVar()
        self.site_box = ttk.Combobox(row, textvariable=self.saved_site, state="readonly", width=36)
        self.site_box.pack(side="left"); self.inputs.append((self.site_box, "readonly"))
        self.button(row, "恢复已保存点位", self.load_site).pack(side="left", padx=6)
        self.button(row, "保存点位及人工选择", self.save_site).pack(side="left", padx=3)
        self.dirty = tk.StringVar(value="位置更改后需要重新检查。")
        ttk.Label(sites, textvariable=self.dirty).pack(anchor="w", pady=(5, 0))

        self.appearance_frame = ttk.LabelFrame(frame, text="2. 人物外观（先保存外观，再保存点位链接）", padding=8)
        self.appearance_frame.pack(fill='x', pady=8)
        self.appearance_body = ttk.Frame(self.appearance_frame)
        self.appearance_body.pack(fill='x')
        ttk.Label(self.appearance_body, text='正在读取角色、服装、发型和表情目录…').pack(anchor='w')
        row = ttk.Frame(self.appearance_frame); row.pack(fill='x', pady=(6, 0))
        self.appearance_name = tk.StringVar(value='人物外观 01')
        self.entry(row, self.appearance_name, 20).pack(side='left')
        self.button(row, '应用人物外观', self.apply_appearance).pack(side='left', padx=4)
        self.button(row, '另存完整外观', self.save_appearance).pack(side='left', padx=4)
        self.saved_appearance = tk.StringVar()
        self.appearance_config_box = self.combo(row, '已保存', self.saved_appearance, 25)
        self.button(row, '恢复完整外观', self.load_appearance).pack(side='left', padx=4)
        self.appearance_note = tk.StringVar(value='外观与场景位置分别保存；换场景保留人物选择。')
        ttk.Label(self.appearance_frame, textvariable=self.appearance_note, wraplength=1100).pack(anchor='w', pady=(5, 0))

        preview = ttk.LabelFrame(frame, text="3. 人物与镜头预览", padding=8)
        preview.pack(fill="x", pady=8)
        row = ttk.Frame(preview); row.pack(fill='x', pady=(0, 5))
        self.source_mode = tk.StringVar(value='正式10秒预览')
        self.source_mode_box = self.combo(row, '预览时长', self.source_mode, 20, ['正式10秒预览', '完整动作预览'])
        ttk.Label(row, text='完整模式播放当前验收动作段；正式模式使用保存的 10 秒窗口。').pack(side='left', padx=8)
        row = ttk.Frame(preview); row.pack(fill="x")
        self.motion, self.camera = tk.StringVar(), tk.StringVar()
        self.aspect, self.seconds = tk.StringVar(value="横屏"), tk.StringVar(value="0")
        self.motion_box = self.combo(row, "动作", self.motion, 30)
        self.camera_box = self.combo(row, "镜头", self.camera, 25)
        self.aspect_box = self.combo(row, "画幅", self.aspect, 7, ["横屏", "竖屏"])
        row = ttk.Frame(preview); row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="时间 (秒)").pack(side="left")
        self.entry(row, self.seconds, 10).pack(side="left", padx=5)
        self.button(row, "显示此刻", self.preview).pack(side="left", padx=5)
        self.button(row, "播放 / 继续", self.play).pack(side="left", padx=3)
        self.button(row, "暂停", lambda: self.send("pause_playback")).pack(side="left", padx=3)
        self.button(row, "停止并回到起点", lambda: self.send("stop_playback")).pack(side="left", padx=3)
        self.loop = tk.BooleanVar(value=True)
        loop_box = ttk.Checkbutton(row, text="循环", variable=self.loop)
        loop_box.pack(side="left", padx=5); self.inputs.append((loop_box, "normal"))
        row = ttk.Frame(preview); row.pack(fill="x", pady=(5, 0))
        self.playback_progress = ttk.Progressbar(row, length=320, mode="determinate")
        self.playback_progress.pack(side="left")
        self.playback_text = tk.StringVar(value="尚未播放")
        ttk.Label(row, textvariable=self.playback_text).pack(side="left", padx=8)
        row = ttk.Frame(preview); row.pack(fill="x", pady=(5, 0))
        self.button(row, "俯看人物与相机轨迹", lambda: self.send("overview", **self.selection())).pack(side="left", padx=5)
        self.ranges = tk.BooleanVar(value=False)
        self.range_box = ttk.Checkbutton(row, text="显示人物与相机轨迹", variable=self.ranges,
                                        command=lambda: self.send("show_ranges", enabled=self.ranges.get()))
        self.range_box.pack(side="left", padx=12); self.inputs.append((self.range_box, "normal"))
        ttk.Label(preview, text="绿色：人物路线与肢体；蓝色：相机轨迹；黄色文字：时刻（秒）。").pack(anchor="w", pady=(6, 0))
        ttk.Label(preview, text="沿用现用 30 动作、21 镜头与横竖画幅；不修改镜头参数。").pack(anchor="w", pady=(3, 0))
        row = ttk.Frame(preview); row.pack(fill="x", pady=(7, 0))
        self.button(row, "允许当前组合", lambda: self.decide("allowed")).pack(side="left", padx=(0, 5))
        self.button(row, "排除当前组合", lambda: self.decide("excluded")).pack(side="left", padx=5)
        self.button(row, "改为未确认", lambda: self.decide(None)).pack(side="left", padx=5)
        self.decision_text = tk.StringVar(value="当前组合：未确认；其他组合默认未确认。")
        ttk.Label(row, textvariable=self.decision_text).pack(side="left", padx=8)
        for box in (self.motion_box, self.camera_box, self.aspect_box):
            box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_decision())
        row = ttk.Frame(preview); row.pack(fill="x", pady=(6, 0))
        self.bulk_scope = tk.StringVar(value="当前动作的全部镜头")
        self.combo(row, "批量排除", self.bulk_scope, 24,
                   ["当前组合", "当前动作的全部镜头", "当前镜头的全部动作"])
        self.bulk_aspect = tk.StringVar(value="当前画幅")
        self.combo(row, "范围", self.bulk_aspect, 12, ["当前画幅", "横竖画幅"])
        self.button(row, "查看待排除清单", self.review_bulk).pack(side="left", padx=5)
        self.button(row, "查看已排除 / 恢复", self.review_excluded).pack(side="left", padx=5)
        self.button(row, "撤销上次组合选择", self.undo_decision).pack(side="left", padx=5)
        self.remaining_text = tk.StringVar(value="默认检查剩余组合。")
        ttk.Label(preview, textvariable=self.remaining_text).pack(anchor="w", pady=(4, 0))

        checking = ttk.LabelFrame(frame, text="3. 检查与问题定位", padding=8)
        checking.pack(fill="both", expand=True)
        row = ttk.Frame(checking); row.pack(fill="x")
        self.button(row, "检查当前动作 / 镜头", lambda: self.send("check_start", **self.selection())).pack(side="left", padx=3)
        self.button(row, "检查全部剩余组合", lambda: self.send("check_all", **self.selection())).pack(side="left", padx=5)
        self.cancel_button = self.button(row, "停止检查", lambda: self.send("cancel_check"), always=True)
        self.cancel_button.pack(side="left", padx=3)
        self.progress = ttk.Progressbar(row, length=220, mode="determinate")
        self.progress.pack(side="right", padx=4)
        self.progress_text = tk.StringVar(value="尚未检查")
        ttk.Label(checking, textvariable=self.progress_text).pack(anchor="w", pady=5)
        self.scope_label = tk.StringVar(value="检查范围：尚未检查")
        ttk.Label(checking, textvariable=self.scope_label).pack(anchor="w", pady=(0, 5))
        row = ttk.Frame(checking); row.pack(fill="x", pady=(0, 5))
        self.issue_filter = tk.StringVar(value="全部")
        filter_box = self.combo(row, "审看筛选", self.issue_filter, 16, ["全部", *ISSUE_STATUSES.values()])
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.render_issues())
        self.issue_count_text = tk.StringVar(value="尚无问题")
        ttk.Label(row, textvariable=self.issue_count_text).pack(side="left")
        table_frame = ttk.Frame(checking); table_frame.pack(fill="both", expand=True)
        columns = ("severity", "review", "message", "action", "camera", "aspect", "time")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=6, selectmode="browse")
        for key, label, width in zip(columns, ("级别", "人工审看", "问题", "动作", "镜头", "画幅", "秒"), (55, 100, 320, 150, 130, 55, 60)):
            self.table.heading(key, text=label); self.table.column(key, width=width, minwidth=40, stretch=key == "message")
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scrollbar.pack(side="right", fill="y"); self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self.jump_event)
        self.table.bind("<Return>", self.jump_event)
        self.table.bind("<<TreeviewSelect>>", self.select_issue)
        row = ttk.Frame(checking); row.pack(fill="x", pady=(6, 0))
        self.button(row, "跳到选中问题", self.jump).pack(side="left")
        ttk.Label(row, text="双击问题可切到对应动作、镜头和时间。检查结果需要人工审看。").pack(side="left", padx=10)
        row = ttk.Frame(checking); row.pack(fill="x", pady=(6, 0))
        for status, label in ISSUE_STATUSES.items():
            self.button(row, label, lambda value=status: self.mark_issue(value)).pack(side="left", padx=(0, 5))
        ttk.Label(row, text="备注").pack(side="left", padx=(6, 3))
        self.issue_note = tk.StringVar()
        self.note_entry = self.entry(row, self.issue_note, 48)
        self.note_entry.pack(side="left", fill="x", expand=True)
        self.issue_note.trace_add("write", self.note_changed)
        ttk.Label(frame, textvariable=self.status, wraplength=1050).pack(anchor="w", pady=(8, 4))
        ttk.Label(frame, text="恢复关闭会移除预览并恢复原视口；仅关闭会暂停播放并保留现场，运行中的 UE 检查继续。", wraplength=1100).pack(anchor="w", pady=(0, 5))
        bottom = ttk.Frame(frame); bottom.pack(fill="x")
        ttk.Button(bottom, text="打开结果文件夹", command=lambda: os.startfile(str(RUN))).pack(side="left")
        self.force_close_button = ttk.Button(bottom, text="仅关闭面板，保持 UE 现场", command=self.keep_scene)
        self.force_close_button.pack(side="right", padx=(8, 0))
        self.restore_close_button = ttk.Button(bottom, text="移除预览、恢复原视口并关闭", command=self.close)
        self.restore_close_button.pack(side="right")
        root.protocol("WM_DELETE_WINDOW", self.keep_scene)
        def site_form_changed(*_args):
            if not self.setting_site_form:
                self.site_form_dirty = True
        for variable in (self.name, self.yaw, *self.position.values()):
            variable.trace_add("write", site_form_changed)
        self.lifecycle("ready")
        self.after_id = root.after(100, self.tick)
        self.send("status")

    def lifecycle(self, stage, error=None):
        write(RUN / "panel_lifecycle.json", {"pid": os.getpid(), "stage": stage, "updated_at": now(), "error": error})

    def entry(self, parent, variable, width):
        widget = self.ttk.Entry(parent, textvariable=variable, width=width)
        self.inputs.append((widget, "normal")); return widget

    def combo(self, parent, label, variable, width, values=()):
        self.ttk.Label(parent, text=label).pack(side="left", padx=(0, 4))
        widget = self.ttk.Combobox(parent, textvariable=variable, state="readonly", width=width, values=values)
        widget.pack(side="left", padx=(0, 10)); self.inputs.append((widget, "readonly")); return widget

    def button(self, parent, label, callback, always=False):
        def guarded():
            try:
                callback()
            except Exception as exc:
                self.status.set("未执行：" + str(exc))
        button = self.ttk.Button(parent, text=label, command=guarded)
        self.buttons.append((button, always)); return button

    def set_enabled(self):
        active = not self.manager.busy and not self.closing and not self.keep_closing
        normal = active and not check_running(self.state)
        for button, always in self.buttons:
            button.configure(state="normal" if (active if always else normal) else "disabled")
        self.cancel_button.configure(state="normal" if active and check_running(self.state) else "disabled")
        for widget, original in self.inputs:
            widget.configure(state=original if normal else "disabled")
        self.note_entry.configure(state="normal" if normal and self.editing_issue is not None else "disabled")
        self.restore_close_button.configure(state="normal" if not self.closing and not self.keep_closing else "disabled")
        self.force_close_button.configure(state="normal" if not self.closing and not self.keep_closing else "disabled")

    def send(self, action, **values):
        if self.keep_closing or (self.closing and action not in {"cancel_check", "restore"}):
            return
        if action in {"check_all", "check_start"}:
            self.remember_draft()
            values["decisions_stamp"] = self.state.get("review_stamp")
            values["excluded_combinations"] = [
                {k: r[k] for k in ("action_id", "camera_id", "aspect")}
                for r in self.decisions if r.get("decision") == "excluded"]
        self.manager.submit(request(action, **values))
        labels = {"status": "读取 UE 状态", "check_all": "启动全部组合检查", "check_start": "启动当前组合检查",
                  "preview": "显示人物与镜头", "overview": "俯看人物与相机轨迹", "snap_ground": "寻找起点地面", "save_site": "保存点位",
                  "restore": "恢复编辑器", "poll_check": "读取检查进度", "play": "播放动作与镜头",
                  "pause_playback": "暂停播放", "stop_playback": "停止播放", "playback_status": "读取播放进度"}
        labels['open_scene'] = '打开所选场景'
        self.status.set("正在" + labels.get(action, "更新拍摄点") + "…")
        self.set_enabled()

    def selection(self):
        def resolve(rows, chosen, kind):
            matches = [r for r in rows if self.row_label(r) == chosen]
            if len(matches) != 1:
                raise ValueError("请先选择" + kind + "。")
            return matches[0]["id"]
        result = {"action_id": resolve(self.catalog.get("motions", []), self.motion.get(), "动作"),
                "camera_id": resolve(self.catalog.get("cameras", []), self.camera.get(), "镜头"),
                "aspect": "portrait" if self.aspect.get() == "竖屏" else "landscape",
                "time_seconds": float(self.seconds.get())}
        if self.catalog.get('appearance_catalog'):
            result['appearance_selection'] = self.current_appearance()
            result['source_mode'] = 'full' if self.source_mode.get() == '完整动作预览' else 'production10'
        return result

    def current_appearance(self):
        if self.appearance_value is None:
            raise ValueError('人物外观目录尚未就绪。')
        return appearance_contract.validate_selection(self.appearance_value, self.catalog['appearance_catalog'])

    def appearance_changed(self):
        self.appearance_dirty = True
        self.appearance_note.set('人物外观已更改；请应用预览，另存后可链接到拍摄点。')

    def render_appearance(self):
        data = self.catalog.get('appearance_catalog')
        if not data:
            return
        if self.appearance_value is None:
            self.appearance_value = appearance_contract.default_selection(data)
        value = self.appearance_value
        sex, choice = value['sex'], value['choice']
        # Remove destroyed controls from the ordinary enable/disable registry.
        for widget in self.appearance_body.winfo_children():
            widget.destroy()
        self.inputs = [(w, state) for w, state in self.inputs if w.winfo_exists()]
        self.appearance_vars = {}
        row = self.ttk.Frame(self.appearance_body); row.pack(fill='x', pady=2)
        def choose(parent, label, options, selected, changed, width=24):
            variable = self.tk.StringVar()
            labels = [str(text) + ('  [' + str(key) + ']' if key is not None else '') for key, text in options]
            box = self.combo(parent, label, variable, width, labels)
            box.current(next((i for i, (key, _) in enumerate(options) if key == selected), 0))
            def callback(_event):
                if box.current() >= 0:
                    changed(options[box.current()][0])
                    self.appearance_changed()
            box.bind('<<ComboboxSelected>>', callback)
            self.appearance_vars[label] = (variable, box)
            return box
        def change_sex(new):
            self.appearance_value = appearance_contract.default_selection(data, new)
            self.render_appearance()
        choose(row, '性别', [('female', '女性'), ('male', '男性')], sex, change_sex, 9)
        choose(row, '角色', [(r['id'], r['label']) for r in data['identities'] if r['sex'] == sex],
               value['character_id'], lambda key: value.update(character_id=key), 23)
        choose(row, '发色', [(r['id'], r['label']) for r in data['hair_colors']],
               value['hair_color'], lambda key: value.update(hair_color=key), 14)
        # The worker composes these accepted face curves over the chosen body.
        faces = {'none': '无表情（身体动作）'}
        for face in data['faces']:
            if face['sex'] == sex:
                faces[face['face_id']] = face['label']
        choose(row, '表情', list(faces.items()), value['face_id'], lambda key: value.update(face_id=key), 24)
        row = self.ttk.Frame(self.appearance_body); row.pack(fill='x', pady=2)
        families = data['families_by_sex'][sex]
        family = next((f for f in families if f['family_id'] == choice['family_id']), None)
        def family_changed(key):
            f = next((r for r in families if r['family_id'] == key), None)
            hair = value['choice']['hair_id']
            value['choice'] = appearance_contract.slots.default_choice(key, f['groups'][0]['group_id'] if f else None)
            value['choice']['hair_id'] = hair
            self.render_appearance()
        choose(row, '服装系列', [(None, '不穿服装')] + [(f['family_id'], f['label']) for f in families],
               choice['family_id'], family_changed, 34)
        if family:
            def group_changed(key):
                hair = value['choice']['hair_id']
                value['choice'] = appearance_contract.slots.default_choice(family['family_id'], key)
                value['choice']['hair_id'] = hair
                self.render_appearance()
            choose(row, '合法搭配组', [(g['group_id'], g['label']) for g in family['groups']],
                   choice['group_id'], group_changed, 32)
        row = self.ttk.Frame(self.appearance_body); row.pack(fill='x', pady=2)
        group = next((g for g in family['groups'] if g['group_id'] == choice['group_id']), None) if family else None
        from panel_hair_availability_v1 import denied
        hair_denied = denied(family, group, choice)
        if hair_denied:
            choice['hair_id'] = None
        hair_options = ([(None, '当前服装不允许使用头发')] if hair_denied else
                        [(None, '不戴头发')] + [(h['hair_id'], str(h['index']) + ' · ' + h['label'])
                                               for h in data['hairs_by_sex'][sex]])
        hair_box = choose(row, '发型', hair_options, choice['hair_id'], lambda key: choice.update(hair_id=key), 35)
        if hair_denied:
            hair_box.configure(state='disabled')
            self.inputs = [(w, 'disabled' if w is hair_box else state) for w, state in self.inputs]
        if group and group['shared_shoe_policy'] != 'forbidden_native_required':
            shoe_options = ([] if group['shared_shoe_policy'] == 'required_universal_female_pool'
                            else [(None, '不选共享鞋 / 赤脚')])
            choose(row, '共享鞋', shoe_options + [(s['asset_id'], s['label']) for s in data['shared_shoes_by_sex'][sex]],
                   choice['shared_shoe_id'], lambda key: choice.update(shared_shoe_id=key), 40)
        if group:
            row = self.ttk.Frame(self.appearance_body); row.pack(fill='x', pady=2)
            for i, (slot, options) in enumerate(group['slot_options'].items()):
                if i and i % 2 == 0:
                    row = self.ttk.Frame(self.appearance_body); row.pack(fill='x', pady=2)
                candidates = ([(None, '不选')] if slot not in group['required_slots'] else [])
                candidates += [(a['asset_id'], a['label']) for a in options]
                def slot_changed(key, s=slot):
                    choice['slot_choices'][s] = key
                    self.render_appearance()
                choose(row, data['slot_labels'].get(slot, slot), candidates, choice['slot_choices'].get(slot),
                       slot_changed, 39)
            if group['required_assets']:
                self.ttk.Label(self.appearance_body, text='固定套装：' + '、'.join(a['label'] for a in group['required_assets']), wraplength=1080).pack(anchor='w')
            for asset in group['optional_assets']:
                selected = self.tk.BooleanVar(value=asset['asset_id'] in choice['optional_asset_ids'])
                def extra_changed(a=asset['asset_id'], variable=selected):
                    extras = choice['optional_asset_ids']
                    if variable.get() and a not in extras:
                        extras.append(a)
                    elif not variable.get() and a in extras:
                        extras.remove(a)
                    self.render_appearance()
                    self.appearance_changed()
                check = self.ttk.Checkbutton(self.appearance_body, text='配件：' + asset['label'], variable=selected, command=extra_changed)
                check.pack(anchor='w'); self.inputs.append((check, 'normal'))

    def apply_appearance(self):
        self.send('set_appearance', appearance_selection=self.current_appearance())

    def save_appearance(self):
        self.send('save_appearance', name=self.appearance_name.get(), appearance_selection=self.current_appearance())

    def load_appearance(self):
        rows = self.state.get('appearance_configs', [])
        chosen = next((r for r in rows if self.row_label(r) == self.saved_appearance.get()), None)
        if chosen is None:
            raise ValueError('请先选择已保存的完整外观。')
        self.send('load_appearance', config_id=chosen['id'])

    @staticmethod
    def row_label(row):
        return str(row.get("label") or row.get("name") or row["id"]) + "  [" + str(row["id"]) + "]"

    def update_site(self):
        self.send("update_site", name=self.name.get().strip(), position={k: float(v.get()) for k, v in self.position.items()}, yaw=float(self.yaw.get()))

    @staticmethod
    def scene_label(row):
        return str(row.get('label') or row.get('name') or row['map_path']) + '  [' + str(row.get('category_label') or '') + ']'

    def refresh_scene_choices(self, select_current=False):
        rows = self.catalog.get('scenes', [])
        current = current_scene_map(self.state)
        current_row = next((row for row in rows if row.get('map_path') == current), None)
        if select_current and current_row and self.scene_category.get() not in {'全部地图', current_row.get('category_label')}:
            self.scene_category.set(current_row['category_label'])
        visible = [row for row in rows if self.scene_category.get() == '全部地图'
                   or row.get('category_label') == self.scene_category.get()]
        self.visible_scenes = visible
        values = [self.scene_label(row) for row in visible]
        self.scene_box.configure(values=values)
        if select_current and current_row in visible:
            self.scene_choice.set(self.scene_label(current_row))
        elif self.scene_choice.get() not in values:
            self.scene_choice.set(values[0] if values else '')
        self.scene_count.set(f"全部 {len({r.get('package') for r in rows})} 个场景包 / {len(rows)} 张地图；当前显示 {len(visible)} 张。总览、工作地图与建筑组合可在“显示”中选择。")

    def refresh_saved_sites(self):
        self.visible_sites = sites_for_scene(self.catalog, current_scene_map(self.state))
        values = [self.row_label(row) for row in self.visible_sites]
        self.site_box.configure(values=values)
        if self.saved_site.get() not in values:
            self.saved_site.set(values[0] if values else '')

    def open_scene(self):
        matches = [row for row in self.visible_scenes if self.scene_label(row) == self.scene_choice.get()]
        if len(matches) != 1:
            raise ValueError('请先选择要打开的场景。')
        target = matches[0]['map_path']
        if target == current_scene_map(self.state):
            self.status.set('所选场景已在 UE 打开。')
            return
        self.remember_draft()
        self.send('open_scene', map_path=target)

    def load_site(self):
        chosen = [r for r in sites_for_scene(self.catalog, current_scene_map(self.state)) if self.row_label(r) == self.saved_site.get()]
        if len(chosen) != 1:
            raise ValueError("请先选择一个已保存点位。")
        self.send("load_site", site_id=chosen[0]["id"])

    def preview(self):
        self.send("preview", **self.selection())

    def play(self):
        self.send("play", **self.selection(), loop=self.loop.get())

    def remember_draft(self):
        if self.state.get("site_id") and self.decisions_dirty:
            self.drafts[site_signature(self.state)] = {
                "allowed_combinations": decision_rows(self.decisions),
                "issue_reviews": issue_review_rows(self.issue_reviews), "updated_at": now()}
            write(self.drafts_path, self.drafts)

    def edits_changed(self):
        self.decisions_dirty = True
        self.remember_draft()
        self.refresh_decision()

    def refresh_remaining(self):
        total = len(self.catalog.get("motions", [])) * len(self.catalog.get("cameras", [])) * 2
        valid_actions = {r["id"] for r in self.catalog.get("motions", [])}
        valid_cameras = {r["id"] for r in self.catalog.get("cameras", [])}
        excluded = {combination_key(r) for r in self.decisions if r.get("decision") == "excluded"
                    and r.get("action_id") in valid_actions and r.get("camera_id") in valid_cameras
                    and r.get("aspect") in {"landscape", "portrait"}}
        self.remaining_text.set(f"默认检查剩余 {total - len(excluded)} / {total} 组合；已排除 {len(excluded)} 项。"
                                + (" 人工选择和备注待保存；本地草稿已保留。" if self.decisions_dirty else ""))
        fresh = self.state.get("current_result_fresh", not self.state.get("needs_recheck", True))
        full = self.state.get("full_matrix_fresh", not self.state.get("needs_recheck", True))
        check = self.state.get("check") or {}
        report = check.get("report") or self.last_report or {}
        scope = report.get("scope") or check.get("scope") or {}
        remaining = scope.get("kind") == "remaining"
        unchecked = {combination_key(row) for row in scope.get("excluded_combinations", [])} - excluded
        reason = str(self.state.get("recheck_reason") or "")
        if full:
            label = "全量检查有效；仍需人工审看。"
        elif fresh and remaining and unchecked:
            label = "已恢复此前未检查的组合；需要重新检查剩余组合。"
            reason = ""
        elif fresh and remaining:
            label = "剩余组合检查有效；已排除组合未检查。"
        elif fresh:
            label = "局部检查有效；全量尚未完成。"
        else:
            label = "检查已过期或尚无有效结果。"
        self.dirty.set(label + reason)

    def refresh_decision(self):
        self.refresh_remaining()
        try:
            key = combination_key(self.selection())
            found = next((r for r in self.decisions if combination_key(r) == key), {})
            label = {"allowed": "人工允许", "excluded": "人工排除"}.get(found.get("decision"), "未确认")
            allowed = sum(r["decision"] == "allowed" for r in self.decisions)
            excluded = sum(r["decision"] == "excluded" for r in self.decisions)
            self.decision_text.set(f"当前组合：{label}；允许 {allowed} / 排除 {excluded} 项" + ("；待保存" if self.decisions_dirty else ""))
        except (ValueError, KeyError):
            self.decision_text.set("请先选择当前动作、镜头和画幅；其他组合默认未确认。")

    def decide(self, decision):
        if not self.state.get("site_id"):
            raise ValueError("请先创建或恢复点位。")
        selected = {k: v for k, v in self.selection().items() if k != "time_seconds"}
        self.undo_decisions.append(copy.deepcopy(self.decisions))
        self.decisions = [r for r in self.decisions if combination_key(r) != combination_key(selected)]
        if decision is not None:
            self.decisions.append({**selected, "decision": decision})
        self.edits_changed()
        self.status.set("人工选择已暂存；点击“保存点位及人工选择”写入配置。未选择的组合仍未确认。")

    def undo_decision(self):
        if not self.undo_decisions:
            raise ValueError("没有可以撤销的组合选择。")
        self.decisions = self.undo_decisions.pop()
        self.edits_changed()
        self.status.set("已撤销上次组合选择；保存后写入点位。")

    def review_bulk(self):
        if not self.state.get("site_id"):
            raise ValueError("请先创建或恢复点位。")
        scope = {"当前组合": "combination", "当前动作的全部镜头": "action",
                 "当前镜头的全部动作": "camera"}[self.bulk_scope.get()]
        rows = scoped_combinations(self.catalog, self.selection(), scope, self.bulk_aspect.get() == "横竖画幅")
        self.combination_dialog(rows, False)

    def review_excluded(self):
        rows = [r for r in self.decisions if r.get("decision") == "excluded"]
        self.combination_dialog(rows, True)

    def combination_dialog(self, rows, restore):
        """Explicit list and final apply step make a bulk exclusion reviewable."""
        signature = site_signature(self.state)
        window = self.tk.Toplevel(self.root)
        window.title("已排除组合：选中后恢复为未确认" if restore else "确认批量排除清单")
        window.geometry("760x500"); window.transient(self.root); window.grab_set()
        self.ttk.Label(window, text=f"共 {len(rows)} 项；" + ("可多选后恢复，或取消返回。" if restore else "下列组合将从后续检查中排除。"), padding=10).pack(anchor="w")
        table = self.ttk.Treeview(window, columns=("action", "camera", "aspect"), show="headings", selectmode="extended")
        for key, label in (("action", "动作"), ("camera", "镜头"), ("aspect", "画幅")):
            table.heading(key, text=label)
        scroll = self.ttk.Scrollbar(window, orient="vertical", command=table.yview)
        scroll.pack(side="right", fill="y"); table.configure(yscrollcommand=scroll.set)
        table.pack(fill="both", expand=True, padx=10)
        for index, row in enumerate(rows):
            table.insert("", "end", iid=str(index), values=(row["action_id"], row["camera_id"],
                         "竖屏" if row["aspect"] == "portrait" else "横屏"))
        def apply_selection():
            if signature != site_signature(self.state):
                self.status.set("点位已变化，请重新查看排除清单。")
                window.destroy(); return
            chosen = [rows[int(i)] for i in table.selection()] if restore else rows
            if not chosen:
                self.status.set("未更改组合；请先选择要恢复的项。")
                return
            keys = {combination_key(r) for r in chosen}
            self.undo_decisions.append(copy.deepcopy(self.decisions))
            self.decisions = [r for r in self.decisions if combination_key(r) not in keys]
            if not restore:
                self.decisions.extend({**{k: r[k] for k in ("action_id", "camera_id", "aspect")},
                                       "decision": "excluded"} for r in chosen)
            self.edits_changed()
            self.status.set(f"已{'恢复' if restore else '排除'} {len(chosen)} 项；可撤销，保存后写入点位。")
            window.destroy()
        bar = self.ttk.Frame(window, padding=10); bar.pack(fill="x")
        self.ttk.Button(bar, text="恢复选中项" if restore else f"排除清单中的 {len(rows)} 项", command=apply_selection).pack(side="left")
        self.ttk.Button(bar, text="取消", command=window.destroy).pack(side="right")

    def save_site(self):
        values = {"allowed_combinations": decision_rows(self.decisions),
                  "issue_reviews": issue_review_rows(self.issue_reviews)}
        if self.state.get("review_stamp"):
            values["decisions_stamp"] = self.state["review_stamp"]
        if self.catalog.get('appearance_catalog'):
            if self.appearance_dirty or not self.state.get('appearance_config_id'):
                raise ValueError('请先“另存完整外观”，再保存拍摄点；现有点位记录未修改。')
            values['appearance_config_id'] = self.state['appearance_config_id']
        self.send("save_site", **values)

    def selected_issue_key(self):
        selected = self.table.selection()
        if not selected:
            raise ValueError("请先选中一条问题。")
        return issue_key(self.issues[int(selected[0])])

    def select_issue(self, _event=None):
        selected = self.table.selection()
        self.editing_issue = issue_key(self.issues[int(selected[0])]) if selected else None
        self.setting_note = True
        try:
            self.issue_note.set(self.issue_reviews.get(self.editing_issue, {}).get("note", ""))
        finally:
            self.setting_note = False
        self.note_entry.configure(state="normal" if self.editing_issue is not None and not self.manager.busy
                                  and not check_running(self.state) else "disabled")

    def note_changed(self, *_args):
        if self.setting_note or self.editing_issue is None:
            return
        previous = self.issue_reviews.get(self.editing_issue, {})
        self.issue_reviews[self.editing_issue] = {"status": previous.get("status", "unreviewed"),
                                                "note": self.issue_note.get()}
        self.edits_changed()

    def mark_issue(self, status):
        if not self.state.get("site_id"):
            raise ValueError("请先创建或恢复点位。")
        key = self.selected_issue_key()
        self.issue_reviews[key] = {"status": status, "note": self.issue_reviews.get(key, {}).get("note", "")}
        self.edits_changed()
        self.render_issues()
        self.status.set("问题审看已暂存；点击“保存点位及人工选择”写入配置。")

    def render_issues(self):
        selected_key = self.editing_issue
        self.table.delete(*self.table.get_children())
        counts = {status: 0 for status in ISSUE_STATUSES}
        visible = []
        for i, issue in enumerate(self.issues):
            key = issue_key(issue)
            review_status = self.issue_reviews.get(key, {}).get("status", "unreviewed")
            counts[review_status] += 1
            if self.issue_filter.get() not in {"全部", ISSUE_STATUSES[review_status]}:
                continue
            visible.append(i)
            severity = {"error": "错误", "warning": "提醒", "info": "提示", "review": "待审"}.get(issue.get("severity"), issue.get("severity", ""))
            self.table.insert("", "end", iid=str(i), values=(severity, ISSUE_STATUSES[review_status],
                              issue.get("message", issue.get("kind", "")), issue.get("action_id", ""),
                              issue.get("camera_id", ""), "竖屏" if issue.get("aspect") == "portrait" else
                              "横屏" if issue.get("aspect") == "landscape" else "", issue.get("time_seconds", "")))
        self.issue_count_text.set(f"显示 {len(visible)} / {len(self.issues)} 条；" + " / ".join(
            f"{ISSUE_STATUSES[status]} {counts[status]}" for status in ISSUE_STATUSES))
        match = next((str(i) for i in visible if issue_key(self.issues[i]) == selected_key), None)
        if match is not None:
            self.table.selection_set(match)
        self.select_issue()

    def jump(self):
        selected = self.table.selection()
        if not selected:
            raise ValueError("请先选中一条问题。")
        values = issue_selection(self.issues[int(selected[0])])
        for key, variable, rows in (("action_id", self.motion, self.catalog.get("motions", [])),
                                    ("camera_id", self.camera, self.catalog.get("cameras", []))):
            matches = [r for r in rows if r["id"] == values[key]]
            if not matches:
                raise ValueError("问题所用动作或镜头已不在当前目录中，请重新检查。")
            variable.set(self.row_label(matches[0]))
        self.aspect.set("竖屏" if values["aspect"] == "portrait" else "横屏")
        self.seconds.set(str(values["time_seconds"]))
        self.refresh_decision()
        self.send("preview", **values)

    def jump_event(self, _event):
        try:
            if self.manager.busy or self.closing or check_running(self.state):
                return
            self.jump()
        except Exception as exc:
            self.status.set("未执行：" + str(exc))

    def apply(self, reply, action):
        signature_changed = False
        previous_map = current_scene_map(self.state)
        if isinstance(reply.get("catalog"), dict):
            self.catalog = reply["catalog"]
            for key, box, variable in (("motions", self.motion_box, self.motion), ("cameras", self.camera_box, self.camera)):
                values = [self.row_label(r) for r in self.catalog.get(key, [])]
                box.configure(values=values)
                if variable.get() not in values:
                    variable.set(values[0] if values else "")
        if isinstance(reply.get("state"), dict):
            previous_signature = site_signature(self.state)
            self.remember_draft()
            self.state = reply["state"]
            signature_changed = previous_signature != site_signature(self.state)
            if signature_changed:
                self.decisions, self.decisions_dirty = [], False
                self.issue_reviews, self.undo_decisions = {}, []
            self.map_label.set("当前场景：" + str(current_scene_map(self.state) or "请打开场景，再创建点位"))
            if previous_map != current_scene_map(self.state):
                self.site_form_dirty = False
                if not self.state.get('site_id'):
                    self.setting_site_form = True
                    try:
                        self.name.set('拍摄点 01')
                        for variable in self.position.values():
                            variable.set('0')
                        self.yaw.set('0')
                    finally:
                        self.setting_site_form = False
            if (action not in {"poll_check", "playback_status", "play", "pause_playback", "stop_playback"}
                    and (not self.site_form_dirty or action in {"create_site", "load_site", "capture_site", "update_site", "snap_ground"})):
                self.setting_site_form = True
                try:
                    self.name.set(str(self.state.get("name") or self.name.get()))
                    p = self.state.get("position") or {}
                    for axis in "xyz":
                        if axis in p:
                            self.position[axis].set(f"{p[axis]:.3f}")
                    if "yaw" in self.state:
                        self.yaw.set(f"{self.state['yaw']:.3f}")
                finally:
                    self.setting_site_form = False
                self.site_form_dirty = False
            if "show_ranges" in self.state:
                self.ranges.set(bool(self.state["show_ranges"]))
            if action in {"create_site", "load_site", "save_site"} or signature_changed or (action == "status" and not self.decisions_dirty):
                self.decisions = decision_rows(self.state.get("allowed_combinations", []))
                self.issue_reviews = issue_review_rows(self.state.get("issue_reviews", {}))
                self.decisions_dirty = False
                signature = site_signature(self.state)
                if action == "save_site":
                    self.drafts.pop(signature, None)
                    write(self.drafts_path, self.drafts)
                elif signature in self.drafts:
                    draft = self.drafts[signature]
                    self.decisions = decision_rows(draft.get("allowed_combinations", []))
                    self.issue_reviews = issue_review_rows(draft.get("issue_reviews", {}))
                    self.decisions_dirty = True
            if signature_changed or (action in {"create_site", "capture_site", "update_site", "snap_ground", "load_site"} and self.state.get("needs_recheck", True)):
                self.issues, self.last_report = [], None
                self.render_issues()
        self.refresh_scene_choices(select_current=previous_map != current_scene_map(self.state))
        if self.catalog.get('appearance_catalog'):
            incoming = self.state.get('appearance_selection')
            if isinstance(incoming, dict) and (self.appearance_value is None or action in {'load_appearance', 'load_site', 'save_appearance'}):
                self.appearance_value = copy.deepcopy(incoming)
                self.appearance_dirty = False
                self.render_appearance()
            elif self.appearance_value is None:
                self.render_appearance()
            if action == 'save_appearance':
                self.appearance_dirty = False
                self.appearance_note.set('完整外观已独立保存；可保存拍摄点以建立链接。')
            configs = self.state.get('appearance_configs', [])
            labels = [self.row_label(r) for r in configs]
            self.appearance_config_box.configure(values=labels)
            selected = next((r for r in configs if r['id'] == self.state.get('appearance_config_id')), None)
            if selected:
                self.saved_appearance.set(self.row_label(selected))
            if action in {'load_site', 'load_appearance'} and self.state.get('source_mode') in {'full', 'production10'}:
                self.source_mode.set('完整动作预览' if self.state['source_mode'] == 'full' else '正式10秒预览')
        self.refresh_saved_sites()
        playback = self.state.get("playback") or {}
        current, duration = playback.get("time_seconds", 0), playback.get("duration_seconds", 0)
        self.playback_progress.configure(maximum=max(0.001, duration), value=current)
        self.playback_text.set(f"{'播放中' if playback.get('playing') else '已暂停 / 停止'}  {current:.2f} / {duration:.2f} 秒"
                               + ("  循环" if playback.get("loop") else "") + ("  " + str(playback["error"]) if playback.get("error") else ""))
        if action in {"play", "pause_playback", "stop_playback", "playback_status"}:
            self.seconds.set(f"{current:.3f}")
            self.last_playback_poll = time.monotonic()
        check = self.state.get("check") or {}
        total, done = check.get("total", 0), check.get("completed", 0)
        self.progress.configure(maximum=max(1, total), value=done)
        check_labels = {"running": "检查中", "completed": "检查完成", "complete": "检查完成", "cancelled": "已停止", "failed": "检查失败", "idle": "尚未检查"}
        self.progress_text.set(f"{check_labels.get(check.get('status'), check.get('status') or '尚未检查')}  {done} / {total}  {check.get('message', '')}")
        report = reply.get("report") or check.get("report")
        scope = check.get("scope") or (report or {}).get("scope")
        self.scope_label.set(scope_text(scope))
        if isinstance(report, dict) and report != self.last_report:
            self.last_report = copy.deepcopy(report)
            self.issues = report.get("issues") or []
            self.render_issues()
            self.progress_text.set(self.progress_text.get() + f"；发现 {len(self.issues)} 条问题 / 提醒")
        elif action in {"save_site", "load_site", "status"} or signature_changed:
            self.render_issues()
        self.refresh_decision()
        write(RUN / "panel_state.json", {"updated_at": now(), "state": self.state, "last_action": action})

    def close(self):
        if self.closing or self.keep_closing:
            return
        self.closing = True
        self.lifecycle("closing")
        self.status.set("正在停止检查并恢复编辑器，请稍候…")
        self.set_enabled()
        if not self.manager.busy:
            self.send("cancel_check" if check_running(self.state) else "restore")

    def keep_scene(self):
        if self.closing or self.keep_closing:
            return
        self.keep_closing = True
        self.set_enabled()
        if self.manager.busy:
            self.status.set("等待已发出的操作完成；播放会暂停，现场保留。")
            return
        if self.state.get("playback", {}).get("playing"):
            self.manager.submit(request("pause_playback"))
            self.status.set("正在暂停播放，随后关闭面板并保留现场…")
            return
        self.force_close()

    def force_close(self):
        if self.manager.busy:
            return
        self.lifecycle("closed_keep_scene", "仅关闭面板，未发送取消或恢复；UE 现场和运行中检查保留。")
        self.manager.requests.put(None)
        self.root.after_cancel(self.after_id)
        self.root.destroy()

    def tick(self):
        item = self.manager.poll()
        if item:
            sent, reply, error = item
            action = sent["action"]
            if self.keep_closing:
                if action == "pause_playback" and error:
                    self.keep_closing = False
                    self.status.set("暂停播放失败：" + str(error) + "。可重试关闭，或恢复编辑器后关闭。")
                    self.set_enabled()
                    self.after_id = self.root.after(100, self.tick)
                    return
                playing = (reply or {}).get("state", {}).get("playback", {}).get("playing", self.state.get("playback", {}).get("playing"))
                if action != "pause_playback" and (playing or (error and action == "play")):
                    self.manager.submit(request("pause_playback"))
                    self.status.set("正在暂停播放，随后关闭面板并保留现场…")
                    self.after_id = self.root.after(100, self.tick)
                    return
                self.force_close()
                return
            if error:
                self.status.set("操作失败：" + str(error))
                write(RUN / "panel_error.json", {"at": now(), "action": action, "error": str(error)})
                if action == "poll_check":
                    self.poll_paused = True
                    self.status.set("读取检查进度失败：" + str(error) + "。点击“刷新状态”后继续。")
                if action == "playback_status":
                    self.playback_poll_paused = True
                    self.status.set("读取播放进度失败：" + str(error) + "。点击“刷新状态”后继续。")
                if self.closing:
                    self.closing = False
                    self.lifecycle("restore_failed", str(error))
                    self.force_close_button.configure(state="normal")
                    self.status.set("恢复未完成：" + str(error) + "。可重试恢复，或仅关闭面板保持当前现场。")
            else:
                if action in {"status", "check_start", "check_all"}:
                    self.poll_paused = False
                if action in {"status", "play"}:
                    self.playback_poll_paused = False
                self.apply(reply, action)
                self.status.set(str(reply.get("message") or "操作完成。"))
                if action == "restore":
                    self.lifecycle("closed")
                    self.manager.requests.put(None)
                    self.root.after_cancel(self.after_id)
                    self.root.destroy()
                    return
            if self.closing and not self.manager.busy:
                self.send("cancel_check" if check_running(self.state) and action != "cancel_check" else "restore")
            elif action == "status" and not error and not self.catalog:
                self.send("catalog")
            self.set_enabled()
        if check_running(self.state) and not self.poll_paused and not self.manager.busy and not self.closing and time.monotonic() - self.last_poll >= 1.5:
            self.last_poll = time.monotonic()
            self.send("poll_check")
        elif (self.state.get("playback", {}).get("playing") and not check_running(self.state)
              and not self.playback_poll_paused and not self.manager.busy and not self.closing
              and not self.keep_closing and time.monotonic() - self.last_playback_poll >= 1.0):
            self.last_playback_poll = time.monotonic()
            self.send("playback_status")
        self.after_id = self.root.after(100, self.tick)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-id")
    parser.add_argument("--action", choices=sorted(ACTIONS), help="执行一次操作，不打开面板")
    parser.add_argument("--request-file", type=Path)
    args = parser.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if args.action:
        values = read(args.request_file) if args.request_file else {}
        values.pop("action", None); values.pop("request_id", None)
        print(json.dumps(execute(request(args.action, **values), args.node_id), ensure_ascii=False))
        return
    import tkinter as tk
    with panel_lock():
        write(RUN / "panel_lifecycle.json", {"pid": os.getpid(), "stage": "starting", "updated_at": now()})
        root = tk.Tk()
        Panel(root, args.node_id)
        root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        lifecycle_path = RUN / "panel_lifecycle.json"
        lifecycle = read(lifecycle_path) if lifecycle_path.is_file() else {}
        if lifecycle.get("pid") in (None, os.getpid()) or lifecycle.get("stage") not in {"ready", "starting", "closing"}:
            write(lifecycle_path, {"pid": os.getpid(), "stage": "failed", "updated_at": now(), "error": str(exc), "traceback": traceback.format_exc()})
        raise
