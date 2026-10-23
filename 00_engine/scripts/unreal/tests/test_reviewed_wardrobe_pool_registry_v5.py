"""Five sex-specific removals cannot affect footwear, clothing or male hair 06."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
import complete_character_slot_review_contract_v1 as slots
from build_reviewed_wardrobe_pool_registry_v1 import read, digest, encoded


def test_exact_revision_preserves_clothing_shoes_and_asset_geometry():
    old = formal.read_registry(formal.reviewed_pool_v4_registry_path())
    current = formal.read_registry()
    assert current == formal.reviewed_pool_v5_expected(old, digest(formal.REVIEWED_POOL_V4_REGISTRY))
    assert old['families'] == current['families']
    assert old['shared_shoe_assets'] == current['shared_shoe_assets']
    before = {h['hair_id']: h for h in old['hair_assets']}
    after = {h['hair_id']: h for h in current['hair_assets']}
    assert set(before) - set(after) == {'HAIR_HB1_18', 'HAIR_HB2_05', 'HAIR_HB3_15', 'HAIR_HB3_20'}
    for hair_id, row in after.items():
        assert {k: v for k, v in before[hair_id].items() if k != 'reviewed_sexes'} == {k: v for k, v in row.items() if k != 'reviewed_sexes'}
    assert formal.hair_available_to(after['HAIR_HB1_13'], 'male')
    assert not formal.hair_available_to(after['HAIR_HB1_13'], 'female')
    assert formal.hair_selection_counts(current) == {'male': 13, 'female': 20, 'union': 28, 'overlap': 5}


def test_excluded_choices_rejected_with_and_without_clothes_and_original_numbers_kept():
    catalog = slots.catalog()
    assert catalog['hair_review_indices_by_sex'] == {
        'male': [1, 2, 3, 5, 6, 11, 27, 28, 30, 31, 32, 37, 39],
        'female': [1, 2, 3, 5, 8, 9, 11, 14, 16, 17, 19, 22, 23, 24, 25, 26, 29, 33, 35, 38]}
    for sex, exclusions in formal.CURRENT_HAIR_EXCLUSIONS.items():
        for hair_id in exclusions.values():
            for choice in [{'hair_id': hair_id}, {**catalog['presets_by_sex'][sex][0]['choice'], 'hair_id': hair_id}]:
                with pytest.raises(formal.RegistryError, match='hair not available'):
                    slots.validate_choice(sex, choice)
    assert slots.validate_choice('male', {'hair_id': 'HAIR_HB1_13'})['resolved_hair_id'] == 'HAIR_HB1_13'


def test_outfit_witnesses_and_previous_publication_bytes_unchanged():
    old_receipt = read(formal.REVIEWED_POOL_V4_PUBLICATION)
    receipt = read(formal.CURRENT_REVIEWED_POOL_PUBLICATION)
    assert read(Path(old_receipt['mapping_report']))['outfits'] == read(Path(receipt['mapping_report']))['outfits']
    for row in read(Path(receipt['protected_sources_report']))['records']:
        assert digest(Path(row['path'])) == row['before_sha256'] == row['after_sha256']


@pytest.mark.parametrize('change', ['restore_female_06', 'remove_male_06', 'change_shoe'])
def test_rehashed_unapproved_change_is_rejected(tmp_path, monkeypatch, change):
    receipt = read(formal.CURRENT_REVIEWED_POOL_PUBLICATION)
    value = read(Path(receipt['output_registry']))
    hair = next(h for h in value['hair_assets'] if h['hair_id'] == 'HAIR_HB1_13')
    if change == 'restore_female_06':
        hair['reviewed_sexes'].append('female')
    elif change == 'remove_male_06':
        hair['reviewed_sexes'] = []
    else:
        value['shared_shoe_assets'].pop()
    path = tmp_path / 'registry.json'
    path.write_bytes(encoded(value))
    receipt['output_registry'], receipt['output_registry_sha256'] = str(path), digest(path)
    pub = tmp_path / 'publication.json'
    pub.write_bytes(encoded(receipt))
    monkeypatch.setattr(formal, 'CURRENT_REVIEWED_POOL_REGISTRY', path)
    monkeypatch.setattr(formal, 'CURRENT_REVIEWED_POOL_PUBLICATION', pub)
    with pytest.raises(formal.RegistryError, match='approved revision delta'):
        formal.current_registry_path()


def test_missing_current_receipt_does_not_restore_old_hairs(tmp_path, monkeypatch):
    monkeypatch.setattr(formal, 'CURRENT_REVIEWED_POOL_PUBLICATION', tmp_path / 'missing.json')
    with pytest.raises(formal.RegistryError, match='refusing unfiltered fallback'):
        formal.current_registry_path()
