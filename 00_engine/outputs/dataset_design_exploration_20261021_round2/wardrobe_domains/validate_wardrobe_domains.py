"""Validate finite catalog arithmetic, not production resolution or pixels."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
x=json.loads((HERE/'wardrobe_domain_inventory.json').read_text(encoding='utf-8'))
d=x['domains'];t=x['totals_by_sex']
assert len(d)==46
assert all(Path(p).is_file() for p in x['formal_source_code_read'])
for sex in ['female','male']:
    rows=[r for r in d if r['sex']==sex]
    assert len(rows)==t[sex]['groups']
    assert sum(bool(r['variable_core_slots']) for r in rows)==t[sex]['groups_with_core_slot_variation']
    assert sum(r['core_pair_sum'] for r in rows)==t[sex]['core_pair_sum_by_group_context']
    for r in rows:
        for slot in r['slots']:
            n=slot['logical_values_including_none']
            assert n==slot['registered_asset_values']+slot['optional_none']
            assert slot['unordered_value_pairs_one_frozen_other_context']==n*(n-1)//2
            assert len(slot['registered_values'])==len(set(slot['registered_values']))==n
        if r['assembly_mode']=='locked_bundle':
            assert not r['slots'] and r['fixed_required_asset_count']>0
assert sum(t[s]['variable_core_slot_domains'] for s in t)==55
assert sum(t[s]['unique_selectable_core_asset_ids'] for s in t)==222
assert [(r['sex'],r['values']) for r in x['current_seven_axis_garment_domains']]==[('female',16),('male',5)]
assert [(r['family_id'],r['group_id']) for r in d if r['family_hair_deny']]==[('male.rugged_trendy','default')]
star=sum(x['registered_core_star_nodes_by_sex_one_context_per_variable_group'].values())
fixed=sum(not r['variable_core_slots'] for r in d)
shoe=sum(r['footwear_values_including_none_if_legal']-1 for r in d)
accessory=sum(r['optional_accessory_toggles_if_independent'] for r in d)
assert (star,fixed,shoe,accessory)==(181,17,250,10)
assert star+fixed+shoe+accessory==458
report={'status':'pass','scope':'exported_contract_arithmetic_only_not_resolver_UE_or_visual_acceptance',
        'families':38,'groups':46,'variable_core_slot_domains':55,'core_choice_ids':222,
        'current7_core_choice_id_coverage':21/222,
        'one_context_star_upper_budget':{'core_variable_domains':181,'fixed_group_anchors':17,'footwear_additions':250,'optional_accessory_additions':10,'total':458},
        'does_not_define_piece_vs_outfit_contract_for_user':True}
(HERE/'SELF_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
