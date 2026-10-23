"""Frozen body-window and independent cross-sex-stage boundaries (offline)."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ue_camera_alignment_review_v1 as w


@pytest.fixture
def source(monkeypatch):
    row={'shot_id':'old_m04','motion_id':'ACT_M04_LIVING_ROOM_SWING','sex':'male','group':'motions',
         'source_animation':'/Game/Original.Original','source_start_seconds':0.,'source_end_seconds':11.8,
         'source_body_play_rate':1.,'window_start_seconds':0.,'duration_seconds':11.8,'frame_count':354,'fps':30}
    monkeypatch.setattr(w,'_SOURCE_SHOTS',{row['motion_id']:row})
    return row


@pytest.mark.parametrize('field,value',[
    ('source_start_seconds',1),('source_end_seconds',12),('source_body_play_rate',.8),
    ('window_start_seconds',1),('duration_seconds',12),('frame_count',355),('fps',24)])
def test_changed_original_window_rejected(source,field,value):
    shot=copy.deepcopy(source);shot.update(group='cameras');shot[field]=value
    with pytest.raises(ValueError,match='accepted body window'):
        w.validate_body_contract(shot)


def test_cross_target_preserves_m04_cut_but_changes_sex_and_animation(source):
    shot=copy.deepcopy(source);shot.update(group='legacy_cross_sex',sex='female',source_animation='/Game/Cross.Cross')
    assert w.validate_body_contract(shot)==source
    shot['duration_seconds']=12
    with pytest.raises(ValueError):w.validate_body_contract(shot)


def test_wrong_group_sex_combination_rejected(source):
    for group,sex in [('cameras','female'),('legacy_cross_sex','male')]:
        shot=dict(source,group=group,sex=sex)
        with pytest.raises(ValueError,match='action sex'):w.validate_body_contract(shot)


def test_normal_source_animation_is_not_replaceable(source):
    shot=dict(source,group='cameras',source_animation='/Game/Wrong.Wrong')
    with pytest.raises(ValueError,match='animation source'):w.validate_body_contract(shot)


def test_cross_stage_does_not_replace_main_plan(tmp_path,monkeypatch):
    monkeypatch.setattr(w,'RUN',tmp_path)
    main=tmp_path/'camera_trial_plan_v1.json';main.write_bytes(b'{"main":true}')
    cross=tmp_path/'legacy_cross_sex_camera_plan_v1.json';cross.write_bytes(b'{"cross":true}')
    monkeypatch.setattr(w,'adapter',lambda:SimpleNamespace(RUN=tmp_path,A=w.ASSETS))
    result=w.cross_adapter()
    assert result.RUN==tmp_path/'legacy_stage'
    assert main.read_bytes()==b'{"main":true}'
    assert (result.RUN/'camera_trial_plan_v1.json').read_bytes()==cross.read_bytes()
    cross.write_bytes(b'{"cross":false}')
    with pytest.raises(ValueError,match='stage plan changed'):w.cross_adapter()


def test_cross_validation_identity_mismatch_rejected_before_composition(source,monkeypatch):
    shot=dict(source,group='legacy_cross_sex',sex='female',source_animation='/Game/Cross.Cross')
    row={'success':True,'action_id':'WRONG','sex':'female','source_sex':'male','target':{'asset':shot['source_animation']}}
    monkeypatch.setattr(w,'read',lambda p:row)
    with pytest.raises(ValueError,match='matching validation'):w.existing_composite(None,shot)
