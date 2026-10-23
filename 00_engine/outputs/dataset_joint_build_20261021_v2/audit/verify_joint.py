"""Independent conditional audit. Pure Python, no builder imports or UE calls.

Reuse the v1 semantic verifier and current formal garment resolver; add tests
which a correct global histogram cannot hide. Run only on an explicit candidate.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import itertools
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1] / 'dataset_trial_build_20261021_v1'
sys.path.insert(0, str(V1))
from verify_trial import Verification, AXES, UPPER_CAMERAS, CORE_SLOTS, UPPER_SLOTS, read, serial, sha


class Tables:
    def __init__(self):
        self.rows = {}

    def add(self, name, condition, actual, probabilities):
        key = name, serial(condition)
        row = self.rows.setdefault(key, {'name': name, 'condition': condition,
                                        'n': 0, 'observed': Counter(),
                                        'expected': Counter(), 'variance': Counter()})
        row['n'] += 1
        row['observed'][str(actual)] += 1
        for value, probability in probabilities.items():
            row['expected'][str(value)] += probability
            row['variance'][str(value)] += probability * (1 - probability)

    def report(self):
        result = []
        for key, row in sorted(self.rows.items()):
            obs, exp, var = row['observed'], row['expected'], row['variance']
            values = set(obs) | set(exp)
            residuals = {v: (obs[v] - exp[v]) / math.sqrt(var[v])
                         for v in values if var[v] > 0}
            impossible = {v: obs[v] for v in values if obs[v] and not exp[v]}
            result.append({**row, 'observed': dict(obs), 'expected': dict(exp),
                           'variance': dict(var),
                           'total_variation': sum(abs(obs[v] - exp[v]) for v in values) / (2 * row['n']),
                           'max_abs_standardized_residual': max(map(abs, residuals.values()), default=0),
                           'standardized_residuals': residuals,
                           'impossible_observations': impossible,
                           'minimum_positive_expected': min((e for e in exp.values() if e), default=0)})
        return result


def uniform(values):
    values = list(values)
    return {str(v): 1 / len(values) for v in values} if values else {}


class Audit(Verification):
    def __init__(self, partial=False, camera_target_policy='uniform'):
        super().__init__()
        self.partial = partial
        self.camera_target_policy = camera_target_policy
        self.expected_shortfalls = []

    def check(self, condition, category, context):
        if self.partial and not condition and category in ('budget_main_nodes', 'budget_sessions', 'session_exact_length_kind_quotas'):
            if category == 'session_exact_length_kind_quotas':
                split, actual, expected = context
                deficit = {key: expected[key] - actual.get(key, 0) for key in expected}
                if all(value >= 0 for value in deficit.values()):
                    self.expected_shortfalls.append({'category': category, 'split': split, 'deficit': deficit})
                    return True
            elif context[1] <= context[2]:
                self.expected_shortfalls.append({'category': category, 'split': context[0],
                                                'actual': context[1], 'target': context[2], 'deficit': context[2] - context[1]})
                return True
        return super().check(condition, category, context)

    def target_probabilities(self, state_json, axis):
        legal = self.targets(state_json, axis)
        weights = {value: (1.5 if axis == 'camera' and self.camera_target_policy == 'weighted_four'
                          and value in ('front_head', 'front_upper', 'dolly_in_front', 'dolly_out_front') else 1)
                   for value in legal}
        total = sum(weights.values())
        return {value: weight / total for value, weight in weights.items()}

    @lru_cache(maxsize=None)
    def outfit_pool(self, sex, hair):
        """Exact small registered clothing domain; no media/asset-wide audit.

        Independent slot draws and optional bits have equal probability before
        the conditional shoe draw. Keep this primitive probability explicitly.
        """
        rows = []
        for family in self.catalog['sexes'][sex]['families']:
            for group in family['groups']:
                slots = list(group['slot_options'])
                options = [[r['asset_id'] for r in group['slot_options'][slot]]
                           + ([None] if slot in group['optional_slots'] else []) for slot in slots]
                accessories = [r['asset_id'] for r in group['optional_assets']]
                group_probability = 1 / (math.prod(map(len, options)) * 2 ** len(accessories))
                for values in itertools.product(*options):
                    for bits in itertools.product((0, 1), repeat=len(accessories)):
                        choice = {'family_id': family['family_id'], 'group_id': group['group_id'],
                                  'slot_choices': dict(zip(slots, values)),
                                  'optional_asset_ids': [a for a, bit in zip(accessories, bits) if bit],
                                  'shared_shoe_id': None, 'hair_id': hair}
                        native = [r['asset_id'] for r in group['required_assets'] if r['slot'] == 'shoes']
                        native += [value for slot, value in zip(slots, values) if slot == 'shoes' and value]
                        native += [r['asset_id'] for r in group['optional_assets']
                                   if r['slot'] == 'shoes' and r['asset_id'] in choice['optional_asset_ids']]
                        shared = [r['asset_id'] for r in self.catalog['sexes'][sex]['shared_shoes']]
                        shoes = ([None] if native else shared if group['shared_shoe_policy'] == 'required_universal_female_pool'
                                 else [None] + shared)
                        for shoe in shoes:
                            target = {**choice, 'shared_shoe_id': shoe}
                            try:
                                resolved = self.resolved(sex, serial(target), hair)
                            except ValueError:
                                continue
                            if not resolved['hair_deny']:
                                rows.append((target, resolved, group_probability / len(shoes)))
        return rows

    @lru_cache(maxsize=128)
    def whole_distribution(self, sex, choice_json, hair, upper):
        source = self.resolved(sex, choice_json, hair)
        choice = source['normalized']
        groups = defaultdict(list)
        for target, resolved, primitive in self.outfit_pool(sex, hair):
            if (target['family_id'] != choice['family_id'] and source['core'] != resolved['core']
                    and (not upper or source['upper'] != resolved['upper'])):
                groups[target['family_id'], target['group_id']].append((target, resolved, primitive))
        families = {family for family, _ in groups}
        result = []
        for (family, group), rows in groups.items():
            group_count = sum(f == family for f, _ in groups)
            primitive_total = sum(row[2] for row in rows)
            for target, resolved, primitive in rows:
                result.append((target, resolved, primitive / primitive_total / len(families) / group_count))
        return result

    @staticmethod
    def marginal(rows, value):
        result = Counter()
        for target, resolved, probability in rows:
            result[str(value(target, resolved))] += probability
        return dict(result)

    @lru_cache(maxsize=None)
    def targets(self, state_json, axis):
        state = json.loads(state_json)
        if axis == 'identity':
            pool = self.ids[state['sex']]
        elif axis == 'hair':
            pool = self.hairs[state['sex']]
        elif axis == 'hair_color':
            pool = self.colors
        else:
            pool = self.pools[axis]
        return tuple(sorted(v for v in pool if v != state[axis]
                            and (axis not in ('action', 'camera', 'site')
                                 or self.legal_scene(dict(state, **{axis: v})))))

    @lru_cache(maxsize=None)
    def single_options(self, state_json):
        """Enumerate core alternatives independently of the builder's neighbors."""
        state = json.loads(state_json)
        source = self.wardrobe(state)
        choice = source['normalized']
        family, group = self.groups[state['sex'], choice['family_id'], choice['group_id']]
        if state['camera'] == 'front_head' or family['assembly_mode'] == 'locked_bundle':
            return ()
        result = []
        upper = state['camera'] in UPPER_CAMERAS
        for slot, assets in group['slot_options'].items():
            if slot not in (UPPER_SLOTS if upper else CORE_SLOTS):
                continue
            values = [r['asset_id'] for r in assets]
            if slot in group['optional_slots']:
                values.append(None)
            for value in values:
                if value == choice['slot_choices'].get(slot):
                    continue
                target = json.loads(serial(choice))
                target['slot_choices'][slot] = value
                try:
                    other = self.resolved(state['sex'], serial(target), state['hair'])
                except ValueError:
                    continue
                if (not other['hair_deny'] and source['core'] != other['core']
                        and source['shoes'] == other['shoes']
                        and (not upper or source['upper'] != other['upper'])):
                    result.append((slot, value, other['assets']))
        return tuple(result)

    def sample_audit(self, root, split):
        nodes = read(root / split / 'nodes.json')
        states = {r['id']: r['state'] for r in nodes}
        features = {nid: {**state, 'wardrobe': self.wardrobe(state)['assets']} for nid, state in states.items()}
        sessions = [json.loads(line) for line in (root / split / 'sessions.jsonl').read_text(encoding='utf-8').splitlines() if line]
        tables = Tables()
        degrees = defaultdict(lambda: defaultdict(set))
        for edge in read(root / split / 'edges.json'):
            degrees[edge['source']][edge['axis']].add(edge['target'])
        support = Counter()
        per_axis_returns = defaultdict(lambda: {'opportunities': 0, 'observed': 0, 'expected': 0.0,
                                               'graph_uniform_expected': 0.0})
        for session in sessions:
            h, steps, L = session['history'], session['steps'], session['length']
            start = states[h[0]]
            sex = start['sex']
            tables.add('initial_sex', {}, sex, {'female': .5, 'male': .5})
            for axis, pool in [('identity', self.ids[sex]), ('hair', self.hairs[sex]), ('hair_color', self.colors)]:
                tables.add('initial_' + axis, {'sex': sex}, start[axis], uniform(pool))
            sw = start['wardrobe']
            families = self.catalog['sexes'][sex]['families']
            family, group = self.groups[sex, sw['family_id'], sw['group_id']]
            tables.add('initial_family', {'sex': sex}, sw['family_id'], uniform(f['family_id'] for f in families))
            tables.add('initial_group', {'sex': sex, 'family': sw['family_id']}, sw['group_id'],
                       uniform(g['group_id'] for g in family['groups']))
            for slot, rows in group['slot_options'].items():
                options = [r['asset_id'] for r in rows] + ([None] if slot in group['optional_slots'] else [])
                tables.add('initial_core_slot', {'sex': sex, 'family': sw['family_id'], 'group': sw['group_id'], 'slot': slot},
                           sw['slot_choices'].get(slot), uniform(options))
            for accessory in group['optional_assets']:
                aid = accessory['asset_id']
                tables.add('initial_optional', {'sex': sex, 'family': sw['family_id'], 'group': sw['group_id'], 'asset': aid},
                           'present' if aid in sw['optional_asset_ids'] else 'absent', {'present': .5, 'absent': .5})
            native = bool(self.wardrobe(start)['shoes']) and sw['shared_shoe_id'] is None
            shared = [r['asset_id'] for r in self.catalog['sexes'][sex]['shared_shoes']]
            shoes = ([None] if native else shared if group['shared_shoe_policy'] == 'required_universal_female_pool'
                     else [None] + shared)
            tables.add('initial_shoe', {'sex': sex, 'family': sw['family_id'], 'group': sw['group_id'], 'native': native},
                       sw['shared_shoe_id'], uniform(shoes))
            if session['kind'] == 'fork':
                ft = session['fork_round']
                tables.add('fork_round', {'L': L}, ft, uniform(range(2, L + 1)))
                tables.add('fork_parent', {'L': L, 't': ft}, steps[ft - 1]['source_position'], uniform(range(ft - 1)))
            for t, step in enumerate(steps, 1):
                u, v, axis = step['source'], step['target'], step['axis']
                source, target = states[u], states[v]
                source_json = serial(source)
                formal = sorted(self.formal_axes(source))
                weights = {a: (2 if a == 'identity' else 1) for a in formal}
                denominator = sum(weights.values())
                axis_probs = {a: w / denominator for a, w in weights.items()}
                for condition in ({'eligible': formal}, {'source_camera': source['camera']},
                                  {'kind': session['kind'], 'L': L, 'round': t}):
                    tables.add('axis', condition, axis, axis_probs)
                if axis == 'wardrobe':
                    singles = self.single_options(source_json)
                    mode_probs = {'single_piece': .5, 'whole_outfit': .5} if singles else {'whole_outfit': 1.0}
                    tables.add('wardrobe_mode', {'formal_single': bool(singles), 'camera': source['camera']}, step['mode'], mode_probs)
                    p = step['source_position']
                    if p > 0 and steps[p - 1]['axis'] == axis:
                        incoming = steps[p - 1]
                        old = states[h[incoming['source_position']]]
                        old_assets = self.wardrobe(old)['assets']
                        return_probability = 0.0
                        slots = {r[0] for r in singles}
                        for slot, value, assets in singles:
                            if assets == old_assets:
                                return_probability += mode_probs.get('single_piece', 0) / len(slots) / sum(r[0] == slot for r in singles)
                        whole = self.whole_distribution(source['sex'], serial(source['wardrobe']), source['hair'],
                                                        source['camera'] in UPPER_CAMERAS)
                        return_probability += mode_probs['whole_outfit'] * sum(prob for _, resolved, prob in whole
                                                                                if resolved['assets'] == old_assets)
                        returned = self.wardrobe(target)['assets'] == old_assets
                        tables.add('selected_parent_same_axis_return', {'axis': axis, 'formal_single': bool(singles),
                                                                       'incoming_mode': incoming['mode'], 'camera': source['camera']},
                                   'return' if returned else 'other', {'return': return_probability, 'other': 1 - return_probability})
                        row = per_axis_returns[axis]
                        row['opportunities'] += 1
                        row['observed'] += returned
                        row['expected'] += return_probability
                        row['graph_uniform_expected'] = None
                    if step['mode'] == 'single_piece':
                        slots = sorted({r[0] for r in singles})
                        slot = step['slot']
                        tables.add('single_slot', {'sex': source['sex'], 'family': source['wardrobe']['family_id'],
                                                 'group': source['wardrobe']['group_id'], 'camera': source['camera']}, slot, uniform(slots))
                        values = [r[1] for r in singles if r[0] == slot]
                        tables.add('single_value', {'sex': source['sex'], 'family': source['wardrobe']['family_id'],
                                                  'group': source['wardrobe']['group_id'], 'slot': slot,
                                                  'source_value': source['wardrobe']['slot_choices'].get(slot)},
                                   target['wardrobe']['slot_choices'].get(slot), uniform(values))
                    else:
                        distribution = self.whole_distribution(source['sex'], serial(source['wardrobe']), source['hair'],
                                                               source['camera'] in UPPER_CAMERAS)
                        family = target['wardrobe']['family_id']
                        group = target['wardrobe']['group_id']
                        condition = {'sex': source['sex'], 'source_family': source['wardrobe']['family_id'],
                                     'upper': source['camera'] in UPPER_CAMERAS}
                        tables.add('whole_family', condition, family,
                                   self.marginal(distribution, lambda w, r: w['family_id']))
                        family_rows = [r for r in distribution if r[0]['family_id'] == family]
                        family_mass = sum(r[2] for r in family_rows)
                        family_rows = [(w, r, p / family_mass) for w, r, p in family_rows]
                        tables.add('whole_group', {**condition, 'target_family': family}, group,
                                   self.marginal(family_rows, lambda w, r: w['group_id']))
                        group_rows = [r for r in family_rows if r[0]['group_id'] == group]
                        group_mass = sum(r[2] for r in group_rows)
                        group_rows = [(w, r, p / group_mass) for w, r, p in group_rows]
                        for slot in target['wardrobe']['slot_choices']:
                            tables.add('whole_slot', {**condition, 'target_family': family, 'target_group': group, 'slot': slot},
                                       target['wardrobe']['slot_choices'][slot],
                                       self.marginal(group_rows, lambda w, r: w['slot_choices'].get(slot)))
                        # Condition shoe distribution on every selected core/accessory
                        # to avoid native-shoe choices hiding shared-shoe bias.
                        shoe_rows = [r for r in group_rows if r[0]['slot_choices'] == target['wardrobe']['slot_choices']
                                     and r[0]['optional_asset_ids'] == target['wardrobe']['optional_asset_ids']]
                        shoe_mass = sum(r[2] for r in shoe_rows)
                        if shoe_mass:
                            shoe_rows = [(w, r, p / shoe_mass) for w, r, p in shoe_rows]
                            tables.add('whole_shoe', {'sex': source['sex'], 'target_family': family, 'target_group': group,
                                                     'native_shoe': bool(self.wardrobe(target)['shoes']) and target['wardrobe']['shared_shoe_id'] is None},
                                       target['wardrobe']['shared_shoe_id'],
                                       self.marginal(shoe_rows, lambda w, r: w['shared_shoe_id']))
                    continue
                legal = self.targets(source_json, axis)
                target_probs = self.target_probabilities(source_json, axis)
                # Each row contributes its own formal domain, so legal exclusions
                # remain in the expectation rather than disappearing in a pool.
                conditions = [{'axis': axis, 'source_value': source[axis], 'sex': source['sex']},
                              {'axis': axis, 'source_camera': source['camera']},
                              {'axis': axis, 'kind': session['kind'], 'L': L, 'round': t}]
                context_axes = {'action': ('site', 'camera'), 'camera': ('site', 'action'),
                                'site': ('action', 'camera')}.get(axis, ())
                if context_axes:
                    conditions.append({'axis': axis, 'source_value': source[axis],
                                       **{key: source[key] for key in context_axes}})
                for condition in conditions:
                    tables.add('target', condition, target[axis], target_probs)
                known_values = {states[nid][axis] for nid in h[:t]} & set(legal)
                known_mass = sum(target_probs[value] for value in known_values)
                tables.add('history_known_target_mass', {'axis': axis, 'N': len(legal), 'K': len(known_values)},
                           'known' if target[axis] in known_values else 'other',
                           {'known': known_mass, 'other': 1 - known_mass})
                historical_targets = {states[nid][axis] for nid in set(h[:t])
                                      if states[nid][axis] in legal and all(
                                          features[nid].get(key) == value for key, value in features[u].items() if key != axis)}
                full_history_mass = sum(target_probs[value] for value in historical_targets)
                tables.add('full_history_node_return', {'axis': axis},
                           'return' if v in h[:t] else 'other',
                           {'return': full_history_mass, 'other': 1 - full_history_mass})
                declared = step.get('sampling_diagnostic')
                if declared:
                    mass = declared['history_probability']
                    tables.add('declared_history_gate', {'axis': axis, 'mode': step['mode']},
                               'return' if declared['history_selected'] else 'other',
                               {'return': mass, 'other': 1 - mass})
                represented = degrees[u][axis]
                support[axis + '_opportunities'] += 1
                support[axis + '_missing_target_slots'] += len(legal) - len(represented)
                support[axis + '_formal_target_slots'] += len(legal)
                p = step['source_position']
                if p > 0:
                    incoming = steps[p - 1]
                    if incoming['axis'] == axis:
                        old = states[h[incoming['source_position']]]
                        if old[axis] in legal:
                            returned = target[axis] == old[axis]
                            probability = target_probs[old[axis]]
                            condition = {'axis': axis, 'N': len(legal), 'camera': source['camera']}
                            tables.add('selected_parent_same_axis_return', condition,
                                       'return' if returned else 'other', {'return': probability, 'other': 1 - probability})
                            row = per_axis_returns[axis]
                            row['opportunities'] += 1
                            row['observed'] += returned
                            row['expected'] += probability
                            row['graph_uniform_expected'] += 1 / len(represented) if represented else 0
        table_report = tables.report()
        material = sorted((r for r in table_report if r['n'] >= 50),
                          key=lambda r: r['max_abs_standardized_residual'], reverse=True)
        return {'largest_conditional_deviations_n_at_least_50': material[:25],
                'conditional_tables': table_report, 'represented_target_support': dict(support),
                'selected_parent_same_axis_returns': dict(per_axis_returns),
                'scope_limits': [
                    'Standardized residuals are diagnostics, not independent-sample p-values: sessions reuse states/edges.',
                    'Sparse conditional bins have low power; exact finite conditional uniformity cannot be certified by histograms.',
                    'Whole targets use eligible family then eligible group, independent slots/optional bits conditioned on legal visible-core change, then conditional shoes. Rejection across family/group can violate this intended hierarchy.',
                    'No media or visual correctness was checked.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--smoke', action='store_true', help='Use the original 180/80-node smoke budgets.')
    parser.add_argument('--partial', action='store_true', help='Record unfilled budgets/quotas as expected shortfalls.')
    parser.add_argument('--camera-target-policy', choices=('uniform', 'weighted_four'), default='uniform')
    parser.add_argument('--train-dir', type=Path)
    parser.add_argument('--test-dir', type=Path)
    args = parser.parse_args()
    root = args.candidate.resolve()
    output = args.output or HERE / ('verification_' + root.name + '.json')
    if bool(args.train_dir) != bool(args.test_dir):
        parser.error('--train-dir and --test-dir must be provided together')
    split_paths = {split: root / split for split in ('train', 'test')}
    if args.train_dir:
        split_paths = {'train': args.train_dir.resolve(), 'test': args.test_dir.resolve()}
    class RoutedRoot:
        def __truediv__(self, split):
            return split_paths[split]
    routed = RoutedRoot()
    verifier = Audit(args.partial, args.camera_target_policy)
    report = {'candidate': str(root), 'rendered': False, 'visual_verified': False,
              'independence': 'No generator import; reuse v1 semantic checks and formal garment resolution.',
              'partial_mode': args.partial, 'camera_target_policy': args.camera_target_policy,
              'split_paths': {key: str(value) for key, value in split_paths.items()},
              'inputs_sha256': {str(V1 / name): sha(V1 / name) for name in
                                ('rules.json', 'catalog.json', 'normalize_catalog.py', 'verify_trial.py')},
              'splits': {}}
    canonical = {}
    for split in ('train', 'test'):
        integrity, canonical[split] = verifier.verify_split(routed, split, not args.smoke)
        report['splits'][split] = {'integrity': integrity, 'conditional_sampling': verifier.sample_audit(routed, split)}
        for name in ('nodes.json', 'edges.json', 'sessions.jsonl'):
            path = split_paths[split] / name
            report['inputs_sha256'][str(path)] = sha(path)
    overlap = canonical['train'] & canonical['test']
    verifier.check(not overlap, 'split_complete_canonical_main_nodes_disjoint', {'count': len(overlap)})
    report.update(canonical_cross_split_overlap_count=len(overlap), integrity_success=not verifier.errors,
                  errors=dict(verifier.errors), error_examples=dict(verifier.examples), passed_checks=dict(verifier.counts))
    report['expected_shortfalls'] = verifier.expected_shortfalls
    report['all_target_budgets_and_quotas_filled'] = not verifier.expected_shortfalls and not any(
        key in verifier.errors for key in ('budget_main_nodes', 'budget_sessions', 'session_exact_length_kind_quotas'))
    report['sampling_claim'] = 'Conditional diagnostics against formal full domains; integrity success is not sampling success.'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'candidate': str(root), 'integrity_success': report['integrity_success'],
                      'errors': report['errors'], 'report': str(output)}, ensure_ascii=False))
    raise SystemExit(0 if report['integrity_success'] else 1)


if __name__ == '__main__':
    main()
