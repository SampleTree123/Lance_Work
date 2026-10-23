"""Independent formal wardrobe frequency feasibility; no graph generation."""
import collections
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules
import normalize_catalog as nc

def main():
    rules=Rules(); rows={}; group_summary=[]
    for sex, data in rules.cat['sexes'].items():
        for family in data['families']:
            for group in family['groups']:
                base=nc.sample_choice(sex,random.Random(0),family_id=family['family_id'],group_id=group['group_id'])
                slots=[s for s in group['slot_options'] if s in nc.CORE_SLOTS]
                values=[[a['asset_id'] for a in group['slot_options'][s]]+([None] if s in group['optional_slots'] else []) for s in slots]
                optional=[a['asset_id'] for a in group['optional_assets'] if a['slot'] in nc.CORE_SLOTS]
                variants=0
                for choices in itertools.product(*values):
                    for flags in itertools.product((False,True),repeat=len(optional)):
                        w=copy.deepcopy(base)
                        w['slot_choices'].update(zip(slots,choices))
                        w['optional_asset_ids']=[a for a in w['optional_asset_ids'] if a not in optional]+[a for a,flag in zip(optional,flags) if flag]
                        w=nc.validate_choice(sex,w)['normalized_choice']
                        state={'sex':sex,'wardrobe':w}
                        c=rules.clothes(state)
                        for view, assets in [('full',c['core']),('upper',c['upper'])]:
                            if assets:
                                key=tuple(sorted(assets))
                                rows.setdefault(key,{'sex':sex,'family':family['family_id'],'group':group['group_id'],'visibility':view,'choice':w,'visible_core':list(key)})
                        variants+=1
                group_summary.append({'sex':sex,'family':family['family_id'],'group':group['group_id'],'assembly':family['assembly_mode'],'core_outfit_variants':variants,'core_slot_option_counts':{s:len(v) for s,v in zip(slots,values)},'required_core':[a['asset_id'] for a in group['required_assets'] if a['slot'] in nc.CORE_SLOTS]})
    rows=list(rows.values());assets=sorted(rules.pools['core_asset'])
    incidence={a:[i for i,row in enumerate(rows) if a in row['visible_core']] for a in assets}
    assert all(incidence.values())
    # Constructive nonnegative witness. This is not an LP infeasibility proof:
    # a successful saved witness disproves a universal fixed-binding conflict.
    weights=[1.0/len(rows)]*len(rows)
    count={}
    for epoch in range(4000):
        for a,indices in incidence.items():
            current=sum(weights[i] for i in indices)
            target=min(1.35,max(.65,current))
            if target!=current:
                multiplier=math.sqrt(target/current)
                for i in indices:weights[i]*=multiplier
        count={a:sum(weights[i] for i in indices) for a,indices in incidence.items()}
        mean=sum(count.values())/len(assets)
        weights=[w/mean for w in weights]
        count={a:sum(weights[i] for i in indices) for a,indices in incidence.items()}
        mean=sum(count.values())/len(assets)
        if min(count.values())>=.5*mean and max(count.values())<=1.5*mean:break
    passed=min(count.values())>=.5*mean and max(count.values())<=1.5*mean
    implications=[]
    for a in assets:
        always=set.intersection(*(set(rows[i]['visible_core']) for i in incidence[a]))-{a}
        if always:implications.append({'visible_asset':a,'always_co_visible':sorted(always)})
    result={'scope':'formal garment-domain continuous frequency feasibility only, not candidate graph/session acceptance',
        'formal_core_asset_count':len(assets),'visible_core_sets':len(rows),'enumerated_group_summary':group_summary,
        'witness_found':passed,'witness_iterations':epoch+1,'witness_mean':mean,'witness_min':min(count.values()),'witness_max':max(count.values()),
        'witness_counts':count,'fixed_binding_implications':implications,
        'conclusion':'A constructive mixture of legal full/upper outfits meets .5–1.5 of own global core mean; fixed bindings do not by themselves force an exception in this catalog.' if passed else 'No witness found by this bounded heuristic; this does not prove infeasibility.',
        'visibility':'front_head none; five upper cameras upper core; remaining cameras full core',
        'limitations':['continuous outfit mixture, not integer graph feasibility','no node budget or chain quotas','no site/action/camera availability intersection','fixed bundles remain resolved individual asset IDs, not one invented item'],
        'inputs':[{'path':str(Path(__file__).resolve()),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}]}
    (HERE/'wardrobe_binding_feasibility.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'wardrobe_binding_witness.json').write_text(json.dumps({'rows':[dict(row,weight=w) for row,w in zip(rows,weights)],'mean':mean,'counts':count},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['formal_core_asset_count','visible_core_sets','witness_found','witness_iterations','witness_mean','witness_min','witness_max','conclusion']},ensure_ascii=False))

if __name__=='__main__':main()
