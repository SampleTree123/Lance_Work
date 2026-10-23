"""Reproduce the compromise refinement warm-started from the economy files."""
import json
import numpy as np
import partition as p

PROFILE=dict(weight={'total':2,'sex':.5,'camera':.07,'sex_camera':.02,'axis':.03,'edit':.005},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.25,.75),'sex_camera':(.20,.80),'axis':(.40,.60),'edit':(.30,.70)},bound_weight=150,temperature=.12)
for split in ['train','test']:
    d=p.load(split)
    records=[json.loads(x) for x in (p.HERE/'economy'/split/'assignment.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [x['id'] for x in records]==[c['id'] for c in d['chains']]
    labels=np.array([p.ASPECTS.index(x['aspect']) for x in records],dtype=np.int8)
    initial=np.array([labels[g[0]] for g in d['groups']],dtype=np.int8)
    assert np.all(p.chain_labels(d,initial)==labels)
    best=None; best_score=float('inf'); metadata=None
    for seed in [6103,6104]:
        x,trace=p.optimize(d,initial,seed,PROFILE,16)
        score=min(t['objective'] for t in trace)
        if score<best_score:
            best=x; best_score=score
            metadata={'seed':seed,'warm_start':'economy/'+split+'/assignment.jsonl','method':'economy warm start; same exact shared-node objective; chain and node-star moves','profile':PROFILE,'passes':16,'trace':trace}
    p.save(d,split,'compromise',p.chain_labels(d,best),metadata)
