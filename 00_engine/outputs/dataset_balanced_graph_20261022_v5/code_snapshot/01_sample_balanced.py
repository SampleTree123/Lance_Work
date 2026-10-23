"""Offline sampler for a supplied, explicit directed configuration graph.

No graph mutation, fabricated edges, UE access, or output writes. The graph uses
the v1 Graph interface: nodes[u], adj[u][axis], edges[u, v], d.allowed_axes(s),
and d.singles(s). sample() returns sessions plus auditable sampling metadata.
"""
from __future__ import annotations

import math
import json
import random
from collections import Counter, defaultdict

AXES = ('identity', 'hair', 'hair_color', 'wardrobe', 'action', 'camera', 'site')
NON_ID = AXES[1:]
ID_CAMERAS = {'front_head', 'front_upper', 'dolly_in_front', 'dolly_out_front'}


def quotas(total):
    """Preserve the original v1 kind and length quotas exactly."""
    fork = total // 3
    jobs = []
    for kind, n, weights in [('linear', total - fork, [.25] * 4),
                              ('fork', fork, [.1, .2, .35, .35])]:
        counts = [round(n * w) for w in weights]
        counts[-1] += n - sum(counts)
        for length, count in zip(range(2, 6), counts):
            jobs.extend([(kind, length)] * count)
    return jobs


def _choose(rng, values, weights):
    return rng.choices(values, weights=weights, k=1)[0]


def _attributes(state, core_assets=()):
    """Represent marginal values without conflating sex-specific catalogs."""
    sex = state.get('sex')
    out = []
    for axis in AXES:
        if axis == 'wardrobe':
            w = state[axis]
            out.extend([(axis + '_family', (sex, w['family_id'])),
                        (axis + '_group', (sex, w['family_id'], w['group_id']))])
            out.extend(('wardrobe_core', (sex, asset)) for asset in sorted(core_assets))
        else:
            value = state[axis]
            if axis in ('identity', 'hair'):
                value = (sex, value)
            out.append((axis, value))
    return tuple(out)


