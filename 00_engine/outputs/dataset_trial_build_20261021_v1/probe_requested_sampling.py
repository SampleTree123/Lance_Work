"""Exact full-domain weighted edit proposals without a video-budget truncation."""
import copy,json,random,time
from collections import Counter
from build_trial import Domain,Graph,quotas,write,HERE,stats,save_graph

def main():
    d=Domain();g=Graph(d);rng=random.Random(20261023);rows=[];schedule=quotas(1000);rng.shuffle(schedule)
    for typ,L in schedule:
        ft=rng.randrange(2,L+1) if typ=='fork' else None
        fp=rng.randrange(ft-1) if ft else None
        h=[g.add(d.initial(rng))];steps=[]
        for t in range(1,L+1):
            p=fp if t==ft else t-1;u=h[p]
            while True:
                m=d.mutate(g.nodes[u],rng)
                if m is not None:break
            target,a=m;v=g.add(target,u,a);e=d.edge(g.nodes[u],g.nodes[v],a)
            assert e is not None
            steps.append({'source_position':p,'source':u,'target':v,**e});h.append(v)
        rows.append({'id':f'probe_{len(rows):05d}','kind':typ,'length':L,'fork_round':ft,'history':h,'steps':steps})
    root=HERE/'requested_sampling_probe';summary=save_graph(root,g,rows,{'scope':'diagnostic_1000_fresh_root_sessions_not_main_dataset','budget_constraint':False})
    summary['notes']=['Each session has an independently sampled initial state; this is an unshared baseline, not a lower bound on required video budget.',
                      'Full-catalog weighted edits, same-session accidental state returns deduplicated; excludes invalid saved scene/action/camera triples.',
                      'First 100 sessions are the unbudgeted small-case sample; these are not added to train/test budgets.']
    write(root/'SUMMARY.json',summary);write(root/'first_100_sessions.json',rows[:100]);print(json.dumps({k:summary[k] for k in ('nodes','sessions','edit_steps','axis_percent','sessions_with_revisited_node','fork_effect')},ensure_ascii=False))
if __name__=='__main__':main()
