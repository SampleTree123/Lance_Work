"""Replace sparse leaves with legal identity/non-identity squares, fixed node budget."""
import copy
import random
from collections import Counter, deque
from pathlib import Path
from resample_local import Domain, Graph, AXES, ID_CAMERAS, load_graph, save_graph, sample_local, write

ROOT = Path(__file__).resolve().parent


def refine(g, count, seed, forbidden):
    rng = random.Random(seed)
    d = g.d
    active = set(range(len(g.nodes)))
    counts = {a: Counter(s['wardrobe']['family_id'] if a == 'wardrobe' else s[a] for s in g.nodes) for a in ['identity','hair','hair_color','wardrobe','action','camera','site']}
    neighbors = {i: set(v for vs in row.values() for v in vs) for i, row in enumerate(g.adj)}
    removed = []
    while len(removed) < count:
        options = []
        for i in active:
            s = g.nodes[i]
            values = {a: s['wardrobe']['family_id'] if a == 'wardrobe' else s[a] for a in counts}
            if any(counts[a][v] <= 1 for a,v in values.items()):
                continue
            ns = neighbors[i] & active
            if len(ns) > 4 or not ns or any(len(neighbors[v] & active) <= 1 for v in ns):
                continue
            axes = {g.edges[i,v]['axis'] for v in ns}
            # Keep represented values; favor weak front-view leaves, then other leaves.
            score = (len(axes), s['camera'] not in ID_CAMERAS, len(ns), rng.random())
            options.append((score, i, values))
        if not options:
            break
        _, i, values = min(options)
        active.remove(i)
        removed.append(i)
        for a,v in values.items():
            counts[a][v] -= 1
    h = Graph(d, forbidden)
    for i in sorted(active):
        h.add(copy.deepcopy(g.nodes[i]))
    added = []
    bridge_counts = Counter()
    attempts = 0
    while len(h.nodes) < len(g.nodes) and attempts < 100000:
        attempts += 1
        eligible = [i for i,s in enumerate(h.nodes) if s['camera'] in ID_CAMERAS and any(a != 'identity' and vs for a,vs in h.adj[i].items())]
        rng.shuffle(eligible)
        if not eligible:
            break
        u = min(eligible[:100], key=lambda i: bridge_counts[h.nodes[i]['identity']])
        s = h.nodes[u]
        target_ids = [x for x in d.ids[s['sex']] if x != s['identity']]
        rng.shuffle(target_ids)
        target = min(target_ids, key=lambda x: bridge_counts[x])
        patch = [u]
        vs = [v for a,values in h.adj[u].items() if a != 'identity' for v in values if h.nodes[v]['camera'] in ID_CAMERAS]
        rng.shuffle(vs)
        patch += vs[:1]
        additions = []
        for v in patch:
            t = copy.deepcopy(h.nodes[v]); t['identity'] = target
            key = d.canonical(t)
            if key not in h.known and key not in forbidden:
                additions.append((v,t))
        if not additions or len(h.nodes) + len(additions) > len(g.nodes):
            continue
        for v,t in additions:
            idx = h.add(t, v, 'identity')
            added.append({'source':v,'target':idx,'axis':'identity'})
        bridge_counts[s['identity']] += len(additions)
        bridge_counts[target] += len(additions)
    assert len(h.nodes) == len(g.nodes), (len(h.nodes), len(g.nodes))
    # Reindex by directed legal spanning edits after pruning, without dangling parents.
    final = Graph(d, forbidden)
    unseen = set(range(len(h.nodes)))
    roots = 0
    while unseen:
        root = min(unseen); unseen.remove(root)
        mapping = {root: final.add(h.nodes[root])}; roots += 1
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for a in AXES:
                for v in h.adj[u].get(a, []):
                    if v not in unseen:
                        continue
                    unseen.remove(v)
                    mapping[v] = final.add(h.nodes[v], mapping[u], a)
                    queue.append(v)
    return final, {'strategy':'prune_low_degree_states_preserving_catalog_values_then_add_identity_nonidentity_squares',
                   'removed_original_indices':removed,'identity_additions_before_reindex':added,'requested_replacements':count,
                   'actual_replacements':len(removed),'reindexed_legal_spanning_roots':roots,
                   'preserve_budget':True,'no_history_filter':True,'source_graph':'blocks/camera_balanced'}


def main():
    d = Domain(); forbidden=set(); summary={}
    for j,(split,total,count) in enumerate([('train',12000,250),('test',2400,50)]):
        original=load_graph(ROOT/'blocks/camera_balanced'/split,d,forbidden)
        g,meta=refine(original,count,20261031+j,forbidden)
        ss,sm=sample_local(g,total,20261101+j)
        meta['sampling']=sm
        summary[split]=save_graph(ROOT/'linked'/split,g,ss,meta)
        forbidden.update(g.keys)
        print(split,len(g.nodes),len(ss),summary[split]['axis_percent'],summary[split]['sessions_with_revisited_node'],flush=True)
    write(ROOT/'linked/SUMMARY.json',summary)


if __name__=='__main__':main()
