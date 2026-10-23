"""Production-name imports; frozen full-map tests, no Unreal import/calls.

Set PYTHONPATH to the reviewed module directory (or production scripts/unreal).
"""
import ast
import copy
import hashlib
import itertools
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import ue_kyoto_showcase_tie_contract_v1 as k
import ue_futuristic_public_owner_contract_v1 as future
import ue_scene_folder_organization_v1 as m


@pytest.fixture(scope='module')
def frozen():
    assert k.sha(k.BASE) == k.BASE_SHA
    assert k.sha(k.FAILED) == k.FAILED_SHA
    base = json.loads(k.BASE.read_text(encoding='utf-8-sig'))
    proof = json.loads(k.FAILED.read_text(encoding='utf-8-sig'))
    before = next(x for x in base['maps'] if x['map'] == k.SHOWCASE)
    after = next(x for x in proof['maps'] if x['map'] == k.SHOWCASE)
    return base, proof, before, after


def test_actual_frozen_533_actor_bijection_and_all_four_maps(frozen):
    base, proof, before, after = frozen
    for original, actual in zip(base['maps'], proof['maps']):
        fixed, _ = k.validated_kyoto_tie_comparison(m, k.ROOT, k.BASE, base, original, actual)
        assert k.encoded(fixed) == k.encoded(original)


def test_source_and_actual_raw_not_modified(frozen):
    base, _, before, after = frozen
    raw = k.encoded(before), k.encoded(after)
    k.validated_kyoto_tie_comparison(m, k.ROOT, k.BASE, base, before, after)
    assert (k.encoded(before), k.encoded(after)) == raw


def test_all_eight_finite_pair_permutations(frozen):
    base, _, before, _ = frozen
    for bits in itertools.product((False, True), repeat=3):
        changed = copy.deepcopy(before)
        for bit, (_, _, (a, b)) in zip(bits, k.TIES):
            if bit:
                changed['actors'][a], changed['actors'][b] = changed['actors'][b], changed['actors'][a]
        fixed, _ = k.validated_kyoto_tie_comparison(m, k.ROOT, k.BASE, base, before, changed)
        assert k.encoded(fixed) == k.encoded(before)


@pytest.mark.parametrize('bad', [
    'transform', 'class', 'name', 'not_bijection', 'tie_material', 'unknown_field',
    'post_process', 'unrelated_transform', 'level_order', 'mesh', 'materials', 'instances'])
def test_every_other_complete_field_remains_strict(frozen, bad):
    base, _, before, after = frozen
    changed = copy.deepcopy(after)
    tie = changed['actors'][43]
    mesh = next(a for a in changed['actors'] if a['components'])['components'][0]
    if bad == 'transform': tie['transform'][0] = 999.0
    elif bad == 'class': tie['class'] = '/Script/Engine.PointLight'
    elif bad == 'name': tie['name'] = 'ExponentialHeightFog_2'
    elif bad == 'not_bijection': changed['actors'][44] = copy.deepcopy(tie)
    elif bad == 'tie_material': tie['components'].append({'name': 'Added', 'mesh': None, 'materials': ['/Game/OTHER.OTHER'], 'instances': None})
    elif bad == 'unknown_field': tie['light_intensity'] = 1.0
    elif bad == 'post_process': next(a for a in changed['actors'] if a['name'] == 'PostProcessVolume_1')['transform'][0] = 999.0
    elif bad == 'unrelated_transform': changed['actors'][0]['transform'][0] = 999.0
    elif bad == 'level_order': changed['levels'].reverse()
    elif bad == 'mesh': mesh['mesh'] = '/Game/OTHER.OTHER'
    elif bad == 'materials': mesh['materials'] = []
    elif bad == 'instances': mesh['instances'] = 123
    with pytest.raises(RuntimeError):
        k.validated_kyoto_tie_comparison(m, k.ROOT, k.BASE, base, before, changed)


