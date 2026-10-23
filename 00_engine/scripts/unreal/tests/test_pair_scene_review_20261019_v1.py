"""Private two-person panel boundaries; no Unreal process or UI required."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import copy
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pair_scene_review_20261019_v1 as panel
import ue_pair_revision_runtime_20261019_v1 as revision


def test_catalog_limits_only_identity_menu_and_adds_new_revision(tmp_path, monkeypatch):
    delivery = tmp_path / 'delivery.json'
    delivery.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(panel, 'DELIVERY', delivery)
    data = {'identities': [{'id': 'CFD40_AF_001', 'sex': 'female'},
                           {'id': 'CFD40_AM_001', 'sex': 'male'},
                           {'id': 'CFD40_AF_002', 'sex': 'female'}],
            'wardrobe': [{'id': 'all_existing_outfits'}],
            'hair': [{'id': 'all_existing_hair'}],
            'faces': ['none', 'smile'], 'sources': {'formal': 'preserved'}}
    before = copy.deepcopy(data)
    result = panel.restricted_catalog(data)
    assert {r['id'] for r in result['identities']} == set(panel.IDS)
    assert result['sources']['character_revision'] == panel.pin(delivery)
    for field in ('wardrobe', 'hair', 'faces'):
        assert result[field] == before[field]
    assert data == before


def test_prepare_preserves_user_save_and_expires_inherited_report(tmp_path, monkeypatch):
    base, run = tmp_path / 'base', tmp_path / 'pair'
    delivery = tmp_path / 'delivery.json'
    panel.write(delivery, {'status': 'pair_import_completed_remaining38_not_started',
                           'cases': [{'character_id': identifier} for identifier in panel.IDS]})
    monkeypatch.setattr(panel, 'BASE_RUN', base)
    monkeypatch.setattr(panel, 'RUN', run)
    monkeypatch.setattr(panel, 'DELIVERY', delivery)
    for name in ('site_review_local_geometry_v1.json', 'site_review_catalog_v1.json'):
        panel.write(base / name, {'input': 'existing'})
    old = {'site': {'site_id': 'inherited', 'map': '/Game/Scenes/Main',
                    'position': {'x': 1, 'y': 2, 'z': 3}, 'yaw': 4,
                    'appearance_config_id': 'old_appearance', 'appearance_selection': {'old': True},
                    'decisions_stamp': 'old_clock', 'allowed_combinations': [{'decision': 'excluded'}]},
           'report': {'status': 'complete'}, 'human_acceptance': 'accepted'}
    source = base / 'sites/inherited.json'
    panel.write(source, old)
    source_bytes = source.read_bytes()
    panel.write(base / 'sites/user_saved.json', {'site': {'site_id': 'user_saved'}, 'report': {'old': True}})
    user_save = {'site': {'site_id': 'user_saved', 'position': {'x': 99}}, 'user': 'new_saved_value'}
    panel.write(run / 'sites/user_saved.json', user_save)
    panel.prepare()
    result = panel.read(run / 'sites/inherited.json')
    assert panel.read(run / 'sites/user_saved.json') == user_save
    assert result['site']['position'] == old['site']['position'] and result['site']['yaw'] == 4
    assert result['site']['allowed_combinations'] == old['site']['allowed_combinations']
    assert not {'appearance_config_id', 'appearance_selection', 'decisions_stamp'} & result['site'].keys()
    assert result['report'] is None and result['human_acceptance'] == 'pending_new_character_revision'
    assert result['site']['review_runtime'] == 'inherited_before_pair_revision'
    assert panel.read(run / 'inherited_sites/inherited.json') == old
    assert source.read_bytes() == source_bytes
    # A later reopen cannot replace the user's edited copy of an inherited point.
    result['site']['position']['x'] = 123
    panel.write(run / 'sites/inherited.json', result)
    panel.prepare()
    assert panel.read(run / 'sites/inherited.json')['site']['position']['x'] == 123


def fake_editor(monkeypatch, *, rendering=False):
    u = ModuleType('unreal')
    u.MoviePipelineQueueSubsystem = object()
    u.get_editor_subsystem = lambda _kind: SimpleNamespace(is_rendering=lambda: rendering)
    monkeypatch.setitem(sys.modules, 'unreal', u)
    return u


def test_restore_bypasses_stale_input_guard_without_rebuilding_state(monkeypatch):
    u = fake_editor(monkeypatch)
    events = []
    def forbidden(*args, **kwargs):
        raise AssertionError('Cleanup must not verify inputs or rebuild state')
    worker = SimpleNamespace(restore=lambda: events.append('released'), current_map=lambda: '/Game/Scenes/Main',
                             state=forbidden, dispatch=forbidden)
    setattr(u, panel.CACHE, {'worker': worker, 'configuration': {}})
    monkeypatch.setattr(panel, 'worker', forbidden)
    result = panel.dispatch({'action': 'restore', 'request_id': 'cleanup'})
    assert events == ['released'] and result['success'] and result['cleanup_only']
    assert result['state']['preview'] == {} and not result['state']['playback']['playing']


@pytest.mark.parametrize('action', ['preview', 'status', 'save_site', 'set_appearance'])
def test_fast_review_commands_do_not_rehash_revision_inputs(monkeypatch, action):
    import pair_review_fast_runtime_v1 as fast
    u = fake_editor(monkeypatch)
    worker = SimpleNamespace(dispatch=lambda p: {'success': True, 'action': p['action']})
    setattr(u, panel.CACHE, {'worker': worker, 'configuration': {}})
    monkeypatch.setattr(fast, 'install', lambda value: value)
    # The camera installer is covered by dedicated integration tests; this
    # dispatch-only stub intentionally has no scene/checking methods.
    monkeypatch.setattr(panel, 'install_camera_checks', lambda value: value)
    import pair_review_site_intent_v1 as site_intent
    monkeypatch.setattr(site_intent, 'install', lambda value: value)
    import scene_review_selection_policy_v1 as selection_policy
    monkeypatch.setattr(selection_policy, 'install_worker', lambda value: value)
    def forbidden(_configuration):
        raise AssertionError('Interactive review must not repeat input verification')
    monkeypatch.setattr(revision, 'unchanged', forbidden)
    assert panel.dispatch({'action': action})['success']


def test_review_startup_bypass_is_private_and_formal_validators_still_reject_changed_sources(tmp_path):
    import pair_review_fast_runtime_v1 as fast
    import production_motion_contract_v1 as formal_motion
    import scene_site_review_geometry_v1 as formal_geometry
    from motion_library_review_adapter_v1 import PrivateModules

    source=tmp_path/'changed.json'
    source.write_text('{}',encoding='utf-8')
    wrong={'path':str(source),'sha256':'0'*64}
    formal_functions=(formal_motion.verify_pin,formal_geometry.verify_sources)
    graph,other_review=PrivateModules(),PrivateModules()
    private_motion=graph.load('production_motion_contract_v1')
    private_geometry=graph.load('scene_site_review_geometry_v1')
    assert private_motion is not formal_motion and private_geometry is not formal_geometry
    fast.disable_startup_asset_audits(graph)
    assert private_motion.verify_pin(wrong) is None
    assert private_geometry.verify_sources([wrong]) is None
    # Reading a missing source still fails; bypassing an audit does not invent inputs.
    with pytest.raises(FileNotFoundError):
        private_geometry.read(tmp_path/'missing.json')
    assert formal_functions==(formal_motion.verify_pin,formal_geometry.verify_sources)
    for module,validator,args in (
            (formal_motion,'verify_pin',(wrong,)),
            (formal_geometry,'verify_sources',([wrong],)),
            (other_review.load('production_motion_contract_v1'),'verify_pin',(wrong,)),
            (other_review.load('scene_site_review_geometry_v1'),'verify_sources',([wrong],))):
        with pytest.raises(ValueError,match='[Cc]hanged'):
            getattr(module,validator)(*args)


def test_restore_does_not_release_preview_during_active_render(monkeypatch):
    u = fake_editor(monkeypatch, rendering=True)
    events = []
    setattr(u, panel.CACHE, {'worker': SimpleNamespace(restore=lambda: events.append('released'))})
    with pytest.raises(ValueError, match='正在渲染'):
        panel.dispatch({'action': 'restore'})
    assert not events


def test_private_panel_initial_state_sync_and_live_catalog_counts(monkeypatch):
    class Variable:
        def __init__(self, value=''):
            self.value = value
        def set(self, value):
            self.value = value
        def get(self):
            return self.value

    class Widget:
        def __init__(self, text='', children=()):
            self.text, self.children = text, children
        def winfo_children(self):
            return self.children
        def cget(self, _key):
            return self.text
        def configure(self, **kwargs):
            self.text = kwargs['text']
        def title(self, _text):
            pass

    class BasePanel:
        def __init__(self, _root):
            self.state, self.catalog = {}, {}
            self.motion, self.camera = Variable('first_motion'), Variable('first_camera')
            self.aspect, self.seconds, self.saved_site = Variable('横屏'), Variable('0'), Variable('old_site')
        @staticmethod
        def row_label(row):
            return row['label'] + ' [' + row['id'] + ']'
        def apply(self, reply, _action):
            self.state = reply.get('state', self.state)
            self.catalog = reply.get('catalog', self.catalog)

    app = SimpleNamespace(Panel=BasePanel)
    import pair_review_transport_fast_v1 as fast_transport
    monkeypatch.setattr(fast_transport, 'install', lambda _app: None)
    import pair_review_site_drafts_v1 as site_drafts
    monkeypatch.setattr(site_drafts, 'install', lambda _app: None)
    monkeypatch.setattr(panel, 'prepare', lambda: None)
    monkeypatch.setattr(panel, 'graph_and_data', lambda: (SimpleNamespace(load=lambda _name: app), {}))
    label = Widget('沿用现用 30 动作、21 镜头与横竖画幅；不修改镜头参数。')
    root = Widget(children=[label])
    ui = panel.controller().Panel(root)
    assert label.text == '正在读取当前动作与镜头目录…'
    catalog = {'motions': [{'id': f'm{i}', 'label': f'motion{i}'} for i in range(26)],
               'cameras': [{'id': f'c{i}', 'label': f'camera{i}'} for i in range(21)],
               'sites': [{'id': 'amusement1', 'label': '游乐园1', 'map': '/Game/Main'}]}
    state = {'current_map': '/Game/Main', 'site_id': 'amusement1',
             'preview': {'action_id': 'm5', 'camera_id': 'c7', 'aspect': 'portrait', 'time_seconds': 2.5}}
    ui.apply({'success': True, 'catalog': catalog}, 'catalog')
    assert not ui._pair_initial_synced  # A catalog alone cannot overwrite live controls.
    ui.apply({'success': True, 'catalog': catalog, 'state': state}, 'status')
    assert label.text == '当前目录 26 动作、21 镜头，支持横竖画幅。'
    assert (ui.motion.get(), ui.camera.get(), ui.aspect.get(), ui.seconds.get(), ui.saved_site.get()) == (
        'motion5 [m5]', 'camera7 [c7]', '竖屏', '2.5', '游乐园1 [amusement1]')
    ui.motion.set('unsubmitted_motion')
    ui.camera.set('unsubmitted_camera')
    ui.aspect.set('横屏')
    ui.seconds.set('7')
    ui.saved_site.set('unsubmitted_site')
    ui.apply({'success': True, 'catalog': catalog, 'state': state}, 'status')
    assert (ui.motion.get(), ui.camera.get(), ui.aspect.get(), ui.seconds.get(), ui.saved_site.get()) == (
        'unsubmitted_motion', 'unsubmitted_camera', '横屏', '7', 'unsubmitted_site')
