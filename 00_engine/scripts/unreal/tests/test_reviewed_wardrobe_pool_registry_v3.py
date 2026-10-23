"""The female shared pool cannot restore native heels or affect male choices."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formal_wardrobe_registry_v1 as formal
import complete_character_slot_review_contract_v1 as slots
import build_reviewed_wardrobe_pool_registry_v3 as publisher
from build_reviewed_wardrobe_pool_registry_v1 import read, digest, encoded


def test_exact_shoe_revision_and_male_hair_preservation():
    old = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    current = formal.read_registry(formal.reviewed_pool_v3_registry_path())
    assert current == formal.reviewed_pool_v3_expected(old, publisher.PARENT_SHA)
    assert [f for f in old['families'] if f['sex'] == 'male'] == [f for f in current['families'] if f['sex'] == 'male']
    assert old['hair_assets'] == current['hair_assets']
    assert [s for s in old['shared_shoe_assets'] if s['sex'] != 'female'] == [s for s in current['shared_shoe_assets'] if s['sex'] != 'female']
    assert [s['asset_id'] for s in current['shared_shoe_assets'] if s['sex'] == 'female'] == formal.FEMALE_SHARED_SHOE_IDS
    assert all(a['slot'] != 'shoes' for f in current['families'] if f['sex'] == 'female' for a in f['assets'])
    parent = read(formal.REVIEWED_POOL_V2_PUBLICATION)
    publication = read(formal.REVIEWED_POOL_V3_PUBLICATION)
    before, after = (read(Path(p['mapping_report'])) for p in (parent, publication))
    assert [r for r in before['outfits'] if r['character_sex'] == 'male'] == [r for r in after['outfits'] if r['character_sex'] == 'male']
    for row in read(Path(publication['protected_sources_report']))['records']:
        assert digest(Path(row['path'])) == row['before_sha256'] == row['after_sha256']


def test_every_female_group_accepts_each_shared_shoe_and_rejects_native_or_retired():
    registry = formal.read_registry(formal.reviewed_pool_v3_registry_path())
    old = formal.read_registry(formal.reviewed_pool_v2_registry_path())
    removed = {f['family_id']: [a['asset_id'] for a in f['assets'] if a['slot'] == 'shoes'] for f in old['families']}
    cases = 0
    for family in registry['families']:
        if family['sex'] != 'female':
            continue
        gids = ([family['assembly']['bundle']['bundle_id']] if family['assembly_mode'] == 'locked_bundle'
                else [g['group_id'] for g in family['assembly']['groups']])
        for gid in gids:
            choice = slots._default(registry, family['family_id'], gid)
            canonical, _ = slots._canonical(registry, 'female', choice)
            for shoe in formal.FEMALE_SHARED_SHOE_IDS:
                result = formal.resolve_selection(registry, character_sex='female', **{**canonical, 'shared_shoe_id': shoe})
                assert [a['source_component_name'] for a in result['assignments'] if a['slot'] == 'shoes'] == [shoe]
                cases += 1
            for shoe in [None, *formal.FEMALE_EXCLUDED_SHOE_IDS]:
                with pytest.raises(formal.RegistryError):
                    formal.resolve_selection(registry, character_sex='female', **{**canonical, 'shared_shoe_id': shoe})
            for native in removed[family['family_id']]:
                with pytest.raises(formal.RegistryError):
                    formal.resolve_selection(registry, character_sex='female', **{**canonical, 'family_asset_ids': canonical['family_asset_ids'] + [native]})
    assert cases > 100


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    receipt = read(formal.REVIEWED_POOL_V3_PUBLICATION)
    for key in ('output_registry', 'mapping_report', 'selection_validation', 'protected_sources_report', 'feedback'):
        dest = tmp_path / Path(receipt[key]).name
        dest.write_bytes(Path(receipt[key]).read_bytes())
        receipt[key], receipt[key + '_sha256'] = str(dest), digest(dest)
    dest = tmp_path / 'publication.json'
    dest.write_bytes(encoded(receipt))
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V3_REGISTRY', Path(receipt['output_registry']))
    monkeypatch.setattr(formal, 'REVIEWED_POOL_V3_PUBLICATION', dest)
    formal.reviewed_pool_v3_registry_path()
    return dest, receipt


@pytest.mark.parametrize('key', ['output_registry', 'mapping_report', 'selection_validation', 'protected_sources_report', 'feedback'])
def test_missing_bound_evidence_is_not_a_fallback(isolated, key):
    _, receipt = isolated
    Path(receipt[key]).unlink()
    with pytest.raises(formal.RegistryError, match='refusing unfiltered fallback'):
        formal.reviewed_pool_v3_registry_path()


@pytest.mark.parametrize('mutation', ['restore_female_heel', 'alter_male', 'alter_hair'])
def test_rehashed_unapproved_registry_delta_rejected(isolated, mutation):
    dest, receipt = isolated
    path = Path(receipt['output_registry'])
    value = read(path)
    if mutation == 'restore_female_heel':
        old = read(Path(receipt['source_registry']))
        value['shared_shoe_assets'].append(next(s for s in old['shared_shoe_assets'] if s['asset_id'] == 'F015'))
    elif mutation == 'alter_male':
        next(f for f in value['families'] if f['sex'] == 'male')['display_name'] = 'changed'
    else:
        value['hair_assets'][0]['reviewed_sexes'] = []
    path.write_bytes(encoded(value))
    receipt['output_registry_sha256'] = digest(path)
    dest.write_bytes(encoded(receipt))
    with pytest.raises(formal.RegistryError, match='approved revision delta'):
        formal.reviewed_pool_v3_registry_path()
