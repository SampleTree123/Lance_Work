"""Latest user exclusion is strict, immutable, and cannot restore prior items."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
import build_reviewed_wardrobe_pool_registry_v2 as publisher
from build_reviewed_wardrobe_pool_registry_v1 import read, digest, encoded


def test_revision_excludes_exact_family_preserving_every_other_asset_and_permission():
    source = formal.read_registry(formal.reviewed_pool_v1_registry_path())
    before = copy.deepcopy(source)
    current = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    assert source == before
    assert formal.reviewed_pool_v2_registry_path() == formal.REVIEWED_POOL_V2_REGISTRY
    assert formal.reviewed_pool_v2_publication_path() == formal.REVIEWED_POOL_V2_PUBLICATION
    assert current == formal.reviewed_pool_v2_expected(source, digest(formal.REVIEWED_POOL_REGISTRY))
    assert current['families'] == [f for f in source['families'] if f['family_id'] != 'male.lift_haul']
    assert current['hair_assets'] == source['hair_assets']
    assert current['shared_shoe_assets'] == source['shared_shoe_assets']
    female_lift = [s for s in current['shared_shoe_assets'] if s['sex'] == 'female' and 'lift_and_haul' in str(s)]
    assert len(female_lift) == 2
    assert current['reviewed_pool']['high_heels'] == source['reviewed_pool']['high_heels']
    assert formal.validate_registry(current) == publisher.COUNTS


def test_revision_witness_mapping_retains_original_numbers_and_resolutions():
    parent_receipt = read(formal.REVIEWED_POOL_PUBLICATION)
    old = read(Path(parent_receipt['mapping_report']))
    receipt = read(formal.REVIEWED_POOL_V2_PUBLICATION)
    current = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    expected_mapping, expected_validation = publisher.revise_mapping(old, current)
    actual = read(Path(receipt['mapping_report']))
    for key, value in expected_mapping.items():
        assert actual[key] == value
    validation = read(Path(receipt['selection_validation']))
    for key, value in expected_validation.items():
        assert validation[key] == value
    assert [r['historical_sex_index'] for r in actual['outfits'] if r['family_id'] == 'male.lift_haul'] == [33, 34, 35, 36]
    assert validation['removed_family_rejection_cases'] == 4
    for row in read(Path(receipt['protected_sources_report']))['records']:
        assert digest(Path(row['path'])) == row['before_sha256'] == row['after_sha256']


@pytest.fixture
def isolated_revision(tmp_path, monkeypatch):
    original = read(formal.REVIEWED_POOL_V2_PUBLICATION)
    receipt = copy.deepcopy(original)
    parent = tmp_path / 'parent_registry.json'
    parent.write_bytes(formal.REVIEWED_POOL_REGISTRY.read_bytes())
    parent_receipt = tmp_path / 'parent_publication.json'
    parent_receipt.write_bytes(formal.REVIEWED_POOL_PUBLICATION.read_bytes())
    monkeypatch.setattr(formal, 'reviewed_pool_v1_registry_path', lambda: parent)
    monkeypatch.setattr(formal, 'REVIEWED_POOL_PUBLICATION', parent_receipt)
    for key in ('output_registry', 'mapping_report', 'selection_validation', 'protected_sources_report', 'feedback'):
        dest = tmp_path / Path(original[key]).name
        dest.write_bytes(Path(original[key]).read_bytes())
        receipt[key], receipt[key + '_sha256'] = str(dest), digest(dest)
    receipt['source_registry'], receipt['source_registry_sha256'] = str(parent), digest(parent)
    receipt['source_publication'], receipt['source_publication_sha256'] = str(parent_receipt), digest(parent_receipt)
    current_receipt = tmp_path / 'publication.json'
    current_receipt.write_bytes(encoded(receipt))
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V2_REGISTRY', Path(receipt['output_registry']))
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V2_PUBLICATION', current_receipt)
    assert formal.reviewed_pool_v2_registry_path() == Path(receipt['output_registry'])
    return current_receipt, receipt


@pytest.mark.parametrize('key', ['receipt', 'source_registry', 'source_publication', 'output_registry',
                                'selection_validation', 'mapping_report', 'protected_sources_report', 'feedback'])
@pytest.mark.parametrize('mode', ['missing', 'changed'])
def test_current_revision_never_falls_back_when_bound_file_unavailable(isolated_revision, key, mode):
    receipt_path, receipt = isolated_revision
    path = receipt_path if key == 'receipt' else Path(receipt[key])
    if mode == 'missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b'\n') if key != 'receipt' else path.write_bytes(b'{}')
    with pytest.raises(formal.RegistryError, match='refusing unfiltered fallback'):
        formal.reviewed_pool_v2_registry_path()


@pytest.mark.parametrize('key', ['selection_validation', 'mapping_report', 'protected_sources_report', 'feedback'])
def test_rehashed_failed_revision_evidence_cannot_publish(isolated_revision, key):
    receipt_path, receipt = isolated_revision
    path = Path(receipt[key])
    value = read(path)
    value['success'] = False
    path.write_bytes(encoded(value))
    receipt[key + '_sha256'] = digest(path)
    receipt_path.write_bytes(encoded(receipt))
    with pytest.raises(formal.RegistryError, match='unsuccessful or stale'):
        formal.reviewed_pool_v2_registry_path()


def test_rehashed_unapproved_delta_cannot_restore_removed_family(isolated_revision):
    receipt_path, receipt = isolated_revision
    current = Path(receipt['output_registry'])
    value = read(current)
    source = read(Path(receipt['source_registry']))
    value['families'].append(next(f for f in source['families'] if f['family_id'] == 'male.lift_haul'))
    current.write_bytes(encoded(value))
    receipt['output_registry_sha256'] = digest(current)
    receipt_path.write_bytes(encoded(receipt))
    with pytest.raises(formal.RegistryError, match='approved revision delta'):
        formal.reviewed_pool_v2_registry_path()
