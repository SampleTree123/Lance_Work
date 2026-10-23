"""Real Tk widgets with an offline executor; never touches the shared UE editor."""
import copy
import importlib.util
import json
from pathlib import Path
import time

import pytest


@pytest.fixture(scope="module")
def tk_root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def panel(monkeypatch, tmp_path, tk_root):
    scripts = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("offline_scene_site_panel", scripts / "scene_site_review_panel_v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "RUN", tmp_path)
    state = {"site_id": "site-a", "review_stamp": "stamp-a", "name": "Point A", "map": "/Test",
             "position": {"x": 0., "y": 0., "z": 50.}, "yaw": 0., "needs_recheck": False,
             "allowed_combinations": [], "issue_reviews": {}, "check": {"status": "idle"},
             "playback": {"playing": False, "time_seconds": 0., "duration_seconds": 5., "loop": False}}
    catalog = {"motions": [{"id": "walk"}, {"id": "jump"}],
               "cameras": [{"id": "front"}, {"id": "side"}], "sites": []}
    calls = []

    def executor(sent, _node):
        calls.append(copy.deepcopy(sent))
        action = sent["action"]
        if action == "save_site":
            assert sent["decisions_stamp"] == state["review_stamp"]
            state["allowed_combinations"] = copy.deepcopy(sent["allowed_combinations"])
            state["issue_reviews"] = copy.deepcopy(sent["issue_reviews"])
        elif action == "play":
            state["playback"].update(playing=True, time_seconds=sent["time_seconds"], loop=sent["loop"])
        elif action == "pause_playback":
            state["playback"].update(playing=False, time_seconds=2.5)
        elif action == "stop_playback":
            state["playback"].update(playing=False, time_seconds=0.)
        return {"state": copy.deepcopy(state), "catalog": copy.deepcopy(catalog)}

    root = tk_root
    app = module.Panel(root, executor=executor)

    def drain():
        deadline = time.monotonic() + 3
        while app.manager.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.005)
        assert not app.manager.busy

    drain()
    yield module, app, root, state, calls, drain
    app.manager.requests.put(None)
    if root.winfo_exists():
        root.after_cancel(app.after_id)
        for widget in root.winfo_children():
            widget.destroy()
        root.unbind_all("<MouseWheel>")


def widgets(parent):
    for child in parent.winfo_children():
        yield child
        yield from widgets(child)


def test_scene_selection_only_opens_on_click_and_keeps_review_draft(panel):
    module, app, root, state, calls, drain = panel
    scene_rows = [
        {'map_path': '/Game/Scenes/A/Map', 'package': 'A', 'label': '场景 A', 'category_label': '主场景'},
        {'map_path': '/Game/Scenes/B/Map', 'package': 'B', 'label': '场景 B', 'category_label': '主场景'},
        {'map_path': '/Game/Scenes/B/Overview', 'package': 'B', 'label': '场景 B 总览', 'category_label': '资产总览'}]
    app.catalog['scenes'] = scene_rows
    app.refresh_scene_choices()
    before = len(calls)
    app.scene_choice.set(app.scene_label(scene_rows[1]))
    root.update()
    assert len(calls) == before
    app.decisions = [{'action_id': 'walk', 'camera_id': 'front', 'aspect': 'landscape', 'decision': 'excluded'}]
    app.decisions_dirty = True
    app.open_scene()
    drain()
    assert calls[-1]['action'] == 'open_scene'
    assert calls[-1]['map_path'] == '/Game/Scenes/B/Map'
    assert app.drafts['stamp-a']['allowed_combinations'][0]['decision'] == 'excluded'
    app.catalog['scenes'] = scene_rows
    app.scene_category.set('全部地图')
    app.refresh_scene_choices()
    assert len(app.scene_box.cget('values')) == 3


def test_complete_appearance_is_independent_and_saved_before_point_link(panel, tmp_path):
    module, app, root, state, calls, drain = panel
    appearance = module.appearance_contract
    data = appearance.catalog()
    assert len(data['identities']) == 40
    assert len(data['hair_colors']) == 10
    assert {r['face_id'] for r in data['faces']} == {'idle', 'smile', 'displeased', 'sad'}
    value = appearance.default_selection(data)
    state['appearance_selection'] = value
    state['appearance_configs'] = []
    app.apply({'state': copy.deepcopy(state), 'catalog': {**app.catalog, 'appearance_catalog': data}}, 'status')
    assert app.appearance_value == value
    app.appearance_value['hair_color'] = 'blue'
    app.appearance_value['face_id'] = 'smile'
    app.appearance_changed()
    app.source_mode.set('完整动作预览')
    selected = app.selection()
    assert selected['appearance_selection']['hair_color'] == 'blue'
    assert selected['source_mode'] == 'full'
    with pytest.raises(ValueError, match='另存完整外观'):
        app.save_site()
    original_point = copy.deepcopy(state['position'])
    saved = appearance.save_configuration('蓝发微笑', app.current_appearance(), data, root=tmp_path / 'appearances')
    loaded = appearance.load_configuration(saved['id'], data, root=tmp_path / 'appearances')
    assert loaded['selection'] == app.appearance_value
    state.update(appearance_selection=loaded['selection'], appearance_config_id=loaded['id'],
                 appearance_configs=[{k: loaded[k] for k in ('id', 'name', 'created_at')}])
    app.apply({'state': copy.deepcopy(state)}, 'save_appearance')
    assert not app.appearance_dirty
    app.save_site()
    drain()
    assert calls[-1]['appearance_config_id'] == saved['id']
    assert state['position'] == original_point
    # Scene refresh and ordinary progress polls cannot discard an outer draft.
    app.appearance_value['hair_color'] = 'pink'
    app.appearance_changed()
    app.apply({'state': copy.deepcopy(state)}, 'playback_status')
    assert app.appearance_value['hair_color'] == 'pink'
    assert app.appearance_dirty
    assert app.source_mode.get() == '完整动作预览'


