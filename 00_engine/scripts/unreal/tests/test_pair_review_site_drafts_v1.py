import copy
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pair_review_site_drafts_v1 as policy
from test_scene_site_review_panel_v1 import panel, tk_root


def install(panel):
    module, app, *_ = panel
    policy.install(module)
    app.__class__ = module.Panel
    return panel


def test_movement_refresh_and_check_version_keep_unsaved_exclusions(panel):
    module, app, root, state, calls, drain = install(panel)
    app.decide('excluded')
    wanted = copy.deepcopy(app.decisions)
    moved = {**state, 'position':{'x':100,'y':200,'z':30}, 'yaw':90,
             'review_stamp':'after-move', 'allowed_combinations':[]}
    app.apply({'state':moved},'update_site')
    app.apply({'state':{**moved,'review_stamp':'after-checker-update'}},'status')
    assert app.decisions == wanted and app.decisions_dirty
    draft = json.loads(app.drafts_path.read_text(encoding='utf-8'))
    assert draft[policy.site_key(moved)]['allowed_combinations'] == wanted


def test_changed_point_does_not_promote_old_pass_or_issue_review(panel):
    module, app, root, state, calls, drain = install(panel)
    app.decide('excluded')
    app.decisions.append({**app.decisions[0],'camera_id':'side','decision':'allowed'})
    app.issue_reviews={'old':{'status':'acceptable','note':'old wall'}}
    app.apply({'state':{**state,'review_stamp':'moved'}},'status')
    assert [r['decision'] for r in app.decisions] == ['excluded']
    assert app.issue_reviews == {}


def test_other_site_is_isolated_and_return_restores_draft(panel):
    module, app, root, state, calls, drain = install(panel)
    app.decide('excluded'); wanted=copy.deepcopy(app.decisions)
    other={**state,'site_id':'site-b','review_stamp':'different'}
    app.apply({'state':other},'load_site')
    assert app.decisions == []
    app.apply({'state':{**state,'review_stamp':'new-a'}},'load_site')
    assert app.decisions == wanted


def test_explicit_removal_stays_empty_after_refresh_and_move(panel):
    module, app, root, state, calls, drain = install(panel)
    app.decide('excluded')
    app.decide(None)
    app.apply({'state':{**state,'review_stamp':'moved'}},'status')
    assert app.decisions == []
    assert app.drafts[policy.site_key(state)]['allowed_combinations'] == []


def test_check_and_save_requests_bind_identity(panel):
    module, app, root, state, calls, drain = install(panel)
    app.decide('excluded')
    app.send('check_all'); drain()
    assert calls[-1]['decision_site_id']==state['site_id']
    assert calls[-1]['decision_map']==state['map']
    assert len(calls[-1]['excluded_combinations'])==1
    app.save_site(); drain()
    assert calls[-1]['decision_site_id']==state['site_id']
    assert not app.decisions_dirty
    assert policy.site_key(state) not in app.drafts


def test_legacy_draft_explicit_empty_is_not_merged_with_older_exclusions():
    state={'site_id':'a','map':'/A','review_stamp':'new'}
    record={'allowed_combinations':[],'issue_reviews':{'old':{}},'review_stamp':'old'}
    assert policy.current_draft(record,state)['allowed_combinations']==[]
    assert policy.current_draft(record,state)['issue_reviews']=={}
    assert policy.site_key(state)!=policy.site_key({**state,'map':'/B'})
