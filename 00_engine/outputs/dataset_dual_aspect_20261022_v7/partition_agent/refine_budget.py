"""Budget-oriented soft compromise; preserve the stronger compromise candidate."""
import json
import numpy as np
import partition as p
profile=dict(weight={'total':2,'sex':.5,'camera':.07,'sex_camera':.02,'axis':.03,'edit':.005},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.25,.75),'sex_camera':(.20,.80),'axis':(.40,.60),'edit':(.30,.70)},bound_weight=150,temperature=.08,bound_weight_by_feature={'camera':30,'sex_camera':15,'edit':15})
for split in ['train','test']:
    d=p.load(split); best=None; best_score=float('inf'); metadata=None
    for warm,seed in [('economy',6105),('compromise',6106)]:
        records=[json.loads(x) for x in (p.HERE/warm/split/'assignment.jsonl').read_text(encoding='utf-8').splitlines()]
        labels=np.array([p.ASPECTS.index(x['aspect']) for x in records],dtype=np.int8)
        initial=np.array([labels[g[0]] for g in d['groups']],dtype=np.int8)
        x,trace=p.optimize(d,initial,seed,profile,12)
        score=min(t['objective'] for t in trace)
        if score<best_score:
            best=x; best_score=score
            metadata={'seed':seed,'warm_start':warm+'/'+split+'/assignment.jsonl','method':'budget-oriented soft camera bounds; exact shared-node objective','profile':profile,'passes':12,'trace':trace}
    p.save(d,split,'compromise_budget',p.chain_labels(d,best),metadata)
