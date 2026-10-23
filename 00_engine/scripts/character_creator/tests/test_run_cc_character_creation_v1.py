"""CLI gating and serial batch stop behavior; never opens CC."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cc_character_creation_v1 as cli


def options(**overrides):
    args = dict(request=None, batch=None, photo="face.jpg", source_project=None,
                sex="female", character_id="alice", seed=1)
    args.update(overrides)
    return argparse.Namespace(**args)


def test_inline_photo_request():
    assert cli.parse_requests(options()) == [{"photo": "face.jpg", "sex": "female", "character_id": "alice", "seed": 1}]


def test_inline_project_request():
    result = cli.parse_requests(options(photo=None, source_project="raw.ccProject"))
    assert result[0]["source_project"] == "raw.ccProject"


@pytest.mark.parametrize("change", [{"sex": None}, {"character_id": None}, {"seed": None},
                                    {"sex": "both"}, {"character_id": "../bad"}, {"seed": True}])
def test_invalid_inline_requests(change):
    with pytest.raises(cli.ControllerError):
        cli.parse_requests(options(**change))


def test_batch_duplicate_ids_rejected(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text('[{"photo":"a.jpg","sex":"male","character_id":"a","seed":1},'
                    '{"photo":"b.jpg","sex":"female","character_id":"a","seed":2}]')
    with pytest.raises(cli.ControllerError, match="repeats"):
        cli.parse_requests(options(batch=str(path), photo=None))


@pytest.mark.parametrize("payload", [[], {}, [{"character_id":"a","sex":"male","seed":1}],
                                    [{"character_id":"a","sex":"male","seed":1,"photo":"a","source_project":"b"}]])
def test_bad_batch_shapes_and_ambiguous_input(tmp_path, payload):
    import json
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(cli.ControllerError):
        cli.parse_requests(options(batch=str(path), photo=None))


class Pipeline:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.prepared, self.advanced = [], []
    def prepare_request(self, request):
        self.prepared.append(request)
        return dict(request, status="prepared", steps={})
    def advance(self, state, driver, wait_seconds):
        self.advanced.append((state["character_id"], wait_seconds))
        state["status"] = next(self.statuses)
        return state


class Driver:
    def verify_state_inputs(self, state):
        pass


def requests():
    return [{"character_id":"a"}, {"character_id":"b"}]


def test_default_prepare_only_never_advances():
    pipeline = Pipeline([])
    assert cli.run_requests(requests(), pipeline=pipeline, driver=Driver(), emit=lambda v: None) == 0
    assert len(pipeline.prepared) == 2
    assert pipeline.advanced == []


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_serial_batch_stops_at_pending_or_failed(status):
    pipeline = Pipeline([status, "completed"])
    assert cli.run_requests(requests(), execute=True, wait_seconds=1800, pipeline=pipeline,
                            driver=Driver(), emit=lambda v: None) == 2
    assert len(pipeline.prepared) == 1
    assert pipeline.advanced == [("a", 1800)]


def test_completed_batch_advances_serially():
    pipeline = Pipeline(["completed", "completed"])
    assert cli.run_requests(requests(), execute=True, pipeline=pipeline,
                            driver=Driver(), emit=lambda v: None) == 0
    assert pipeline.advanced == [("a", 600), ("b", 600)]


def test_main_rejects_simultaneous_photo_and_project():
    with pytest.raises(SystemExit):
        cli.main(["--photo", "a.jpg", "--source-project", "a.ccProject"])


def test_main_default_and_execute_modes(monkeypatch):
    from contextlib import nullcontext
    modes = []
    monkeypatch.setattr(cli, "controller_lock", lambda: nullcontext())
    monkeypatch.setattr(cli, "run_requests", lambda rs, **kw: modes.append(kw) or 0)
    argv = ["--photo", "a.jpg", "--sex", "male", "--character-id", "a", "--seed", "0"]
    assert cli.main(argv) == 0
    assert modes[-1]["execute"] is False
    assert cli.main(argv + ["--execute"]) == 0
    assert modes[-1]["execute"] is True


def test_cli_explicit_native_mode_is_part_of_request():
    parsed=cli.parse_requests(options(appearance_mode='headshot_native'))
    assert parsed[0]['appearance_mode']=='headshot_native'
    assert 'appearance_mode' not in cli.parse_requests(options())[0]


def test_native_wrapper_forces_mode_and_keeps_execution_explicit(monkeypatch):
    import run_cc_headshot_geometry_only_v1 as native
    calls=[]
    monkeypatch.setattr(native,'creation_main',lambda args, **kw: calls.append((args,kw)) or 0)
    native.main(['--photo','photo.jpg','--sex','male','--character-id','native_male','--seed','42'])
    assert calls[-1][1]['fixed_appearance_mode']=='headshot_native'
    assert '--execute' not in calls[-1][0]
    native.main(['--request','request.json','--execute'])
    assert '--execute' in calls[-1][0]
    with pytest.raises(cli.ControllerError,match='fixes appearance_mode'):
        native.main(['--appearance-mode','assembled'])


def test_native_cli_cannot_override_declared_assembled_request(tmp_path):
    path=tmp_path/'request.json'
    path.write_text('{"photo":"face.jpg","sex":"female","character_id":"a","seed":42,"appearance_mode":"assembled"}')
    with pytest.raises(cli.ControllerError,match='conflicts'):
        cli.parse_requests(options(request=str(path),appearance_mode='headshot_native'))


def test_native_help_explains_preservation_without_exposing_mode_switch(capsys):
    import run_cc_headshot_geometry_only_v1 as native
    with pytest.raises(SystemExit) as error:
        native.main(['--help'])
    assert error.value.code==0
    help_text=capsys.readouterr().out
    assert 'native appearance' in help_text
    assert '--appearance-mode' not in help_text
    assert 'Default assembled' not in help_text
