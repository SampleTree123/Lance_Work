"""Chinese fixed-slot review panel/CLI; connect to an existing UE only.

CLI accepts a full UI-choice request with --request-file, or historical preset
numbers with --female-preset / --male-preset. No CLI action records acceptance.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
import uuid

import complete_character_slot_review_contract_v1 as contract
import run_complete_character_wardrobe_hair_review_v1 as previous

SCRIPT_ROOT = Path(__file__).resolve().parent
ROOT = previous.ROOT / "tonight_20261006_v1/runtime"
WORKER = SCRIPT_ROOT / "ue_complete_character_slot_review_v1.py"
LEVEL = previous.LEVEL
MARKER = "DM_COMPLETE_SLOT_REVIEW="
COMMAND_TIMEOUT = 120
ACTIONS = ("show", "view", "playback", "status", "sample", "save", "reload", "restore")
STATE_KEYS = ("choices", "action_index", "playing", "view", "focus", "framing", "registry_sha256")
REQUEST_KEYS = set(STATE_KEYS) | {"action", "save"}
now, read, write, digest = previous.now, previous.read, previous.write, previous.digest
select_node, command_lock = previous.select_node, previous.command_lock


def record_error(exc, stage, trace=None):
    write(ROOT / "controller_error.json", {"at": now(), "pid": os.getpid(), "stage": stage,
          "error_type": type(exc).__name__, "error": str(exc),
          "traceback": trace if trace is not None else traceback.format_exc()})


def load_catalog():
    data = contract.catalog()
    for sex in ("female", "male"):
        rows = data["presets_by_sex"][sex]
        # The contract checks these rows against the current bound mapping.
        # A later reviewed exclusion keeps original numbers and leaves gaps.
        if not rows or len({p["index"] for p in rows}) != len(rows):
            raise ValueError("快捷预设缺失或原编号重复。")
        if ([h["index"] for h in data["hairs_by_sex"][sex]] != data["hair_review_indices_by_sex"][sex]
                or len(data["actions_by_sex"][sex]) != 5):
            raise ValueError("发型或动作目录不完整。")
    return data


def initial_request(data, saved=None):
    choices = {sex: copy.deepcopy(data["presets_by_sex"][sex][0]["choice"]) for sex in ("female", "male")}
    old = (saved or {}).get("request", saved or {})
    allowed_saved_versions = {data["sources"]["registry"]["sha256"],
                              data["sources"].get("source_registry", {}).get("sha256")}
    if old.get("registry_sha256") and old.get("registry_sha256") in allowed_saved_versions:
        for sex in choices:
            try:
                contract.validate_choice(sex, old["choices"][sex])
                choices[sex] = copy.deepcopy(old["choices"][sex])
            except (KeyError, TypeError, ValueError):
                pass
    for sex in choices:
        choices[sex]["hair_id"] = next(h["hair_id"] for h in data["hairs_by_sex"][sex] if h["index"] == 2)
    # Reopening always starts statically, including when saved state was playing.
    return {"action": "show", "choices": choices, "action_index": 0, "playing": False,
            "view": "front", "focus": "both", "framing": "full", "save": False,
            "registry_sha256": data["sources"]["registry"]["sha256"]}


def validate_request(request, data=None):
    if not isinstance(request, dict) or request.get("action") not in ACTIONS:
        raise ValueError("不支持的审查操作。")
    if request["action"] == "restore":
        # Closing remains possible if a source changes or a draft is incomplete.
        return {"action": "restore"}
    if set(request) != REQUEST_KEYS:
        raise ValueError("审查请求字段不完整或包含未知字段。")
    data = load_catalog() if data is None else data
    if request["registry_sha256"] != data["sources"]["registry"]["sha256"]:
        raise ValueError("服装版本已变化，请重新打开面板。")
    if not isinstance(request["choices"], dict) or set(request["choices"]) != {"female", "male"}:
        raise ValueError("必须明确指定男女各自的搭配。")
    for sex, choice in request["choices"].items():
        contract.validate_choice(sex, choice)
    if type(request["action_index"]) is not int or not 0 <= request["action_index"] <= 5:
        raise ValueError("身体动作编号必须为 0 到 5。")
    if type(request["playing"]) is not bool or type(request["save"]) is not bool:
        raise ValueError("播放与保存选项必须是布尔值。")
    if request["action_index"] == 0 and request["playing"]:
        raise ValueError("静态姿势不能播放，请先选择身体动作。")
    for key, values in (("view", ("front", "side", "back", "threequarter")),
                        ("focus", ("both", "female", "male")), ("framing", ("full", "head", "torso", "legs", "feet"))):
        if request[key] not in values:
            raise ValueError(f"无效的视角选项：{key}。")
    return copy.deepcopy(request)


def command_payload(request):
    return (f"import sys, runpy\nsys.path.insert(0, {str(SCRIPT_ROOT)!r})\n"
            f"runpy.run_path({str(WORKER)!r}, run_name='__main__', "
            f"init_globals={{'DM_SLOT_REVIEW_REQUEST': {request!r}}})")


def verify_result(result, request):
    if not isinstance(result, dict) or result.get("success") is not True:
        raise RuntimeError("UE 审查未完成，请检查本次错误记录。")
    if request["action"] == "restore":
        if result.get("action") != "restore" or result.get("editor_closed") is not False:
            raise RuntimeError("UE 未确认恢复编辑器设置。")
        return result
    actual = result.get("request")
    if not isinstance(actual, dict) or any(actual.get(k) != v for k, v in request.items()):
        raise RuntimeError("UE 实际选择与请求不一致，暂不确认加载。")
    if result.get("level") != LEVEL:
        raise RuntimeError("UE 返回的不是本次独立审查关卡。")
    bindings = result.get("bindings")
    if (not isinstance(bindings, dict) or bindings.get("success") is not True or bindings.get("errors") != []
            or set(bindings.get("characters", {})) != {"female", "male"}):
        raise RuntimeError("UE 缺少成功的男女实际装配检查。")
    for character in bindings["characters"].values():
        if not character.get("components") or any(c.get("errors") for c in character["components"]):
            raise RuntimeError("UE 实际部件检查不完整或存在错误。")
    source = result.get("sources", {}).get("registry", {})
    if source.get("sha256") != request["registry_sha256"]:
        raise RuntimeError("UE 回执中的服装版本与面板不同。")
    if not result.get("plan_sha256") or result["plan_sha256"] != bindings.get("plan_sha256"):
        raise RuntimeError("UE 装配检查未绑定同一搭配计划。")
    return result


def parse_reply(reply, request):
    if not isinstance(reply, dict) or reply.get("success") is not True:
        raise RuntimeError("UE 执行失败，详细记录已保存在 runtime 的 remote 日志。")
    markers = [item.get("output", "").split(MARKER, 1)[1] for item in reply.get("output", [])
               if MARKER in item.get("output", "")]
    if len(markers) != 1:
        raise RuntimeError("UE 未返回唯一审查完成标记，不会自动重试。")
    marker, _ = json.JSONDecoder().raw_decode(markers[0].lstrip())
    if not isinstance(marker, dict) or marker.get("success") is not True:
        raise RuntimeError("UE 审查未成功。")
    raw_path = marker.get("result_file")
    if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
        raise RuntimeError("回执必须使用本次 replies 目录中的绝对 JSON 路径。")
    try:
        path, expected_root = Path(raw_path).resolve(strict=True), (ROOT / "replies").resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("UE 回执文件不存在或无法解析。") from exc
    if path.parent != expected_root or path.suffix.lower() != ".json" or not path.is_file():
        raise RuntimeError("拒绝读取本次 replies 目录之外的回执。")
    result = verify_result(read(path), request)
    return {**result, "controller_result_file": str(path), "controller_result_sha256": contract._source(path)["sha256"]}


def execute(request, node_id=None):
    request = validate_request(request)
    if not WORKER.is_file():
        raise FileNotFoundError("审查执行脚本尚未就绪。")
    # The historical controller's OS lock and editor pin also serialize old UI.
    with command_lock():
        log = ROOT / ("remote_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        envelope = {"started_at": now(), "request": request, "success": False}
        session = None
        try:
            module = previous.load_remote_execution(previous.DEFAULT_ENGINE_ROOT.resolve())
            session = module.RemoteExecution()
            session_path = previous.ROOT / "session.json"
            pinned = read(session_path) if session_path.is_file() else None
            session.start()
            deadline, first_match, last_error = time.monotonic() + 12, None, None
            while time.monotonic() < deadline:
                try:
                    node = select_node(list(session.remote_nodes), node_id, pinned)
                    first_match = first_match or time.monotonic()
                    if time.monotonic() - first_match >= 2:
                        break
                except RuntimeError as exc:
                    first_match, last_error = None, exc
                time.sleep(.2)
            else:
                raise last_error or RuntimeError("未发现可用的 UE 实例。")
            node = select_node(list(session.remote_nodes), node_id, pinned)
            envelope["node"] = node
            write(session_path, {"node_id": node["node_id"], "project": previous.PROJECT,
                                 "user": node.get("user"), "node": node, "pinned_at": now()})
            session.open_command_connection(node["node_id"])
            session._command_connection._command_channel_socket.settimeout(COMMAND_TIMEOUT)
            reply = session.run_command(command_payload(request), unattended=True,
                                        exec_mode=module.MODE_EXEC_FILE, raise_on_failure=False)
            envelope["command_result"] = reply
            result = parse_reply(reply, request)
            envelope.update(success=True, result=result)
            return result
        except Exception as exc:
            envelope["error"] = {"type": type(exc).__name__, "message": str(exc)}
            record_error(exc, "execute")
            raise
        finally:
            envelope["finished_at"] = now()
            try:
                if session is not None:
                    session.stop()
            finally:
                write(log, envelope)


def state_of(request):
    return {k: copy.deepcopy(request.get(k)) for k in STATE_KEYS}


def record_observation(sex, outcome, note, selected, reply, data, *, human_button=False):
    """Only the GUI's explicit human buttons call this after fresh status."""
    if not human_button or sex not in {"female", "male"} or outcome not in {"accepted", "issue"}:
        raise ValueError("观察结果必须由使用者点击正常或有问题按钮记录。")
    verify_result(reply, {**selected, "action": "status", "save": False})
    evidence_path = Path(reply.get("controller_result_file", ""))
    if (not evidence_path.is_absolute() or evidence_path.resolve().parent != (ROOT / "replies").resolve()
            or not evidence_path.is_file() or evidence_path.suffix.lower() != ".json"
            or contract._source(evidence_path)["sha256"] != reply.get("controller_result_sha256")
            or read(evidence_path) != {k: v for k, v in reply.items() if not k.startswith("controller_result_")}):
        raise ValueError("实际装配回执文件已变化或缺失，不能写入人工观察。")
    if digest(reply["sources"]) != digest(data["sources"]) or digest(load_catalog()["sources"]) != digest(data["sources"]):
        raise ValueError("来源已变化，请重新打开面板后记录；旧记录不会覆盖。")
    path = ROOT / "manual_review.json"
    # Reuse the OS lock for append protection across panels/CLI; no UE command.
    with command_lock():
        document = read(path) if path.exists() else {"schema_version": 1, "level": LEVEL,
            "scope": "human_observation_of_loaded_complete_character_fixed_slot_combination",
            "sources": data["sources"], "sources_sha256": digest(data["sources"]), "observations": []}
        if document.get("sources_sha256") != digest(data["sources"]):
            raise ValueError("已有观察记录属于另一版来源，不会覆盖。")
        observation = {"at": now(), "observation_id": uuid.uuid4().hex, "origin": "human_panel_button",
                       "sex": sex, "outcome": outcome, "note": str(note).strip(), "request": copy.deepcopy(reply["request"]),
                       "bindings": copy.deepcopy(reply["bindings"]), "animation": copy.deepcopy(reply.get("animation")),
                       "plan_sha256": reply["plan_sha256"], "sources_sha256": digest(reply["sources"]),
                       "result_file": reply.get("controller_result_file"), "result_sha256": reply.get("controller_result_sha256")}
        document["observations"].append(observation)
        write(path, document)
    return observation


