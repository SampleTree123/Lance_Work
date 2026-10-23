"""Pooled-start full-domain session construction, offline only.

The finite root pool is an explicit experimental restriction on initial support.
All subsequent edits sample the full current catalog, never existing neighbors.
This is a measured construction route, not an impossibility proof or a lower bound.
"""
from __future__ import annotations
import argparse, copy, json, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1] / 'dataset_trial_build_20261021_v1'
sys.path.insert(0, str(V1))
from build_trial import Domain, Graph, AXES, COLORS, ID_CAMERAS, UPPER, quotas, weighted, token, write, save_graph


class ObservedGraph(Graph):
    """Store exactly sampled transitions, without O(nodes^2) adjacency closure."""
    def add(self, state, parent=None, axis=None):
        key = self.d.canonical(state)
        if key in self.forbidden:
            raise ValueError('cross-split canonical collision')
        if key in self.known:
            return self.known[key]
        i = len(self.nodes)
        self.nodes.append(state); self.keys.append(key); self.known[key] = i
        self.adj.append(defaultdict(list)); self.provenance.append({'parent':parent, 'axis':axis})
        return i

    def register(self, u, v, axis):
        edge = self.d.edge(self.nodes[u], self.nodes[v], axis)
        assert edge is not None
        if (u, v) not in self.edges:
            self.edges[u, v] = edge; self.adj[u][axis].append(v)
        return edge


class ExactDomain(Domain):
    def __init__(self):
        super().__init__()
        self.choice_cache = {}
        self.whole_families = {sex:[f['family_id'] for f in self.cat['sexes'][sex]['families']] for sex in self.ids}

    def choices(self, s):
        # Actual non-noop targets determine eligibility before the axis draw.
        k = self.canonical(s)
        if k in self.choice_cache:
            return self.choice_cache[k]
        choices = {}
        for axis, values in {'identity':self.ids[s['sex']], 'hair':self.hairs[s['sex']],
                             'hair_color':COLORS, 'action':self.actions,
                             'camera':self.cameras, 'site':self.sites}.items():
            if axis not in self.allowed_axes(s):
                continue
            values = [v for v in values if v != s[axis] and self.valid({**s, axis:v})]
            if values:
                choices[axis] = values
        if 'wardrobe' in self.allowed_axes(s):
            singles = self.singles(s)
            families = [f for f in self.whole_families[s['sex']] if f != s['wardrobe']['family_id']]
            if singles or families:
                choices['wardrobe'] = {'singles':singles, 'families':families}
        self.choice_cache[k] = choices
        return choices

    def exact_edit(self, s, rng):
        opts = self.choices(s)
        axes = list(opts)
        axis = weighted(rng, axes, [2 if a == 'identity' else 1 for a in axes])
        target = copy.deepcopy(s)
        if axis == 'wardrobe':
            singles, families = opts[axis]['singles'], opts[axis]['families']
            mode = rng.choice(['single_piece', 'whole_outfit']) if singles and families else ('single_piece' if singles else 'whole_outfit')
            if mode == 'single_piece':
                slot = rng.choice(sorted({r['slot'] for r in singles}))
                target['wardrobe'] = copy.deepcopy(rng.choice([r for r in singles if r['slot'] == slot])['choice'])
            else:
                family = rng.choice(families)
                target['wardrobe'] = self.nc.sample_choice(s['sex'], rng, family_id=family, hair_id=s['wardrobe'].get('hair_id'))
            # The current catalog's other families must change visible core. Stop
            # if that catalog property ceases to hold; never repair by resampling.
            assert self.edge(s, target, axis) is not None, 'catalog whole-target validity assumption failed'
        else:
            values = opts[axis]
            target[axis] = weighted(rng, values, [1.5 if axis == 'camera' and v in ID_CAMERAS else 1 for v in values])
        assert self.valid(target)
        assert [a for a, x, y in zip(AXES, self.canonical(s), self.canonical(target)) if x != y] == [axis]
        return target, axis, opts


def root_pool(d, per_identity, rng, forbidden):
    pool = defaultdict(list)
    for sex in ('female', 'male'):
        for identity in d.ids[sex]:
            for _ in range(per_identity):
                while True:
                    state = d.initial(rng)
                    if state['sex'] != sex:
                        continue
                    state['identity'] = identity
                    if d.canonical(state) not in forbidden:
                        pool[sex, identity].append(state)
                        break
    return pool


