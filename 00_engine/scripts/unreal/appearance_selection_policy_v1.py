"""Current shooting appearance choices over the retained source inventory."""
import copy

HAIR_COLORS = ('original', 'black', 'gold', 'silver_white', 'red', 'blue', 'pink')
RED_SOUL = 'male.redsoul'
RED_SOUL_HOOD = 'male.redsoul.asset.b37f9c3bd4cf'
RETIRED_FAMILIES = frozenset(('male.rugged_trendy',))


def remove_retired_wardrobe(registry, wardrobe):
    """Retire shooting choices while retaining their source assets on disk."""
    registry['families'] = [f for f in registry['families'] if f['family_id'] not in RETIRED_FAMILIES]
    for sex in wardrobe['families_by_sex']:
        wardrobe['families_by_sex'][sex] = [f for f in wardrobe['families_by_sex'][sex]
                                          if f['family_id'] not in RETIRED_FAMILIES]
        wardrobe['presets_by_sex'][sex] = [r for r in wardrobe['presets_by_sex'][sex]
                                         if r['choice']['family_id'] not in RETIRED_FAMILIES]


def apply(registry, wardrobe, palette):
    remove_retired_wardrobe(registry, wardrobe)
    family = next(f for f in registry['families'] if f['family_id'] == RED_SOUL)
    family['assembly']['bundle']['required_assets'] = [
        a for a in family['assembly']['bundle']['required_assets'] if a != RED_SOUL_HOOD]
    family['hair_interface'] = {'allow_all':True, 'deny_all':False}
    for family in wardrobe['families_by_sex']['male']:
        if family['family_id'] == RED_SOUL:
            family['hair_interface'] = {'allow_all':True, 'deny_all':False}
            for group in family['groups']:
                group['required_assets'] = [a for a in group['required_assets'] if a['asset_id'] != RED_SOUL_HOOD]
    for row in wardrobe['presets_by_sex']['male']:
        if row['choice']['family_id'] == RED_SOUL:
            row['hair_deny'] = False
            row['canonical_choice']['family_asset_ids'] = [
                a for a in row['canonical_choice']['family_asset_ids'] if a != RED_SOUL_HOOD]
            row['label'] = row['label'].replace(' + SHSV_S02_MA_hood','').replace('SHSV_S02_MA_hood + ','')
    palette['hair'] = list(HAIR_COLORS)
    by_id = {r['id']:r for r in palette['hair_color_trials']}
    palette['hair_color_trials'] = [copy.deepcopy(by_id[k]) for k in HAIR_COLORS]
    next(r for r in palette['hair_color_trials'] if r['id']=='silver_white')['label'] = '白色'