class CommandQueue:
    """One background thread; closing always waits, then sends one restore."""
    def __init__(self, executor, node_id=None):
        self.executor, self.node_id = executor, node_id
        self.requests, self.results = queue.Queue(), queue.Queue()
        self.busy = self.closing = self.closed = False
        self.loaded_request = self.loaded_reply = None
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            request = self.requests.get()
            if request is None:
                return
            try:
                self.results.put((request, self.executor(request, self.node_id), None))
            except Exception as exc:
                record_error(exc, "background_command")
                self.results.put((request, None, exc))

    def submit(self, request):
        if self.busy or self.closed or (self.closing and request.get("action") != "restore"):
            raise RuntimeError("当前操作尚未结束或面板正在关闭。")
        self.busy = True
        self.requests.put(copy.deepcopy(request))

    def close(self):
        if self.closing or self.closed:
            return
        self.closing = True
        if not self.busy:
            self.submit({"action": "restore"})

    def poll(self):
        try:
            request, reply, error = self.results.get_nowait()
        except queue.Empty:
            return None
        self.busy = False
        if request["action"] == "restore":
            self.closed = True
            self.requests.put(None)
        elif error is not None:
            self.loaded_request = self.loaded_reply = None
        else:
            self.loaded_request, self.loaded_reply = copy.deepcopy(request), reply
        if self.closing and not self.closed:
            self.submit({"action": "restore"})
        return request, reply, error


