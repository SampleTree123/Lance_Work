"""One final test-only refinement preserving every original chain.

Pair axis_balanced/test with the unchanged economy/train assignment.
"""
import csv
import json
import numpy as np
import partition as p

profile=dict(weight={'total':2,'sex':.5,'camera':.03,'sex_camera':.005,'axis':3,'edit':.001},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.20,.80),'sex_camera':(.15,.85),'axis':(.49,.51),'edit':(.25,.75)},bound_weight=150,temperature=.12,bound_weight_by_feature={'axis':3000,'camera':50,'sex_camera':10,'edit':5},record_distribution=True)
d=p.load('test')
records=[json.loads(x) for x in (p.HERE/'economy'/'test'/'assignment.jsonl').read_text(encoding='utf-8').splitlines()]
assert [x['id'] for x in records]==[c['id'] for c in d['chains']]
labels=np.array([p.ASPECTS.index(x['aspect']) for x in records],dtype=np.int8)
initial=np.array([labels[g[0]] for g in d['groups']],dtype=np.int8)
assert np.all(p.chain_labels(d,initial)==labels)
x,trace=p.optimize(d,initial,6107,profile,24)
report=p.save(d,'test','axis_balanced',p.chain_labels(d,x),{'seed':6107,'warm_start':'economy/test/assignment.jsonl','method':'single final test refinement; preserve all source chains; strong 49-51% per-axis portrait allocation','profile':profile,'passes':24,'trace':trace})
curve=[t for t in trace if t['pass_index']>=0]
with (p.HERE/'axis_balanced'/'test'/'cost_distribution_curve.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(curve[0])); writer.writeheader(); writer.writerows(curve)
train=json.loads((p.HERE/'economy'/'train'/'stats.json').read_text(encoding='utf-8'))
p.dump(p.HERE/'axis_balanced'/'COMPOSITION.json',{'train_assignment':'../economy/train/assignment.jsonl','test_assignment':'test/assignment.jsonl','train_unchanged':True,'train_render_jobs':train['render_jobs'],'test_render_jobs':report['render_jobs'],'combined_render_jobs':train['render_jobs']+report['render_jobs'],'combined_original_nodes':train['original_nodes']+report['original_nodes'],'combined_extra_nodes':train['shared_nodes']+report['shared_nodes']})
print(json.dumps(curve,indent=2))
