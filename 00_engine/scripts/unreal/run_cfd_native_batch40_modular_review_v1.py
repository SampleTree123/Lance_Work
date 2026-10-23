"""Reuse the full fixed-slot panel with 20 identities per sex and source checks."""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

import cfd_native_batch40_contract_v1 as batch
import cfd_native_batch40_modular_contract_v1 as identities
import cfd_native_batch40_configuration_v1 as configurations

# Private instances prevent this adapter from retargeting old pair controllers
# when several controllers are imported by the same offline test process.
panel = batch.module('run_complete_character_slot_review_v1')
panel.previous = batch.module('run_complete_character_wardrobe_hair_review_v1')
target = batch.module('cfd_native_pair_ue_target_v1')
target.RUN, target.TARGET_FILE = identities.RUN, identities.RUN / 'ue_target.json'
panel.ROOT = identities.ROOT
panel.WORKER = identities.SCRIPTS / 'ue_cfd_native_batch40_modular_review_v1.py'
panel.LEVEL = identities.LEVEL
panel.previous.ROOT = identities.ROOT / 'controller'
panel.previous.LEVEL = identities.LEVEL
panel.select_node = target.select_panel_node
panel.command_lock = panel.previous.command_lock
panel.STATE_KEYS += ('character_ids', 'character_registry_sha256', 'appearance', 'face_registry_sha256')

_load = panel.load_catalog
_initial = panel.initial_request
_validate = panel.validate_request
_verify = panel.verify_result
_parser = panel.build_parser
_cli = panel.cli_request
_editor = panel.SexEditor
_queue = panel.CommandQueue
_record_observation = panel.record_observation
_active_request = None
_active_manager = None
_active_editors = {}
_config_status = None
EXTENDED_KEYS = {'character_ids', 'character_registry_sha256', 'appearance', 'face_registry_sha256'}
COLOR_LABELS = {'original': '原色', 'black': '黑色', 'blue': '蓝色', 'pink': '粉色',
                'purple': '紫色', 'red': '红色', 'teal': '青色', 'orange': '橙色',
                'gold': '金色', 'silver_white': '银白色', 'brown': '棕色', 'green': '绿色'}


def load_catalog():
    data = _load()
    data['identities'] = identities.identity_catalog()
    data['sources']['character_registry'] = data['identities']['source']
    data['appearance'] = identities.appearance_catalog()
    data['sources']['appearance_palette'] = data['appearance']['source']
    data['face_library'] = identities.face_catalog()
    if data['face_library'].get('registry_source'):
        data['sources']['native_face_library'] = data['face_library']['registry_source']
    return data


def initial_request(data, saved=None):
    global _active_request
    result = _initial(data, saved)
    result.update(character_ids=copy.deepcopy(identities.DEFAULT_CHARACTER_IDS),
                  character_registry_sha256=data['identities']['source']['sha256'],
                  appearance=identities.default_appearance(), face_registry_sha256=None)
    old = (saved or {}).get('request', saved or {})
    if old.get('character_registry_sha256') == result['character_registry_sha256']:
        result['character_ids'] = identities.validate_character_ids(old.get('character_ids'), data['identities'])
        appearance = old.get('appearance', identities.default_appearance())
        changes = []
        if any(r['face_id'] != 'none' for r in appearance.values()):
            appearance, changes = identities.face_library.migrate_legacy_appearance(appearance, old.get('face_registry_sha256'), data['face_library'])
        result['appearance'] = identities.validate_appearance(appearance, data['face_library'])
        result['face_registry_sha256'] = (data['face_library'].get('registry_source', {}).get('sha256') if changes else old.get('face_registry_sha256'))
        if changes:
            print('已明确迁移旧表情选择：' + json.dumps(changes, ensure_ascii=False))
        # The old panel deliberately selected hair 2 on reopening. This batch
        # panel keeps the last displayed legal outfit AND hair for each identity.
        # Motion still opens paused/static, so merely opening a window is calm.
        if old.get('registry_sha256') == data['sources']['registry']['sha256']:
            for sex in identities.SEXES:
                try:
                    choice = old['choices'][sex]
                    panel.contract.validate_choice(sex, choice)
                    result['choices'][sex] = copy.deepcopy(choice)
                except (KeyError, TypeError, ValueError):
                    pass
    _active_request = result
    return result


