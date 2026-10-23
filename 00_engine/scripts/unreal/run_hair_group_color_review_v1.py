"""Chinese six-hair review panel; source-bound, serial and draft-only grouping."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import threading
import uuid

import cfd_native_batch40_contract_v1 as module_loader
import hair_group_color_review_contract_v1 as contract

WORKER = contract.SCRIPTS / 'ue_hair_group_color_review_v1.py'
target = module_loader.module('cfd_native_pair_ue_target_v1')
target.RUN, target.TARGET_FILE = contract.ROOT.parent, contract.TARGET_FILE


def now():
    return datetime.now(timezone.utc).isoformat()


def show(request, node_id=None, expected_sources=None):
    data = contract.catalog()
    if expected_sources is not None and data['sources'] != expected_sources:
        raise ValueError('来源已更新，请关闭并重新打开面板。')
    request = contract.normalize_request(request, data)
    run = contract.ROOT / 'controller' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + uuid.uuid4().hex[:8])
    result_path = run / 'display.json'
    command = (f'import sys,runpy,json\nsys.path.insert(0,{str(contract.SCRIPTS)!r})\n'
               f'm=runpy.run_path({str(WORKER)!r},init_globals={{"DM_HAIR_REVIEW_SOURCES":{data["sources"]!r}}})\n'
               f'r=m["show"]({request!r})\n'
               f'm["contract"].write({str(result_path)!r},r)\n'
               'print("DM_HAIR_GROUP_COLOR="+json.dumps({"success":r["success"]}))')
    target.remote(command, run, 'review', node_id=node_id, timeout=600)
    result = contract.verify_result(contract.read(result_path), request, data)
    return {**result, 'controller_result_file': str(result_path), 'controller_result_sha256': contract.source(result_path)['sha256']}


def record_draft(result, data, slot, group_label, note):
    """Only the GUI draft button calls this. No acceptance or formal groups."""
    request = result['request']
    contract.verify_result(result, request, data)
    path = Path(result['controller_result_file'])
    if (not path.resolve().is_relative_to((contract.ROOT / 'controller').resolve()) or not path.is_file()
            or contract.source(path)['sha256'] != result['controller_result_sha256']
            or contract.catalog()['sources'] != data['sources']):
        raise ValueError('本次显示记录已变化，请先重新显示。')
    rows = contract.page_hairs(data, request)
    if type(slot) is not int or not 1 <= slot <= len(rows):
        raise ValueError('请选择本页需要备注的发型。')
    if request['focus'] != 'all' and slot != int(request['focus']):
        raise ValueError('单款放大时，只能记录正在显示的这一款。')
    if not str(group_label).strip() and not str(note).strip():
        raise ValueError('请填写拟分组名称或观察备注。')
    row = rows[slot - 1]
    draft = {'at': now(), 'id': uuid.uuid4().hex, 'sex': request['sex'], 'hair_id': row['hair_id'],
             'original_index': row['index'], 'group_draft': str(group_label).strip(), 'note': str(note).strip(),
             'request': request, 'sources': data['sources'], 'display_receipt': contract.source(path),
             'status': 'draft_pending_user_confirmation', 'formal_configuration_written': False}
    destination = contract.ROOT / 'grouping_drafts.json'
    document = contract.read(destination) if destination.exists() else {'schema_version': 1, 'drafts': []}
    document['drafts'].append(draft)
    contract.write(destination, document)
    return draft


def panel(initial, node_id=None):
    import tkinter as tk
    from tkinter import ttk
    data = contract.catalog()
    initial = contract.normalize_request(initial, data)
    root = tk.Tk()
    root.title('发型与发色审查 · 每页六款')
    root.geometry('690x565')
    root.minsize(630, 520)
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='按最新保留名单显示；保留原编号，不再对发型分组。').pack(anchor='w')
    ttk.Label(frame, text='选择发色查看效果；眼睛保持角色原色。').pack(anchor='w', pady=(3, 12))
    sexes = {'女性': 'female', '男性': 'male'}
    views = {'正面': 'front', '侧面': 'side', '背面': 'back', '斜侧面': 'threequarter'}
    labels = {'original': '栗色（原色）', 'black': '黑色', 'blue': '蓝色', 'pink': '粉色', 'purple': '紫色', 'red': '红色', 'teal': '绿色', 'orange': '橙色', 'gold': '金色', 'silver_white': '银白色'}
    sex = tk.StringVar(value=next(k for k, v in sexes.items() if v == initial['sex']))
    page = tk.StringVar(value=str(initial['page']))
    focus = tk.StringVar(value='整页' if initial['focus'] == 'all' else initial['focus'])
    view = tk.StringVar(value=next(k for k, v in views.items() if v == initial['view']))
    hair = tk.StringVar(value=labels[initial['hair_color']])
    eye = tk.StringVar(value=labels[initial['eye_color']])
    inputs, controls, boxes = ttk.Frame(frame), [], {}
    inputs.pack(fill='x')
    for index, (key, title, variable, values) in enumerate((
            ('sex', '性别', sex, list(sexes)), ('page', '页码', page, []), ('focus', '放大', focus, []),
            ('view', '角度', view, list(views)), ('hair', '发色', hair, [labels[v] for v in data['colors']['hair']]))):
        ttk.Label(inputs, text=title, width=12).grid(row=index, column=0, sticky='w', pady=3)
        widget = ttk.Combobox(inputs, values=values, textvariable=variable, state='readonly', width=25)
        widget.grid(row=index, column=1, sticky='w', pady=3)
        controls.append(widget)
        boxes[key] = widget
    status = tk.StringVar(value='准备显示…')
    order = tk.StringVar()
    messages, state = queue.Queue(), {'busy': False, 'closing': False, 'loaded': None}
    lifecycle = {'pid': os.getpid(), 'started_at': now(), 'level': contract.LEVEL, 'sources': data['sources']}

    def checkpoint(stage, **details):
        lifecycle.update(stage=stage, updated_at=now(), **details)
        contract.write(contract.ROOT / 'panel_lifecycle.json', lifecycle)

    def selection(save=False):
        color = lambda value, kind: next(v for v in data['colors'][kind] if labels[v] == value)
        return contract.normalize_request({'sex': sexes[sex.get()], 'page': int(page.get()),
                  'focus': 'all' if focus.get() == '整页' else focus.get(), 'view': views[view.get()],
                  'hair_color': color(hair.get(), 'hair'), 'eye_color': color(eye.get(), 'eye'), 'save': save}, data)

    def refresh_page(reset=False):
        if reset:
            page.set('1')
        maximum = contract.page_count(data, sexes[sex.get()])
        page.set(str(min(maximum, max(1, int(page.get())))))
        boxes['page'].configure(values=[str(i) for i in range(1, maximum + 1)])
        count = min(6, len(data['hairs_by_sex'][sexes[sex.get()]]) - (int(page.get()) - 1) * 6)
        boxes['focus'].configure(values=['整页'] + [str(i) for i in range(1, count + 1)])
        focus.set('整页')
        status.set('选项已改变，请点“显示”。')

    def enable(value):
        for widget in controls:
            widget.configure(state=('readonly' if isinstance(widget, ttk.Combobox) else 'normal') if value else 'disabled')

    def submit(save=False, step=0, original=False):
        if state['busy'] or state['closing']:
            return
        try:
            if step:
                page.set(str(max(1, min(contract.page_count(data, sexes[sex.get()]), int(page.get()) + step))))
                refresh_page()
            if original:
                hair.set(labels['original']); eye.set(labels['original'])
            request = selection(save)
        except Exception as exc:
            status.set('未执行：' + str(exc)); return
        state['busy'] = True
        enable(False)
        checkpoint('loading', request=request, error=None)
        status.set('正在加载，请稍候…')
        def work():
            try:
                messages.put((request, show(request, node_id, data['sources']), None))
            except Exception as exc:
                messages.put((request, None, str(exc)))
        threading.Thread(target=work, daemon=False).start()

    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=10)
    for label, callback in [('上一页', lambda: submit(step=-1)), ('显示', submit), ('下一页', lambda: submit(step=1)),
                             ('恢复原色', lambda: submit(original=True)), ('保存场景', lambda: submit(save=True))]:
        button = ttk.Button(buttons, text=label, command=callback)
        button.pack(side='left', padx=(0, 6)); controls.append(button)
    ttk.Label(frame, textvariable=status, wraplength=640).pack(anchor='w', pady=5)
    ttk.Label(frame, textvariable=order, wraplength=640).pack(anchor='w', pady=5)
    boxes['sex'].bind('<<ComboboxSelected>>', lambda event: refresh_page(True))
    boxes['page'].bind('<<ComboboxSelected>>', lambda event: refresh_page())
    refresh_page()
    focus.set('整页' if initial['focus'] == 'all' else initial['focus'])

    def close():
        state['closing'] = True
        enable(False)
        if state['busy']:
            status.set('等待当前加载结束后关闭；UE 会保留当前场景。')
            checkpoint('closing_waiting_for_command')
        else:
            checkpoint('closed', editor_closed=False)
            root.destroy()

    def poll():
        try:
            request, result, error = messages.get_nowait()
        except queue.Empty:
            pass
        else:
            state['busy'] = False
            if error:
                state['loaded'] = None
                checkpoint('error', request=request, error=error)
                status.set('未完成：' + error[:350])
            else:
                state['loaded'] = result
                checkpoint('ready', request=request, error=None, result_file=result['controller_result_file'])
                rows = contract.page_hairs(data, request)
                order.set('\n'.join(f'{i} · 原编号 {row["index"]:02d} · {row["label"]}' for i, row in enumerate(rows, 1)))
                status.set('已显示。可切换角度，或选本页位置进行单款放大。')
            if state['closing']:
                checkpoint('closed', editor_closed=False)
                root.destroy(); return
            enable(True)
        root.after(120, poll)
    checkpoint('starting')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(120, poll)
    root.after(200, submit)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('panel', 'show', 'catalog'), default='panel')
    parser.add_argument('--sex', choices=('female', 'male'), default='female')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--focus', default='all')
    parser.add_argument('--view', choices=('front', 'side', 'back', 'threequarter'), default='front')
    parser.add_argument('--hair-color', choices=contract.HAIR_COLORS, default='original')
    parser.add_argument('--eye-color', choices=contract.EYE_COLORS, default='original')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--node-id')
    args = parser.parse_args()
    if args.action == 'catalog':
        print(json.dumps(contract.catalog(), ensure_ascii=False, indent=2)); return
    request = {key: getattr(args, key) for key in contract.DEFAULT}
    if args.action == 'panel':
        panel(request, args.node_id)
    else:
        print(json.dumps(show(request, args.node_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
