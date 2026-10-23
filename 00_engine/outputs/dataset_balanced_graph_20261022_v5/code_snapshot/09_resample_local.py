"""Offline local-support session sampler; construction-aware coverage, no history ban."""
from __future__ import annotations
import argparse
import copy
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
V1 = ROOT.parent / 'dataset_trial_build_20261021_v1'
sys.path.insert(0, str(V1))
from build_trial import Domain, Graph, AXES, ID_CAMERAS, quotas, weighted, save_graph, read, write


def load_graph(path, d, forbidden=None):
    g = Graph(d, forbidden)
    for row in read(path / 'nodes.json'):
        p = row.get('created_by', {})
        idx = g.add(row['state'], p.get('parent'), p.get('axis'))
        assert idx == row['id'], 'Node IDs must preserve input order; no split overlap.'
    return g


def sample_local(g, total, seed, balance=True):
    rng = random.Random(seed)
    jobs = quotas(total)
    rng.shuffle(jobs)
    by_id = defaultdict(list)
    for i, s in enumerate(g.nodes):
        if any(g.adj[i].values()):
            by_id[s['identity']].append(i)
    identities = sorted(by_id)
    # Equal counts per represented identity; all 40 identities expected from builder.
    starts = [identities[i % len(identities)] for i in range(total)]
    rng.shuffle(starts)
    unseen = {k: set(v) for k, v in by_id.items()}
    out = []
    seen = set()
    used = Counter()
    axis_actual = Counter()
    axis_expected = Counter()
    mode_actual = Counter()
    mode_expected = Counter()
    starts_seen = defaultdict(Counter)
    errors = Counter()
    history_revisits = 0
    camsum = sum(1.5 if x in ID_CAMERAS else 1 for x in g.d.cameras)

    def start_weight(i):
        s = g.nodes[i]
        n = len(out)
        goals = {
            'camera': (1.5 if s['camera'] in ID_CAMERAS else 1) / camsum,
            'site': 1 / len(g.d.sites), 'action': 1 / len(g.d.actions),
            'hair_color': 1 / 7,
        }
        w = 1 / (1 + used[i]) ** .25
        for k, target in goals.items():
            ratio = (n * target + 8) / (starts_seen[k][s[k]] + 8)
            w *= max(.2, min(5, ratio)) ** .65
        return w

    for job, ident in zip(jobs, starts):
        kind, length = job
        ft = rng.randrange(2, length + 1) if kind == 'fork' else None
        fp = rng.randrange(ft - 1) if ft else None
        for attempt in range(1000):
            candidates = sorted(unseen[ident]) or by_id[ident]
            u0 = weighted(rng, candidates, [start_weight(i) for i in candidates])
            history = [u0]
            steps = []
            local_actual = axis_actual.copy()
            local_expected = axis_expected.copy()
            local_modes = mode_actual.copy()
            local_mode_expected = mode_expected.copy()
            for t in range(1, length + 1):
                p = fp if t == ft else t - 1
                u = history[p]
                s = g.nodes[u]
                formal = g.d.allowed_axes(s)
                denom = sum(2 if a == 'identity' else 1 for a in formal)
                for a in formal:
                    local_expected[a] += (2 if a == 'identity' else 1) / denom
                axes = [a for a in formal if g.adj[u].get(a)]
                if not axes:
                    break
                weights = []
                for a in axes:
                    compensation = ((local_expected[a] + 20) / (local_actual[a] + 20)) ** 2 if balance else 1
                    weights.append((2 if a == 'identity' else 1) * compensation)
                a = weighted(rng, axes, weights)
                vs = g.adj[u][a]
                if a == 'wardrobe':
                    by_mode = defaultdict(list)
                    for v in vs:
                        by_mode[g.edges[u, v]['mode']].append(v)
                    formal_single = bool(g.d.singles(s))
                    if formal_single:
                        for mode in ['single_piece', 'whole_outfit']:
                            local_mode_expected[mode] += .5
                        mw = [((local_mode_expected[m] + 5) / (local_modes[m] + 5)) ** 2 if balance else 1 for m in sorted(by_mode)]
                    else:
                        mw = [1 for m in sorted(by_mode)]
                    mode = weighted(rng, sorted(by_mode), mw)
                    vs = by_mode[mode]
                    if formal_single:
                        local_modes[mode] += 1
                    if mode == 'single_piece':
                        slots = sorted({g.edges[u, v]['slot'] for v in vs})
                        slot = rng.choice(slots)
                        vs = [v for v in vs if g.edges[u, v]['slot'] == slot]
                    else:
                        for field in ['family_id', 'group_id']:
                            values = sorted({g.nodes[v]['wardrobe'][field] for v in vs})
                            val = rng.choice(values)
                            vs = [v for v in vs if g.nodes[v]['wardrobe'][field] == val]
                v = weighted(rng, vs, [1.5 if a == 'camera' and g.nodes[v]['camera'] in ID_CAMERAS else 1 for v in vs])
                steps.append({'source_position': p, 'source': u, 'target': v, **g.edges[u, v]})
                history.append(v)
                local_actual[a] += 1
            if len(steps) != length:
                errors['dead_end_attempts'] += 1
                continue
            sig = (u0, tuple((s['source_position'], s['target']) for s in steps))
            if sig in seen:
                errors['duplicate_structure_attempts'] += 1
                continue
            seen.add(sig)
            out.append({'id': f'session_{len(out):06d}', 'kind': kind, 'length': length, 'fork_round': ft, 'history': history, 'steps': steps})
            axis_actual, axis_expected = local_actual, local_expected
            mode_actual, mode_expected = local_modes, local_mode_expected
            unseen[ident].discard(u0)
            used.update(history)
            for k in ['camera', 'site', 'action', 'hair_color']:
                starts_seen[k][g.nodes[u0][k]] += 1
            history_revisits += len(set(history)) < len(history)
            break
        else:
            errors[f'unfilled_{kind}_{length}'] += 1
        if len(out) and len(out) % 3000 == 0:
            print('sampled', len(out), 'revisit', history_revisits, flush=True)
    return out, {
        'start_policy': 'equal represented identity job counts; unseen node starts before reuse; marginal camera/site/action/color feedback',
        'represented_identity_count': len(identities),
        'unseen_start_nodes': sum(map(len, unseen.values())),
        'axis_policy': 'formal axis weights within local support with cumulative marginal compensation' if balance else 'formal axis weights renormalized over local support',
        'axis_compensation_exponent': 2 if balance else 0,
        'axis_counts': dict(axis_actual), 'source_conditioned_formal_axis_expectation': dict(axis_expected),
        'conditional_wardrobe_mode_counts': dict(mode_actual), 'conditional_wardrobe_mode_expectation': dict(mode_expected),
        'history_avoidance_or_revisit_quota': False,
        'full_catalog_target_uniformity_claimed': False,
        'errors_and_retries': dict(errors),
        'notes': 'Global compensation is an experimental implementation, not exact per-source probability preservation. No changed target can violate formal semantic legality.',
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'balanced')
    p.add_argument('--no-balance', action='store_true')
    a = p.parse_args()
    d = Domain()
    forbidden = set()
    report = {}
    for j, (split, count) in enumerate([('train', 12000), ('test', 2400)]):
        g = load_graph(a.input / split, d, forbidden)
        ss, meta = sample_local(g, count, 20261023 + j, not a.no_balance)
        report[split] = save_graph(a.output / split, g, ss, {'source_graph': str(a.input.resolve()), 'sampling': meta})
        forbidden.update(g.keys)
        print(split, report[split]['sessions'], report[split]['unused_nodes'], report[split]['axis_percent'], flush=True)
    write(a.output / 'SUMMARY.json', report)


if __name__ == '__main__':
    main()