def session_signature(session):
    return session['history'][0], tuple((s['source_position'], s['target']) for s in session['steps'])


def audit(g, sessions, expected_axis, wardrobe_both, wardrobe_both_single):
    counts = Counter(r['axis'] for s in sessions for r in s['steps'])
    start_sex = Counter(g.nodes[s['history'][0]]['sex'] for s in sessions)
    starts = Counter(g.nodes[s['history'][0]]['identity'] for s in sessions)
    return {'observed_axis_counts':dict(counts), 'expected_axis_counts_given_real_sources':dict(expected_axis),
            'observed_over_expected_axis':{a:counts[a]/e for a,e in expected_axis.items()},
            'wardrobe_both_branches_available_steps':wardrobe_both,
            'single_given_both_available':wardrobe_both_single/wardrobe_both if wardrobe_both else None,
            'initial_sex_counts':dict(start_sex), 'initial_identity_counts':dict(starts),
            'initial_support_warning':'Each identity has a fixed finite root pool; other initial attributes have finite correlated support. This does not satisfy a full-catalog initial-draw interpretation.',
            'adjacency_warning':'Graph edges record observed transitions only; missing graph neighbors are not missing true-domain eligibility.'}


def build(d, total, budget, per_identity, seed, forbidden, output, write_unbounded=False):
    rng = random.Random(seed); g = ObservedGraph(d, forbidden)
    pool = root_pool(d, per_identity, rng, forbidden)
    root_ids = {key:[g.add(state) for state in rows] for key,rows in pool.items()}
    schedule = quotas(total); rng.shuffle(schedule)
    sessions = []; seen = set(); expected_axis = Counter(); wardrobe_both = wardrobe_both_single = 0
    duplicate_structures = 0; cutoff = None; curve = []; collision = None
    for kind, length in schedule:
        ft = rng.randrange(2, length+1) if kind == 'fork' else None
        fp = rng.randrange(ft-1) if ft else None
        sex = rng.choice(['female','male']); identity = rng.choice(d.ids[sex])
        root = rng.choice(root_ids[sex, identity])
        states = [g.nodes[root]]; planned = []
        # Plan the complete chain before committing any node/edge/counter.
        old_nodes = len(g.nodes)
        for t in range(1, length+1):
            p = fp if t == ft else t-1
            target, axis, opts = d.exact_edit(states[p], rng)
            # Cross-split overlap is reported, never silently repaired by another draw.
            if d.canonical(target) in forbidden:
                collision = {'at_session':len(sessions), 'at_round':t, 'axis':axis,
                             'target_state':target, 'policy':'stop before committing whole chain; do not redraw'}
                break
            planned.append((p,target,axis,opts)); states.append(target)
        if collision:
            break
        history = [root]; steps = []
        for p,target,axis,opts in planned:
            u = history[p]; v = g.add(target,u,axis); edge = g.register(u,v,axis)
            norm = sum(2 if a == 'identity' else 1 for a in opts)
            for a in opts:
                expected_axis[a] += (2 if a == 'identity' else 1) / norm
            if axis == 'wardrobe' and opts[axis]['singles'] and opts[axis]['families']:
                wardrobe_both += 1; wardrobe_both_single += edge['mode'] == 'single_piece'
            steps.append({'source_position':p, 'source':u, 'target':v, **edge}); history.append(v)
        session = {'id':f'session_{len(sessions):06d}', 'kind':kind, 'length':length,
                   'fork_round':ft, 'history':history, 'steps':steps}
        signature = session_signature(session)
        if signature in seen:
            # Do not redraw the session: that would condition exact draws on uniqueness.
            duplicate_structures += 1
        seen.add(signature); sessions.append(session)
        if cutoff is None and len(g.nodes) > budget:
            cutoff = {'sessions':len(sessions)-1, 'nodes':old_nodes,
                      'unfilled_budget_nodes':budget-old_nodes,
                      'first_nonfitting_chain_nodes':len(g.nodes)-old_nodes,
                      'first_nonfitting_chain_length':length,
                      'expected_axis_including_first_nonfitting_chain':dict(expected_axis),
                      'definition':'Prefix before first full chain that cannot fit; no rejection/resampling or partial-chain commit.'}
        if len(sessions) in {100,250,500,1000,2400,6000,12000}:
            curve.append({'sessions':len(sessions), 'nodes':len(g.nodes), 'used_edges':len(g.edges)})
    cutoff = cutoff or {'sessions':len(sessions), 'nodes':len(g.nodes), 'unfilled_budget_nodes':budget-len(g.nodes)}
    n = cutoff['nodes']; kept = cutoff['sessions']
    prefix = ObservedGraph(d, forbidden)
    for i,state in enumerate(g.nodes[:n]):
        p = g.provenance[i]
        prefix.add(state, p['parent'], p['axis'])
    for s in sessions[:kept]:
        for r in s['steps']:
            prefix.register(r['source'],r['target'],r['axis'])
    meta = {'route':'finite_pooled_roots_full_domain_edits_hard_prefix_budget',
            'root_nodes':sum(map(len, root_ids.values())), 'per_identity_roots':per_identity,
            'budget':budget, 'requested_sessions':total, 'budget_cutoff':cutoff,
            'camera_target_weights':'four ID cameras 1.5; others 1, matching current user clarification',
            'natural_revisit_repair':False, 'duplicates_redrawn':False}
    metrics = save_graph(output/'budget_prefix', prefix, sessions[:kept], meta)
    summary = {'root_nodes':meta['root_nodes'], 'requested_sessions':total,
               'actual_full_domain_nodes':len(g.nodes), 'budget':budget,
               'budget_prefix_sessions':kept, 'budget_prefix_nodes':n,
               'session_deficit':total-kept, 'duplicate_structures':duplicate_structures,
               'completed_unbounded_sessions':len(sessions), 'cross_split_collision':collision,
               'curve':curve, 'audit':audit(g,sessions,expected_axis,wardrobe_both,wardrobe_both_single),
               'natural_revisit_session_fraction':sum(len(set(s['history']))<len(s['history']) for s in sessions)/len(sessions),
               'single_axis_sessions':sum(len({r['axis'] for r in s['steps']})==1 for s in sessions),
               'terminal_fork_sessions':sum(s['fork_round']==s['length'] for s in sessions),
               'budget_prefix_metrics':metrics,
               'claims':'Measured cost of this route only; not a necessary node count, theoretical lower bound, or proof of impossibility.'}
    output.mkdir(parents=True, exist_ok=True)
    write(output/'SUMMARY.json',summary)
    if write_unbounded:
        save_graph(output/'full_domain',g,sessions,meta)
    return summary, set(g.keys), set(prefix.keys)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); ap.add_argument('--save-full',action='store_true'); ap.add_argument('--resume',action='store_true'); args=ap.parse_args()
    started=time.time(); d=ExactDomain(); reports={}
    for roots_per_id in (1,2,4):
        total = 1000 if args.quick or roots_per_id != 1 else 12000
        tag=f'roots_{40*roots_per_id}_train'
        if args.resume and (HERE/tag/'SUMMARY.json').exists():
            summary=json.loads((HERE/tag/'SUMMARY.json').read_text(encoding='utf-8'))
            prefixkeys={d.canonical(r['state']) for r in json.loads((HERE/tag/'budget_prefix/nodes.json').read_text(encoding='utf-8'))}
        else:
            summary, fullkeys, prefixkeys = build(d,total,2500,roots_per_id,202610210+roots_per_id,set(),HERE/tag,args.save_full)
        reports[tag]=summary
        print(tag, json.dumps({k:summary[k] for k in ('actual_full_domain_nodes','budget_prefix_sessions','natural_revisit_session_fraction','duplicate_structures')}),flush=True)
        if roots_per_id == 1:
            summary_test, testkeys, testprefixkeys = build(d,2400 if not args.quick else 1000,500,roots_per_id,202610310+roots_per_id,prefixkeys,HERE/'roots_40_test',args.save_full)
            reports['roots_40_test']=summary_test
            assert not prefixkeys & testkeys
            print('roots_40_test',json.dumps({k:summary_test[k] for k in ('actual_full_domain_nodes','budget_prefix_sessions','natural_revisit_session_fraction','duplicate_structures')}),flush=True)
    reports['elapsed_seconds']=time.time()-started
    write(HERE/'SUMMARY.json',reports)

if __name__=='__main__':
    main()
