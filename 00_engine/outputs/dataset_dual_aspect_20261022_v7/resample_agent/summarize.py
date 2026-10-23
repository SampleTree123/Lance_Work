import json
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
report={}
for p in HERE.iterdir():
    if not (p/'sessions.jsonl').exists(): continue
    n=json.loads((p/'nodes.json').read_text()); ss=[json.loads(l) for l in (p/'sessions.jsonl').read_text().splitlines()]
    aspects={}
    for asp in ('landscape','portrait'):
        part=[s for s in ss if n[s['history'][0]]['state']['aspect']==asp]
        l5=[s for s in part if s['length']==5]
        aspects[asp]={'sessions':len(part),'used_nodes':len({u for s in part for u in s['history']}),
            'start_camera':dict(Counter(n[s['history'][0]]['state']['camera'] for s in part)),
            'start_sex':dict(Counter(n[s['history'][0]]['state']['sex'] for s in part)),
            'axis_counts':dict(Counter(e['axis'] for s in part for e in s['steps'])),
            'length5_sessions':len(l5), 'length5_mean_distinct_axes':sum(len({e['axis'] for e in s['steps']}) for s in l5)/max(1,len(l5))}
    l5=[s for s in ss if s['length']==5]
    report[p.name]={'graph_nodes':len(n),'actual_used_nodes':len({u for s in ss for u in s['history']}),
        'sessions':len(ss),'edits':sum(len(s['steps']) for s in ss),
        'fixed_aspect_all':all(len({n[u]['state']['aspect'] for u in s['history']})==1 for s in ss),
        'max_edge_use':max(Counter((e['source'],e['target']) for s in ss for e in s['steps']).values()),
        'length5_mean_distinct_axes':sum(len({e['axis'] for e in s['steps']}) for s in l5)/max(1,len(l5)),
        'aspects':aspects}
(HERE/'COMPARISON.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for key,row in report.items():
    print(key,'used',row['actual_used_nodes'],'L5',row['length5_mean_distinct_axes'],'edgecap',row['max_edge_use'],
          'aspect cameras',[(a,len(r['start_camera']),min(r['start_camera'].values())) for a,r in row['aspects'].items()])