class SexEditor:
    """A draft editor; changing fields never implicitly sends to Unreal."""
    def __init__(self, parent, sex, data, choice, changed):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk, self.sex, self.data, self.changed = tk, ttk, sex, data, changed
        self.families = data["families_by_sex"][sex]
        self.presets = data["presets_by_sex"][sex]
        self.hairs = data["hairs_by_sex"][sex]
        self.shoes = data["shared_shoes_by_sex"][sex]
        self.frame = ttk.Frame(parent, padding=10)
        self.frame.columnconfigure(1, weight=1)
        self.widgets, self.slot_boxes, self.extra_vars = [], {}, {}
        self.preset = self._combo(0, "旧编号快捷搭配", ["自定义搭配"] + [f"{p['index']:02d} · {p['label']}" for p in self.presets])
        self.family = self._combo(1, "服装系列", ["不穿外层服装"] + [f["label"] for f in self.families])
        self.group = self._combo(2, "合法搭配组", [])
        self.slot_frame = ttk.Frame(self.frame)
        self.slot_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        self.slot_frame.columnconfigure(1, weight=1)
        self.shoe = self._combo(4, "共用鞋", ["不加共用鞋"] + [s["label"] for s in self.shoes])
        self.hair = self._combo(5, "本性别发型", ["0 · 无发型"] + [f"{h['index']:02d} · {h['label']}" for h in self.hairs])
        self.hint = tk.StringVar()
        ttk.Label(self.frame, textvariable=self.hint, wraplength=970).grid(row=6, column=0, columnspan=2, sticky="w", pady=6)
        self.preset.bind("<<ComboboxSelected>>", lambda _: self._select_preset())
        self.family.bind("<<ComboboxSelected>>", lambda _: self._select_family())
        self.group.bind("<<ComboboxSelected>>", lambda _: self._select_group())
        self.shoe.bind("<<ComboboxSelected>>", lambda _: self._changed())
        self.hair.bind("<<ComboboxSelected>>", lambda _: self._changed())
        self.enabled_flag = True
        self.set_choice(choice)

    def _combo(self, row, label, values):
        self.ttk.Label(self.frame, text=label, width=16).grid(row=row, column=0, sticky="w", pady=3)
        widget = self.ttk.Combobox(self.frame, state="readonly", values=values)
        widget.grid(row=row, column=1, sticky="ew", pady=3)
        if values:
            widget.current(0)
        self.widgets.append(widget)
        return widget

    def _current_family(self):
        return self.families[self.family.current() - 1] if self.family.current() > 0 else None

    def _current_group(self):
        family = self._current_family()
        return family["groups"][self.group.current()] if family and self.group.current() >= 0 else None

    def _select_preset(self):
        index = self.preset.current()
        if index > 0:
            choice = copy.deepcopy(self.presets[index - 1]["choice"])
            choice["hair_id"] = self.read_choice()["hair_id"]
            self.set_choice(choice)
            self.preset.current(index)
            self.changed()

    def _select_family(self):
        family = self._current_family()
        hair_id = self.read_hair()
        choice = contract.default_choice(family["family_id"], family["groups"][0]["group_id"]) if family else contract.default_choice(None, None)
        choice["hair_id"] = hair_id
        self.set_choice(choice)
        self.changed()

    def _select_group(self):
        family, group = self._current_family(), self._current_group()
        choice = contract.default_choice(family["family_id"], group["group_id"])
        choice["hair_id"] = self.read_hair()
        self.set_choice(choice)
        self.changed()

    def read_hair(self):
        return self.hairs[self.hair.current() - 1]["hair_id"] if self.hair.current() > 0 else None

    def set_choice(self, choice):
        self.preset.current(0)
        self.family.current(next((i for i, f in enumerate(self.families, 1) if f["family_id"] == choice.get("family_id")), 0))
        family = self._current_family()
        self.group.configure(values=[g["label"] for g in family["groups"]] if family else ["无需搭配组"])
        self.group.current(next((i for i, g in enumerate(family["groups"]) if g["group_id"] == choice.get("group_id")), 0) if family else 0)
        self._build_slots(choice)
        self.shoe.current(next((i for i, s in enumerate(self.shoes, 1) if s["asset_id"] == choice.get("shared_shoe_id")), 0))
        self.hair.current(next((i for i, h in enumerate(self.hairs, 1) if h["hair_id"] == choice.get("hair_id")), 0))
        self._update_policy()

    def _build_slots(self, choice):
        for widget in self.slot_frame.winfo_children():
            widget.destroy()
        self.slot_boxes, self.extra_vars, self.dynamic_widgets = {}, {}, []
        group, family = self._current_group(), self._current_family()
        if group is None:
            self.ttk.Label(self.slot_frame, text="保留完整身体基础部件，只选择发型。").grid(sticky="w")
            return
        row = 0
        for slot, options in group["slot_options"].items():
            optional = slot in group["optional_slots"]
            ids = ([None] if optional else []) + [a["asset_id"] for a in options]
            labels = (["不添加"] if optional else []) + [a["label"] for a in options]
            self.ttk.Label(self.slot_frame, text=contract.SLOT_LABELS[slot] + ("（可选）" if optional else "（必选）"), width=16).grid(row=row, column=0, sticky="w", pady=2)
            box = self.ttk.Combobox(self.slot_frame, values=labels, state="readonly")
            box.grid(row=row, column=1, sticky="ew", pady=2)
            selected = choice.get("slot_choices", {}).get(slot)
            box.current(ids.index(selected) if selected in ids else 0)
            box.bind("<<ComboboxSelected>>", lambda _: self._changed())
            self.slot_boxes[slot] = (box, ids)
            self.dynamic_widgets.append(box)
            row += 1
        if group["required_assets"]:
            label = "整套固定部件" if family["assembly_mode"] == "locked_bundle" else "必须保留配件"
            self.ttk.Label(self.slot_frame, text=label + "：" + " + ".join(a["label"] for a in group["required_assets"]),
                           wraplength=950).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
            row += 1
        if group["optional_assets"]:
            extras = self.ttk.Frame(self.slot_frame)
            extras.grid(row=row, column=0, columnspan=2, sticky="w")
            self.ttk.Label(extras, text="可选配件：").pack(side="left")
            for asset in group["optional_assets"]:
                var = self.tk.BooleanVar(value=asset["asset_id"] in choice.get("optional_asset_ids", []))
                button = self.ttk.Checkbutton(extras, text=asset["label"], variable=var, command=self._changed)
                button.pack(side="left", padx=5)
                self.extra_vars[asset["asset_id"]] = var
                self.dynamic_widgets.append(button)

    def read_choice(self):
        family, group = self._current_family(), self._current_group()
        return {"family_id": family["family_id"] if family else None, "group_id": group["group_id"] if group else None,
                "slot_choices": {slot: ids[box.current()] for slot, (box, ids) in self.slot_boxes.items()},
                "optional_asset_ids": [aid for aid, var in self.extra_vars.items() if var.get()],
                "shared_shoe_id": self.shoes[self.shoe.current() - 1]["asset_id"] if self.shoe.current() > 0 else None,
                "hair_id": self.read_hair()}

    def _update_policy(self):
        group = self._current_group()
        native = (group is None or group["shared_shoe_policy"] == "forbidden_native_required"
                  or ("shoes" in self.slot_boxes and self.slot_boxes["shoes"][1][self.slot_boxes["shoes"][0].current()] is not None))
        if native:
            self.shoe.current(0)
        universal = group is not None and group["shared_shoe_policy"] == "required_universal_female_pool"
        if universal and self.shoe.current() <= 0:
            self.shoe.current(next(i for i, shoe in enumerate(self.shoes, 1) if shoe["asset_id"] == "F001"))
        self.shoe.configure(state="readonly" if self.enabled_flag and not native else "disabled")
        self.group.configure(state="readonly" if self.enabled_flag and group is not None else "disabled")
        result = contract.validate_choice(self.sex, self.read_choice())
        notes = ["外套、裤子等只能在当前合法搭配组内选择。"] if group else []
        if native and group:
            notes.append("搭配已含必需鞋款，不能再添加共用鞋。")
        if universal:
            notes.append("女性服装统一使用这 9 款共享鞋；未选鞋时使用 F001。")
        if group and group["shared_shoe_policy"] == "optional_universal_female_pool":
            notes.append("可不穿鞋；穿鞋时统一从这 9 款共享鞋中选择。")
        if result["hair_deny"]:
            notes.append("该服装禁止额外发型；显示时会清空头发部件。")
        self.hint.set(" ".join(notes))

    def _changed(self):
        self.preset.current(0)
        self._update_policy()
        self.changed()

    def enable(self, value):
        self.enabled_flag = value
        for widget in self.widgets + self.dynamic_widgets:
            widget.configure(state=("readonly" if isinstance(widget, self.ttk.Combobox) else "normal") if value else "disabled")
        if value:
            self._update_policy()


