"""Inherited real target, start-quota and formal single-opportunity checks.

No legacy 5000/800 node cap is reinstated. Existing diagnostic functions remain
read-only and are called without modifying their source or module globals.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]
sys.path.insert(0,str(OUT/'dataset_compact_graph_20261022_v6'))
from audit_compact import start_camera_diagnostic,single_slot_diagnostic
from audit_candidate import Rules,ID_CAMERAS,audit_split as legacy_audit_split

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}

def legacy_semantics(root,split,rules=None):
    """Retain all old pure semantic checks; disclose only superseded cap errors."""
    result,_,_=legacy_audit_split(Path(root)/split,split,rules or Rules())
    old_errors=dict(result['error_counts'])
    current_errors={k:v for k,v in old_errors.items() if k!='node_budget'}
    result['legacy_error_counts_before_scope_adjustment']=old_errors
    result['scope_adjustment']={'node_budget':'old 5000/800 cap superseded by user-authorized actual cost reporting; no other legacy error excluded'}
    result['current_error_counts']=current_errors
    result['passed_current_inherited_semantics']=not current_errors
    return result

def audit_split(root,split,rules=None):
    rules=rules or Rules();path=Path(root)/split
    states={r['id']:r['state'] for r in read(path/'nodes.json')};edges=read(path/'edges.json')
    sessions=[json.loads(s) for s in (path/'sessions.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    target={axis:collections.Counter() for axis in rules.pools};gained=collections.Counter();gained_by_mode=collections.defaultdict(collections.Counter)
    conditional=collections.Counter();whole_only=collections.Counter();modes=collections.Counter();error=collections.Counter()
    for chain in sessions:
        for step in chain['steps']:
            s,t=states[step['source']],states[step['target']];axis=step['axis']
            try:
                formal=rules.edge(s,t)
                if formal['axis']!=axis:error['step_axis_mismatch']+=1
            except Exception:error['illegal_atomic_edge']+=1;continue
            if axis!='wardrobe':target[axis][t[axis]]+=1;continue
            w=t['wardrobe'];tc=set(rules.clothes(t)['core']);sc=set(rules.clothes(s)['core'])
            target['family'][w['family_id']]+=1;target['group'][w['family_id']+'/'+w['group_id']]+=1;target['core_asset'].update(tc)
            introduced=tc-sc;gained.update(introduced);gained_by_mode[formal['mode']].update(introduced);modes[formal['mode']]+=1
            if rules.singles(s):conditional[formal['mode']]+=1
            else:whole_only[formal['mode']]+=1
    target_report={axis:{'distinct':len(counts),'expected':len(rules.pools[axis]),'missing':sorted(rules.pools[axis]-set(counts)),'counts':dict(counts)} for axis,counts in target.items()}
    missing_core=sorted(rules.pools['core_asset']-set(gained))
    actual_target_pass=all(not row['missing'] for axis,row in target_report.items() if axis!='core_asset') and not missing_core
    cameras=[r if isinstance(r,str) else r['id'] for r in rules.cat['cameras']]
    weights={c:1.5 if c in ID_CAMERAS else 1 for c in cameras};total=12000 if split=='train' else 2400
    exact={c:total*weights[c]/sum(weights.values()) for c in cameras};quota={c:math.floor(exact[c]) for c in cameras}
    tie_order=sorted(cameras,key=lambda c:-(exact[c]-quota[c]))
    for c in tie_order[:total-sum(quota.values())]:quota[c]+=1
    actual=collections.Counter(states[c['history'][0]]['camera'] for c in sessions)
    mismatches={c:{'expected':quota[c],'actual':actual[c]} for c in cameras if quota[c]!=actual[c]}
    start=start_camera_diagnostic(states,sessions,rules)
    slots=single_slot_diagnostic(states,edges,sessions,rules)
    # Formal denominator is recomputed independently from each source state;
    # no graph adjacency or saved 'eligible' count defines legality.
    eligible=sum(conditional.values());single=conditional['single_piece']
    return {'split':split,'inputs':[pin(path/f) for f in ('nodes.json','edges.json','sessions.jsonl')],
        'edited_axis_actual_target_value_coverage':target_report,
        'genuinely_introduced_core':{'distinct':len(gained),'expected':len(rules.pools['core_asset']),'missing':missing_core,'counts':dict(gained),'counts_by_mode':{k:dict(v) for k,v in gained_by_mode.items()}},
        'training_actual_target_full_coverage_required':split=='train','actual_target_full_coverage_diagnostic':actual_target_pass,
        'actual_target_full_coverage_passed_when_required':actual_target_pass if split=='train' else True,
        'initial_camera_integer_quota':{'weights':weights,'expected':quota,'actual':dict(actual),'rounding':'largest remainder; stable approved camera catalog order breaks ties','mismatches':mismatches,'passed':not mismatches},
        'start_camera_legacy_diagnostic':start,'single_slot_legacy_diagnostic':slots,
        'wardrobe_formal_opportunity':{'all_modes':dict(modes),'formal_single_eligible_modes':dict(conditional),'formal_whole_only_modes':dict(whole_only),'conditional_single_fraction':single/eligible if eligible else None,'target_single_given_formal_eligibility':.5,'whole_only_sources_excluded_from_conditional_denominator':True,'conditional_50_50_is_reported_approximately_not_new_exact_count_gate':True},
        'error_counts':dict(error),'no_legacy_node_budget_reinstated':True,
        'passed_inherited_required_checks':not error and (actual_target_pass if split=='train' else True) and not mismatches and not slots['illegal_chosen_slot_count']}

def audit(candidate,output):
    rules=Rules();report={'schema':'independent_inherited_target_start_slot_checks_v10','candidate':str(Path(candidate).resolve()),
        'scope':'inherits v6 real edited targets, exact weighted starts and formal single opportunities; no new fixed single-slot percentage gate; no media acceptance',
        'implementation_inputs':[pin(Path(__file__)),pin(OUT/'dataset_compact_graph_20261022_v6/audit_compact.py'),pin(OUT/'dataset_balanced_graph_20261022_v5/audit_candidate.py'),pin(OUT/'dataset_trial_build_20261021_v1/catalog.json')],
        'splits':{s:audit_split(candidate,s,rules) for s in ('train','test')}}
    report['legacy_pure_semantic_audit']={s:legacy_semantics(candidate,s,rules) for s in ('train','test')}
    report['passed']=all(s['passed_inherited_required_checks'] for s in report['splits'].values()) and all(s['passed_current_inherited_semantics'] for s in report['legacy_pure_semantic_audit'].values())
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'splits':{s:{'actual_target_check':r['actual_target_full_coverage_passed_when_required'],'introduced_core':r['genuinely_introduced_core']['distinct'],'start_quota':r['initial_camera_integer_quota']['passed'],'conditional_single_fraction':r['wardrobe_formal_opportunity']['conditional_single_fraction'],'slot_TV':r['single_slot_legacy_diagnostic']['conditional_actual_vs_expected_total_variation']} for s,r in report['splits'].items()}}))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,default=HERE/'inherited_contract_audit.json');args=p.parse_args();audit(args.candidate,args.output)
