import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('cfd_target_test', SCRIPTS / 'cfd_native_pair_ue_target_v1.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_selects_exact_user_project_node_and_rejects_wrong_identity():
    target = {'node_id': 'visible', 'user': 'Macheniek', 'project': 'datatry_02'}
    human = {'node_id': 'visible', 'user': 'Macheniek', 'project_name': 'datatry_02'}
    background = {'node_id': 'offline', 'user': 'CodexSandboxOffline', 'project_name': 'datatry_02'}
    assert mod.select_exact([background, human], target) is human
    for nodes in ([background], [dict(human, user='CodexSandboxOffline')],
                  [dict(human, project_name='other')], [human, dict(human)]):
        with pytest.raises(RuntimeError, match='no other instance'):
            mod.select_exact(nodes, target)


def test_panel_and_cli_share_scope_target_and_cannot_override(tmp_path, monkeypatch):
    path = tmp_path / 'ue_target.json'
    path.write_text(json.dumps({'node_id': 'visible', 'user': 'Macheniek', 'project': 'datatry_02'}))
    monkeypatch.setattr(mod, 'TARGET_FILE', path)
    human = {'node_id': 'visible', 'user': 'Macheniek', 'project_name': 'datatry_02'}
    assert mod.select_panel_node([human], None, {'node_id': 'old'}) is human
    assert mod.select_panel_node([human], 'visible') is human
    with pytest.raises(RuntimeError, match='differs from this run target'):
        mod.load_target('offline')