def panel(args):
    import tkinter as tk
    from tkinter import ttk
    write(ROOT / "panel_lifecycle.json", {"pid": os.getpid(), "stage": "starting", "started_at": now(), "error": None})
    data = load_catalog()
    saved = read(ROOT / "current_case.json") if (ROOT / "current_case.json").is_file() else None
    request = initial_request(data, saved)
    root = tk.Tk()
    root.title("完整角色 · 按部件选择衣服和发型")
    root.geometry("1100x880")
    root.minsize(930, 800)
    lifecycle = {"pid": os.getpid(), "started_at": now(), "sources_sha256": digest(data["sources"])}
    def checkpoint(stage, **details):
        lifecycle.update(stage=stage, updated_at=now(), **details)
        write(ROOT / "panel_lifecycle.json", lifecycle)
    checkpoint("window_created", initial_request=request, error=None)
    manager = CommandQueue(execute, args.node_id)
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="按合法搭配组选择衣服，点击“显示当前搭配”后在 UE 中检查。", font=("Microsoft YaHei UI", 12)).pack(anchor="w")
    ttk.Label(frame, text="旧编号快捷搭配仅供对照。高跟鞋与新身体贴合仍需检查；关闭面板不会关闭 UE。").pack(anchor="w", pady=5)
    status, note = tk.StringVar(value="正在连接 UE…"), tk.StringVar()
    pending_observation = [None]
    controls = []
    tabs = ttk.Notebook(frame)
    tabs.pack(fill="x", pady=6)
    def draft_changed():
        pending_observation[0] = None
        status.set("选项已修改，点击“显示当前搭配”后再检查。")
    editors = {}
    for sex, label in (("female", "女性"), ("male", "男性")):
        editor = SexEditor(tabs, sex, data, request["choices"][sex], draft_changed)
        editors[sex] = editor
        tabs.add(editor.frame, text=label)
    action_row = ttk.Frame(frame)
    action_row.pack(fill="x", pady=5)
    ttk.Label(action_row, text="身体动作", width=12).pack(side="left")
    action_box = ttk.Combobox(action_row, state="readonly", values=["0 · 静态姿势"] +
        [f"{f['index']} · 女：{f['label']} / 男：{m['label']}" for f, m in zip(data["actions_by_sex"]["female"], data["actions_by_sex"]["male"])])
    action_box.pack(side="left", fill="x", expand=True)
    action_box.current(0)
    action_box.bind("<<ComboboxSelected>>", lambda _: draft_changed())

    def current(action="show", **updates):
        value = {**request, "choices": {s: e.read_choice() for s, e in editors.items()},
                 "action_index": action_box.current(), "action": action, "save": False, **updates}
        if value["action_index"] == 0:
            value["playing"] = False
        return value

    def enable(value):
        for editor in editors.values():
            editor.enable(value)
        action_box.configure(state="readonly" if value else "disabled")
        for button in controls:
            button.configure(state="normal" if value else "disabled")

    def submit(action, **updates):
        if manager.busy or manager.closing:
            return
        try:
            outgoing = validate_request(current(action, **updates), data)
            if action != "show" and (manager.loaded_request is None or outgoing["choices"] != manager.loaded_request["choices"]):
                raise ValueError("请先点击“显示当前搭配”，再操作当前已加载的组合。")
            if action in {"save", "reload", "status", "sample"} and state_of(outgoing) != state_of(manager.loaded_request):
                raise ValueError("动作或视角尚未显示，请先显示当前搭配。")
            manager.submit(outgoing)
            enable(False)
            checkpoint("loading", request=outgoing, error=None)
            status.set("正在检查实际装配…" if action == "status" else "正在更新 UE，请稍候…")
        except Exception as exc:
            pending_observation[0] = None
            record_error(exc, "submit")
            status.set("未执行：" + str(exc)[:400])

    def record(sex, outcome):
        if manager.busy or manager.closing:
            return
        if manager.loaded_request is None or state_of(current()) != state_of(manager.loaded_request):
            status.set("请先成功显示当前搭配，再记录观察。")
            return
        pending_observation[0] = {"sex": sex, "outcome": outcome, "note": note.get()}
        submit("status")

    def poll():
        try:
            item = manager.poll()
            if item is None:
                return
            sent, reply, error = item
            if manager.closed:
                if error is not None:
                    write(ROOT / "restore_error.json", {"at": now(), "error": str(error), "editor_closed": False,
                          "note": "Panel closed; restoration of editor CPU setting was not confirmed."})
                checkpoint("closed", restore_success=error is None, error=str(error) if error else None)
                root.destroy()
                return
            if error is not None:
                pending_observation[0] = None
                checkpoint("load_failed", request=sent, error=str(error))
                status.set("未完成：" + str(error)[:430])
            else:
                request.update({k: copy.deepcopy(sent[k]) for k in STATE_KEYS})
                checkpoint("ready", request=sent, error=None)
                write(ROOT / "panel_state.json", {"pid": os.getpid(), "updated_at": now(), "request": sent,
                      "bindings": reply["bindings"], "sources": reply["sources"], "sources_sha256": digest(reply["sources"]),
                      "plan_sha256": reply["plan_sha256"], "result_file": reply.get("controller_result_file")})
                status.set("当前搭配已显示。" + ("动作播放中。" if sent["playing"] else "当前静止。") + "请在 UE 中检查。")
                pending = pending_observation[0]
                pending_observation[0] = None
                if pending and sent["action"] == "status" and not manager.closing:
                    record_observation(**pending, selected=sent, reply=reply, data=data, human_button=True)
                    status.set("已记录" + ("女性" if pending["sex"] == "female" else "男性") + "当前搭配：" + ("正常。" if pending["outcome"] == "accepted" else "有问题。"))
            enable(not manager.busy and not manager.closing)
            if manager.closing:
                checkpoint("restoring")
                status.set("正在恢复编辑器设置，然后关闭面板…")
        except Exception as exc:
            pending_observation[0] = None
            record_error(exc, "poll")
            checkpoint("callback_failed", error=str(exc))
            status.set("处理未完成，错误已保存：" + str(exc)[:350])
            if not manager.closed:
                enable(not manager.busy and not manager.closing)
        finally:
            if not manager.closed:
                root.after(100, poll)

    def toolbar(items):
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=3)
        for label, callback in items:
            button = ttk.Button(row, text=label, command=callback)
            button.pack(side="left", padx=(0, 6), pady=2)
            controls.append(button)

    def play():
        if action_box.current() == 0:
            action_box.current(1)
        submit("playback", playing=True)
    toolbar([("显示当前搭配", lambda: submit("show")), ("播放动作", play), ("暂停", lambda: submit("playback", playing=False)),
             ("保存审查场景", lambda: submit("save")), ("保存并重载检查", lambda: submit("reload"))])
    toolbar([(label, lambda v=value: submit("view", view=v)) for label, value in
             (("正面", "front"), ("侧面", "side"), ("背面", "back"), ("斜侧面", "threequarter"))] +
            [(label, lambda v=value: submit("view", focus=v)) for label, value in (("男女同屏", "both"), ("只看女性", "female"), ("只看男性", "male"))])
    toolbar([(label, lambda v=value: submit("view", framing=v)) for label, value in
             (("全身", "full"), ("头部", "head"), ("上身", "torso"), ("裤裙", "legs"), ("脚部", "feet"))])
    ttk.Label(frame, textvariable=status, wraplength=1030).pack(anchor="w", pady=8)
    ttk.Separator(frame).pack(fill="x", pady=5)
    ttk.Label(frame, text="人工观察备注（仅点击下方按钮才保存观察结果）：").pack(anchor="w")
    ttk.Entry(frame, textvariable=note).pack(fill="x", pady=5)
    toolbar([(label, lambda s=sex, result=outcome: record(s, result)) for label, sex, outcome in
             (("女性正常", "female", "accepted"), ("女性有问题", "female", "issue"),
              ("男性正常", "male", "accepted"), ("男性有问题", "male", "issue"))])

    def close():
        if manager.closing:
            return
        pending_observation[0] = None
        checkpoint("closing")
        enable(False)
        manager.close()
        status.set("等待当前操作完成并恢复编辑器设置；UE 会保持打开…")
    def callback_error(exc_type, exc, trace):
        record_error(exc, "tk_callback", "".join(traceback.format_exception(exc_type, exc, trace)))
        checkpoint("callback_failed", error=str(exc))
        status.set("面板操作未完成，详情已保存：" + str(exc)[:350])
    root.report_callback_exception = callback_error
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.after(250, lambda: submit("show"))
    try:
        root.mainloop()
    finally:
        if not manager.closed:
            manager.close()
            checkpoint("unexpected_window_exit", error="Waiting for queued editor restoration")
            # Even a mainloop exception must not abandon a queued restore when
            # the daemon thread would otherwise be killed by process exit.
            deadline, restore_error = time.monotonic() + 2 * (COMMAND_TIMEOUT + 15), None
            while not manager.closed and time.monotonic() < deadline:
                item = manager.poll()
                if item and item[0]["action"] == "restore":
                    restore_error = item[2]
                time.sleep(.05)
            if not manager.closed or restore_error is not None:
                message = str(restore_error) if restore_error else "Editor restoration timed out after window exit"
                write(ROOT / "restore_error.json", {"at": now(), "error": message, "editor_closed": False})
                checkpoint("closed", restore_success=False, error=message)
            else:
                checkpoint("closed", restore_success=True, error=None)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("panel",) + ACTIONS, default="panel")
    parser.add_argument("--request-file", type=Path, help="完整 UI choice JSON 请求；不接受 family_asset_ids 作为 UI 输入")
    parser.add_argument("--node-id", help="明确选择当前 UE 节点并替换该工具共用的旧固定记录")
    for sex in ("female", "male"):
        parser.add_argument("--" + sex + "-preset", type=int, help="原面板编号，0 表示无服装")
        parser.add_argument("--" + sex + "-hair", type=int, help="原发型编号 1–40，0 表示无发型")
    parser.add_argument("--action-index", type=int)
    parser.add_argument("--playing", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--view", choices=("front", "side", "back", "threequarter"))
    parser.add_argument("--focus", choices=("both", "female", "male"))
    parser.add_argument("--framing", choices=("full", "head", "torso", "legs", "feet"))
    parser.add_argument("--save", action="store_true")
    return parser


def cli_request(args, data):
    if args.action == "restore":
        return {"action": "restore"}
    request = read(args.request_file) if args.request_file else initial_request(data)
    request["action"] = args.action
    for sex in ("female", "male"):
        preset, hair = getattr(args, sex + "_preset"), getattr(args, sex + "_hair")
        if preset is not None:
            old_hair = request["choices"][sex].get("hair_id")
            rows = [p for p in data["presets_by_sex"][sex] if p["index"] == preset]
            if preset != 0 and len(rows) != 1:
                raise ValueError(f"{sex} 旧编号 {preset} 未保留，不能按列表位置替代。")
            request["choices"][sex] = copy.deepcopy(rows[0]["choice"]) if preset else contract.default_choice(None, None)
            request["choices"][sex]["hair_id"] = old_hair
        if hair is not None:
            rows = [h for h in data["hairs_by_sex"][sex] if h["index"] == hair]
            if hair != 0 and len(rows) != 1:
                raise ValueError(f"{sex} 不能选择发型旧编号 {hair}。")
            request["choices"][sex]["hair_id"] = rows[0]["hair_id"] if hair else None
    for key in ("action_index", "playing", "view", "focus", "framing"):
        if getattr(args, key) is not None:
            request[key] = getattr(args, key)
    request["save"] = bool(args.save) or request.get("save", False)
    return validate_request(request, data)


def main():
    args = build_parser().parse_args()
    if args.action == "panel":
        panel(args)
        return
    request = cli_request(args, None if args.action == "restore" else load_catalog())
    result = execute(request, args.node_id)
    print(json.dumps({"success": True, "action": args.action, "level": result.get("level"),
                      "result_file": result.get("controller_result_file"), "plan_sha256": result.get("plan_sha256"),
                      "bindings_success": (result.get("bindings") or {}).get("success")}, ensure_ascii=False))


def entrypoint():
    try:
        main()
    except Exception as exc:
        record_error(exc, "entrypoint")
        lifecycle_path = ROOT / "panel_lifecycle.json"
        if lifecycle_path.is_file():
            lifecycle = read(lifecycle_path)
            if lifecycle.get("pid") == os.getpid() and lifecycle.get("stage") != "closed":
                lifecycle.update(stage="failed", error=str(exc), updated_at=now())
                write(lifecycle_path, lifecycle)
        raise


if __name__ == "__main__":
    entrypoint()
