"""Checks logical fixtures, not visual observability or generated video quality."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'semantic_counterexamples.json').read_text(encoding='utf-8'))
cases={c['id']:c for c in data['cases']}
checks=[]
def edit(state, command): return {**state,command['axis']:command['value']}

c=cases['history_needed_despite_identical_current_input']
assert c['left_history'][-1]==c['right_history'][-1]
assert edit(c['left_history'][0],c['edit'])==c['left_target']
assert edit(c['right_history'][0],c['edit'])==c['right_target']
assert c['left_target']!=c['right_target']
checks.append(c['id'])
c=cases['full_history_still_insufficient_when_projection_hides_difference']
project=lambda history:[{k:s[k] for k in c['visible_fields_in_all_history_media']} for s in history]
assert project(c['left_history'])==project(c['right_history'])
assert edit(c['left_history'][0],c['edit'])!=edit(c['right_history'][0],c['edit'])
checks.append(c['id'])
c=cases['latest_filter_does_not_remove_other_edit_conditional_aliases']
assert [i for i,s in enumerate(c['history']) if edit(s,c['edit'])==c['target']]==c['result_equivalent_sources']
assert edit(c['history'][-1],c['edit'])!=c['target']
checks.append(c['id'])
c=cases['partial_attribute_restore_is_not_full_historical_fork']
assert {**c['history'][-1],'outfit':c['history'][0]['outfit']}==c['expected_target']
assert c['history'][0]!=c['expected_target']
checks.append(c['id'])
c=cases['rollout_nominal_gt_conflicts_with_actual_source_preservation']
assert edit(c['actual_generated_parent'],c['edit'])==c['faithful_to_visible_parent']
assert edit(c['nominal_parent'],c['edit'])==c['nominal_gt_target']
assert c['faithful_to_visible_parent']!=c['nominal_gt_target']
checks.append(c['id'])
c=cases['ambiguous_visual_reference_has_multiple_admissible_targets']
assert all(s['outfit']=='blue' for s in c['history'])
assert edit(c['history'][0],c['edit'])!=edit(c['history'][1],c['edit'])
checks.append(c['id'])
(HERE/'semantic_self_check.json').write_text(json.dumps({'status':'pass','scope':'symbolic_logic_only','checks':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: 6 symbolic counterexamples; no image/video performance claim.')
