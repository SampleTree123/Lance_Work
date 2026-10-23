"""Bounded current-domain checks for this offline trial export."""
import collections
import copy
import json
import random
from pathlib import Path
import normalize_catalog as n


def main():
    data=n.load_catalog()
    rng=random.Random(20261021)
    counts=collections.Counter()
    barefoot=[]
    required_shared=[]
    ids_by_sex={}
    for sex,pool in data['sexes'].items():
        ids_by_sex[sex]={h['hair_id'] for h in pool['hairs']}
        for family in pool['families']:
            assert family['family_id']!='male.rugged_trendy'
            for group in family['groups']:
                counts['groups']+=1
                policy=group['shoe_rules']
                if policy['shared_required']:
                    required_shared.append([sex,family['family_id'],group['group_id']])
                if policy['barefoot_allowed_when_no_native_selected']:
                    barefoot.append([sex,family['family_id'],group['group_id']])
                for lock in group['lock_presets']:
                    result=n.validate_choice(sex,lock)
                    assert set(result['selected_family_asset_ids'])==set(group['lock_required_asset_ids'])
                    assert not lock['slot_choices']
                    assert n.single_piece_neighbors(sex,lock)==[]
                    counts['locks_checked']+=1
                for hair in pool['hairs']:
                    choice=n.sample_choice(sex,rng,family_id=family['family_id'],
                                           group_id=group['group_id'],hair_id=hair['hair_id'])
                    resolution=n.validate_choice(sex,choice)
                    assert resolution['resolved_hair_id']==hair['hair_id']
                    assert resolution['hair_deny'] is False
                    counts['hair_group_samples_validated']+=1
                    native=[r for r in resolution['assignments'] if r['slot']=='shoes']
                    if choice['shared_shoe_id']:
                        assert set(r['source_component_name'] for r in native)=={choice['shared_shoe_id']}
                    if policy['shared_required']:
                        assert choice['shared_shoe_id']
                    old_ids=n.wardrobe_key(sex,choice)
                    for edge in n.single_piece_neighbors(sex,choice):
                        target=edge['choice']
                        assert target['family_id']==choice['family_id']
                        assert target['group_id']==choice['group_id']
                        assert target['shared_shoe_id']==choice['shared_shoe_id']
                        assert target['optional_asset_ids']==choice['optional_asset_ids']
                        assert target['hair_id']==choice['hair_id']
                        changed=[s for s in choice['slot_choices'] if
                                 choice['slot_choices'][s]!=target['slot_choices'][s]]
                        assert changed==[edge['slot']] and edge['slot'] in n.CORE_SLOTS
                        assert n.wardrobe_key(sex,target)!=old_ids
                        counts['single_piece_edges_validated']+=1
                    whole=n.sample_whole_change(sex,choice,rng,require_upper_change=True)
                    assert whole['family_id']!=choice['family_id']
                    assert n.core_asset_ids(sex,whole)!=n.core_asset_ids(sex,choice)
                    assert n.upper_asset_ids(sex,whole)!=n.upper_asset_ids(sex,choice)
                    assert whole['hair_id']==choice['hair_id']
                    counts['whole_transitions_validated']+=1
                # Test exact conditional shared shoe domains through formal
                # validation, with empty optional assets/native optional shoe.
                c=n.sample_choice(sex,rng,family_id=family['family_id'],group_id=group['group_id'])
                c['optional_asset_ids']=[]
                if 'shoes' in group['optional_slots']:
                    c['slot_choices']['shoes']=None
                options=n._footwear_options(sex,family,group,c)
                for shoe in options:
                    v=copy.deepcopy(c);v['shared_shoe_id']=shoe
                    n.validate_choice(sex,v)
                    counts['conditional_shoe_states_validated']+=1
                if policy['shared_required']:
                    invalid=copy.deepcopy(c);invalid['shared_shoe_id']=None
                    try:n.validate_choice(sex,invalid)
                    except ValueError:counts['required_shoe_omissions_rejected']+=1
                    else:raise AssertionError('Required shared shoe accepted as barefoot')
    assert len(data['sites'])==21 and len(data['actions'])==25 and len(data['cameras'])==21
    assert len(data['exclusions'])==1428
    assert all(e['action_id']!='MOTION_CAND_007' for e in data['exclusions'])
    # Check current selected object-path mappings actually name local files,
    # including the corrected pink coat and current character revision.
    objects=set()
    def walk(x):
        if isinstance(x,dict):
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
        elif isinstance(x,str) and x.startswith('/Game/') and '.' in x:
            objects.add(x)
    for pool in data['sexes'].values():
        walk(pool['identities']);walk(pool['hairs']);walk(pool['families']);walk(pool['shared_shoes'])
    missing=[obj for obj in sorted(objects) if not
             (Path('D:/UE/projects/datatry_02/Content')/(obj.split('.')[0][6:]+'.uasset')).is_file()]
    assert not missing,missing
    report={'success':True,'counts':dict(counts),
            'direct_selectable_object_paths_exist':len(objects),
            'hair_overlap_ids':sorted(ids_by_sex['female'] & ids_by_sex['male']),
            'hair_none_formally_legal_but_not_a_trial_candidate':True,
            'barefoot_allowed_groups_when_no_native_selected':barefoot,
            'required_shared_shoe_groups':required_shared,
            'scope':'finite group/hair/shoe checks; sampled outfits; not exhaustive Cartesian or visual acceptance'}
    (n.HERE/'catalog_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in
                      ('barefoot_allowed_groups_when_no_native_selected','required_shared_shoe_groups')},ensure_ascii=True))


if __name__=='__main__':main()