def sample(g, total, seed, *, max_attempts=240, start_pool=160,
           feedback_exponent=4.0, progress_every=3000,
           identity_target_fraction=.09, nonidentity_upper_slack=.025,
           cap2_attempts=12, enforce_core_coverage=True):
    """Sample fixed jobs; unsuccessful retries never change kind/length/fork.

    Hard edge cap is four, counting repeated directed edges inside a session.
    Attempts first use cap two, then cap three, and only finally cap four.
    Missing jobs remain missing and are reported, never converted to other jobs.
    feedback_exponent controls global six-nonidentity-axis count compensation;
    the local legal-axis base weights always remain identity=2, others=1, with
    0.5**n decay for every earlier edit of that axis in the entire session.
    """
    if total < 0 or max_attempts < 1 or start_pool < 1:
        raise ValueError('total >= 0, max_attempts >= 1 and start_pool >= 1 required')
    if not 0 < identity_target_fraction < 1 or not 0 <= nonidentity_upper_slack < .1:
        raise ValueError('identity fraction must be in (0,1), nonidentity slack in [0,.1)')
    rng = random.Random(seed)
    jobs = quotas(total)
    rng.shuffle(jobs)
    planned_steps = sum(length for _, length in jobs)
    nonidentity_target = planned_steps * (1 - identity_target_fraction) / len(NON_ID)
    # Unlike a weight alone, this bound cannot be overwhelmed by a large local
    # wardrobe neighborhood once the other axes' cap-two support is exhausted.
    nonidentity_upper = max(1, math.ceil(nonidentity_target * (1 + nonidentity_upper_slack)))
    explicit = []
    by_identity = defaultdict(list)
    for u, state in enumerate(g.nodes):
        axes = {}
        for axis in g.d.allowed_axes(state):
            # An adjacency reference alone must never invent an edge.
            vs = sorted({v for v in g.adj[u].get(axis, ())
                         if (u, v) in g.edges and g.edges[u, v]['axis'] == axis})
            if vs:
                axes[axis] = vs
        explicit.append(axes)
        if axes:
            by_identity[(state.get('sex'), state['identity'])].append(u)
    identities = sorted(by_identity)
    if total and not identities:
        raise ValueError('graph has no explicit legal directed edges')

    core_cache = {}
    attributes = []
    for state in g.nodes:
        key = (state.get('sex'), json.dumps(state['wardrobe'], sort_keys=True, separators=(',', ':')))
        if key not in core_cache:
            core_cache[key] = frozenset(g.d.nc.core_asset_ids(state['sex'], state['wardrobe']))
        attributes.append(_attributes(state, core_cache[key]))
    attribute_sets = [frozenset(attrs) for attrs in attributes]

    def edited_target_attributes(u, v, axis):
        for field, value in attributes[v]:
            if field == axis or (axis == 'wardrobe' and field.startswith('wardrobe_')):
                # Clothes already worn at the source do not count as changed-in
                # core targets merely because some other garment was edited.
                if field != 'wardrobe_core' or (field, value) not in attribute_sets[u]:
                    yield field, value
    universe = defaultdict(set)
    for attrs in attributes:
        for field, value in attrs:
            universe[field].add(value)
    target_universe = defaultdict(set)
    for u, axes in enumerate(explicit):
        for axis, vs in axes.items():
            for v in vs:
                for field, value in edited_target_attributes(u, v, axis):
                    target_universe[field].add(value)
    core_incoming = defaultdict(list)
    edge_new_core = {}
    for u, axes in enumerate(explicit):
        for v in axes.get('wardrobe', ()):
            gained = frozenset(value for field, value in edited_target_attributes(u, v, 'wardrobe')
                               if field == 'wardrobe_core')
            if gained:
                edge_new_core[u, v] = gained
                for value in gained:
                    core_incoming[value].append((u, v))

    sessions, seen = [], set()
    edge_use, node_use, starts, identity_starts = Counter(), Counter(), Counter(), Counter()
    axis_use, axis_expected = Counter(), Counter()
    target_counts, start_counts = defaultdict(Counter), defaultdict(Counter)
    modes, mode_expected = Counter(), Counter()
    errors, cap_attempts, failed_jobs = Counter(), Counter(), []
    forced_coverage_jobs = []
    unseen_starts = {ident: set(nodes) for ident, nodes in by_identity.items()}
    start_attr_fields = ('identity', 'camera', 'site', 'action', 'hair', 'hair_color',
                         'wardrobe_family', 'wardrobe_group')

    def start_node(attempt, cap):
        # Identity balance is soft: retries may move to another identity.
        ident = _choose(rng, identities,
                        [1 / (1 + identity_starts[x]) ** 1.5 for x in identities])
        pool = sorted(unseen_starts[ident]) or by_identity[ident]
        candidates = rng.sample(pool, min(start_pool, len(pool)))
        weights = []
        for u in candidates:
            weight = 1 / (1 + starts[u]) ** .6
            weight *= 1.5 if g.nodes[u]['camera'] in ID_CAMERAS else 1
            for field, value in attributes[u]:
                if field in start_attr_fields:
                    weight *= (1 / (1 + start_counts[field][value])) ** .12
            residual = 0
            for axis, vs in explicit[u].items():
                if axis != 'identity' and axis_use[axis] >= nonidentity_upper:
                    continue
                deficit = (nonidentity_target - axis_use[axis]) / max(1, nonidentity_target)
                urgency = 1 if axis == 'identity' else max(.05, deficit)
                residual += urgency * sum(edge_use[u, v] < cap for v in vs)
            weights.append(weight * (.001 + min(4, math.sqrt(residual))))
        return _choose(rng, candidates, weights)

    def target_weight(u, v, axis, local_edges):
        count = edge_use[u, v] + local_edges[u, v]
        # Both zero/one-use edges are preferred; four-use edges are unavailable.
        weight = (1.0, 1.2, .045, .0008)[count]
        weight *= 1.8 if not node_use[v] else (1 + node_use[v]) ** -.10
        if axis == 'camera' and g.nodes[v]['camera'] in ID_CAMERAS:
            weight *= 1.5
        for field, value in edited_target_attributes(u, v, axis):
            if field == 'wardrobe_core':
                weight *= 64 if not target_counts[field][value] else (1 + target_counts[field][value]) ** -.12
            else:
                weight *= 2.0 if not target_counts[field][value] else (1 + target_counts[field][value]) ** -.25
        return weight

    def coverage_first_edge():
        """Explicit warmup, not a claim of pure stochastic target selection."""
        if not enforce_core_coverage or axis_use['wardrobe'] >= nonidentity_upper:
            return None
        missing = set(core_incoming) - set(target_counts['wardrobe_core'])
        candidates = []
        for value in sorted(missing):
            available = [edge for edge in core_incoming[value] if edge_use[edge] < 4]
            if available:
                # Deal with scarce genuine incoming transitions first.
                candidates.append((len(available), value, available))
        if not candidates:
            return None
        scarcity = min(row[0] for row in candidates)
        _, value, edges = rng.choice([row for row in candidates if row[0] == scarcity])
        # Prefer zero/one use before considering a third/fourth use, then cover
        # as many genuinely new assets as possible in the selected real edge.
        score = lambda edge: (edge_use[edge] >= 2, edge_use[edge],
                              -len(edge_new_core[edge] & missing))
        best = min(map(score, edges))
        edge = rng.choice([edge for edge in edges if score(edge) == best])
        return {'edge': edge, 'requested_core': value,
                'unseen_core_gains': sorted(edge_new_core[edge] & missing),
                'reuse_before': edge_use[edge]}

    for job_index, (kind, length) in enumerate(jobs):
        ft = rng.randrange(2, length + 1) if kind == 'fork' else None
        fp = rng.randrange(ft - 1) if ft is not None else None
        coverage_override = coverage_first_edge()
        for attempt in range(max_attempts):
            # Escalation is about support exhaustion; it cannot change the job.
            cap = 2 if attempt < min(cap2_attempts, max_attempts * .65) else (3 if attempt < max_attempts * .97 else 4)
            if coverage_override:
                cap = max(cap, coverage_override['reuse_before'] + 1)
            cap_attempts[cap] += 1
            u0 = coverage_override['edge'][0] if coverage_override else start_node(attempt, cap)
            history, steps = [u0], []
            local_edges, local_axes, local_modes = Counter(), Counter(), Counter()
            local_expected, local_mode_expected = Counter(), Counter()
            for turn in range(1, length + 1):
                parent = fp if turn == ft else turn - 1
                u = history[parent]
                state = g.nodes[u]
                formal = g.d.allowed_axes(state)
                denominator = sum(2 if axis == 'identity' else 1 for axis in formal)
                for axis in formal:
                    local_expected[axis] += (2 if axis == 'identity' else 1) / denominator
                options = {axis: [v for v in vs if edge_use[u, v] + local_edges[u, v] < cap]
                           for axis, vs in explicit[u].items()
                           if axis == 'identity' or axis_use[axis] + local_axes[axis] < nonidentity_upper}
                options = {axis: vs for axis, vs in options.items() if vs}
                if turn == 1 and coverage_override:
                    forced_target = coverage_override['edge'][1]
                    options = ({'wardrobe': [forced_target]}
                               if forced_target in options.get('wardrobe', ()) else {})
                if not options:
                    errors['dead_end_or_cap_attempts'] += 1
                    break
                axes = list(options)
                progress_steps = sum(axis_use.values()) + len(steps) + 1
                nonid_mean = sum(axis_use[a] + local_axes[a] for a in NON_ID) / len(NON_ID)
                weights = []
                for axis in axes:
                    actual = axis_use[axis] + local_axes[axis]
                    expected = (progress_steps * identity_target_fraction
                                if axis == 'identity' else nonid_mean)
                    ratio = max(.03, min(30, (expected + 25) / (actual + 25)))
                    weights.append((2 if axis == 'identity' else 1)
                                   * .5 ** local_axes[axis]
                                   * ratio ** feedback_exponent)
                axis = _choose(rng, axes, weights)
                vs = options[axis]
                conditional_modes = False
                if axis == 'wardrobe':
                    by_mode = defaultdict(list)
                    for v in vs:
                        by_mode[g.edges[u, v]['mode']].append(v)
                    conditional_modes = bool(g.d.singles(state))
                    available_modes = sorted(by_mode)
                    if conditional_modes:
                        for mode in ('single_piece', 'whole_outfit'):
                            local_mode_expected[mode] += .5
                        weights = [((mode_expected[m] + local_mode_expected[m] + 8)
                                    / (modes[m] + local_modes[m] + 8)) ** 4
                                   for m in available_modes]
                    else:
                        weights = [1] * len(available_modes)
                    mode = _choose(rng, available_modes, weights)
                    vs = by_mode[mode]
                    if mode == 'single_piece':
                        slots = sorted({g.edges[u, v]['slot'] for v in vs})
                        slot = rng.choice(slots)
                        vs = [v for v in vs if g.edges[u, v]['slot'] == slot]
                    else:
                        for field in ('family_id', 'group_id'):
                            values = sorted({g.nodes[v]['wardrobe'][field] for v in vs})
                            value = rng.choice(values)
                            vs = [v for v in vs if g.nodes[v]['wardrobe'][field] == value]
                    if conditional_modes:
                        local_modes[mode] += 1
                v = _choose(rng, vs, [target_weight(u, v, axis, local_edges) for v in vs])
                steps.append({'source_position': parent, 'source': u, 'target': v,
                              **g.edges[u, v]})
                history.append(v)
                local_edges[u, v] += 1
                local_axes[axis] += 1
            if len(steps) != length:
                continue
            signature = (u0, tuple((step['source_position'], step['target']) for step in steps))
            if signature in seen:
                errors['duplicate_structure_attempts'] += 1
                continue
            seen.add(signature)
            sessions.append({'id': f'session_{len(sessions):06d}', 'kind': kind,
                             'length': length, 'fork_round': ft,
                             'history': history, 'steps': steps})
            edge_use.update(local_edges)
            axis_use.update(local_axes)
            axis_expected.update(local_expected)
            modes.update(local_modes)
            mode_expected.update(local_mode_expected)
            node_use.update(history)
            starts[u0] += 1
            ident = (g.nodes[u0].get('sex'), g.nodes[u0]['identity'])
            identity_starts[ident] += 1
            unseen_starts[ident].discard(u0)
            for field, value in attributes[u0]:
                start_counts[field][value] += 1
            for step in steps:
                for field, value in edited_target_attributes(step['source'], step['target'], step['axis']):
                    target_counts[field][value] += 1
            if coverage_override:
                forced_coverage_jobs.append({
                    'job': job_index, 'session_id': sessions[-1]['id'],
                    'kind': kind, 'length': length, 'fork_round': ft,
                    'fork_source_position': fp, 'forced_round': 1,
                    'source': coverage_override['edge'][0],
                    'target': coverage_override['edge'][1], 'axis': 'wardrobe',
                    'mode': steps[0]['mode'],
                    'requested_core': coverage_override['requested_core'],
                    'new_core_gains': coverage_override['unseen_core_gains'],
                    'edge_reuse_before': coverage_override['reuse_before'],
                })
            break
        else:
            errors[f'unfilled_{kind}_{length}'] += 1
            failed_jobs.append({'job': job_index, 'kind': kind, 'length': length,
                                'fork_round': ft, 'fork_source_position': fp})
        if progress_every and len(sessions) and len(sessions) % progress_every == 0:
            print('sampled', len(sessions), '/', total, flush=True)

    mean_nonid = sum(axis_use[a] for a in NON_ID) / len(NON_ID)
    deviation = {a: axis_use[a] / mean_nonid - 1 if mean_nonid else 0 for a in NON_ID}
    edge_hist = Counter(edge_use.values())
    per_axis_reuse = {}
    for axis in AXES:
        distinct = sum(1 for edge in edge_use if g.edges[edge]['axis'] == axis)
        per_axis_reuse[axis] = {'steps': axis_use[axis], 'used_directed_edges': distinct,
                                'mean': axis_use[axis] / distinct if distinct else 0,
                                'available_directed_edges': sum(1 for edge, data in g.edges.items() if data['axis'] == axis)}
    target_coverage = {field: {'represented_values': len(values),
                              'covered_values': len(set(target_counts[field]) & values),
                              'missing_values': sorted(values - set(target_counts[field]), key=str)}
                       for field, values in target_universe.items()}
    return sessions, {
        'sampling_variant': 'v5.3_explicit_core_first_step_coverage',
        'requested_sessions': total, 'sampled_sessions': len(sessions),
        'complete': len(sessions) == total,
        'quota_counts': dict(Counter(f'{k}_{n}' for k, n in jobs)),
        'failed_jobs': failed_jobs, 'errors_and_retries': dict(errors),
        'hard_directed_edge_cap': 4, 'attempt_cap_counts': dict(cap_attempts),
        'edge_reuse_histogram': dict(sorted(edge_hist.items())),
        'four_use_edge_fraction': edge_hist[4] / len(edge_use) if edge_use else 0,
        'four_use_edge_soft_target': .005,
        'axis_counts': dict(axis_use), 'nonidentity_axis_mean': mean_nonid,
        'nonidentity_relative_deviation': deviation,
        'nonidentity_balance_within_10_percent': all(abs(x) <= .10 for x in deviation.values()),
        'axis_reuse': per_axis_reuse,
        'source_conditioned_formal_axis_expectation': dict(axis_expected),
        'conditional_wardrobe_mode_counts': dict(modes),
        'conditional_wardrobe_mode_expectation': dict(mode_expected),
        'unused_nodes': len(g.nodes) - len(node_use),
        'unused_start_nodes': len(g.nodes) - len(starts),
        'isolated_start_nodes': len(g.nodes) - sum(map(len, by_identity.values())),
        'identity_start_counts': {str(k): v for k, v in sorted(identity_starts.items())},
        'edited_attribute_target_coverage': target_coverage,
        'history_axis_decay': .5, 'history_revisits_allowed': True,
        'start_policy': 'soft identity balance; unused node starts; marginal attribute feedback; residual edge support',
        'axis_policy': 'legal identity=2/other=1; whole-history 0.5**n; global count feedback',
        'feedback_exponent': feedback_exponent,
        'planned_edit_steps': planned_steps,
        'soft_identity_target_fraction': identity_target_fraction,
        'nonidentity_axis_terminal_target': nonidentity_target,
        'nonidentity_axis_hard_upper': nonidentity_upper,
        'nonidentity_upper_slack': nonidentity_upper_slack,
        'cap2_attempts_before_cap3': cap2_attempts,
        'core_coverage_warmup_enabled': enforce_core_coverage,
        'forced_coverage_job_count': len(forced_coverage_jobs),
        'forced_coverage_jobs': forced_coverage_jobs,
        'core_coverage_override_policy': 'For missing changed-in core values, lock a genuine directed wardrobe edge as round one of an existing fixed job; prioritize scarce incoming support, low reuse, and new-core gain. Kind, length, fork round and fork source remain unchanged. This is explicit coverage sampling, not pure random selection.',
        'reuse_note': 'Reuse below two can result from coverage, zero/one-use preference, fixed fork jobs, and local graph support; no missing edge is invented to raise reuse.',
        'full_catalog_target_uniformity_claimed': False,
    }