def test_appearance_rejects_cross_sex_hair_tampering_and_config_path_escape(panel, tmp_path):
    module, app, root, state, calls, drain = panel
    appearance = module.appearance_contract
    data = appearance.catalog()
    value = appearance.default_selection(data, 'male')
    male_hairs = {r['hair_id'] for r in data['hairs_by_sex']['male']}
    value['choice']['hair_id'] = next(r['hair_id'] for r in data['hairs_by_sex']['female'] if r['hair_id'] not in male_hairs)
    with pytest.raises(ValueError):
        appearance.validate_selection(value, data)
    with pytest.raises(ValueError):
        appearance.load_configuration('../site', data, root=tmp_path)
    valid = appearance.default_selection(data)
    saved = appearance.save_configuration('外观', valid, data, root=tmp_path)
    path = tmp_path / (saved['id'] + '.json')
    changed = json.loads(path.read_text(encoding='utf-8'))
    changed['selection']['hair_color'] = 'red'
    path.write_text(json.dumps(changed), encoding='utf-8')
    with pytest.raises(ValueError, match='内容校验'):
        appearance.load_configuration(saved['id'], data, root=tmp_path)


def test_current_scene_filters_saved_points_even_when_site_map_is_stale(panel):
    module, app, root, state, calls, drain = panel
    state['current_map'] = '/Game/Scenes/B/Map'
    sites = [{'id': 'a', 'name': 'A 点位', 'map': '/Game/Scenes/A/Map'},
             {'id': 'b', 'name': 'B 点位', 'map': '/Game/Scenes/B/Map'}]
    app.apply({'state': copy.deepcopy(state), 'catalog': {**app.catalog, 'sites': sites}}, 'status')
    assert app.visible_sites == [sites[1]]
    assert app.map_label.get().endswith('/Game/Scenes/B/Map')
    assert len(app.site_box.cget('values')) == 1
    app.load_site()
    drain()
    assert calls[-1]['site_id'] == 'b'
    with pytest.raises(ValueError):
        module.request('open_scene', map_path='/Game/Scenes/../Other')


def test_overview_uses_new_dropdown_selection_without_preview(panel):
    module, app, root, state, calls, drain = panel
    app.motion.set(app.row_label(app.catalog['motions'][1]))
    app.camera.set(app.row_label(app.catalog['cameras'][1]))
    app.aspect.set('竖屏')
    app.seconds.set('3')
    next(w for w in widgets(root) if w.winfo_class() == 'TButton'
         and w.cget('text') == '俯看人物与相机轨迹').invoke()
    drain()
    assert calls[-1]['action'] == 'overview'
    assert {k: calls[-1][k] for k in ('action_id', 'camera_id', 'aspect', 'time_seconds')} == {
        'action_id': 'jump', 'camera_id': 'side', 'aspect': 'portrait', 'time_seconds': 3.}


def test_bulk_list_is_explicit_undoable_and_checks_only_remaining(panel):
    module, app, root, state, calls, drain = panel
    app.bulk_aspect.set("横竖画幅")
    app.review_bulk()
    dialog = next(w for w in root.winfo_children() if w.winfo_class() == "Toplevel")
    tree = next(w for w in widgets(dialog) if w.winfo_class() == "Treeview")
    assert len(tree.get_children()) == 4
    assert app.decisions == []  # Viewing the list is not a decision.
    next(w for w in widgets(dialog) if w.winfo_class() == "TButton" and "排除清单" in w.cget("text")).invoke()
    assert len(app.decisions) == 4
    assert "剩余 4 / 8" in app.remaining_text.get()
    app.send("check_all", **app.selection())
    drain()
    assert len(calls[-1]["excluded_combinations"]) == 4
    assert all(row["action_id"] == "walk" for row in calls[-1]["excluded_combinations"])
    app.undo_decision()
    assert app.decisions == []
    app.bulk_scope.set("当前镜头的全部动作")
    app.bulk_aspect.set("当前画幅")
    assert module.scoped_combinations(app.catalog, app.selection(), "camera") == [
        {"action_id": "walk", "camera_id": "front", "aspect": "landscape"},
        {"action_id": "jump", "camera_id": "front", "aspect": "landscape"}]


