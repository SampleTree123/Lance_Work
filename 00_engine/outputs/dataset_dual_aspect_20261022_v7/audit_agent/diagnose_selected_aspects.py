"""Actual per-aspect axis and formal single-slot diagnostics for saved chains."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from audit_dual_aspect import BASELINE, HERE, OUTPUTS, load_rules, pin, read, sessions


def main():
    source = OUTPUTS/'dataset_compact_graph_20261022_v6/audit_compact.py'
    spec = importlib.util.spec_from_file_location('_v6_selected_aspect_diagnostics', source)
    compact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compact)
    rules = load_rules()
    candidate = HERE.parent/'selected_candidate'
    result = {'schema': 'selected_fixed_aspect_actual_distribution_diagnostics_v1',
              'scope': 'Actual saved-chain events, formal wardrobe eligibility from source clothes/camera; no rendering',
              'graph_missing_support_is_descriptive_only_for_fixed_sessions': True,
              'inputs': [pin(__file__), pin(source)], 'splits': {}}
    for split in ('train', 'test'):
        root = candidate/split
        state = {r['id']: r['state'] for r in read(root/'nodes.json')}
        edge, ss = read(root/'edges.json'), sessions(root/'sessions.jsonl')
        oldstate = {r['id']: r['state'] for r in read(BASELINE/split/'nodes.json')}
        oldss, oldedges = sessions(BASELINE/split/'sessions.jsonl'), read(BASELINE/split/'edges.json')

        def summary(selected, states, edges):
            axes = Counter(st['axis'] for s in selected for st in s['steps'])
            mean = sum(axes[a] for a in compact.base.NONIDENTITY)/6
            deviation = {a: abs(axes[a]-mean)/mean for a in compact.base.NONIDENTITY}
            conditional, modes = Counter(), Counter()
            for s in selected:
                for st in s['steps']:
                    if st['axis'] != 'wardrobe':
                        continue
                    modes[st['mode']] += 1
                    if rules.singles(states[st['source']]):
                        conditional[st['mode']] += 1
            slot = compact.single_slot_diagnostic(states, edges, selected, rules)
            ex = [abs(v['relative_deviation_when_expected_positive']) for v in slot['slots'].values()
                  if v['relative_deviation_when_expected_positive'] is not None]
            starts = Counter(states[s['history'][0]]['camera'] for s in selected)
            sex = Counter(states[s['history'][0]]['sex'] for s in selected)
            return {'sessions': len(selected), 'edits': sum(axes.values()), 'axis_counts': dict(axes),
                    'six_nonidentity_relative_deviation': deviation, 'six_nonidentity_max_relative_deviation': max(deviation.values()),
                    'wardrobe_modes': dict(modes), 'formal_single_eligible_modes': dict(conditional),
                    'formal_single_eligible_single_fraction': conditional['single_piece']/sum(conditional.values()),
                    'single_slot_max_absolute_relative_deviation': max(ex), 'single_slot_diagnostic': slot,
                    'starting_camera_counts': dict(starts), 'starting_sex_counts': dict(sex)}

        overall = summary(ss, state, edge)
        baseline = summary(oldss, oldstate, oldedges)
        preserving = ('sessions','edits','axis_counts','wardrobe_modes','formal_single_eligible_modes',
                      'formal_single_eligible_single_fraction','starting_camera_counts','starting_sex_counts')
        invariants = {field: overall[field] == baseline[field] for field in preserving}
        invariants['actual_slot_counts_and_formal_expectations'] = all(
            overall['single_slot_diagnostic']['slots'][sl][field] == baseline['single_slot_diagnostic']['slots'][sl][field]
            for sl in compact.SLOTS for field in ('actual_single_edit_count','formal_conditional_expected_given_actual_single_events'))
        byaspect = {}
        for aspect in ('landscape', 'portrait'):
            selected = [s for s in ss if state[s['history'][0]]['aspect'] == aspect]
            st = {n: v for n, v in state.items() if v['aspect'] == aspect}
            ee = [e for e in edge if e['source'] in st]
            byaspect[aspect] = summary(selected, st, ee)
        result['splits'][split] = {'overall': overall, 'by_aspect': byaspect,
                                    'original_overall_event_invariants': invariants,
                                    'all_original_overall_event_invariants_preserved': all(invariants.values())}
        result['inputs'] += [pin(root/f) for f in ('nodes.json','edges.json','sessions.jsonl')]
        result['inputs'] += [pin(BASELINE/split/f) for f in ('nodes.json','edges.json','sessions.jsonl')]
    result['all_original_overall_event_invariants_preserved'] = all(s['all_original_overall_event_invariants_preserved'] for s in result['splits'].values())
    output = HERE/'selected_per_aspect_diagnostics.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'overall_preserved': result['all_original_overall_event_invariants_preserved'],
                      'splits': {split: {a: {k: values[k] for k in ('sessions','six_nonidentity_max_relative_deviation',
                                 'formal_single_eligible_single_fraction','single_slot_max_absolute_relative_deviation')}
                                          for a, values in report['by_aspect'].items()} for split, report in result['splits'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
