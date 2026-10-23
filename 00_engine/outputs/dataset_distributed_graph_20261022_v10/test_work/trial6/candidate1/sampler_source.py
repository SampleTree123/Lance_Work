"""V6 offline sampler with exact start-camera quotas and legal slot feedback.

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
           identity_target_fraction=.09, nonidentity_upper_slack=.06,
           cap2_attempts=12, enforce_core_coverage=True,
           camera_capacity_preflight=True, support_lookahead_strength=1.0,
           history_decay=.5, enforce_attribute_target_coverage=True,
           start_support_exponent=4.0, tail_fallback_after=120):
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
    if not 0 < history_decay <= 1:
        raise ValueError('history_decay must be in (0,1] to preserve natural repeats')
    if tail_fallback_after < 0:
        raise ValueError('tail_fallback_after must be nonnegative')
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
    by_camera_identity = defaultdict(lambda: defaultdict(list))
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
            ident = (state.get('sex'), state['identity'])
            by_identity[ident].append(u)
            by_camera_identity[state['camera']][ident].append(u)
    identities = sorted(by_identity)
    if total and not identities:
        raise ValueError('graph has no explicit legal directed edges')
    cameras = list(dict.fromkeys(g.d.cameras))
    camera_weights = {camera: 1.5 if camera in ID_CAMERAS else 1 for camera in cameras}
    camera_weight_sum = sum(camera_weights.values())
    camera_exact = {camera: total * camera_weights[camera] / camera_weight_sum for camera in cameras}
    camera_quota = {camera: math.floor(camera_exact[camera]) for camera in cameras}
    remainder_order = sorted(cameras, key=lambda camera: -(camera_exact[camera] - camera_quota[camera]))
    for camera in remainder_order[:total - sum(camera_quota.values())]:
        camera_quota[camera] += 1
    camera_support = {}
    for camera in cameras:
        source_nodes = [u for nodes in by_camera_identity[camera].values() for u in nodes]
        first_edges = sum(len(vs) for u in source_nodes for vs in explicit[u].values())
        camera_support[camera] = {'start_nodes': len(source_nodes),
                                  'outgoing_directed_edges': first_edges,
                                  'hard_first_step_capacity': 4 * first_edges,
                                  'requested_starts': camera_quota[camera],
                                  'necessary_capacity_sufficient': 4 * first_edges >= camera_quota[camera]}
    insufficient = {camera: row for camera, row in camera_support.items()
                    if not row['necessary_capacity_sufficient']}
    if insufficient and camera_capacity_preflight:
        # This bound uses just the first edge of each session, so failure is a
        # proof of impossibility even before considering later-chain demand.
        return [], {
            'sampling_variant': 'v6.8_tail_live_source_fallback',
            'requested_sessions': total, 'sampled_sessions': 0, 'complete': False,
            'blocked_by': 'provably_insufficient_start_camera_edge_capacity',
            'start_camera_quota': camera_quota,
            'start_camera_counts': {camera: 0 for camera in cameras},
            'start_camera_quota_deficits': camera_quota,
            'start_camera_quota_met': False,
            'start_camera_graph_support': camera_support,
            'insufficient_start_camera_support': insufficient,
            'quota_redistribution_permitted': False,
            'unattempted_jobs': len(jobs),
            'axis_counts': {}, 'edge_reuse_histogram': {},
            'nonidentity_relative_deviation': {}, 'unused_nodes': len(g.nodes),
            'unused_start_nodes': len(g.nodes),
            'errors_and_retries': {'camera_capacity_preflight_block': 1},
        }
    formal_slots = [tuple(sorted({row['slot'] for row in g.d.singles(state)})) for state in g.nodes]

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
    attribute_incoming = defaultdict(list)
    edge_target_values = {}
    for u, axes in enumerate(explicit):
        for axis, vs in axes.items():
            for v in vs:
                tokens = frozenset(edited_target_attributes(u, v, axis))
                edge_target_values[u, v] = tokens
                for field, value in tokens:
                    attribute_incoming[field, value].append((u, v))
                gained = frozenset(value for field, value in tokens if field == 'wardrobe_core')
                if gained:
                    edge_new_core[u, v] = gained
                    for value in gained:
                        core_incoming[value].append((u, v))

    sessions, seen = [], set()
    edge_use, node_use, starts, identity_starts = Counter(), Counter(), Counter(), Counter()
    axis_use, axis_expected = Counter(), Counter()
    target_counts, start_counts = defaultdict(Counter), defaultdict(Counter)
    modes, mode_expected = Counter(), Counter()
    slot_actual, slot_expected, missing_slot_support = Counter(), Counter(), Counter()
    camera_slot_actual, camera_slot_expected = defaultdict(Counter), defaultdict(Counter)
    camera_starts = Counter()
    support_lookahead_cache = {}
    eligible_start_cache = {}
    tail_fallback_counts = Counter()
    tail_fallback_jobs = []
    errors, cap_attempts, failed_jobs = Counter(), Counter(), []
    forced_allaxis_coverage_jobs = []
    unseen_starts = {ident: set(nodes) for ident, nodes in by_identity.items()}
    start_attr_fields = ('identity', 'camera', 'site', 'action', 'hair', 'hair_color',
                         'wardrobe_family', 'wardrobe_group')

    history_counts = defaultdict(Counter)
    history_cache = {}
    visible_assets = []
    frequency_fields = ('identity','action','hair','hair_color','site')
    frequency_pools = {f: {s[f] for s in g.nodes} for f in frequency_fields}
    frequency_cameras = defaultdict(set)
    all_visible_core = set()
    for state in g.nodes:
        core = set(g.d.nc.core_asset_ids(state['sex'],state['wardrobe']))
        if state['camera']=='front_head': core=set()
        elif state['camera'] in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}:
            core &= set(g.d.nc.upper_asset_ids(state['sex'],state['wardrobe']))
        visible_assets.append(core); all_visible_core.update(core)
        if state['camera']!='front_head': frequency_cameras[state['action']].add(state['camera'])

    def occurrence_weight(u):
        if u in history_cache:return history_cache[u]
        state=g.nodes[u];total=sum(node_use.values())
        weight=((total/max(1,len(g.nodes))+2)/(node_use[u]+2))**1.5
        for field in frequency_fields:
            expected=(total+20)/len(frequency_pools[field])
            ratio=(expected+5)/(history_counts[field][state[field]]+5)
            weight*=max(.20,min(5,ratio))**1.0
        core=visible_assets[u]
        if core:
            expected=(sum(history_counts['visible_core'].values())+20)/max(1,len(all_visible_core))
            weight*=math.exp(sum(math.log(max(.15,min(6,(expected+5)/(history_counts['visible_core'][v]+5)))) for v in core)/len(core)*4.0)
        if state['camera']!='front_head':
            expected=(sum(v for (act,cam),v in history_counts['action_camera'].items() if act==state['action'])+10)/max(1,len(frequency_cameras[state['action']]))
            weight*=max(.15,min(6,(expected+4)/(history_counts['action_camera'][state['action'],state['camera']]+4)))**3.0
        history_cache[u]=weight
        return weight

    def camera_frequency_ratio(u):
        state=g.nodes[u]
        if state['camera']=='front_head':return 1.0
        expected=(sum(v for (act,cam),v in history_counts['action_camera'].items() if act==state['action'])+10)/max(1,len(frequency_cameras[state['action']]))
        return (expected+4)/(history_counts['action_camera'][state['action'],state['camera']]+4)

    def camera_exit_start_weight(u):
        if g.nodes[u]['camera'] not in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}:return 1.0
        if camera_frequency_ratio(u)>.90:return 1.0
        return 4.0 if explicit[u].get('camera') else .20

    def axis_frequency_weight(u,axis,options):
        if axis not in ('camera','action'):return 1.0
        current=max(.1,camera_frequency_ratio(u))
        ratios=[camera_frequency_ratio(v)/current for v in options]
        return max(.15,min(8,sum(ratios)/len(ratios)))**2

    def source_support_weight(u):
        """Favor sources that can actually serve current formal mode/slot debt.

        This changes source exposure, never legal slot definitions. A formally
        available but absent slot remains absent; current endpoint choices may
        instead move the next edit to a better-supported source state.
        """
        if not support_lookahead_strength or not formal_slots[u]:
            return 1.0
        if u in support_lookahead_cache:
            return support_lookahead_cache[u]
        available_slots = set()
        has_whole = False
        for v in explicit[u].get('wardrobe', ()):
            if edge_use[u, v] >= 3:
                continue
            edge = g.edges[u, v]
            if edge['mode'] == 'single_piece':
                available_slots.add(edge['slot'])
            elif edge['mode'] == 'whole_outfit':
                has_whole = True
        formal = formal_slots[u]
        slot_desire = {slot: max(.03, min(30, ((slot_expected[slot] + 8)
                                              / (slot_actual[slot] + 8)) ** 2)) for slot in formal}
        # Compare the best debt-serving real slot against this source's own
        # formal expectation. A one-slot full-body source is neutral rather
        # than automatically beating a multi-slot shirt/pants source.
        available_desire = [slot_desire[slot] for slot in formal if slot in available_slots]
        formal_mean_desire = sum(slot_desire.values()) / len(formal)
        single_quality = (max(0.0, min(2.0, 1 + math.log(max(available_desire) / formal_mean_desire)))
                          if available_desire else 0.0)
        single_desire = max(.05, min(20, ((mode_expected['single_piece'] + 8)
                                         / (modes['single_piece'] + 8)) ** 2))
        whole_desire = max(.05, min(20, ((mode_expected['whole_outfit'] + 8)
                                        / (modes['whole_outfit'] + 8)) ** 2))
        quality = (single_desire * single_quality + whole_desire * has_whole) / (single_desire + whole_desire)
        weight = ((.1 + 2.9 * quality) / 3) ** support_lookahead_strength
        support_lookahead_cache[u] = weight
        return weight

    def choose_start_camera():
        # Every successful start consumes exactly one catalog-camera quota.
        # Missing support is never redistributed to a different camera target.
        possible = [camera for camera in cameras if camera_starts[camera] < camera_quota[camera]
                    and by_camera_identity[camera]]
        if not possible:
            return None
        return _choose(rng, possible, [camera_quota[c] - camera_starts[c] for c in possible])

    def start_node(attempt, cap, camera, length):
        if camera is None:
            return None
        tail_fallback = attempt >= tail_fallback_after
        if tail_fallback:
            tail_fallback_counts['source_selection_attempts'] += 1
        cache_key = (camera, cap)
        if cache_key not in eligible_start_cache:
            live_groups, live_residual, live_breadth = {}, {}, {}
            for ident, nodes in by_camera_identity[camera].items():
                live_nodes = []
                for u in nodes:
                    residual = 0
                    breadth = 0
                    for axis, vs in explicit[u].items():
                        if axis != 'identity' and axis_use[axis] >= nonidentity_upper:
                            continue
                        deficit = (nonidentity_target - axis_use[axis]) / max(1, nonidentity_target)
                        urgency = 1 if axis == 'identity' else max(.05, deficit)
                        available = sum(edge_use[u, v] < cap for v in vs)
                        residual += urgency * available
                        breadth += bool(available)
                    if residual > 0:
                        live_nodes.append(u)
                        live_residual[u] = residual
                        live_breadth[u] = breadth
                if live_nodes:
                    live_groups[ident] = live_nodes
            eligible_start_cache[cache_key] = live_groups, live_residual, live_breadth
        live_groups, live_residual, live_breadth = eligible_start_cache[cache_key]
        camera_ids = sorted(live_groups)
        if not camera_ids:
            if tail_fallback:
                tail_fallback_counts['no_live_source_at_current_cap'] += 1
            return None
        wanted = min(length, 5)
        support = {u: (min(wanted, live_breadth[u]) / wanted) ** start_support_exponent
                   for nodes in live_groups.values() for u in nodes}
        identity_support = {ident: sum(support[u] for u in nodes) / len(nodes)
                            for ident, nodes in live_groups.items()}
        if tail_fallback:
            # All real live sources in the fixed camera become eligible. Do
            # not first choose an identity or impose the unseen-node pool.
            candidates = sorted(u for nodes in live_groups.values() for u in nodes)
        else:
            ident = _choose(rng, camera_ids,
                            [identity_support[x] / (1 + identity_starts[x]) ** 1.5 for x in camera_ids])
            nodes = live_groups[ident]
            unseen = [u for u in nodes if u in unseen_starts[ident]]
            pool = unseen or nodes
            candidates = rng.sample(pool, min(start_pool, len(pool)))
        weights = []
        for u in candidates:
            weight = 1 / (1 + starts[u]) ** .6
            for field, value in attributes[u]:
                if field in start_attr_fields:
                    weight *= (1 / (1 + start_counts[field][value])) ** .12
            capacity_weight = (live_residual[u] * live_breadth[u] ** 2 if tail_fallback
                               else min(4, math.sqrt(live_residual[u])))
            weights.append(weight * capacity_weight * source_support_weight(u) * support[u] * occurrence_weight(u) * camera_exit_start_weight(u))
        return _choose(rng, candidates, weights)

    def target_weight(u, v, axis, local_edges):
        count = edge_use[u, v] + local_edges[u, v]
        # Both zero/one-use edges are preferred; four-use edges are unavailable.
        weight = (.30, 1.0, 3.0, .0005)[count]
        weight *= 1.8 if not node_use[v] else (1 + node_use[v]) ** -.10
        if axis == 'camera' and g.nodes[v]['camera'] in ID_CAMERAS:
            weight *= 1.5
        for field, value in edited_target_attributes(u, v, axis):
            if field == 'wardrobe_core':
                weight *= 64 if not target_counts[field][value] else (1 + target_counts[field][value]) ** -.12
            else:
                weight *= 2.0 if not target_counts[field][value] else (1 + target_counts[field][value]) ** -.25
        return weight * source_support_weight(v) * occurrence_weight(v)

    def coverage_first_edge():
        """Explicit warmup, not a claim of pure stochastic target selection."""
        if not enforce_core_coverage and not enforce_attribute_target_coverage:
            return None
        missing = {token for token in attribute_incoming if not target_counts[token[0]][token[1]]
                   and (enforce_core_coverage if token[0] == 'wardrobe_core' else enforce_attribute_target_coverage)}
        candidates = []
        for token in sorted(missing, key=str):
            available = [edge for edge in attribute_incoming[token] if edge_use[edge] < 4
                         and (g.edges[edge]['axis'] == 'identity' or axis_use[g.edges[edge]['axis']] < nonidentity_upper)
                         and camera_starts[g.nodes[edge[0]]['camera']] < camera_quota.get(g.nodes[edge[0]]['camera'], 0)]
            if available:
                # Deal with scarce genuine incoming transitions first.
                candidates.append((len(available), token, available))
        if not candidates:
            return None
        scarcity = min(row[0] for row in candidates)
        _, token, edges = rng.choice([row for row in candidates if row[0] == scarcity])
        # Prefer zero/one use before considering a third/fourth use, then cover
        # as many genuinely new assets as possible in the selected real edge.
        score = lambda edge: (edge_use[edge] >= 2, edge_use[edge],
                              -len(edge_target_values[edge] & missing))
        best = min(map(score, edges))
        edge = rng.choice([edge for edge in edges if score(edge) == best])
        gains = edge_target_values[edge] & missing
        return {'edge': edge, 'axis': g.edges[edge]['axis'],
                'requested_attribute': {'field': token[0], 'value': token[1]},
                'requested_core': token[1] if token[0] == 'wardrobe_core' else None,
                'unseen_attribute_gains': [{'field': field, 'value': value} for field, value in sorted(gains, key=str)],
                'unseen_core_gains': sorted(value for field, value in gains if field == 'wardrobe_core'),
                'reuse_before': edge_use[edge]}

    for job_index, (kind, length) in enumerate(jobs):
        ft = rng.randrange(2, length + 1) if kind == 'fork' else None
        fp = rng.randrange(ft - 1) if ft is not None else None
        coverage_override = coverage_first_edge()
        job_camera = (g.nodes[coverage_override['edge'][0]]['camera']
                      if coverage_override else choose_start_camera())
        job_rejections = Counter()
        for attempt in range(max_attempts):
            # Escalation is about support exhaustion; it cannot change the job.
            cap = 2 if attempt < min(cap2_attempts, max_attempts * .65) else (3 if attempt < max_attempts * .97 else 4)
            if coverage_override:
                cap = max(cap, coverage_override['reuse_before'] + 1)
            cap_attempts[cap] += 1
            u0 = coverage_override['edge'][0] if coverage_override else start_node(attempt, cap, job_camera, length)
            if u0 is None:
                errors['no_live_start_at_current_cap'] += 1
                job_rejections['no_live_start_at_current_cap'] += 1
                if job_camera is not None:
                    continue
                errors['unsupported_remaining_camera_quota'] += 1
                errors[f'unfilled_{kind}_{length}'] += 1
                failed_jobs.append({'job': job_index, 'kind': kind, 'length': length,
                                    'fork_round': ft, 'fork_source_position': fp,
                                    'start_camera': job_camera,
                                    'reason': 'unsupported_remaining_camera_quota'})
                break
            history, steps = [u0], []
            local_edges, local_axes, local_modes = Counter(), Counter(), Counter()
            local_expected, local_mode_expected = Counter(), Counter()
            local_slot_actual, local_slot_expected, local_slot_missing = Counter(), Counter(), Counter()
            local_camera_slot_actual, local_camera_slot_expected = defaultdict(Counter), defaultdict(Counter)
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
                supported_single_slots = {g.edges[u, v]['slot'] for v in options.get('wardrobe', ())
                                          if g.edges[u, v]['mode'] == 'single_piece'}
                if turn == 1 and coverage_override:
                    forced_target = coverage_override['edge'][1]
                    forced_axis = coverage_override['axis']
                    options = ({forced_axis: [forced_target]}
                               if forced_target in options.get(forced_axis, ()) else {})
                if not options:
                    errors['dead_end_or_cap_attempts'] += 1
                    job_rejections['dead_end_under_cap_or_axis_budget'] += 1
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
                                   * history_decay ** local_axes[axis]
                                   * ratio ** feedback_exponent * axis_frequency_weight(u,axis,options[axis]))
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
                        formal = formal_slots[u]
                        if not formal:
                            raise ValueError('graph single-piece edge has no formal legal slot')
                        for formal_slot in formal:
                            local_slot_expected[formal_slot] += 1 / len(formal)
                            local_camera_slot_expected[state['camera']][formal_slot] += 1 / len(formal)
                            if formal_slot not in supported_single_slots:
                                local_slot_missing[formal_slot] += 1
                        slot = _choose(rng, slots, [((slot_expected[sl] + local_slot_expected[sl] + 5)
                                                   / (slot_actual[sl] + local_slot_actual[sl] + 5)) ** 4 for sl in slots])
                        local_slot_actual[slot] += 1
                        local_camera_slot_actual[state['camera']][slot] += 1
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
                job_rejections['duplicate_structure'] += 1
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
            slot_actual.update(local_slot_actual)
            slot_expected.update(local_slot_expected)
            missing_slot_support.update(local_slot_missing)
            for camera, counts in local_camera_slot_actual.items():
                camera_slot_actual[camera].update(counts)
            for camera, counts in local_camera_slot_expected.items():
                camera_slot_expected[camera].update(counts)
            node_use.update(history)
            for history_node in history:
                history_state=g.nodes[history_node]
                for field in frequency_fields:history_counts[field][history_state[field]]+=1
                history_counts['visible_core'].update(visible_assets[history_node])
                if history_state['camera']!='front_head':history_counts['action_camera'][history_state['action'],history_state['camera']]+=1
            history_cache.clear()

            starts[u0] += 1
            camera_starts[g.nodes[u0]['camera']] += 1
            ident = (g.nodes[u0].get('sex'), g.nodes[u0]['identity'])
            identity_starts[ident] += 1
            unseen_starts[ident].discard(u0)
            for field, value in attributes[u0]:
                start_counts[field][value] += 1
            for step in steps:
                for field, value in edited_target_attributes(step['source'], step['target'], step['axis']):
                    target_counts[field][value] += 1
            support_lookahead_cache.clear()
            eligible_start_cache.clear()
            if not coverage_override and attempt >= tail_fallback_after:
                tail_fallback_counts['successful_jobs'] += 1
                tail_fallback_jobs.append({
                    'job': job_index, 'session_id': sessions[-1]['id'],
                    'kind': kind, 'length': length, 'fork_round': ft,
                    'fork_source_position': fp, 'start_camera': job_camera,
                    'accepted_attempt': attempt + 1, 'cap': cap, 'source': u0,
                    'previous_rejections': dict(job_rejections),
                    'reason': 'Normal retries exceeded the configured threshold; broaden source selection within the fixed camera while preserving the complete job and edge caps.',
                })
            if coverage_override:
                forced_allaxis_coverage_jobs.append({
                    'job': job_index, 'session_id': sessions[-1]['id'],
                    'kind': kind, 'length': length, 'fork_round': ft,
                    'fork_source_position': fp, 'forced_round': 1,
                    'source': coverage_override['edge'][0],
                    'target': coverage_override['edge'][1], 'axis': coverage_override['axis'],
                    'mode': steps[0]['mode'],
                    'requested_attribute': coverage_override['requested_attribute'],
                    'new_attribute_target_gains': coverage_override['unseen_attribute_gains'],
                    'requested_core': coverage_override['requested_core'],
                    'new_core_gains': coverage_override['unseen_core_gains'],
                    'edge_reuse_before': coverage_override['reuse_before'],
                })
            break
        else:
            errors[f'unfilled_{kind}_{length}'] += 1
            failed_jobs.append({'job': job_index, 'kind': kind, 'length': length,
                                'fork_round': ft, 'fork_source_position': fp,
                                'start_camera': job_camera})
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
    # Keep the old core-only disclosure schema intact for the inherited audit.
    forced_coverage_jobs = []
    for record in forced_allaxis_coverage_jobs:
        if record['new_core_gains']:
            core_record = dict(record)
            core_record['requested_core'] = record['requested_core'] or record['new_core_gains'][0]
            forced_coverage_jobs.append(core_record)
    return sessions, {
        'sampling_variant': 'v6.8_tail_live_source_fallback',
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
        'single_piece_slot_actual': dict(slot_actual),
        'source_support_lookahead_strength': support_lookahead_strength,
        'start_live_axis_support_exponent': start_support_exponent,
        'tail_source_fallback_after_attempts': tail_fallback_after,
        'tail_source_fallback_counts': dict(tail_fallback_counts),
        'tail_source_fallback_jobs': tail_fallback_jobs,
        'tail_source_fallback_policy': 'After normal retries, select among all real live nodes in the already fixed start camera, weighted by residual directed-edge capacity and axis breadth. Only the soft identity/unseen source partition is bypassed; kind, length, fork, camera quota and every cap remain fixed.',
        'start_live_axis_support_policy': 'Retain soft identity-count compensation, multiplied by real unsaturated distinct-axis support relative to job length. A two-axis source is neutral for L2 and softly downweighted for L5; no repeat or low-diversity session is hard rejected.',
        'source_support_lookahead_policy': 'Softly prefer starts and target nodes with real unsaturated wardrobe edges serving formal single-piece slot deficits and conditional 50:50 mode deficits. Does not invent absent slots or replace source-conditioned formal expectations.',
        'single_piece_slot_source_conditioned_expectation': dict(slot_expected),
        'single_piece_slot_relative_to_expectation': {slot: slot_actual[slot] / expected - 1 if expected else 0
                                                     for slot, expected in slot_expected.items()},
        'single_piece_slot_missing_graph_or_cap_support': dict(missing_slot_support),
        'single_piece_slot_actual_by_camera': {camera: dict(counts) for camera, counts in camera_slot_actual.items()},
        'single_piece_slot_expectation_by_camera': {camera: dict(counts) for camera, counts in camera_slot_expected.items()},
        'start_camera_quota': camera_quota,
        'start_camera_counts': {camera: camera_starts[camera] for camera in cameras},
        'start_camera_quota_deficits': {camera: camera_quota[camera] - camera_starts[camera] for camera in cameras},
        'start_camera_quota_met': all(camera_starts[camera] == camera_quota[camera] for camera in cameras),
        'start_camera_graph_support': camera_support,
        'start_camera_quota_policy': 'Largest-remainder integer quotas over the full catalog: each of the four identity cameras has weight 1.5, every other camera weight 1. Core-coverage starts consume these same quotas. Select a camera once per job, retry within that camera, and never redistribute unsupported quota.',
        'unused_nodes': len(g.nodes) - len(node_use),
        'unused_start_nodes': len(g.nodes) - len(starts),
        'isolated_start_nodes': len(g.nodes) - sum(map(len, by_identity.values())),
        'identity_start_counts': {str(k): v for k, v in sorted(identity_starts.items())},
        'edited_attribute_target_coverage': target_coverage,
        'history_axis_decay': history_decay, 'history_revisits_allowed': True,
        'history_decay_override_from_v5': history_decay != .5,
        'start_policy': 'exact catalog-camera quotas; soft identity balance within camera; unused nodes; residual edge support',
        'axis_policy': f'legal identity=2/other=1; whole-history {history_decay}**n; global count feedback',
        'feedback_exponent': feedback_exponent,
        'planned_edit_steps': planned_steps,
        'soft_identity_target_fraction': identity_target_fraction,
        'nonidentity_axis_terminal_target': nonidentity_target,
        'nonidentity_axis_hard_upper': nonidentity_upper,
        'nonidentity_upper_slack': nonidentity_upper_slack,
        'cap2_attempts_before_cap3': cap2_attempts,
        'core_coverage_warmup_enabled': enforce_core_coverage,
        'attribute_target_coverage_warmup_enabled': enforce_attribute_target_coverage,
        'forced_coverage_job_count': len(forced_coverage_jobs),
        'forced_coverage_jobs': forced_coverage_jobs,
        'forced_allaxis_coverage_job_count': len(forced_allaxis_coverage_jobs),
        'forced_allaxis_coverage_jobs': forced_allaxis_coverage_jobs,
        'core_coverage_override_policy': 'For missing edited attribute targets including genuinely changed-in core values, lock a real directed edge as round one of an existing fixed job; prioritize scarce incoming support, low reuse, and new-value gain. Kind, length, start-camera quota, fork round and fork source remain unchanged. Explicit coverage sampling, not pure random selection.',
        'reuse_note': 'Reuse below two can result from coverage, zero/one-use preference, fixed fork jobs, and local graph support; no missing edge is invented to raise reuse.',
        'full_catalog_target_uniformity_claimed': False,
    }
