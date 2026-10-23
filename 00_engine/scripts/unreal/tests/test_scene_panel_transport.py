"""Regression for short TCP reads splitting Chinese review receipts."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def panel_module(monkeypatch, tmp_path):
    scripts = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('transport_panel', scripts / 'scene_site_review_panel_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'RUN', tmp_path)
    return module


def test_large_request_is_lossless_and_command_stays_small(panel_module):
    sent = panel_module.request('save_site', issue_reviews={str(i): {'note': '遮挡不影响'} for i in range(5000)})
    command = panel_module.command_payload(sent)
    assert len(command.encode('utf-8')) < 2000
    assert panel_module.read(panel_module.RUN / 'requests' / (sent['request_id'] + '.json')) == sent
    compile(command, '<request>', 'exec')


@pytest.mark.parametrize('split_chinese', [True, False])
def test_short_reads_are_not_message_boundaries(panel_module, split_chinese):
    class Message:
        def __init__(self, *_): pass
        def from_json_bytes(self, data):
            self.payload = json.loads(data)
            self.type_ = self.payload['type']
            return True
        def passes_receive_filter(self, node): return node == 'ue'
    class Connection: pass
    module = SimpleNamespace(_RemoteExecutionCommandConnection=Connection,
        _RemoteExecutionMessage=Message, DEFAULT_RECEIVE_BUFFER_SIZE=65536)
    panel_module.install_complete_reply_receiver(module)
    data = json.dumps({'type': 'result', 'text': '遮挡已审查' * 5000}, ensure_ascii=False).encode()
    cut = data.index('遮'.encode()) + (1 if split_chinese else 0)
    chunks = iter([data[:cut], data[cut:cut+31], data[cut+31:]])
    connection = Connection()
    connection._node_id = 'ue'
    connection._command_channel_socket = SimpleNamespace(recv=lambda _: next(chunks, b''))
    assert connection._receive_message('result').payload == json.loads(data)


def test_truncated_reply_fails_without_retry(panel_module):
    class Connection: pass
    module = SimpleNamespace(_RemoteExecutionCommandConnection=Connection, DEFAULT_RECEIVE_BUFFER_SIZE=65536)
    panel_module.install_complete_reply_receiver(module)
    chunks = iter([b'{"text":"\xe7', b''])
    connection = Connection()
    connection._command_channel_socket = SimpleNamespace(recv=lambda _: next(chunks))
    with pytest.raises(RuntimeError, match='传输中断'):
        connection._receive_message('result')
