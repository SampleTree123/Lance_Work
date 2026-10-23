from pathlib import Path
from types import SimpleNamespace
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pair_review_face_fast_v1 as fast


def make_runtime(tmp_path):
    calls = []
    choices = {(sex, face): ({'asset': '/Faces/' + sex + '/' + face}, {})
               for sex in ('female', 'male') for face in ('smile', 'sad')}
    def accepted():
        calls.append('faces')
        return choices, {'path': 'accepted.json'}
    def prepare(_u, selection, motion, **kwargs):
        calls.append(('cold', selection['sex'], selection['face_id'], motion, kwargs))
        return {'motion': 'generated', 'face': {'face_id': selection['face_id']}}
    assembly = SimpleNamespace(prepare=prepare, COMPOSITE_ROOT='/Pair/Expressions',
        contract=SimpleNamespace(ROOT=tmp_path / 'appearances',
            formal_runtime=lambda: (SimpleNamespace(accepted_faces=accepted), object())))
    def load(path):
        calls.append(('load', path))
        return path
    return assembly, SimpleNamespace(load_asset=load), calls


def receipt(tmp_path, name='one', sex='female', face='smile', body='/Body/A', root='/Pair/Expressions'):
    folder = tmp_path / 'appearance_composites' / 'cache'
    folder.mkdir(parents=True, exist_ok=True)
    value = {'schema': 'full_motion_loop_cache_v1', 'success': True,
        'animation_path': root + '/Composites/' + sex + '/A_' + name,
        'spec': {'sex': sex, 'face_id': face, 'duration_seconds': 10., 'sources': [
            {'asset': body, 'path': 'large-body.uasset', 'sha256': 'unused'},
            {'asset': '/Faces/' + sex + '/' + face, 'path': 'large-face.uasset', 'sha256': 'unused'}]}}
    (folder / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
    return value


def test_reuses_exact_successful_receipt_without_source_or_repeat_json_reads(tmp_path, monkeypatch):
    a, u, calls = make_runtime(tmp_path)
    doc = receipt(tmp_path)
    selection = {'sex': 'female', 'face_id': 'smile', 'choice': {'clothes': 1}}
    clip, face = fast.resolve(u, a, selection, '/Body/A', 'action')
    assert clip == doc['animation_path']
    assert face['original_body']['path'] == 'large-body.uasset'
    assert not any(isinstance(c, tuple) and c[0] == 'cold' for c in calls)
    monkeypatch.setattr(Path, 'read_text', lambda *_a, **_kw: pytest.fail('repeat JSON read'))
    monkeypatch.setattr(Path, 'read_bytes', lambda *_a, **_kw: pytest.fail('source hash read'))
    selection['choice'] = {'clothes': 2, 'hair': 3, 'color': 'pink'}
    clip2, face2 = fast.resolve(u, a, selection, '/Body/A', 'another-label')
    assert clip2 == clip and face2 == face
    face2['original_body']['path'] = 'mutated-reply'
    assert fast.resolve(u, a, selection, '/Body/A')[1]['original_body']['path'] == 'large-body.uasset'
    assert calls.count('faces') == 1


@pytest.mark.parametrize('change', ['sex', 'face', 'body', 'face_asset', 'root'])
def test_different_inputs_never_reuse_receipt(tmp_path, change):
    a, u, calls = make_runtime(tmp_path)
    receipt(tmp_path)
    selection = {'sex': 'female', 'face_id': 'smile'}
    body = '/Body/A'
    if change == 'sex':
        selection['sex'] = 'male'
    elif change == 'face':
        selection['face_id'] = 'sad'
    elif change == 'body':
        body = '/Body/B'
    elif change == 'root':
        a.COMPOSITE_ROOT = '/Other/Expressions'
    else:
        fast.install(a)
        choices = fast._faces(a, a._pair_fast_faces)
        choices[('female', 'smile')][0]['asset'] = '/Faces/new/smile'
    assert fast.resolve(u, a, selection, body, 'action')[0] == 'generated'
    assert len([c for c in calls if isinstance(c, tuple) and c[0] == 'cold']) == 1


def test_none_preserves_body_and_does_not_load_or_install(tmp_path):
    a, u, calls = make_runtime(tmp_path)
    assert fast.resolve(u, a, {'face_id': 'none'}, 'body') == ('body', None)
    assert fast.resolve(u, a, {'face_id': 'none'}, None) == (None, None)
    assert not calls and not hasattr(a, '_pair_fast_faces')


def test_static_face_and_cold_generation_are_cached(tmp_path):
    a, u, calls = make_runtime(tmp_path)
    selection = {'sex': 'female', 'face_id': 'smile'}
    clip, face = fast.resolve(u, a, selection, None)
    assert clip == '/Faces/female/smile' and face['kind'] == 'accepted_static_face'
    assert fast.resolve(u, a, selection, None)[0] == clip
    fast.install(a)
    a.prepare = lambda *_a, **_kw: pytest.fail('must retain original generator')
    assert fast.resolve(u, a, selection, '/Body/B')[0] == 'generated'
    assert fast.resolve(u, a, selection, '/Body/B')[0] == 'generated'
    assert len([c for c in calls if isinstance(c, tuple) and c[0] == 'cold']) == 1


def test_cold_generation_uses_pair_catalog_and_identity_overlay(tmp_path):
    a, u, calls = make_runtime(tmp_path)
    data = {'sources': {'character_revision': {'path': 'pair-delivery.json'}},
            'identities': [{'id': 'CFD40_AF_001'}]}
    overlay = {'/Old/Body.Body': '/Pair/NewBody.NewBody'}
    selection = {'sex': 'female', 'face_id': 'smile', 'character_id': 'CFD40_AF_001',
                 'sources': data['sources']}
    original = a.prepare
    def prepare(api, selected, motion, **kwargs):
        assert kwargs['data'] is data
        assert kwargs['path_overlay'] is overlay
        assert selected['sources'] == kwargs['data']['sources']
        assert kwargs['path_overlay']['/Old/Body.Body'] == '/Pair/NewBody.NewBody'
        return original(api, selected, motion, **kwargs)
    a.prepare = prepare
    fast.install(a)
    assert fast.resolve(u, a, selection, '/Body/A', 'action',
                        data=data, path_overlay=overlay)[0] == 'generated'
    assert calls[-1][-1] == {'body_action_id': 'action', 'data': data, 'path_overlay': overlay}


def test_load_and_cold_errors_propagate_without_caching_failure(tmp_path):
    a, u, _calls = make_runtime(tmp_path)
    receipt(tmp_path)
    selection = {'sex': 'female', 'face_id': 'smile'}
    u.load_asset = lambda _p: None
    with pytest.raises(RuntimeError, match='could not load'):
        fast.resolve(u, a, selection, '/Body/A')
    assert not a._pair_fast_faces['resolved']
    a._pair_fast_faces['prepare'] = lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError('generation failed'))
    with pytest.raises(RuntimeError, match='generation failed'):
        fast.resolve(u, a, selection, '/Body/B')
    assert not a._pair_fast_faces['resolved']


def test_other_root_and_unsuccessful_receipts_cannot_win(tmp_path):
    a, u, _calls = make_runtime(tmp_path)
    receipt(tmp_path, name='foreign', root='/Old')
    doc = receipt(tmp_path, name='failed')
    doc['success'] = False
    path = tmp_path / 'appearance_composites/cache/failed.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    assert fast.resolve(u, a, {'sex': 'female', 'face_id': 'smile'}, '/Body/A')[0] == 'generated'
