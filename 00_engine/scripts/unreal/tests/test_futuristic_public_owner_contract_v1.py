"""Focused pure data tests. No UE import or mutation of immutable receipts."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
import ue_futuristic_public_owner_contract_v1 as p
import ue_scene_folder_organization_v1 as m

SOURCE = p.read_pinned(p.RUN / 'futuristic_generated_ownership_source_v2.json', p.SOURCE_SHA)
TARGET = p.read_pinned(p.RUN / 'futuristic_generated_ownership_target_v2.json',
                       '796de7e542986410992d9edc65f80d86c35a856512d06d81283ab568bf777299')
KEY = p.SHOW + '.ShowcaseMap:PersistentLevel.BP__Building_Shop_B__2.BP_AlphabetSignMaker'


def current(map_index, repaired=False):
    target = copy.deepcopy(TARGET['maps'][map_index])
    if repaired:
        src = next(r for r in SOURCE['maps'][0]['ownership']['value']['children'] if r['public_mapping_key'] == KEY)
        target['ownership']['value']['children'] = [copy.deepcopy(src) if r['public_mapping_key'] == KEY else r
                                                  for r in target['ownership']['value']['children']]
        actor = next(r for r in target['capture']['signature']['actors'] if r['name'] == src['child']['name'])
        actor['transform'][4] = 0.0
    return target


def compare(target, i):
    return p.comparison_from_public_frames(m, SOURCE['maps'][i], target['ownership']['value'],
                                          target['capture']['signature'], target['capture']['component_transforms'])


def test_actual_target_yaw_does_not_activate_name_hook():
    with pytest.raises(RuntimeError, match='including sign yaw'):
        compare(current(0), 0)


def test_repaired_fixture_changes_only_names_keeps_four_relative_failures():
    target = current(0, repaired=True)
    untouched = copy.deepcopy(target)
    sig, rel, witness = compare(target, 0)
    assert target == untouched
    assert len(witness['satellite_pairs']) == 2
    assert m.compare_map(SOURCE['maps'][0]['capture']['signature'], sig)[0]
    assert not m.compare_component_transforms(SOURCE['maps'][0]['capture']['component_transforms'], rel)


def test_virtual_actual_passes_full_strict_with_twelve_pairs():
    target = current(1)
    sig, rel, witness = compare(target, 1)
    assert len(witness['satellite_pairs']) == 12
    assert m.compare_map(SOURCE['maps'][1]['capture']['signature'], sig)[0]
    assert m.compare_component_transforms(SOURCE['maps'][1]['capture']['component_transforms'], rel)


def test_fresh_allocation_number_requires_same_finite_owner_and_complete_semantics():
    target = current(1)
    row = next(r for r in target['ownership']['value']['children'] if r['child']['name'] == p.SAT_PREFIX + '7821')
    old = copy.deepcopy(row['child'])
    new = dict(old, name=p.SAT_PREFIX + '99999', path=old['path'].rsplit('.', 1)[0] + '.' + p.SAT_PREFIX + '99999',
               raw_path=old['raw_path'].rsplit('.', 1)[0] + '.' + p.SAT_PREFIX + '99999')
    replacement = p.renamed_frame(row, old, new)
    replacement['child']['raw_path'] = new['raw_path']
    replacement['child_root']['identity']['raw_path'] = new['raw_path'] + '.' + row['child_root']['identity']['name']
    replacement['child_root']['owner']['raw_path'] = new['raw_path']
    index = target['ownership']['value']['children'].index(row)
    target['ownership']['value']['children'][index] = replacement
    for rows in (target['capture']['signature']['actors'], target['capture']['component_transforms']):
        next(r for r in rows if r['name'] == old['name'])['name'] = new['name']
    sig, rel, witness = compare(target, 1)
    assert any(r['current_name'] == new['name'] for r in witness['satellite_pairs'])
    assert m.compare_map(SOURCE['maps'][1]['capture']['signature'], sig)[0]
    assert m.compare_component_transforms(SOURCE['maps'][1]['capture']['component_transforms'], rel)


@pytest.mark.parametrize('bad', ['owner', 'world', 'mesh', 'material', 'relative', 'camera'])
def test_owner_or_semantics_change_rejects_hook(bad):
    target = current(0, repaired=True)
    row = next(r for r in target['ownership']['value']['children'] if r['child']['name'] == p.SAT_PREFIX + '648')
    if bad == 'owner':
        row['parent_actor']['name'] = 'WrongOwner'
    elif bad == 'world':
        row['child_world_transform'][4] += 1
    elif bad == 'camera':
        target['ownership']['value']['camera_proxies'][0]['mesh']['path'] = '/Engine/Wrong.Wrong'
    else:
        actor = next(r for r in target['capture']['signature']['actors'] if r['name'] == row['child']['name'])
        if bad == 'mesh':
            actor['components'][0]['mesh'] = '/Game/Wrong.Wrong'
        elif bad == 'material':
            actor['components'][0]['materials'] = ['/Game/Wrong.Wrong']
        else:
            rel = next(r for r in target['capture']['component_transforms'] if r['name'] == row['child']['name'])
            rel['components'][0]['transform'][0] += 0.0001
    with pytest.raises(RuntimeError):
        compare(target, 0)


def test_unlisted_parent_cannot_borrow_suffix_rule():
    target = current(1)
    row = next(r for r in target['ownership']['value']['children'] if r['child']['name'] == p.SAT_PREFIX + '0')
    row['child']['name'] = p.SAT_PREFIX + '12345'
    row['child_root']['owner']['name'] = row['child']['name']
    with pytest.raises(RuntimeError, match='fourteen'):
        compare(target, 1)


def test_actual_frozen_source_receipts_and_official_pins_validate_without_temp_collector():
    base_path = p.RUN / 'baseline_FuturisticMetaCity_v1.json'
    base = p.read_pinned(base_path, p.BASE_SHA)
    target = current(1)
    before = next(row for row in base['maps'] if row['map'] == p.VIRTUAL)
    raw = copy.deepcopy(target)
    # The public capture is the sole UE boundary; all real receipt and official
    # source hashes and all complete source signature/relative guards execute.
    with patch.object(m, 'dirty', return_value=[]), \
         patch.object(p, 'capture_current_ownership', return_value=target['ownership']['value']) as capture:
        sig, rel, witness = p.validated_map_comparison(None, m, p.ROOT, base_path, base, before,
                                                      target['capture']['signature'], target['capture']['component_transforms'])
    capture.assert_called_once_with(None, m, p.DEST + p.VIRTUAL[len(p.ROOT):])
    assert target == raw
    assert m.compare_map(before, sig)[0]
    assert m.compare_component_transforms(base['component_transforms'][p.VIRTUAL], rel)
    assert witness['source_ownership_sha256'] == p.SOURCE_SHA
    assert witness['source_full903_sha256'] == p.FULL_SOURCE_SHA
    assert p.SOURCE_HELPER_SHA == 'eae640ee12f0c5a07719f169eea1e7065a06ad4bfc6a50e567e51bca1c620429'
    assert p.SOURCE_HELPER_SHA != m.sha(m.__file__)


def test_changed_receipt_bytes_fail_hash_guard(tmp_path):
    path = tmp_path / 'changed_source_receipt.json'
    path.write_text('{}', encoding='utf-8')
    with pytest.raises(RuntimeError, match='evidence SHA changed'):
        p.read_pinned(path, p.SOURCE_SHA)


def test_caller_changed_baseline_fails_before_public_capture():
    base_path = p.RUN / 'baseline_FuturisticMetaCity_v1.json'
    base = p.read_pinned(base_path, p.BASE_SHA)
    before = next(row for row in base['maps'] if row['map'] == p.VIRTUAL)
    changed = copy.deepcopy(base)
    changed['maps'][1]['actors'][0]['transform'][0] += 1
    with patch.object(p, 'capture_current_ownership') as capture, pytest.raises(RuntimeError, match='caller baseline changed'):
        p.validated_map_comparison(None, m, p.ROOT, base_path, changed, before, {}, [])
    capture.assert_not_called()
