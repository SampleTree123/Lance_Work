"""Common v3 sampling and focused checks for the frozen wide graph."""
import sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'dataset_local_support_20261021_v3'))
from resample_local import *

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='wide');args=ap.parse_args()
    d=Domain();forbidden=set();summary={};checks={}
    for j,(split,total) in enumerate([('train',12000),('test',2400)]):
        path=HERE/args.variant/split
        original=read(path/'metrics.json')['construction']
        g=load_graph(path,d,forbidden)
        errors=[]
        for i,s in enumerate(g.nodes):
            p=g.provenance[i]
            if not d.valid(s):errors.append(['invalid_state',i])
            if p['parent'] is not None:
                u=p['parent'];a=p['axis']
                if u>=i or (u,i) not in g.edges or g.edges[u,i]['axis']!=a:errors.append(['invalid_parent',i])
                if [AXES[k] for k in range(len(AXES)) if g.keys[u][k]!=g.keys[i][k]]!=[a]:errors.append(['non_atomic',i])
        assert not errors,errors[:10]
        ss,sm=sample_local(g,total,20261122+j)
        original['sampling']=sm
        summary[split]=save_graph(path,g,ss,original)
        m=summary[split]
        per_length={}
        for length in range(2,6):
            rows=[s for s in ss if s['length']==length]
            per_length[length]={'count':len(rows),'mean_distinct_axes':sum(len({r['axis'] for r in s['steps']}) for s in rows)/len(rows),
                                'distinct_axis_histogram':dict(Counter(len({r['axis'] for r in s['steps']}) for s in rows))}
        checks[split]={'provenance_errors':errors,'roots':sum(p['parent'] is None for p in g.provenance),
                       'per_length_axes':per_length,'identity_counts':dict(Counter(s['identity'] for s in g.nodes)),
                       'unused_node_ids':sorted(set(range(len(g.nodes)))-{i for s in ss for i in s['history']}),
                       'sample_seed':20261122+j}
        checks[split]['identity_camera_nodes_fraction']=sum(s['camera'] in ID_CAMERAS for s in g.nodes)/len(g.nodes)
        checks[split]['identity_camera_starts_fraction']=sum(v for c,v in m['start_camera_counts'].items() if c in ID_CAMERAS)/len(ss)
        checks[split]['identity_camera_target_fraction']=6/23
        print(split,{k:m[k] for k in ['nodes','sessions','unused_nodes','used_edges','axis_percent','wardrobe_modes','sessions_with_revisited_node','single_axis_sessions','fork_effect']},per_length,flush=True)
        forbidden.update(g.keys)
    checks['canonical_split_overlap']=0
    write(HERE/args.variant/'SUMMARY.json',summary)
    write(HERE/args.variant/'focused_checks.json',checks)

if __name__=='__main__':main()