def validate_request(request, data=None):
    if isinstance(request, dict) and request.get('action') == 'restore':
        return {'action': 'restore'}
    data = load_catalog() if data is None else data
    if isinstance(request, dict) and 'appearance' not in request:
        request = dict(request, appearance=identities.default_appearance())
    if isinstance(request, dict) and 'face_registry_sha256' not in request:
        request = dict(request, face_registry_sha256=None)
    if not isinstance(request, dict) or set(request) != panel.REQUEST_KEYS | EXTENDED_KEYS:
        raise ValueError('人物插槽请求必须包含角色编号和角色索引版本。')
    identities.validate_appearance(request['appearance'], data['face_library'])
    original = {k: v for k, v in request.items() if k not in EXTENDED_KEYS}
    has_face = any(r.get('face_id') != 'none' for r in request['appearance'].values())
    # The old static-body validator does not know a face-only clip can play.
    if original['action_index'] == 0 and has_face:
        if type(original['playing']) is not bool:
            raise ValueError('播放开关必须是布尔值。')
        original['playing'] = False
    _validate(original, data)
    identities.validate_character_ids(request['character_ids'], data['identities'])
    for sex in identities.SEXES:
        if request['appearance'][sex]['face_id'] not in {r['face_id'] for r in identities.faces_for_action(data, sex, request['action_index'])}:
            raise ValueError('当前身体动作尚无该表情的已验证组合：' + sex)
    expected_face_sha = data['face_library'].get('registry_source', {}).get('sha256') if has_face else None
    if request['face_registry_sha256'] != expected_face_sha:
        raise ValueError('表情库版本已变化，请重新打开面板。')
    if request['character_registry_sha256'] != data['identities']['source']['sha256']:
        raise ValueError('角色索引版本已变化，请重新打开面板。')
    return copy.deepcopy(request)


def verify_result(result, request):
    _verify(result, request)
    if request['action'] == 'restore':
        return result
    catalog = identities.identity_catalog()
    if (result.get('sources', {}).get('character_registry') != catalog['source']
            or request['character_registry_sha256'] != catalog['source']['sha256']):
        raise RuntimeError('UE 回执没有绑定当前 40 人角色索引。')
    if result.get('sources', {}).get('appearance_palette') != identities.appearance_catalog()['source']:
        raise RuntimeError('UE 回执没有绑定当前固定色板。')
    library = identities.face_catalog()
    if library.get('registry_source') and result.get('sources', {}).get('native_face_library') != library['registry_source']:
        raise RuntimeError('UE 回执没有绑定当前表情库。')
    for sex, identifier in request['character_ids'].items():
        actual, expected = result['bindings']['characters'][sex], catalog['by_id'][identifier]
        if actual.get('character_id') != identifier or actual.get('body_skeleton') != expected['skeleton']:
            raise RuntimeError('UE 实际身份或共享骨骼与选择不一致。')
        expected_meshes = {m['path'] for m in expected['meshes']}
        actual_meshes = {m.get('mesh_path') for m in actual['components']}
        if not expected_meshes <= actual_meshes:
            raise RuntimeError('UE 回执未确认该身份全部六个基础部件。')
        color_check = result.get('appearance_readback', {}).get(sex, {})
        if color_check.get('success') is not True or color_check.get('requested') != request['appearance'][sex]:
            raise RuntimeError('UE 实际颜色未通过读取校验。')
        if request['appearance'][sex]['face_id'] != 'none':
            face = result.get('face_readback', {}).get(sex, {})
            if face.get('success') is not True or face.get('face_id') != request['appearance'][sex]['face_id']:
                raise RuntimeError('UE 实际表情动画未通过读取校验。')
    return result


