"""Independent character/hair inspection panel; connect to the existing UE only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
import uuid

import run_complete_character_wardrobe_hair_review_v1 as bridge
from scene_site_review_panel_v1 import install_complete_reply_receiver

SCRIPT_ROOT = Path(__file__).resolve().parent
RUN = SCRIPT_ROOT.parents[2] / '00_engine/outputs/hair_only_review_20261017_v1'
SESSION = SCRIPT_ROOT.parents[2] / '00_engine/outputs/scene_site_review_20261014_v1/session.json'
WORKER = SCRIPT_ROOT / 'ue_hair_only_review_v1.py'
MARKER = 'DM_HAIR_ONLY_REVIEW='
VIEWS = {'正面': 'front', '侧面': 'side', '背面': 'back', '斜侧面': 'threequarter'}
now, read, write = bridge.now, bridge.read, bridge.write


def request(action, **values):
    if action not in {'catalog', 'status', 'show', 'view'}:
        raise ValueError('不支持的发型审查操作。')
    if 'view' in values and values['view'] not in VIEWS.values():
        raise ValueError('请选择有效的观察角度。')
    return {'action': action, 'request_id': uuid.uuid4().hex, **values}


def command_payload(sent):
    return (f'import sys, importlib, json\nsys.path.insert(0, {str(SCRIPT_ROOT)!r})\n'
            'import ue_hair_only_review_v1 as hair_review\n'
            'importlib.reload(hair_review)\n'
            f'hair_result = hair_review.dispatch({sent!r})\n'
            f'print({MARKER!r} + json.dumps(hair_result, ensure_ascii=False))')


def parse_reply(reply, sent):
    if not isinstance(reply, dict) or reply.get('success') is not True:
        raise RuntimeError('UE 未完成操作，请查看输出目录中的 remote 记录。')
    markers = [str(row.get('output', '')).split(MARKER, 1)[1]
               for row in reply.get('output', []) if MARKER in str(row.get('output', ''))]
    if len(markers) != 1:
        raise RuntimeError('UE 未返回唯一的发型审查回执；本次操作不会自动重试。')
    result, _ = json.JSONDecoder().raw_decode(markers[0].lstrip())
    if not isinstance(result, dict) or result.get('success') is not True:
        detail = result.get('error') or result.get('message') if isinstance(result, dict) else str(result)
        raise RuntimeError('操作未完成：' + str(detail or '请查看输出目录中的记录。'))
    if result.get('request_id') not in (None, sent['request_id']):
        raise RuntimeError('UE 回执与本次操作不匹配。')
    return result


def execute(sent, node_id=None):
    if not WORKER.is_file():
        raise FileNotFoundError('独立发型审查脚本尚未就绪。')
    with bridge.command_lock():
        record = {'started_at': now(), 'request': sent, 'success': False}
        session = None
        try:
            module = bridge.load_remote_execution(bridge.DEFAULT_ENGINE_ROOT.resolve())
            install_complete_reply_receiver(module)
            session = module.RemoteExecution()
            session.start()
            pinned = read(SESSION) if SESSION.is_file() else None
            deadline, last_error, found_at = time.monotonic() + 12, None, None
            while time.monotonic() < deadline:
                try:
                    bridge.select_node(list(session.remote_nodes), node_id, pinned)
                    found_at = found_at or time.monotonic()
                    if time.monotonic() - found_at >= .6:
                        break
                except RuntimeError as exc:
                    last_error, found_at = exc, None
                time.sleep(.2)
            else:
                raise last_error or RuntimeError('未发现可用 UE，请先打开 datatry_02。')
            node = bridge.select_node(list(session.remote_nodes), node_id, pinned)
            record['node'] = node
            write(RUN / 'session.json', {'node_id': node['node_id'], 'node': node, 'pinned_at': now()})
            session.open_command_connection(node['node_id'])
            session._command_connection._command_channel_socket.settimeout(300)
            reply = session.run_command(command_payload(sent), unattended=True,
                                        exec_mode=module.MODE_EXEC_FILE, raise_on_failure=False)
            record['command_result'] = reply
            result = parse_reply(reply, sent)
            record.update(success=True, result=result)
            return result
        except Exception as exc:
            record['error'] = {'message': str(exc), 'traceback': traceback.format_exc()}
            raise
        finally:
            record['finished_at'] = now()
            try:
                if session is not None:
                    session.stop()
            finally:
                write(RUN / 'remote' / (sent['request_id'] + '.json'), record)


@contextmanager
def panel_lock():
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / 'panel.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if sys.platform == 'win32':
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError('独立发型面板已经打开，请使用现有窗口。') from exc
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


def choose_initial(catalog, state=None):
    identities = catalog['identities']
    if not identities:
        raise ValueError('角色目录为空。')
    state = state or {}
    identity = next((row for row in identities if row['id'] == state.get('character_id')), None)
    identity = identity or next((row for row in identities if row['sex'] == 'female'), identities[0])
    hairs = catalog['hairs_by_sex'][identity['sex']]
    if not hairs:
        raise ValueError('该角色没有可审看的保留发型。')
    hair = next((row for row in hairs if row['hair_id'] == state.get('hair_id')), None)
    hair = hair or next((row for row in hairs if row['hair_id'] == 'HB3_14'), hairs[0])
    return {'character_id': identity['id'], 'hair_id': hair['hair_id'],
            'view': state.get('view') if state.get('view') in VIEWS.values() else 'front'}


class CommandQueue:
    def __init__(self, node_id=None, executor=execute):
        self.node_id, self.executor = node_id, executor
        self.requests, self.results = queue.Queue(), queue.Queue()
        self.busy = False
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        while True:
            sent = self.requests.get()
            if sent is None:
                return
            try:
                self.results.put((sent, self.executor(sent, self.node_id), None))
            except Exception as exc:
                self.results.put((sent, None, str(exc)))

    def submit(self, sent):
        if self.busy:
            raise RuntimeError('上一个操作尚未完成，请稍候。')
        self.busy = True
        self.requests.put(dict(sent))

    def poll(self):
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            return None
        self.busy = False
        return result


def panel(node_id=None):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title('独立发型审查 · 角色与发型')
    root.geometry('560x350')
    root.minsize(520, 330)
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='独立发型审查', font=('Microsoft YaHei UI', 16, 'bold')).pack(anchor='w')
    counts = tk.StringVar(value='正在读取角色与保留发型…')
    ttk.Label(frame, textvariable=counts).pack(anchor='w', pady=(5, 16))
    form = ttk.Frame(frame)
    form.pack(fill='x')
    form.columnconfigure(1, weight=1)
    character, hair = tk.StringVar(), tk.StringVar()
    boxes, controls = {}, []
    for row, (key, title, variable) in enumerate((('character', '角色', character), ('hair', '发型', hair))):
        ttk.Label(form, text=title, width=8).grid(row=row, column=0, sticky='w', pady=5)
        widget = ttk.Combobox(form, textvariable=variable, state='disabled')
        widget.grid(row=row, column=1, sticky='ew', pady=5)
        boxes[key] = widget
        controls.append(widget)
    navigation = ttk.Frame(frame)
    navigation.pack(fill='x', pady=(12, 5))
    angles = ttk.Frame(frame)
    angles.pack(fill='x', pady=5)
    status = tk.StringVar(value='正在连接现有 UE 编辑器…')
    ttk.Label(frame, textvariable=status, wraplength=505).pack(anchor='w', pady=(13, 0))
    jobs = CommandQueue(node_id)
    data, identities, hairs, shown = {}, [], [], {}
    selected_view = 'front'
    started_at = now()

    def lifecycle(phase, **values):
        write(RUN / 'panel_lifecycle.json', {'pid': os.getpid(), 'started_at': started_at,
              'updated_at': now(), 'phase': phase, **values})

    def enable(enabled):
        for widget in controls:
            widget.configure(state=('readonly' if isinstance(widget, ttk.Combobox) else 'normal')
                             if enabled else 'disabled')

    def send(sent):
        enable(False)
        status.set('正在打开独立关卡并显示角色与发型…' if sent['action'] == 'show' else '正在连接 UE…')
        lifecycle('busy', request=sent)
        jobs.submit(sent)

    def rebuild_hairs(remember=None):
        if not identities or boxes['character'].current() < 0:
            return
        identity = identities[boxes['character'].current()]
        hairs[:] = data['hairs_by_sex'][identity['sex']]
        boxes['hair']['values'] = [f"{int(row['index']):02d} 号 · {row.get('label') or row['hair_id']}" for row in hairs]
        choice = next((i for i, row in enumerate(hairs) if row['hair_id'] == remember), None)
        if choice is None:
            choice = next((i for i, row in enumerate(hairs) if row['hair_id'] == 'HB3_14'), 0)
        if hairs:
            boxes['hair'].current(choice)
        else:
            hair.set('')
        female = len(data['hairs_by_sex'].get('female', []))
        male = len(data['hairs_by_sex'].get('male', []))
        counts.set(f'{len(identities)} 个角色 · 女性 {female} 款发型 · 男性 {male} 款发型\n发型沿用原编号，反馈时可直接说“女性 02 号”。')

    def show(view=None):
        nonlocal selected_view
        if jobs.busy or not hairs or boxes['character'].current() < 0 or boxes['hair'].current() < 0:
            return
        selected_view = view or selected_view
        selection = {'character_id': identities[boxes['character'].current()]['id'],
                     'hair_id': hairs[boxes['hair'].current()]['hair_id']}
        if view and all(shown.get(key) == value for key, value in selection.items()):
            send(request('view', view=selected_view))
        else:
            send(request('show', **selection, view=selected_view))

    def move(offset):
        if jobs.busy or not hairs:
            return
        boxes['hair'].current((boxes['hair'].current() + offset) % len(hairs))
        show()

    for text, callback in (('上一款', lambda: move(-1)), ('显示角色与发型', show), ('下一款', lambda: move(1))):
        button = ttk.Button(navigation, text=text, command=callback)
        button.pack(side='left', padx=(0, 8))
        controls.append(button)
    for text, view in VIEWS.items():
        button = ttk.Button(angles, text=text, command=lambda value=view: show(value), width=9)
        button.pack(side='left', padx=(0, 7))
        controls.append(button)
    retry = ttk.Button(frame, text='重新连接', command=lambda: send(request('catalog')))
    retry.pack(anchor='e', pady=(5, 0))
    controls.append(retry)
    boxes['character'].bind('<<ComboboxSelected>>', lambda event: rebuild_hairs(shown.get('hair_id')))

    def poll():
        nonlocal selected_view
        item = jobs.poll()
        if item:
            sent, result, error = item
            if error:
                enable(bool(data))
                retry.configure(state='normal')
                status.set('未完成：' + error)
                lifecycle('error', error=error)
            elif sent['action'] == 'catalog':
                try:
                    data.clear()
                    data.update(result['catalog'])
                    identities[:] = data['identities']
                    initial = choose_initial(data, result.get('state'))
                    boxes['character']['values'] = [str(row.get('label') or row['id']) for row in identities]
                    boxes['character'].current(next(i for i, row in enumerate(identities) if row['id'] == initial['character_id']))
                    rebuild_hairs(initial['hair_id'])
                    selected_view = initial['view']
                    send(request('show', **initial))
                except Exception as exc:
                    retry.configure(state='normal')
                    status.set('目录读取失败：' + str(exc))
                    lifecycle('error', error=str(exc))
            else:
                shown.clear()
                shown.update(result.get('state') or {})
                enable(True)
                view_label = next((label for label, value in VIEWS.items() if value == selected_view), selected_view)
                status.set(f'已显示：{character.get()} · {hair.get()} · {view_label}')
                lifecycle('ready', state=shown)
        root.after(100, poll)

    def close():
        lifecycle('closed', command_in_flight=jobs.busy)
        jobs.requests.put(None)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    lifecycle('starting')
    send(request('catalog'))
    root.after(100, poll)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=['panel', 'catalog', 'status', 'show', 'view'], default='panel')
    parser.add_argument('--node-id')
    parser.add_argument('--character-id')
    parser.add_argument('--hair-id')
    parser.add_argument('--view', choices=list(VIEWS.values()))
    args = parser.parse_args()
    try:
        if args.action == 'panel':
            with panel_lock():
                panel(args.node_id)
        else:
            values = {key: getattr(args, key) for key in ('character_id', 'hair_id', 'view') if getattr(args, key) is not None}
            print(json.dumps(execute(request(args.action, **values), args.node_id), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        write(RUN / 'controller_error.json', {'at': now(), 'pid': os.getpid(), 'error': str(exc), 'traceback': traceback.format_exc()})
        if args.action == 'panel':
            import tkinter.messagebox
            tkinter.messagebox.showerror('独立发型审查', str(exc))
        else:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
