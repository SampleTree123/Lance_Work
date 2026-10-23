"""Finite slot/pair counts from the exported formal wardrobe contract.

No UE import. Does not enumerate outfit Cartesian products or modify inputs.
Counts are registered choices, not pixel-distinct validated garment changes.
"""
from collections import Counter,defaultdict
import hashlib
import itertools
import json
from math import comb
from pathlib import Path

HERE=Path(__file__).resolve().parent
CATALOG=HERE.parent/'graph/appearance_catalog.json'
SCRIPTS=HERE.parents[2]/'scripts/unreal'

def pairs(n): return n*(n-1)//2
def dump(name,obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    raw=CATALOG.read_bytes();data=json.loads(raw)
    domains=[];totals={};registered_ids=defaultdict(set);unique_pairs=defaultdict(set)
    star_cost=Counter(); current=[];preset_pairs={}
    for sex,families in data['families_by_sex'].items():
        summary=Counter();summary['families']=len(families)
        all_ids=set();optional_ids=set();native_shoe_ids=set()
        summary['presets']=len(data['presets_by_sex'][sex])
        summary['shared_shoes']=len(data['shared_shoes_by_sex'][sex])
        summary['hair_entries']=len(data['hairs_by_sex'][sex])
        for f in families:
            summary['locked_families']+=f['assembly_mode']=='locked_bundle'
            for g in f['groups']:
                summary['groups']+=1
                family_deny=f['hair_interface']['deny_all']
                required_deny=any((a.get('hair_interface') or {}).get('deny_all',False) for a in g['required_assets'])
                slots=[]
                all_assets=sum(g['slot_options'].values(),[])+g['required_assets']+g['optional_assets']
                all_ids.update(a['asset_id'] for a in all_assets)
                optional_ids.update(a['asset_id'] for a in g['optional_assets'])
                native_shoe_ids.update(a['asset_id'] for a in all_assets if a['slot']=='shoes')
                for slot,options in g['slot_options'].items():
                    optional=slot in g['optional_slots']
                    values=[o['asset_id'] for o in options]+(['none'] if optional else [])
                    allows=[not (family_deny or required_deny or (o.get('hair_interface') or {}).get('deny_all',False)) for o in options]+([not(family_deny or required_deny)] if optional else [])
                    n=len(values);sig={tuple(o['mesh_paths']) for o in options}
                    p=pairs(n)
                    row={'slot':slot,'registered_asset_values':len(options),'optional_none':optional,
                         'logical_values_including_none':n,'unordered_value_pairs_one_frozen_other_context':p,
                         'directed_value_pairs':2*p,'mesh_signature_count_not_material_or_visual_acceptance':len(sig),
                         'nonempty_hair_compatible_values_under_allowing_other_slots':sum(allows),
                         'nonempty_hair_compatible_pairs_under_allowing_other_slots':pairs(sum(allows)),
                         'registered_values':values}
                    slots.append(row)
                    if slot!='shoes':
                        registered_ids[sex].update(o['asset_id'] for o in options)
                        summary['core_slot_occurrences']+=1
                        summary['variable_core_slot_domains']+=n>1
                        summary['core_pair_sum_by_group_context']+=p
                        summary['core_registered_value_occurrences']+=len(options)
                        for a,b in itertools.combinations(values,2):
                            unique_pairs[sex].add((f['family_id'],slot,*sorted((a,b))))
                optional_assets=g['optional_assets']
                independent=g['optional_asset_policy']=='independent_subset'
                variable_core=[s for s in slots if s['slot']!='shoes' and s['logical_values_including_none']>1]
                summary['groups_with_core_slot_variation']+=bool(variable_core)
                summary['groups_with_no_core_slot_variation']+=not variable_core
                summary['optional_accessory_occurrences']+=len(optional_assets)
                summary['family_hair_deny_groups']+=family_deny
                policy=g['shared_shoe_policy']
                native=next((s for s in slots if s['slot']=='shoes'),None)
                if policy=='optional_universal_female_pool':
                    footwear_n=len(data['shared_shoes_by_sex'][sex])+1
                elif policy=='required_universal_female_pool':
                    footwear_n=len(data['shared_shoes_by_sex'][sex])
                elif policy=='forbidden_native_required':
                    footwear_n=native['logical_values_including_none'] if native else 1
                elif policy=='only_without_selected_native_shoes':
                    footwear_n=len(data['shared_shoes_by_sex'][sex])+1+(native['registered_asset_values'] if native else 0)
                else: raise ValueError(policy)
                summary['footwear_pair_sum_by_group_context']+=pairs(footwear_n)
                summary['variable_footwear_groups']+=footwear_n>1
                summary['shoe_policy_'+policy]+=1
                # One anchor + one-axis substitutions. No cross-product.
                star=1+sum(s['logical_values_including_none']-1 for s in variable_core)
                if variable_core:
                    star_cost[sex]+=star
                domains.append({'sex':sex,'family_id':f['family_id'],'family_label':f['label'],'group_id':g['group_id'],
                    'assembly_mode':f['assembly_mode'],'family_hair_deny':family_deny,'required_asset_hair_deny':required_deny,
                    'fixed_required_asset_count':len(g['required_assets']),'fixed_required_asset_slots':dict(Counter(a['slot'] for a in g['required_assets'])),
                    'slots':slots,'variable_core_slots':[s['slot'] for s in variable_core],
                    'core_pair_sum':sum(s['unordered_value_pairs_one_frozen_other_context'] for s in variable_core),
                    'optional_accessory_toggles_if_independent':len(optional_assets) if independent else None,
                    'optional_accessory_ids':[a['asset_id'] for a in optional_assets],
                    'footwear_policy':policy,'footwear_values_including_none_if_legal':footwear_n,
                    'footwear_unordered_pairs_one_frozen_context':pairs(footwear_n),
                    'core_star_nodes_one_frozen_visual_context':star if variable_core else 0,
                    'core_slot_variation_supported':bool(variable_core),
                    'not_cross_family_interchangeability':True})
        summary['unique_selectable_core_asset_ids']=len(registered_ids[sex])
        summary['unique_exposed_family_asset_ids_all_roles']=len(all_ids)
        summary['unique_optional_accessory_ids']=len(optional_ids)
        summary['unique_native_shoe_ids']=len(native_shoe_ids)
        summary['deduplicated_core_value_pairs_ignoring_repeated_groups']=len(unique_pairs[sex])
        totals[sex]=dict(summary)
        asset_slots={a['asset_id']:a['slot'] for f in families for g in f['groups'] for a in sum(g['slot_options'].values(),[])+g['required_assets']+g['optional_assets']}
        presets=data['presets_by_sex'][sex]
        footwear=lambda r:(('shared',r['choice']['shared_shoe_id']) if r['choice']['shared_shoe_id'] else
                            ('native',tuple(sorted(a for a in r['canonical_choice']['family_asset_ids'] if asset_slots[a]=='shoes'))))
        pc=Counter()
        for left,right in itertools.combinations(presets,2):
            a,b=left['choice'],right['choice'];same=(a['family_id'],a['group_id'])==(b['family_id'],b['group_id'])
            pc['all_unordered_preset_pairs']+=1
            pc['same_family_group_pairs']+=same
            pc['cross_family_or_group_pairs']+=not same
            pc['footwear_signature_differs']+=footwear(left)!=footwear(right)
            pc['hair_deny_policy_differs']+=left['hair_deny']!=right['hair_deny']
            changed=[k for k in a['slot_choices'].keys()|b['slot_choices'].keys() if a['slot_choices'].get(k)!=b['slot_choices'].get(k)]
            if same:
                core=[k for k in changed if k!='shoes']
                pc['same_group_at_least_two_core_slots_differ']+=len(core)>=2
                pc['same_group_exact_one_core_slot_other_selection_fixed']+=(len(changed)==1 and changed[0]!='shoes' and a['optional_asset_ids']==b['optional_asset_ids'] and footwear(left)==footwear(right) and left['hair_deny']==right['hair_deny'])
        pc['preset_rows_with_null_hair_id_not_proof_UI_clears_hair']=sum(r['choice']['hair_id'] is None for r in presets)
        preset_pairs[sex]=dict(pc)
        candidates=[]
        for preset in data['presets_by_sex'][sex]:
            if preset.get('hair_deny'):continue
            c=preset['choice'];f=next(f for f in families if f['family_id']==c['family_id'])
            if not f['hair_interface']['allow_all']:continue
            g=next(g for g in f['groups'] if g['group_id']==c['group_id'])
            for slot,opts in g['slot_options'].items():
                if slot=='shoes' or slot not in c['slot_choices']:continue
                opts=[o for o in opts if not (o.get('hair_interface') or {}).get('deny_all')]
                if len(opts)>1:candidates.append((len(opts),f['family_id'],g['group_id'],slot,opts))
        n,fam,group,slot,opts=max(candidates,key=lambda x:x[:4])
        current.append({'sex':sex,'family_id':fam,'group_id':group,'slot':slot,'values':n,'unordered_pairs':pairs(n),
                        'registered_ids':[o['asset_id'] for o in opts]})
    result={'status':'registered_interface_domains_not_visual_acceptance','catalog_sha256':hashlib.sha256(raw).hexdigest(),
            'formal_source_code_read':[str(SCRIPTS/x) for x in ['formal_wardrobe_registry_v1.py','complete_character_slot_review_contract_v1.py','appearance_selection_policy_v1.py','scene_site_appearance_v1.py']],
            'no_cartesian_product_enumeration':True,'pair_counts_are_one_axis_at_one_frozen_other_state_not_full_graph_edge_counts':True,
            'totals_by_sex':totals,'current_seven_axis_garment_domains':current,
            'finite_existing_preset_pair_diagnostics_not_cartesian_outfits':preset_pairs,
            'registered_core_star_nodes_by_sex_one_context_per_variable_group':dict(star_cost),
            'star_is_catalog_upper_budget_before_canonical_node_dedup_and_runtime_validation':True,
            'domains':domains}
    dump('wardrobe_domain_inventory.json',result)
    lines=['# 候选局部编辑域（注册接口计数）','','不代表跨族互换或视觉验收。值数含合法 optional none；不对其他属性做笛卡尔积。',
           '','| 性别 / family / group | 核心服装槽位值数 | 单槽无向值对合计 | 可选配饰开关 | 鞋值数 / 策略 | 头发限制 |',
           '| --- | --- | ---: | ---: | --- | --- |']
    for d in domains:
        sl=', '.join(s['slot']+':'+str(s['logical_values_including_none'])+('（含无）' if s['optional_none'] else '') for s in d['slots'] if s['slot']!='shoes') or 'locked core'
        lines.append('| '+ ' / '.join([d['sex'],d['family_id'],d['group_id']])+' | '+sl+' | '+str(d['core_pair_sum'])+' | '+str(d['optional_accessory_toggles_if_independent'])+' | '+str(d['footwear_values_including_none_if_legal'])+' / '+d['footwear_policy']+' | '+('禁用，固定 none/原色' if d['family_hair_deny'] else '当前 family 允许，仍看部件规则')+' |')
    (HERE/'DOMAIN_TABLE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'totals':totals,'current7':current,'star_budget':dict(star_cost)},ensure_ascii=True,indent=2))


if __name__=='__main__': main()