def test_selectively_restore_exclusion_and_preserve_other_decisions(panel):
    module, app, root, state, calls, drain = panel
    app.decisions = [{"action_id": "walk", "camera_id": "front", "aspect": "landscape", "decision": "excluded"},
                     {"action_id": "jump", "camera_id": "side", "aspect": "portrait", "decision": "excluded"}]
    app.review_excluded()
    dialog = next(w for w in root.winfo_children() if w.winfo_class() == "Toplevel")
    tree = next(w for w in widgets(dialog) if w.winfo_class() == "Treeview")
    tree.selection_set("0")
    next(w for w in widgets(dialog) if w.winfo_class() == "TButton" and w.cget("text") == "恢复选中项").invoke()
    assert [r["action_id"] for r in app.decisions] == ["jump"]
    app.undo_decision()
    assert len(app.decisions) == 2


def test_issue_marks_filter_notes_persist_and_status_keeps_unsaved_edits(panel):
    module, app, root, state, calls, drain = panel
    first = {"kind": "camera_blocked", "action_id": "walk", "camera_id": "front",
             "aspect": "landscape", "time_seconds": 1, "message": "Wall"}
    second = {**first, "message": "Branch", "time_seconds": 2.}
    app.apply({"report": {"issues": [first, second]}}, "poll_check")
    app.table.selection_set("0")
    app.select_issue()
    app.issue_note.set("Acceptable background branch")
    app.mark_issue("acceptable")
    app.issue_filter.set("可接受")
    app.render_issues()
    assert app.table.get_children() == ("0",)
    app.position["x"].set("123")
    app.send("status")
    drain()
    assert app.position["x"].get() == "123"
    key = module.issue_key(first)
    assert module.issue_key({**first, "time_seconds": 1.}) == key
    assert app.issue_reviews[key] == {"status": "acceptable", "note": "Acceptable background branch"}
    assert app.decisions_dirty
    draft = json.loads(app.drafts_path.read_text(encoding="utf-8"))
    assert draft["stamp-a"]["issue_reviews"][key]["status"] == "acceptable"
    app.save_site()
    drain()
    assert calls[-1]["issue_reviews"][key]["note"] == "Acceptable background branch"
    assert not app.decisions_dirty
    assert "stamp-a" not in app.drafts


def test_stamp_change_archives_unsaved_reviews_and_restores_matching_draft(panel):
    module, app, root, state, calls, drain = panel
    app.decide("excluded")
    old = copy.deepcopy(state)
    changed = {**state, "review_stamp": "stamp-b", "site_id": "site-b"}
    app.apply({"state": changed}, "status")
    assert app.decisions == []
    assert "stamp-a" in app.drafts
    app.apply({"state": old}, "status")
    assert app.decisions[0]["decision"] == "excluded"
    assert app.decisions_dirty


def test_playback_pause_resume_stop_and_request_contract(panel):
    module, app, root, state, calls, drain = panel
    app.loop.set(True)
    app.seconds.set("1.25")
    app.play()
    drain()
    assert calls[-1]["action"] == "play"
    assert calls[-1]["loop"] is True
    assert calls[-1]["time_seconds"] == 1.25
    app.send("pause_playback")
    drain()
    assert app.seconds.get() == "2.500"
    assert app.playback_progress["value"] == 2.5
    app.play()
    drain()
    assert calls[-1]["time_seconds"] == 2.5
    app.send("stop_playback")
    drain()
    assert app.seconds.get() == "0.000"
    assert app.playback_progress["value"] == 0.


def test_close_waits_for_inflight_play_then_pauses_before_retaining_scene(panel, monkeypatch):
    module, app, root, state, calls, drain = panel
    closed = []
    monkeypatch.setattr(app, "force_close", lambda: closed.append(True))
    app.play()
    app.keep_scene()
    drain()
    assert calls[-1]["action"] == "pause_playback"
    assert state["playback"]["playing"] is False
    assert closed == [True]


def test_remaining_scope_does_not_claim_full_matrix_is_valid(panel):
    module, app, root, state, calls, drain = panel
    exclusion = {"action_id": "walk", "camera_id": "front", "aspect": "portrait"}
    state.update(full_matrix_fresh=False, current_result_fresh=True,
                 allowed_combinations=[{**exclusion, "decision": "excluded"}],
                 check={"status": "complete", "scope": {"kind": "remaining", "combinations": 7,
                         "excluded_combinations": [{"action_id": "walk", "camera_id": "front", "aspect": "portrait"}]}})
    app.apply({"state": state}, "status")
    assert "剩余组合检查有效" in app.dirty.get()
    assert "排除 1 项" in app.scope_label.get()
    assert "全量检查有效" not in app.dirty.get()
    app.decisions = []
    app.edits_changed()
    assert "需要重新检查剩余组合" in app.dirty.get()
    app.decisions = [{**exclusion, "decision": "excluded"}]
    app.edits_changed()
    assert "剩余组合检查有效" in app.dirty.get()
    app.state["full_matrix_fresh"] = True
    app.decisions = []
    app.edits_changed()
    assert "全量检查有效" in app.dirty.get()