def record_observation(sex, outcome, note, selected, reply, data, *, human_button=False):
    if data.get('face_library', {}).get('schema') != identities.face_library.SCHEMA_V2:
        return _record_observation(sex, outcome, note, selected, reply, data, human_button=human_button)
    if not human_button or sex not in identities.SEXES or outcome not in {'accepted', 'issue'}:
        raise ValueError('观察结果必须由使用者点击正常或有问题按钮记录。')
    verify_result(reply, {**selected, 'action': 'status', 'save': False})
    evidence = Path(reply.get('controller_result_file', ''))
    if (not evidence.is_absolute() or evidence.resolve().parent != (identities.ROOT / 'replies').resolve()
            or not evidence.is_file() or evidence.suffix.lower() != '.json'
            or identities.source(evidence)['sha256'] != reply.get('controller_result_sha256')
            or identities.read(evidence) != {k: v for k, v in reply.items() if not k.startswith('controller_result_')}):
        raise ValueError('实际装配回执文件已变化或缺失，不能写入人工观察。')
    if reply['sources'] != data['sources'] or load_catalog()['sources'] != data['sources']:
        raise ValueError('来源已变化，请重新打开面板后记录。')
    path = identities.face_library.PANEL_RUN / 'manual_review.json'
    with panel.command_lock():
        document = identities.read(path) if path.exists() else {'schema_version': 1, 'level': identities.LEVEL,
            'scope': 'human_observation_of_loaded_native5_character_combination',
            'sources': data['sources'], 'sources_sha256': panel.digest(data['sources']), 'observations': []}
        if document.get('sources_sha256') != panel.digest(data['sources']):
            raise ValueError('已有观察记录属于另一版来源，不会覆盖。')
        document['observations'].append({'at': panel.now(), 'observation_id': uuid.uuid4().hex,
            'origin': 'human_panel_button', 'sex': sex, 'outcome': outcome, 'note': str(note).strip(),
            'request': copy.deepcopy(reply['request']), 'bindings': copy.deepcopy(reply['bindings']),
            'animation': copy.deepcopy(reply.get('animation')), 'plan_sha256': reply['plan_sha256'],
            'sources_sha256': panel.digest(reply['sources']), 'result_file': str(evidence),
            'result_sha256': reply['controller_result_sha256']})
        identities.write(path, document)
    return document['observations'][-1]


class IdentitySexEditor(_editor):
    def __init__(self, parent, sex, data, choice, changed):
        super().__init__(parent, sex, data, choice, changed)
        parent.winfo_toplevel().title('CFD40 · 角色切换与分离槽位审查')
        for widget in parent.master.winfo_children():
            if widget.winfo_class() != 'TLabel':
                continue
            text = str(widget.cget('text'))
            if text.startswith('按合法搭配组选择衣服'):
                widget.configure(text='先选择角色，再按槽位搭配衣服和发型，点击“显示当前搭配”检查。')
            elif text.startswith('旧编号快捷搭配仅供对照'):
                widget.configure(text='男女各 20 人；换人会保留搭配与动作。重新打开时保留搭配，以静态姿势开始。')
        # Move the inherited controls down one row, leaving their slot policies
        # and all original callbacks untouched.
        for widget in self.frame.winfo_children():
            grid = widget.grid_info()
            if grid:
                widget.grid_configure(row=int(grid['row']) + 1)
        self.identity_rows = data['identities']['by_sex'][sex]
        self.identity = self._combo(0, '当前角色（20 人）',
                                   [row['character_id'] for row in self.identity_rows])
        identifier = _active_request['character_ids'][sex]
        self.identity.current(next(i for i, row in enumerate(self.identity_rows) if row['character_id'] == identifier))
        self.identity.bind('<<ComboboxSelected>>', self._identity_changed)
        self.hair_color = self._combo(8, '发色（固定 10 色）', [COLOR_LABELS[v] for v in data['appearance']['hair']])
        for kind in ('hair',):
            box = getattr(self, kind + '_color')
            box.current(data['appearance'][kind].index(_active_request['appearance'][sex][kind + '_color']))
            box.bind('<<ComboboxSelected>>', lambda _, k=kind: self._color_changed(k))
        self.face = self._combo(9, '表情（原速 5 秒，结束后可重播）', [])
        self.refresh_faces(_active_request['action_index'])
        self.face.bind('<<ComboboxSelected>>', self._face_changed)
        reset = self.ttk.Button(self.frame, text='本角色恢复原色', command=self._original_colors)
        reset.grid(row=10, column=1, sticky='w', pady=3)
        self.widgets.append(reset)
        _active_editors[sex] = self
        if sex == 'male':
            parent.after_idle(lambda: install_configuration_controls(parent.master, data))

    def refresh_faces(self, index):
        self.face_rows = identities.faces_for_action(self.data, self.sex, index)
        selected = _active_request['appearance'][self.sex]['face_id']
        self.face.configure(values=[r['label'] for r in self.face_rows])
        matches = [i for i, r in enumerate(self.face_rows) if r['face_id'] == selected]
        if matches:
            self.face.current(matches[0])
        else:
            # Keep the draft selection visible; never silently replace it.
            self.face.set('该动作暂不支持所选表情，请重新选择')

    def _face_changed(self, _event=None):
        index = self.face.current()
        if index >= 0:
            _active_request['appearance'][self.sex]['face_id'] = self.face_rows[index]['face_id']
            pin_face_registry(_active_request, self.data)
            self.changed()

    def _identity_changed(self, _event=None):
        replacement = identities.switch_identity(_active_request, self.sex,
                         self.identity_rows[self.identity.current()]['character_id'], self.data['identities'])
        _active_request['character_ids'] = replacement['character_ids']
        self.changed()

    def _color_changed(self, kind):
        _active_request['appearance'][self.sex][kind + '_color'] = self.data['appearance'][kind][getattr(self, kind + '_color').current()]
        self.changed()

    def _original_colors(self):
        for kind in ('hair',):
            getattr(self, kind + '_color').current(self.data['appearance'][kind].index('original'))
            _active_request['appearance'][self.sex][kind + '_color'] = 'original'
        self.changed()


