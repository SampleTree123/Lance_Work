"""Independent, bounded validation of offline trial nodes, edges and sessions.

Reuses the current formal garment resolver via normalize_catalog, but never
imports build_trial or its edge oracle. Does not call UE or validate pixels.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
import normalize_catalog as nc

HERE = Path(__file__).resolve().parent
AXES = ('identity', 'hair', 'hair_color', 'wardrobe', 'action', 'camera', 'site')
IDENTITY_CAMERAS = {'front_head', 'front_upper', 'dolly_in_front', 'dolly_out_front'}
UPPER_CAMERAS = {'front_upper', 'side_upper', 'back_upper',
                 'front_three_quarter_upper', 'rear_three_quarter_upper'}
CORE_SLOTS = {'shirts', 'coats', 'pants', 'skirts', 'full_body'}
UPPER_SLOTS = {'shirts', 'coats', 'full_body'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def serial(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Verification:
    def __init__(self):
        self.catalog = nc.load_catalog()
        self.rules = read(HERE / 'rules.json')
        self.errors = Counter()
        self.examples = defaultdict(list)
        self.counts = Counter()
        self.ids = {sex: {r['id'] for r in pool['identities']}
                    for sex, pool in self.catalog['sexes'].items()}
        self.hairs = {sex: {r['hair_id'] for r in pool['hairs']}
                      for sex, pool in self.catalog['sexes'].items()}
        self.pools = {axis: {r['id'] if isinstance(r, dict) else r
                            for r in self.catalog[plural]}
                      for axis, plural in [('action', 'actions'), ('camera', 'cameras'), ('site', 'sites')]}
        self.colors = set(self.rules['edit_sampling']['color']['values'])
        self.excluded = {(r.get('site_id', r.get('site')), r['action_id'],
                          r['camera_id'], r.get('aspect', 'landscape'))
                         for r in self.catalog['exclusions']}
        self.groups = {(sex, family['family_id'], group['group_id']): (family, group)
                       for sex, pool in self.catalog['sexes'].items()
                       for family in pool['families'] for group in family['groups']}
        self.assets = {}
        for sex, pool in self.catalog['sexes'].items():
            for family in pool['families']:
                for group in family['groups']:
                    rows = group['required_assets'] + group['optional_assets']
                    rows += [row for values in group['slot_options'].values() for row in values]
                    for row in rows:
                        self.assets[sex, row['asset_id']] = row

    def check(self, condition, category, context):
        if condition:
            self.counts[category] += 1
        else:
            self.errors[category] += 1
            if len(self.examples[category]) < 5:
                self.examples[category].append(context)
        return bool(condition)

    def legal_scene(self, state):
        return (state['site'], state['action'], state['camera'], state['aspect']) not in self.excluded

    @lru_cache(maxsize=None)
    def resolved(self, sex, choice_json, hair):
        choice = json.loads(choice_json)
        # The builder stores the actual hair separately. Inject it into the
        # formal resolver so a clothing/hair incompatibility cannot pass via None.
        choice['hair_id'] = hair
        result = nc.validate_choice(sex, choice)
        family_ids = result['selected_family_asset_ids']
        assets = tuple(sorted(family_ids + ([result['shared_shoe_id']]
                                            if result['shared_shoe_id'] else [])))
        core = tuple(sorted(i for i in family_ids if self.assets[sex, i]['slot'] in CORE_SLOTS))
        upper = tuple(sorted(i for i in family_ids if self.assets[sex, i]['slot'] in UPPER_SLOTS))
        shoes = tuple(sorted(i for i in family_ids if self.assets[sex, i]['slot'] == 'shoes'))
        if result['shared_shoe_id']:
            shoes += (result['shared_shoe_id'],)
        return {'assets': assets, 'core': core, 'upper': upper, 'shoes': shoes,
                'normalized': result['normalized_choice'],
                'hair_deny': result['hair_deny'], 'hair': result['resolved_hair_id']}

    def wardrobe(self, state):
        return self.resolved(state['sex'], serial(state['wardrobe']), state['hair'])

    def canonical(self, state):
        # Include sex, aspect and every other state field. Family/group aliases
        # are replaced by physical selected garments and shoes.
        result = copy.deepcopy(state)
        result['wardrobe'] = self.wardrobe(state)['assets']
        return serial(result)

    def check_node(self, node, split):
        state = node['state']
        context = [split, node['id']]
        sex = state['sex']
        if not self.check(sex in self.ids, 'node_sex', context):
            return None
        self.check(state['identity'] in self.ids[sex], 'node_identity_same_sex', context)
        self.check(state['hair'] in self.hairs[sex], 'node_hair_same_sex', context)
        self.check(state['hair_color'] in self.colors, 'node_color', context)
        for axis, pool in self.pools.items():
            self.check(state[axis] in pool, 'node_' + axis, context)
        self.check(state['aspect'] in self.catalog['aspects'], 'node_symbolic_aspect', context)
        self.check(self.legal_scene(state), 'node_saved_exclusions', context)
        self.check(state['wardrobe']['family_id'] != 'male.rugged_trendy', 'node_no_rugged', context)
        try:
            resolved = self.wardrobe(state)
            self.check(not resolved['hair_deny'] and resolved['hair'] == state['hair'],
                       'node_formal_hair_wardrobe', context)
            self.check(bool(resolved['core']), 'node_clothed_core', context)
            self.check(state['wardrobe'].get('hair_id') in (None, state['hair']),
                       'node_embedded_hair_not_conflicting', context)
            self.counts['node_formal_wardrobe_resolution'] += 1
            return self.canonical(state)
        except Exception as exc:
            self.check(False, 'node_formal_wardrobe_resolution', [*context, str(exc)])
            return None

    def check_edge(self, edge, states, split, label='registered'):
        u, v = edge['source'], edge['target']
        context = [split, label, u, v]
        if not self.check(u in states and v in states, 'edge_endpoints', context):
            return
        source, target = states[u], states[v]
        axis = edge['axis']
        self.check(source['sex'] == target['sex'], 'edge_same_sex', context)
        self.check(source['aspect'] == target['aspect'], 'edge_same_symbolic_aspect', context)
        source_w, target_w = self.wardrobe(source), self.wardrobe(target)
        changed = [a for a in AXES if (source_w['assets'] != target_w['assets'] if a == 'wardrobe'
                                     else source[a] != target[a])]
        self.check(changed == [axis], 'edge_exactly_declared_semantic_axis', [*context, changed, axis])
        extras = set(source) | set(target)
        self.check(all(source.get(a) == target.get(a) for a in extras - set(AXES)),
                   'edge_inherit_nonaxis_state', context)
        self.check(self.legal_scene(target), 'edge_target_saved_exclusions', context)
        if axis == 'identity':
            self.check(source['camera'] in IDENTITY_CAMERAS, 'edge_identity_camera', context)
        if axis == 'action':
            self.check(source['camera'] != 'front_head', 'edge_action_camera', context)
        if axis != 'wardrobe':
            self.check(edge.get('mode') == 'attribute', 'edge_attribute_mode', context)
            return
        self.check(source['camera'] != 'front_head', 'edge_wardrobe_not_head', context)
        self.check(source_w['core'] != target_w['core'], 'edge_wardrobe_not_shoe_only', context)
        if source['camera'] in UPPER_CAMERAS:
            self.check(source_w['upper'] != target_w['upper'], 'edge_wardrobe_visible_upper_change', context)
        sw, tw = source_w['normalized'], target_w['normalized']
        if edge.get('mode') == 'whole_outfit':
            self.check(sw['family_id'] != tw['family_id'], 'edge_whole_other_family', context)
        elif edge.get('mode') == 'single_piece':
            self.check(sw['family_id'] == tw['family_id'] and sw['group_id'] == tw['group_id'],
                       'edge_single_same_family_group', context)
            keys = set(sw['slot_choices']) | set(tw['slot_choices'])
            changed_slots = [k for k in sorted(keys)
                             if sw['slot_choices'].get(k) != tw['slot_choices'].get(k)]
            self.check(len(changed_slots) == 1 and changed_slots[0] in CORE_SLOTS
                       and changed_slots[0] == edge.get('slot'), 'edge_single_exact_core_slot',
                       [*context, changed_slots, edge.get('slot')])
            self.check(source_w['shoes'] == target_w['shoes'], 'edge_single_preserve_actual_shoes', context)
            self.check(all(sw.get(k) == tw.get(k) for k in set(sw) | set(tw)
                           if k != 'slot_choices'), 'edge_single_preserve_noncore_choice', context)
            if source['camera'] in UPPER_CAMERAS:
                self.check(edge.get('slot') in UPPER_SLOTS, 'edge_single_visible_slot', context)
        else:
            self.check(False, 'edge_wardrobe_known_mode', [*context, edge.get('mode')])

    @lru_cache(maxsize=None)
    def single_available(self, sex, choice_json, hair, upper):
        resolved = self.resolved(sex, choice_json, hair)
        choice = resolved['normalized']
        family, group = self.groups[sex, choice['family_id'], choice['group_id']]
        if family['assembly_mode'] == 'locked_bundle':
            return False
        for slot, rows in group['slot_options'].items():
            if slot not in (UPPER_SLOTS if upper else CORE_SLOTS):
                continue
            values = [r['asset_id'] for r in rows]
            if slot in group['optional_slots']:
                values.append(None)
            for value in values:
                if value == choice['slot_choices'].get(slot):
                    continue
                target = copy.deepcopy(choice)
                target['slot_choices'][slot] = value
                try:
                    other = self.resolved(sex, serial(target), hair)
                    if (not other['hair_deny'] and other['core'] != resolved['core']
                            and other['shoes'] == resolved['shoes']
                            and (not upper or other['upper'] != resolved['upper'])):
                        return True
                except ValueError:
                    pass
        return False

    def formal_axes(self, state):
        axes = set()
        if state['camera'] in IDENTITY_CAMERAS and len(self.ids[state['sex']]) > 1:
            axes.add('identity')
        if len(self.hairs[state['sex']]) > 1:
            axes.add('hair')
        if len(self.colors) > 1:
            axes.add('hair_color')
        for axis, pool in self.pools.items():
            if axis == 'action' and state['camera'] == 'front_head':
                continue
            if any(value != state[axis] and self.legal_scene(dict(state, **{axis: value}))
                   for value in pool):
                axes.add(axis)
        # The current catalog has many other-family visible-upper alternatives.
        # Whole target enumeration is deliberately not a Cartesian full audit.
        if state['camera'] != 'front_head':
            axes.add('wardrobe')
        return axes

    @staticmethod
    def quota_counts(total):
        forks = total // 3
        result = {}
        for kind, count, weights in [('linear', total - forks, [.25] * 4),
                                     ('fork', forks, [.1, .2, .35, .35])]:
            values = [round(count * p) for p in weights]
            values[-1] += count - sum(values)
            result.update({f'{kind}_{length}': n for length, n in zip(range(2, 6), values)})
        return result

    def verify_split(self, root, split, full):
        directory = root / split
        nodes = read(directory / 'nodes.json')
        edges = read(directory / 'edges.json')
        sessions = [json.loads(line) for line in (directory / 'sessions.jsonl').read_text(encoding='utf-8').splitlines() if line]
        states, canonical, registered, adjacency = {}, {}, {}, defaultdict(lambda: defaultdict(list))
        seen_keys, seen_canonical_ids = set(), set()
        for node in nodes:
            nid = node['id']
            self.check(nid not in states, 'node_unique_local_id', [split, nid])
            states[nid] = node['state']
            key = self.check_node(node, split)
            if key is not None:
                self.check(key not in seen_keys, 'node_canonical_state_dedup', [split, nid])
                seen_keys.add(key)
                canonical[nid] = key
            cid = node.get('canonical_id')
            self.check(cid and cid not in seen_canonical_ids, 'node_canonical_id_unique', [split, nid, cid])
            seen_canonical_ids.add(cid)
        for edge in edges:
            pair = edge['source'], edge['target']
            self.check(pair not in registered, 'edge_unique_endpoints', [split, pair])
            registered[pair] = edge
            self.check_edge(edge, states, split)
            adjacency[pair[0]][edge['axis']].append(edge)
        for node in nodes:
            provenance = node.get('created_by', {})
            if provenance.get('parent') is not None:
                pair = provenance['parent'], node['id']
                self.check(pair in registered and registered[pair]['axis'] == provenance.get('axis'),
                           'node_edit_first_provenance', [split, pair, provenance])
        counts, signatures, session_ids = Counter(), set(), set()
        fork_rounds, fork_parents, axes_actual, axes_formal_expected, axes_graph_expected = Counter(), Counter(), Counter(), Counter(), Counter()
        missing_axes, missing_opportunities, wardrobe_modes = Counter(), Counter(), Counter()
        starts = Counter()
        single_formal_steps = single_graph_missing_steps = single_selected_steps = 0
        modes_when_formal_single = Counter()
        for session in sessions:
            sid, length, history, steps = session['id'], session['length'], session['history'], session['steps']
            context = [split, sid]
            self.check(sid not in session_ids, 'session_id_unique', context)
            session_ids.add(sid)
            self.check(length in (2, 3, 4, 5), 'session_length_range', context)
            self.check(len(history) == length + 1 and len(steps) == length, 'session_history_length', context)
            self.check(all(nid in states for nid in history), 'session_all_history_nodes_exist', context)
            signature = (history[0], tuple((r['source_position'], r['target']) for r in steps))
            self.check(signature not in signatures, 'session_structural_unique', context)
            signatures.add(signature)
            counts[f'{session["kind"]}_{length}'] += 1
            starts[history[0]] += 1
            nonlatest = []
            for t, step in enumerate(steps, 1):
                parent = step['source_position']
                if not self.check(isinstance(parent, int) and 0 <= parent <= t - 1,
                                  'session_historical_parent_bounds', [*context, t, parent]):
                    continue
                self.check(step['source'] == history[parent] and step['target'] == history[t],
                           'session_parent_occurrence_and_target', [*context, t])
                pair = step['source'], step['target']
                exists = self.check(pair in registered, 'session_registered_edge', [*context, t, pair])
                if exists:
                    self.check(all(step.get(k) == value for k, value in registered[pair].items()),
                               'session_edge_metadata', [*context, t])
                if parent != t - 1:
                    nonlatest.append(t)
                    fork_rounds[f'L{length}_t{t}'] += 1
                    fork_parents[f'L{length}_t{t}_p{parent}'] += 1
                source = states[step['source']]
                actual = step['axis']
                axes_actual[actual] += 1
                formal = self.formal_axes(source)
                graph_axes = set(adjacency[step['source']])
                for axis in formal:
                    missing_opportunities[axis] += 1
                    if axis not in graph_axes:
                        missing_axes[axis] += 1
                for pool, destination in [(formal, axes_formal_expected), (graph_axes, axes_graph_expected)]:
                    denom = sum(2 if axis == 'identity' else 1 for axis in pool)
                    for axis in pool:
                        destination[axis] += (2 if axis == 'identity' else 1) / denom
                if actual == 'wardrobe':
                    wardrobe_modes[step['mode']] += 1
                    available = self.single_available(source['sex'], serial(source['wardrobe']), source['hair'], source['camera'] in UPPER_CAMERAS)
                    if available:
                        single_formal_steps += 1
                        graph_modes = {e.get('mode') for e in adjacency[step['source']]['wardrobe']}
                        represented = ('both' if {'single_piece', 'whole_outfit'} <= graph_modes
                                       else 'single_only' if 'single_piece' in graph_modes else 'whole_only')
                        modes_when_formal_single[represented] += 1
                        if 'single_piece' not in graph_modes:
                            single_graph_missing_steps += 1
                        single_selected_steps += step['mode'] == 'single_piece'
            if session['kind'] == 'linear':
                self.check(not nonlatest and session.get('fork_round') is None, 'session_linear_no_fork', context)
            else:
                self.check(session['kind'] == 'fork' and len(nonlatest) == 1
                           and session.get('fork_round') == nonlatest[0], 'session_fork_exactly_one', [*context, nonlatest])
        expected_nodes = self.rules['budgets'][split]['main_canonical_nodes'] if full else {'train': 180, 'test': 80}[split]
        expected_sessions = self.rules['budgets'][split]['structural_sessions'] if full else {'train': 80, 'test': 20}[split]
        self.check(len(nodes) == expected_nodes, 'budget_main_nodes', [split, len(nodes), expected_nodes])
        self.check(len(sessions) == expected_sessions, 'budget_sessions', [split, len(sessions), expected_sessions])
        expected_quotas = self.quota_counts(expected_sessions)
        self.check(dict(counts) == expected_quotas, 'session_exact_length_kind_quotas', [split, dict(counts), expected_quotas])
        sex_counts = Counter()
        initial_distributions = defaultdict(Counter)
        for nid, count in starts.items():
            state = states[nid]
            sex_counts[state['sex']] += count
            for axis in ('identity', 'site', 'action', 'camera', 'hair', 'hair_color'):
                initial_distributions[axis][state[axis]] += count
        return {'nodes': len(nodes), 'registered_edges': len(edges), 'sessions': len(sessions),
                'structurally_unique_sessions': len(signatures), 'length_kind_counts': dict(counts),
                'fork_round_counts': dict(fork_rounds), 'fork_parent_conditional_counts': dict(fork_parents),
                'start_sex_counts': dict(sex_counts),
                'start_distributions': {k: dict(v) for k, v in initial_distributions.items()},
                'sampling_diagnostics': {
                    'actual_axis_counts': dict(axes_actual),
                    'expected_axis_counts_given_formal_eligible_source_axes': dict(axes_formal_expected),
                    'expected_axis_counts_given_only_represented_graph_axes': dict(axes_graph_expected),
                    'missing_formal_axis_graph_neighbor_opportunities': dict(missing_axes),
                    'formal_axis_opportunities': dict(missing_opportunities),
                    'wardrobe_modes': dict(wardrobe_modes),
                    'wardrobe_steps_with_formal_single_available': single_formal_steps,
                    'of_those_steps_missing_graph_single': single_graph_missing_steps,
                    'of_those_steps_single_selected': single_selected_steps,
                    'graph_modes_on_steps_with_formal_single_available': dict(modes_when_formal_single),
                    'formal_single_50_percent_target_count': single_formal_steps * .5,
                    'source_wardrobe_whole_axis_availability_assumption': 'current catalog has many other-family visible-core targets; no full Cartesian enumeration',
                    'interpretation': 'diagnostics expose graph-conditioned sampling; finite-sample differences are not hard integrity failures'
                }}, seen_keys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', default='full_squares')
    args = parser.parse_args()
    root = (HERE / args.candidate).resolve()
    if root.parent != HERE:
        parser.error('candidate must name a direct child run directory')
    verifier = Verification()
    report = {'candidate': args.candidate, 'scope': 'offline node/edge/session integrity and sampling diagnostics only',
              'independent_edge_oracle': 'formal wardrobe resolver plus explicit independent semantic checks; build_trial not imported',
              'rendered': False, 'visual_verified': False, 'inputs_sha256': {}, 'splits': {}}
    for name in ('catalog.json', 'rules.json', 'normalize_catalog.py', 'build_trial.py', 'verify_trial.py'):
        report['inputs_sha256'][name] = sha(HERE / name)
    canonical = {}
    for split in ('train', 'test'):
        report['splits'][split], canonical[split] = verifier.verify_split(root, split, args.candidate.startswith('full_'))
        for name in ('nodes.json', 'edges.json', 'sessions.jsonl'):
            path = root / split / name
            report['inputs_sha256'][f'{split}/{name}'] = sha(path)
    overlap = canonical['train'] & canonical['test']
    verifier.check(not overlap, 'split_complete_canonical_main_nodes_disjoint', {'overlap_count': len(overlap)})
    report['canonical_cross_split_overlap_count'] = len(overlap)
    report['passed_checks'] = dict(verifier.counts)
    report['errors'] = dict(verifier.errors)
    report['error_examples'] = dict(verifier.examples)
    report['integrity_success'] = not verifier.errors
    report['sampling_claim'] = 'graph-conditioned candidate; not proof of global full-catalog uniform sampling'
    report['implementation_limitations'] = [
        'Session starts sample a hierarchy over represented nodes and stop when one node remains; later requested independent marginals are not guaranteed.',
        'Formal legal axes/targets missing from the finite graph are unavailable to session sampling, shifting the confirmed axis probabilities.',
        'Formal single-piece availability may be lost in the graph; mode sampling among represented modes then need not be 50/50.',
        'Whole target selection is hierarchical by represented family/group, then by represented state; core-piece and shoe marginals may be coupled.',
        'Initial joint rejection on saved exclusions conditions scene/action/camera probabilities; it is not independent uniform marginals.',
        'Builder canonical lacks explicit sex/aspect/profile-domain prefix; current identity determines sex and all states use one provisional landscape label. This verifier includes sex/aspect and every state field.',
        'Landscape is a symbolic trial domain. Resolution/fps/duration/aspect are not production-frozen and no media was inspected.'
    ]
    output = HERE / f'verification_{args.candidate}.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'candidate': args.candidate, 'integrity_success': report['integrity_success'],
                      'errors': report['errors'], 'cross_split_overlap': len(overlap),
                      'output': str(output)}, ensure_ascii=False))
    raise SystemExit(0 if report['integrity_success'] else 1)


if __name__ == '__main__':
    main()
