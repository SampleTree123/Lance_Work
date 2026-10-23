"""Finite exact-count geometry analysis; no external solver or model needed.

Counterfactual policies are hypothetical quotas, not a successful graph resample.
The small grid search is only over declared late-fork schedules and 5% masses.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def compositions(n,k):
    if k==1:
        yield (n,)
    else:
        for i in range(n+1):
            for rest in compositions(n-i,k-1): yield (i,)+rest

def analyze_schedule(name, cells):
    # cells contain (edit length, fork round, number of 5%-mass blocks).
    # At round t, allowed nonlatest occurrence slots are 0,...,t-2.
    best=None; best_assignment=None
    for assignment in itertools.product(*(list(compositions(m,t-1)) for _,t,m in cells)):
        if sum(row[0] for row in assignment)!=8: continue # exact global root40%.
        counts=defaultdict(Counter)
        for (_,t,_),row in zip(cells,assignment):
            for parent,n in enumerate(row): counts[t][parent]+=n
        correct=sum(max(row.values()) for row in counts.values())
        if best is None or correct<best:
            best=correct;best_assignment=assignment
    assert best is not None
    parent_sizes=Counter();followup=0
    for length,t,m in cells:
        parent_sizes[t-1]+=m*50
        followup+=m*50*(t<length)
    chance=sum(Fraction(n,k) for k,n in parent_sizes.items())/1000
    return {'name':name,'scope':'late_position_schedules_only_not_all_sampler_or_visual_constraints',
            'fork_count':1000,'root_count':400,'followup_count':followup,
            'nonlatest_history_slot_count_histogram':dict(parent_sizes),
            'uniform_slot_choice_expected_accuracy':float(chance),
            'grid_step_mass':0.05,'best_round_only_prior_accuracy_on_this_grid':best/20,
            'one_feasible_parent_assignment':[{'length':length,'fork_round':t,
                'parent_counts':{str(p):n*50 for p,n in enumerate(row)}}
                for (length,t,m),row in zip(cells,best_assignment)]}

def main():
    comparison=json.loads((HERE/'source_balance_comparison.json').read_text(encoding='utf-8'))
    observed={}
    for name,row in comparison.items():
        if 'test_statistics' not in row: continue
        byround=row['test_statistics']['fork_source_parent_counts_by_round']
        slot_counts={str(int(t)-1):sum(counts.values()) for t,counts in byround.items()}
        total=sum(slot_counts.values()); forced=slot_counts.get('1',0)
        chance=sum(Fraction(n,int(k)) for k,n in slot_counts.items())/total
        baseline=row['test_policies']['oracle_fork_flag_then_train_turn_index']['source_exact_forks']
        observed[name]={'fork_count':total,'nonlatest_history_slot_count_histogram':slot_counts,
            'uniform_slot_choice_expected_accuracy':float(chance),
            'one_slot_source_selection_questions':forced,'two_or_more_slot_questions':total-forced,
            'train_round_prior_accuracy_on_two_or_more_slots':(baseline-forced)/(total-forced),
            'round_prior_accuracy_all_forks':baseline/total}
    schedules=[
        analyze_schedule('all_followup_and_latest_eligible_positions',[(3,2,4),(4,3,8),(5,4,8)]),
        analyze_schedule('half_L3_terminal_10percent_of_all_forks',[(3,2,2),(3,3,2),(4,3,8),(5,4,8)]),
        analyze_schedule('all_L3_terminal_20percent_of_all_forks',[(3,3,4),(4,3,8),(5,4,8)]),
        analyze_schedule('all_terminal_loses_followup_control',[(3,3,4),(4,4,8),(5,5,8)])]
    result={'kind':'source_choice_geometry_not_model_accuracy','observed':observed,'hypothetical_schedules':schedules,
            'all_schedules_preserve_length_20_40_40_and_global_root40_nonroot60':True,
            'requires_graph_capacity_and_visibility_check_before_adopting_schedule':True}
    (HERE/'branch_geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
