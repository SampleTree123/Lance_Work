"""Barefoot permission follows original group requirements, not a shoe default."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
import complete_character_slot_review_contract_v1 as slots
from build_reviewed_wardrobe_pool_registry_v1 import read, digest, encoded


def test_original_barefoot_permission_restored_and_every_group_uses_same_shoe_pool():
    current = formal.read_registry(formal.reviewed_pool_v4_registry_path())
    original = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    current_families = {f['family_id']: f for f in current['families']}
    barefoot, required, shod = [], [], 0
    for old in original['families']:
        if old['sex'] != 'female':
            continue
        family = current_families[old['family_id']]
        assets = {a['asset_id']: a for a in old['assets']}
        groups = ([{'group_id': old['assembly']['bundle']['bundle_id'], 'required_assets': old['assembly']['bundle']['required_assets']}]
                  if old['assembly_mode'] == 'locked_bundle' else old['assembly']['groups'])
        for g in groups:
            gid = g['group_id']
            was_required = 'shoes' in g.get('required_slots', []) or any(assets[a]['slot'] == 'shoes' for a in g.get('required_assets', []))
            choice = slots._default(current, family['family_id'], gid)
            assert choice['shared_shoe_id'] == ('F001' if was_required else None)
            canonical, _ = slots._canonical(current, 'female', choice)
            if was_required:
                required.append((family['family_id'], gid))
                with pytest.raises(formal.RegistryError):
                    formal.resolve_selection(current, character_sex='female', **{**canonical, 'shared_shoe_id': None})
            else:
                barefoot.append((family['family_id'], gid))
                result = formal.resolve_selection(current, character_sex='female', **canonical)
                assert not any(a['slot'] == 'shoes' for a in result['assignments'])
            for shoe in formal.FEMALE_SHARED_SHOE_IDS:
                result = formal.resolve_selection(current, character_sex='female', **{**canonical, 'shared_shoe_id': shoe})
                assert [a['source_component_name'] for a in result['assignments'] if a['slot'] == 'shoes'] == [shoe]
                shod += 1
            for shoe in formal.FEMALE_EXCLUDED_SHOE_IDS:
                with pytest.raises(formal.RegistryError):
                    formal.resolve_selection(current, character_sex='female', **{**canonical, 'shared_shoe_id': shoe})
    assert len(barefoot) == 13 and len(required) == 4 and shod == 153
    assert set(required) == {('female.pretty_dresses', 'pants'), ('female.pretty_dresses', 'skirts'),
                             ('female.dress_collection', 'full_body'), ('female.dress_collection', 'shirt_with_skirt')}


def test_historical_barefoot_presets_male_rows_and_hair_preserved():
    old = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    current = formal.read_registry(formal.reviewed_pool_v4_registry_path())
    assert [f for f in old['families'] if f['sex'] == 'male'] == [f for f in current['families'] if f['sex'] == 'male']
    assert old['hair_assets'] == current['hair_assets']
    assert [s for s in old['shared_shoe_assets'] if s['sex'] != 'female'] == [s for s in current['shared_shoe_assets'] if s['sex'] != 'female']
    receipts = [read(formal.REVIEWED_POOL_V2_PUBLICATION), read(formal.REVIEWED_POOL_V4_PUBLICATION)]
    before, after = [read(Path(r['mapping_report'])) for r in receipts]
    assert [r for r in before['outfits'] if r['character_sex'] == 'male'] == [r for r in after['outfits'] if r['character_sex'] == 'male']
    old_by_number = {r['historical_sex_index']: r for r in before['outfits'] if r['character_sex'] == 'female' and r['status'] == 'retained'}
    for row in after['outfits']:
        if row['character_sex'] != 'female' or row['status'] != 'retained':
            continue
        source = old_by_number[row['historical_sex_index']]
        old_result = formal.resolve_selection(old, **source['request'])
        if not any(a['slot'] == 'shoes' for a in old_result['assignments']):
            assert row == source
    for row in read(Path(receipts[1]['protected_sources_report']))['records']:
        assert digest(Path(row['path'])) == row['before_sha256'] == row['after_sha256']


def test_rehashed_barefoot_policy_expansion_rejected(tmp_path, monkeypatch):
    receipt = read(formal.REVIEWED_POOL_V4_PUBLICATION)
    path = tmp_path / 'registry.json'
    value = read(Path(receipt['output_registry']))
    next(f for f in value['families'] if f['family_id'] == 'female.dress_collection')['shared_footwear_policy']['barefoot_allowed_groups'] = ['full_body']
    path.write_bytes(encoded(value))
    receipt['output_registry'], receipt['output_registry_sha256'] = str(path), digest(path)
    pub = tmp_path / 'publication.json'
    pub.write_bytes(encoded(receipt))
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V4_REGISTRY', path)
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V4_PUBLICATION', pub)
    with pytest.raises(formal.RegistryError, match='approved revision delta'):
        formal.reviewed_pool_v4_registry_path()
