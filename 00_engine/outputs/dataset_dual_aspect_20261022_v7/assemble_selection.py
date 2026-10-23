"""Freeze the selected assignments, materialize render variants, and replan references."""
from pathlib import Path
import json, shutil, sys
from materialize import ROOT, SOURCE, build, read, write, pin

def main():
    assignments=ROOT/'selected_assignment'
    if assignments.exists(): raise FileExistsError(assignments)
    assignments.mkdir()
    sources={'train':ROOT/'partition_agent/economy/train',
             'test':ROOT/'partition_agent/axis_balanced/test'}
    for split,src in sources.items():
        dest=assignments/split;dest.mkdir()
        for f in ('assignment.jsonl','stats.json','method.json','node_requirements.json'):
            if (src/f).exists(): shutil.copyfile(src/f,dest/f)
    policy={'initial_policy':'economy shared-node hypergraph partition',
        'refinement_trigger':'either aspect has six-nonidentity-axis deviation above 10% of its own six-axis mean',
        'refinement_policy':'retain original chains; rebalance aspect allocation of edit axes with soft camera coverage/cost constraints',
        'train_triggered':False,'test_triggered':True,
        'ratio_bounds_are_working_targets_not_new_user_hard_rules':True}
    write(assignments/'SOURCES.json',{'source_assignments':{s:pin(p/'assignment.jsonl') for s,p in sources.items()},'policy':policy})
    candidate=ROOT/'selected_candidate'
    counts=build(assignments,candidate)
    rules=read(SOURCE.parents[0]/'RULES.json')
    rules['schema_version']=7;rules['rule_set_id']=ROOT.name
    rules['status']='dual_aspect_offline_candidate_pending_user_adoption_not_rendered'
    rules['scope']['document']='PLAN.md; execution evidence REPORT.md and CURRENT_CANDIDATE.json'
    for split in ('train','test'):
        budget=rules['budgets'][split]
        budget['previous_main_canonical_nodes_max']=budget['main_canonical_nodes_max']
        budget['main_canonical_nodes_max']=None
        budget['user_authorized_moderate_increase_for_dual_aspect']=True
    rules['split']['disjoint_key']='complete_canonical_content_state_excluding_aspect'
    rules['aspect_policy']={'values':['landscape','portrait'],'fixed_for_entire_history_and_forks':True,
        'is_edit_axis':False,'chain_counts_approximately_balanced':True,
        'exact_half_required':False,'render_versions_count_against_main_budget':True,
        'content_configuration_not_counted_twice_as_new_content':True,
        'same_content_across_train_test_even_with_different_aspect_forbidden':True,
        'per_aspect_full_value_coverage_required':False,
        'each_aspect_has_both_sexes_all_start_cameras_all_edit_axes':True,
        'selection_policy':policy}
    rules['unfrozen']=[x for x in rules['unfrozen'] if x!='aspect']
    rules['actual_implementation']={'source':str(SOURCE),'candidate':str(candidate),
        'all_original_sessions_preserved_exactly_once':True,'counts':counts,
        'new_sampler_invoked_for_selected_candidate':False,'selected_assignments':str(assignments),
        'camera_trajectory_template_not_final_world_trajectory':True}
    rules['stability']={'baseline':'v6 same-graph sampling checked with three seeds',
        'this_candidate':'deterministic aspect assignment of unchanged selected_seed1 sessions; no new structural sampling claim',
        'assignment_trials':'partition_agent/summary.json'}
    rules['optimization']={'baseline':str(SOURCE),'baseline_render_nodes':{'train':3752,'test':800},
        'scope':'aspect allocation; preserve original structural samples',
        'selected_policy':policy,'retained_v6_sampling_parameters':True}
    rules['inherited_rule_snapshot']=str(SOURCE.parent/'RULES.json')
    write(ROOT/'RULES.json',rules)
    sys.path.insert(0,str(ROOT.parent/'dataset_trial_build_20261021_v1'))
    from plan_references import Planner
    planner=Planner(candidate,20261022)
    planner.rules=rules
    planner.inputs.append(pin(ROOT/'RULES.json'))
    ref_summary=planner.run()
    # The shared v1 writer describes aspect as unfrozen; the wrapper records the current frozen context.
    doc=candidate/'REFERENCES.md'
    text=doc.read_text(encoding='utf-8').replace('分辨率、帧率、时长、画幅，','分辨率、帧率、时长，')
    text+='\n本候选已确定横屏/竖屏两种上下文，每条链固定一种；具体像素尺寸未冻结。动作和背景参考需求已按实际目标画幅重算，不复用旧横屏需求ID冒充竖屏。\n'
    doc.write_text(text,encoding='utf-8')
    write(ROOT/'CURRENT_CANDIDATE.json',{'status':rules['status'],'candidate':str(candidate),
        'source_v6_content_and_chains':str(SOURCE),'rules':str(ROOT/'RULES.json'),
        'render_nodes':{s:counts[s]['render_nodes'] for s in counts},
        'content_nodes':{s:counts[s]['content_nodes'] for s in counts},
        'chains':{s:counts[s]['chain_count'] for s in counts},
        'structural_chains_duplicated_for_aspect':False,'rendered':False,
        'independent_audit':str(ROOT/'audit_agent/audit_selected.json'),
        'references':str(candidate/'reference_manifest.json'),
        'cheaper_trial_not_selected':'resample_agent/REPORT.md'})
    print(json.dumps({'counts':counts,'reference_summary':ref_summary},ensure_ascii=False))

if __name__=='__main__':main()
