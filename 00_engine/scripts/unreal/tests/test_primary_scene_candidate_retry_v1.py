"""Direct-retry selection and remote-envelope failure handling; no UE execution."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import pytest

S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S))


def retry_module(monkeypatch):
    monkeypatch.setitem(sys.modules,'ue_all_primary_scene_survey_v1',types.SimpleNamespace())
    spec=importlib.util.spec_from_file_location('candidate_retry_test',S/'ue_primary_scene_candidate_retry_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_selects_exact_persisted_candidate_without_mutating_evidence(monkeypatch):
    retry=retry_module(monkeypatch)
    old={'position':[-5114.,7686.,100.],'yaw':0.,'score':0.,'findings':[]}
    report={'screen_candidates':[old]}
    selected=retry.select_candidate(report,[-5114,7686,100],0)
    assert selected==old and selected is not old
    selected['findings'].append('new')
    assert old['findings']==[]


def test_retry_rejects_unmeasured_position_and_nonzero_screen_findings(monkeypatch):
    retry=retry_module(monkeypatch)
    report={'screen_candidates':[{'position':[1.,2.,3.],'yaw':0.,'score':-4.}]}
    with pytest.raises(ValueError):retry.select_candidate(report,[9,9,9],0)
    with pytest.raises(ValueError):retry.select_candidate(report,[1,2,3],0)


def test_remote_rejects_embedded_failure_even_when_process_exit_is_zero(monkeypatch,tmp_path):
    import run_primary_scene_surveys_v1 as runner
    monkeypatch.setattr(runner,'RUN',tmp_path)
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:types.SimpleNamespace(
        returncode=0,stdout=json.dumps({'command_result':{'success':False}}),stderr=''))
    with pytest.raises(RuntimeError,match='envelope reported failure'):runner.remote('pass','fake_failure')


def test_remote_returns_verified_success_envelope(monkeypatch,tmp_path):
    import run_primary_scene_surveys_v1 as runner
    monkeypatch.setattr(runner,'RUN',tmp_path)
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:types.SimpleNamespace(
        returncode=0,stdout=json.dumps({'command_result':{'success':True}}),stderr=''))
    assert runner.remote('pass','fake_success')['command_result']['success'] is True
