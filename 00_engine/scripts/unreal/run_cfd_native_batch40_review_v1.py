"""Small Chinese control panel for five pages of eight native CFD identities."""
import argparse
from datetime import datetime
import json
import queue
import threading
import uuid

import cfd_native_batch40_contract_v1 as contract

WORKER = contract.SCRIPTS / 'ue_cfd_native_batch40_review_v1.py'


def show(request, node_id=None):
    request = contract.normalize_request(request)
    run = contract.RUN / 'runtime/controller' / (datetime.now().strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8])
    result_path = run / 'display.json'
    # Each callback goes through the same exact run-scoped node/user/project
    # selector as import/audit; there is no project-only or background fallback.
    command = ('import sys,runpy,json;sys.path.insert(0,'+repr(str(contract.SCRIPTS))+');'
               'm=runpy.run_path('+repr(str(WORKER))+');'
               'r=m["show"]('+repr(request)+');'
               'm["contract"].write('+repr(str(result_path))+',r);'
               'print("DM_CFD40_REVIEW="+json.dumps({"success":r["success"]}))')
    contract.target_remote()(command,run,'review',node_id=node_id,timeout=600)
    result = contract.read(result_path)
    expected_count = 8 if request['focus'] == 'all' else 1
    if (result.get('success') is not True or result.get('request') != request
            or result.get('level') != contract.LEVEL or len(result.get('displayed',[])) != expected_count):
        raise RuntimeError('Review result does not match the requested page/view')
    return result


def panel(initial, node_id=None):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title('CFD 四十人对照审查')
    root.geometry('570x485')
    root.minsize(520,430)
    box = ttk.Frame(root,padding=16)
    box.pack(fill='both',expand=True)
    ttk.Label(box,text='每页八人：上排男 A / B / L / W，下排女 A / B / L / W',wraplength=520).pack(anchor='w')
    ttk.Label(box,text='五页对应每组第 1–5 人；单人放大后可继续切换角度。',wraplength=520).pack(anchor='w',pady=(3,14))
    page = tk.StringVar(value=str(initial['page']))
    focus = tk.StringVar(value='整页' if initial['focus']=='all' else initial['focus'])
    views = {'正面':'front','侧面':'side','背面':'back'}
    framing = {'全身':'full','头部':'head'}
    view = tk.StringVar(value=next(k for k,v in views.items() if v==initial['view']))
    frame = tk.StringVar(value=next(k for k,v in framing.items() if v==initial['framing']))
    hair = tk.BooleanVar(value=initial['hair'])
    inputs = ttk.Frame(box)
    inputs.pack(fill='x')
    for row,(title,variable,values) in enumerate((('页码',page,tuple(map(str,range(1,6)))),
            ('放大',focus,('整页',)+tuple(map(str,range(1,9)))),('角度',view,tuple(views)),('范围',frame,tuple(framing)))):
        ttk.Label(inputs,text=title).grid(row=row,column=0,sticky='w',padx=(0,12),pady=4)
        ttk.Combobox(inputs,textvariable=variable,values=values,state='readonly',width=22).grid(row=row,column=1,sticky='w',pady=4)
    ttk.Checkbutton(inputs,text='显示统一参考发型',variable=hair).grid(row=4,column=1,sticky='w',pady=6)
    buttons = ttk.Frame(box)
    buttons.pack(fill='x',pady=8)
    status = tk.StringVar(value='选择后点击“显示”。完整导入八人后该页才能打开。')
    ttk.Label(box,textvariable=status,wraplength=520).pack(anchor='w',pady=6)
    order = tk.StringVar(value='')
    ttk.Label(box,textvariable=order,wraplength=520).pack(anchor='w')
    messages = queue.Queue()
    busy = [False]

    def submit(save=False, step=0):
        if busy[0]:
            return
        if step:
            page.set(str(max(1,min(5,int(page.get())+step))))
            focus.set('整页')
        request = {'page':int(page.get()),'focus':'all' if focus.get()=='整页' else focus.get(),
                   'view':views[view.get()],'framing':framing[frame.get()],'hair':hair.get(),'save':save}
        busy[0] = True
        status.set('正在加载所选页面…')
        def work():
            try:
                messages.put((True,show(request,node_id)))
            except Exception as exc:
                messages.put((False,str(exc)))
        threading.Thread(target=work,daemon=True).start()

    ttk.Button(buttons,text='上一页',command=lambda:submit(step=-1)).pack(side='left',padx=(0,6))
    ttk.Button(buttons,text='显示',command=submit).pack(side='left',padx=6)
    ttk.Button(buttons,text='下一页',command=lambda:submit(step=1)).pack(side='left',padx=6)
    ttk.Button(buttons,text='保存当前审查场景',command=lambda:submit(save=True)).pack(side='right')

    def poll():
        try:
            ok,result = messages.get_nowait()
        except queue.Empty:
            pass
        else:
            busy[0] = False
            if ok:
                status.set('已显示。服装和头发的贴合情况仍需逐人查看。')
                order.set('\n'.join(str(r['slot'])+'  '+r['character_id']+'  '+r['group'] for r in result['page_order']))
            else:
                status.set('未完成：'+result)
        root.after(150,poll)
    root.after(150,poll)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',choices=('show','panel'),default='panel')
    parser.add_argument('--page',type=int,default=1)
    parser.add_argument('--focus',default='all',choices=('all',)+tuple(map(str,range(1,9))))
    parser.add_argument('--view',choices=('front','side','back'),default='front')
    parser.add_argument('--framing',choices=('full','head'),default='full')
    parser.add_argument('--no-hair',action='store_true')
    parser.add_argument('--save',action='store_true')
    parser.add_argument('--node-id')
    args = parser.parse_args()
    request = contract.normalize_request({'page':args.page,'focus':args.focus,'view':args.view,
                'framing':args.framing,'hair':not args.no_hair,'save':args.save})
    if args.action == 'panel':
        panel(request,args.node_id)
    else:
        print(json.dumps(show(request,args.node_id),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