def action_box():
    if not _active_editors:
        return None
    root = next(iter(_active_editors.values())).frame.winfo_toplevel()
    def visit(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == 'TCombobox':
                values = tuple(child.cget('values'))
                if values and str(values[0]).startswith('0 · 静态姿势'):
                    return child
            found = visit(child)
            if found is not None:
                return found
    return visit(root)


def update_editor_selection(request):
    _active_request.update(copy.deepcopy(request))
    for sex, editor in _active_editors.items():
        editor.set_choice(request['choices'][sex])
        editor.identity.current(next(i for i, row in enumerate(editor.identity_rows) if row['character_id'] == request['character_ids'][sex]))
        for kind in ('hair',):
            getattr(editor, kind + '_color').current(editor.data['appearance'][kind].index(request['appearance'][sex][kind + '_color']))
        editor.refresh_faces(request['action_index'])
    widget = action_box()
    if widget is not None:
        widget.current(request['action_index'])


def pin_face_registry(request, data):
    has_face = any(r['face_id'] != 'none' for r in request['appearance'].values())
    request['face_registry_sha256'] = data['face_library'].get('registry_source', {}).get('sha256') if has_face else None
    return request


def ui_request(data, action='show', **updates):
    request = {**copy.deepcopy(_active_request), 'choices': {s: e.read_choice() for s, e in _active_editors.items()},
               'action_index': action_box().current(), 'action': action, 'save': False, **updates}
    if request['action_index'] == 0 and all(r['face_id'] == 'none' for r in request['appearance'].values()):
        request['playing'] = False
    return validate_request(pin_face_registry(request, data), data)


def install_face_controls(frame, data):
    """Reuse original widgets/queue/poll; extend static playback in this adapter."""
    def changed(_event=None):
        for editor in _active_editors.values():
            editor.refresh_faces(action_box().current())
    action_box().bind('<<ComboboxSelected>>', changed, add='+')
    def submit(action='show', **updates):
        if _active_manager.busy or _active_manager.closing:
            return
        try:
            outgoing = ui_request(data, action, **updates)
            loaded = _active_manager.loaded_request
            if action != 'show' and (loaded is None or outgoing['choices'] != loaded['choices']):
                raise ValueError('请先显示当前搭配。')
            if action in {'save', 'reload', 'status', 'sample'} and panel.state_of(outgoing) != panel.state_of(loaded):
                raise ValueError('请先显示当前动作与视角。')
            _active_manager.submit(outgoing)
            for editor in _active_editors.values(): editor.enable(False)
            action_box().configure(state='disabled')
            _config_status.set('正在更新角色，请稍候…')
            return True
        except Exception as exc:
            _config_status.set('未执行：' + str(exc))
            return False
    def play():
        if action_box().current() == 0 and all(r['face_id'] == 'none' for r in _active_request['appearance'].values()):
            action_box().current(1)
            changed()
        submit('playback', playing=True)
    callbacks = {'显示当前搭配': lambda: submit('show'), '播放动作': play,
                 '暂停': lambda: submit('playback', playing=False),
                 '保存审查场景': lambda: submit('save'), '保存并重载检查': lambda: submit('reload')}
    def observe(sex, outcome):
        note = next((c.get() for c in frame.winfo_children() if c.winfo_class() == 'TEntry'), '')
        if submit('status'):
            _active_manager.pending_observation = (sex, outcome, note, data)
    for label, sex, outcome in [('女性正常', 'female', 'accepted'), ('女性有问题', 'female', 'issue'),
                                 ('男性正常', 'male', 'accepted'), ('男性有问题', 'male', 'issue')]:
        callbacks[label] = lambda s=sex, o=outcome: observe(s, o)
    for key, rows in [('view', [('正面', 'front'), ('侧面', 'side'), ('背面', 'back'), ('斜侧面', 'threequarter')]),
                      ('focus', [('男女同屏', 'both'), ('只看女性', 'female'), ('只看男性', 'male')]),
                      ('framing', [('全身', 'full'), ('头部', 'head'), ('上身', 'torso'), ('裤裙', 'legs'), ('脚部', 'feet')])]:
        for label, value in rows:
            callbacks[label] = lambda k=key, v=value: submit('view', **{k: v})
    def walk(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == 'TButton' and str(child.cget('text')) in callbacks:
                child.configure(command=callbacks[str(child.cget('text'))])
            walk(child)
    walk(frame)


def install_configuration_controls(frame, data):
    global _config_status
    from tkinter import ttk, filedialog, StringVar
    row = ttk.Frame(frame)
    # Keep the complete-selection controls close to the top, independent of
    # the inherited local closures and their existing wardrobe callbacks.
    row.pack(fill='x', pady=5, before=frame.winfo_children()[2])
    _config_status = StringVar(value='整套配置保存身份、衣鞋、发型发色、表情、动作和播放开关。')
    install_face_controls(frame, data)
    def available():
        if _active_manager is None or _active_manager.busy or _active_manager.closing:
            raise ValueError('当前操作尚未结束，请稍候。')
    def save():
        try:
            available()
            loaded = _active_manager.loaded_request
            if loaded is None:
                raise ValueError('请先显示当前搭配。')
            draft = {**_active_request, 'choices': {s: e.read_choice() for s, e in _active_editors.items()},
                     'action_index': action_box().current()}
            if panel.state_of(draft) != panel.state_of(loaded):
                raise ValueError('尚有未显示的修改，请先点击“显示当前搭配”。')
            identities.CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
            path = filedialog.asksaveasfilename(parent=frame.winfo_toplevel(), title='保存整套角色配置',
                initialdir=str(identities.CONFIG_ROOT), defaultextension='.json', filetypes=[('角色配置', '*.json')])
            if path:
                _active_manager.pending_save = (Path(path), data)
                _active_manager.submit(dict(loaded, action='status', save=False))
                for editor in _active_editors.values(): editor.enable(False)
                action_box().configure(state='disabled')
                _config_status.set('正在核对当前场景并保存配置…')
        except Exception as exc:
            _config_status.set(str(exc))
    def load():
        try:
            available()
            path = filedialog.askopenfilename(parent=frame.winfo_toplevel(), title='恢复整套角色配置',
                initialdir=str(identities.CONFIG_ROOT), filetypes=[('角色配置', '*.json')])
            if path:
                request = configurations.load_configuration(path, load_catalog(), validate_request)
                update_editor_selection(request)
                _active_manager.submit(request)
                for editor in _active_editors.values(): editor.enable(False)
                action_box().configure(state='disabled')
                _config_status.set('正在恢复配置，包括所保存的动作播放开关…')
        except Exception as exc:
            _config_status.set(str(exc))
    ttk.Button(row, text='保存整套配置', command=save).pack(side='left', padx=(0, 6))
    ttk.Button(row, text='恢复整套配置', command=load).pack(side='left')
    ttk.Label(row, textvariable=_config_status, wraplength=660).pack(side='left', padx=10)


class IdentityCommandQueue(_queue):
    def __init__(self, *args, **kwargs):
        global _active_manager
        super().__init__(*args, **kwargs)
        self.pending_save = None
        self.pending_observation = None
        _active_manager = self

    def submit(self, request):
        if (request.get('action') not in {'show', 'restore'} and self.loaded_request
                and any(request.get(key) != self.loaded_request.get(key) for key in ('character_ids', 'appearance'))):
            raise ValueError('角色或颜色已改变，请先点击“显示当前搭配”。')
        super().submit(request)

    def poll(self):
        item = super().poll()
        if item and self.pending_observation:
            sex, outcome, note, data = self.pending_observation
            self.pending_observation = None
            if item[2] is None and item[0]['action'] == 'status' and not self.closing:
                panel.record_observation(sex=sex, outcome=outcome, note=note, selected=item[0], reply=item[1],
                                         data=data, human_button=True)
        if item and self.pending_save:
            path, data = self.pending_save
            self.pending_save = None
            try:
                if item[2] is not None:
                    raise item[2]
                configurations.save_configuration(path, item[1], data, validate_request)
                if _config_status is not None: _config_status.set('已保存：' + path.name)
            except Exception as exc:
                if _config_status is not None: _config_status.set('配置未保存：' + str(exc))
        elif item and item[2] is None and _config_status is not None:
            _config_status.set('当前选择已显示，可保存整套配置。')
        return item


def build_parser():
    parser = _parser()
    parser.description = __doc__
    parser.add_argument('--stage', action='store_true', help='建立独立双人插槽场景后退出，不打开面板')
    for sex in identities.SEXES:
        parser.add_argument('--' + sex + '-character', help='已导入的 CFD40 角色编号')
        parser.add_argument('--' + sex + '-hair-color', choices=identities.color_runtime.CAPABILITIES['hair'])
        parser.add_argument('--' + sex + '-face-id', help='已验证的表情编号，none 恢复身体动作')
    parser.add_argument('--save-config', type=Path, help='读取当前场景状态并保存整套配置')
    parser.add_argument('--load-config', type=Path, help='校验并恢复已保存整套配置后退出')
    return parser


def cli_request(args, data):
    # Original CLI validates before extension fields are applied. Defer only
    # that validation until the complete appearance and library pin are set.
    original_validate = panel.validate_request
    panel.validate_request = lambda request, data: copy.deepcopy(request)
    try:
        request = _cli(args, data)
    finally:
        panel.validate_request = original_validate
    if request['action'] != 'restore':
        for sex in identities.SEXES:
            identifier = getattr(args, sex + '_character', None)
            if identifier:
                request = identities.switch_identity(request, sex, identifier, data['identities'])
            for kind in ('hair',):
                value = getattr(args, sex + '_' + kind + '_color', None)
                if value is not None:
                    request['appearance'][sex][kind + '_color'] = value
            face = getattr(args, sex + '_face_id', None)
            if face is not None:
                request['appearance'][sex]['face_id'] = face
        pin_face_registry(request, data)
        request = validate_request(request, data)
    return request


def stage(node_id=None):
    request = initial_request(load_catalog())
    command = (f'import sys,runpy\nsys.path.insert(0,{str(identities.SCRIPTS)!r})\n'
               f'runpy.run_path({str(panel.WORKER)!r},run_name="__main__",'
               f'init_globals={{"DM_CFD_BATCH40_MODULAR_STAGE":True,"DM_SLOT_REVIEW_REQUEST":{request!r}}})')
    with panel.command_lock():
        target.remote(command, identities.ROOT / 'controller', 'stage', node_id=node_id, timeout=1200)
    result = identities.read(identities.ROOT / 'stage_result.json')
    if result.get('success') is not True or result.get('level') != identities.LEVEL:
        raise RuntimeError('独立插槽场景尚未准备完成。')
    return result


panel.load_catalog, panel.initial_request = load_catalog, initial_request
panel.validate_request, panel.verify_result = validate_request, verify_result
panel.SexEditor, panel.CommandQueue = IdentitySexEditor, IdentityCommandQueue
panel.build_parser, panel.cli_request = build_parser, cli_request
panel.record_observation = record_observation


def main():
    args = build_parser().parse_args()
    if args.save_config and args.load_config:
        raise ValueError('一次只进行保存或恢复配置。')
    if args.load_config:
        request = configurations.load_configuration(args.load_config, load_catalog(), validate_request)
        print(json.dumps(panel.execute(request, args.node_id), ensure_ascii=False))
    elif args.save_config:
        data = load_catalog()
        request = validate_request(dict(identities.read(identities.ROOT / 'current_case.json')['request'], action='status', save=False), data)
        result = panel.execute(request, args.node_id)
        print(json.dumps(configurations.save_configuration(args.save_config, result, data, validate_request), ensure_ascii=False))
    elif args.stage:
        print(json.dumps(stage(args.node_id), ensure_ascii=False))
    else:
        panel.entrypoint()


if __name__ == '__main__':
    main()