def test_shared_hook_preserves_raw_and_keeps_generic_checks(frozen):
    base, _, before, after = frozen
    relative = copy.deepcopy(base['component_transforms'][k.SHOWCASE])
    raw = k.encoded(after), k.encoded(relative)
    fixed, rel, witness = m.finite_map_comparison_signature(None, k.ROOT, k.BASE, base, before, after, relative)
    assert k.encoded(fixed) == k.encoded(before)
    assert rel is relative and witness['expected_contract_sha256'] == m.KYOTO_SHOWCASE_TIE_CONTRACT_SHA256
    assert (k.encoded(after), k.encoded(relative)) == raw
    assert m.compare_map(before, fixed)[0] and m.compare_component_transforms(relative, rel)
    changed = copy.deepcopy(after)
    changed['actors'][43]['transform'][0] += 1
    with pytest.raises(RuntimeError):
        m.finite_map_comparison_signature(None, k.ROOT, k.BASE, base, before, changed, relative)
    # Post now has its own bounded hook and must reject a Kyoto baseline.
    with pytest.raises(RuntimeError, match='Exact actual original baseline'):
        m.finite_map_comparison_signature(None, '/Game/PostCity', k.BASE, base, before, changed, relative)
    a, r, w = m.finite_map_comparison_signature(None, '/Game/UnrelatedGenericScene', k.BASE, base, before, changed, relative)
    assert a is changed and r is relative and w is None and not m.compare_map(before, a)[0]


def test_future_branch_delegates_eight_arguments_and_pins_contract(frozen):
    base, _, before, after = frozen
    relative = []
    sentinel = object()
    with patch.object(m, 'sha', return_value=m.FUTURISTIC_PUBLIC_OWNER_CONTRACT_SHA256), \
         patch('importlib.reload', side_effect=lambda module: module), \
         patch.object(future, 'validated_map_comparison', return_value=(after, relative, {})) as call:
        sig, rel, witness = m.finite_map_comparison_signature(sentinel, future.ROOT, k.BASE, base, before, after, relative)
    call.assert_called_once_with(sentinel, m, future.ROOT, k.BASE, base, before, after, relative)
    assert sig is after and rel is relative and witness['expected_contract_sha256'] == m.FUTURISTIC_PUBLIC_OWNER_CONTRACT_SHA256
    with patch.object(m, 'sha', return_value='0' * 64), pytest.raises(RuntimeError, match='code SHA differs'):
        m.finite_map_comparison_signature(None, future.ROOT, k.BASE, base, before, after, relative)


def test_verify_uses_seven_argument_hook_before_strict_generic_checks():
    tree = ast.parse(Path(m.__file__).read_text(encoding='utf-8'))
    verify = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'verify')
    calls = [n for n in ast.walk(verify) if isinstance(n, ast.Call)]
    named = lambda n: n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, 'id', '')
    hook = [n for n in calls if named(n) == 'finite_map_comparison_signature']
    assert len(hook) == 1 and len(hook[0].args) == 7
    assert any(named(n) == 'compare_map' and n.lineno > hook[0].lineno for n in calls)
    assert any(named(n) == 'compare_component_transforms' and n.lineno > hook[0].lineno for n in calls)


def test_other_three_kyoto_maps_keep_original_signature_and_relative(frozen):
    base, proof, _, _ = frozen
    for before, after in zip(base['maps'], proof['maps']):
        if before['map'] == k.SHOWCASE:
            continue
        relative = base['component_transforms'][before['map']]
        sig, rel, witness = m.finite_map_comparison_signature(None, k.ROOT, k.BASE, base, before, after, relative)
        assert sig is after and rel is relative and witness is None


def test_five_generic_functions_stay_identical_to_historical_eae_producer():
    # These are source-segment hashes with read_text newline normalization;
    # they are predicates for unchanged functions, never artifact/code-file pins.
    expected = {
        'canonical_registry_class': 'd0e25623844ef8d237c3c5de34cfb67646d8438d2b803fd1a688e7ec8ccfd81e',
        'registry_identities': '8496e1f76e6c193a19addaee76eecc023fba0b3d6d8929b345f730048e1e9dc3',
        'signature_equal': '2767faa2e18d13e275d4e7ce13895f51fa77a027a41ff37d9d8bd2471a4b6d33',
        'compare_map': 'a24a86b64cefe1fc21fd7766042d4655d926a02c963b427bfba2a09edaf1bac7',
        'compare_component_transforms': '5f5985a84e807806e813a33a4e344bd9d178e1638a0ac6c36e69488c1446abe9'}
    source = Path(m.__file__).read_text(encoding='utf-8')
    actual = {n.name: hashlib.sha256(ast.get_source_segment(source, n).encode('utf-8')).hexdigest()
              for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in expected}
    assert actual == expected
