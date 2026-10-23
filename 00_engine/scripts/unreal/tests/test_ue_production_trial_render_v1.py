"""Formal trial lookups require relocated provenance, without any UE calls."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
import ue_production_trial_render_v1 as trials


def test_old_prepared_camera_must_be_rebuilt_for_level_exposure():
    with pytest.raises(ValueError,match='曝光'):
        trials.require_level_exposure({})
    trials.require_level_exposure({'exposure_policy':trials.EXPOSURE_POLICY})
import scene_site_appearance_v1 as appearance


def test_resolve_uses_explicit_formal_package_and_object_overlay(monkeypatch):
    domain=SimpleNamespace(formal_path_overlay={'/Game/Old/Map':'/Game/New/Map',
        '/Game/Old/Mesh.Mesh':'/Game/New/Mesh.Mesh'})
    monkeypatch.setattr(appearance,'formal_runtime',lambda:(object(),domain))
    assert trials.resolve('/Game/Old/Map')=='/Game/New/Map'
    assert trials.resolve('/Game/Old/Mesh.Mesh')=='/Game/New/Mesh.Mesh'
    assert trials.resolve('/Game/Scenes/Main')=='/Game/Scenes/Main'


def test_formal_motion_resolves_selected_sex_and_refuses_missing_publication(monkeypatch):
    monkeypatch.setattr(appearance,'formal_runtime',lambda:(object(),object()))
    source={'asset':'/Game/Body/Production/female/A.A','path':'/fixture','sha256':'fixture'}
    variant={'production10':source,'original_bake_receipt':{'path':'/proof','sha256':'proof'}}
    runtime=SimpleNamespace(load_formal_motion_runtime=lambda:{'source':{'path':'/manifest','sha256':'manifest'},
        'variants':{('MOTION_CAND_019','female'):variant}})
    monkeypatch.setattr(trials,'module',lambda name:runtime)
    actual,proof=trials.motion_record('MOTION_CAND_019','female')
    assert actual==source and 'formal_motion_catalog' in proof
    runtime.load_formal_motion_runtime=lambda:None
    with pytest.raises(ValueError,match='published formal motion'):
        trials.motion_record('MOTION_CAND_019','female')


def test_failed_prepare_releases_cached_actor_references(monkeypatch):
    events=[]
    monkeypatch.setitem(sys.modules,'ue_scene_site_appearance_v1',SimpleNamespace(
        invalidate_cache=lambda u:events.append('cleared')))
    def failed(u,index):raise RuntimeError('partial sequence failure')
    monkeypatch.setattr(trials,'_prepare',failed)
    with pytest.raises(RuntimeError,match='partial sequence'):
        trials.prepare(object(),0)
    assert events==['cleared']


def test_trial_samples_exact_animation_and_sequence_clock(monkeypatch):
    calls=[]
    trajectory={'version':'ground_height_follow_v1','frames':[]}
    def sample(u,actor,animation,**kwargs):
        calls.append((u,actor,animation,kwargs));return trajectory
    monkeypatch.setattr(trials,'module',lambda name:SimpleNamespace(sample_trajectory=sample)
        if name=='ue_ground_height_follow_v1' else None)
    u,actor,camera,animation=object(),object(),object(),object()
    assert trials.sample_ground_height(u,actor,camera,animation,{'frame_count':300,'window_start_seconds':.75}) is trajectory
    assert calls==[(u,actor,animation,{'frame_count':300,'fps':30.,'source_start_seconds':.75,'ignore_actors':[actor,camera]})]


def test_new_trial_cannot_reuse_old_prepared_sequence():
    with pytest.raises(ValueError,match='new trial ID'):
        trials.require_ground_height_follow({'success':True},{'frame_count':300})


def test_ground_receipt_requires_matching_policy_and_complete_curve():
    rows=[{'frame':i,'t':i/30,'actor_z_cm':100.+i} for i in range(3)]
    trajectory={'version':trials.GROUND_HEIGHT_VERSION,'camera_policy':'unchanged','frames':rows}
    record={'ground_height_follow':trajectory,'sequence_ground_height_follow':{
        'version':trials.GROUND_HEIGHT_VERSION,'camera_policy':'unchanged','actor_z_key_count':3,'baseline_actor_z_cm':100.}}
    assert trials.require_ground_height_follow(record,{'frame_count':2}) is trajectory
    record['sequence_ground_height_follow']['actor_z_key_count']=2
    with pytest.raises(ValueError):trials.require_ground_height_follow(record,{'frame_count':2})


def test_render_refuses_legacy_preparation_before_any_ue_dispatch(tmp_path,monkeypatch):
    from production_motion_contract_v1 import pin
    monkeypatch.setattr(trials,'RUN',tmp_path)
    monkeypatch.setattr(trials,'renderer',lambda:pytest.fail('Legacy sequence must not dispatch a render'))
    trials.write(tmp_path/'four_trials_plan.json',{'shots':[{'shot_id':'legacy','frame_count':300}]})
    trials.write(tmp_path/'prepared/legacy.json',{'trial_plan':pin(tmp_path/'four_trials_plan.json')})
    with pytest.raises(ValueError,match='ground height follow'):trials.render(object(),0,'unused')
