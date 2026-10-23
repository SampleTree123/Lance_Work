import sys,json
from pathlib import Path
from collections import Counter,defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;V6=HERE.parent.parent/'dataset_compact_graph_20261022_v6'
sys.path[:0]=[str(V6),str(V6.parent/'dataset_local_support_20261021_v3')]
from resample_local import Domain
from sample_compact_v68_snapshot import _attributes,NON_ID
d=Domain();report={}
for split in ('train','test'):
    p=HERE/f'repair_{split}';n=json.loads((p/'nodes.json').read_text()); ss=[json.loads(l) for l in (p/'sessions.jsonl').read_text().splitlines()]
    states=[r['state'] for r in n]; cache={}
    def attrs(s):
        k=(s['sex'],json.dumps(s['wardrobe'],sort_keys=True))
        if k not in cache:cache[k]=frozenset(d.nc.core_asset_ids(s['sex'],s['wardrobe']))
        return frozenset(_attributes(s,cache[k]))
    aa=[attrs(s) for s in states]
    def target(u,v,axis):
        return {(f,val) for f,val in aa[v] if (f==axis or axis=='wardrobe' and f.startswith('wardrobe_')) and (f!='wardrobe_core' or (f,val) not in aa[u])}
    universe=defaultdict(set); covered=defaultdict(set)
    for e in json.loads((p/'edges.json').read_text()):
        for f,val in target(e['source'],e['target'],e['axis']):universe[f].add(val)
    axes=Counter()
    for s in ss:
        for e in s['steps']:
            axes[e['axis']]+=1
            for f,val in target(e['source'],e['target'],e['axis']):covered[f].add(val)
    mean=sum(axes[a] for a in NON_ID)/6
    report[split]={'coverage':{f:{'represented':len(vals),'covered':len(vals&covered[f]),'missing_count':len(vals-covered[f])} for f,vals in universe.items()},'axis_counts':dict(axes),'six_axis_relative_to_mean':{a:(axes[a]-mean)/mean for a in NON_ID},'actual_used_nodes':len({u for s in ss for u in s['history']})}
(HERE/'POST_REPAIR_CHECK.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
