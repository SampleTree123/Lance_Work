"""Verify saved prefix node/session structure and actual split canonical keys."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode=True
from pooled_exact import HERE, ExactDomain, AXES, session_signature, write


def main():
    d=ExactDomain(); result={}; split_keys={}
    for name in ('roots_40_train','roots_40_test','roots_80_train','roots_160_train'):
        path=HERE/name/'budget_prefix'
        nodes=json.loads((path/'nodes.json').read_text(encoding='utf-8'))
        states={r['id']:r['state'] for r in nodes}
        keys=[d.canonical(r['state']) for r in nodes]
        assert len(keys)==len(set(keys))
        sessions=[json.loads(line) for line in (path/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
        seen=set(); duplicate=0; steps=0; unused=set(states)
        for s in sessions:
            h=s['history']; assert len(h)==s['length']+1
            nonlatest=0
            for t,r in enumerate(s['steps'],1):
                p=r['source_position']; assert 0<=p<t
                assert r['source']==h[p] and r['target']==h[t]
                nonlatest+=p!=t-1
                source,target=states[r['source']],states[r['target']]
                changed=[a for a,x,y in zip(AXES,d.canonical(source),d.canonical(target)) if x!=y]
                assert changed==[r['axis']]
                assert source['sex']==target['sex'] and source['aspect']==target['aspect']
                assert r['axis'] in d.choices(source)
                assert d.valid(source) and d.valid(target)
                assert d.edge(source,target,r['axis']) is not None
                steps+=1
            assert nonlatest==(s['kind']=='fork')
            assert s['fork_round'] is None if s['kind']=='linear' else 2<=s['fork_round']<=s['length']
            signature=session_signature(s); duplicate+=signature in seen;seen.add(signature)
            unused.difference_update(h)
        result[name]={'nodes':len(nodes),'sessions':len(sessions),'edit_steps_verified':steps,
                      'duplicate_structures':duplicate,'unused_seed_nodes':len(unused),
                      'canonical_unique':True,'atomic_inheritance_and_occurrence_parents':True,
                      'exactly_one_nonlatest_fork_parent':True}
        split_keys[name]=set(keys)
    assert not split_keys['roots_40_train'] & split_keys['roots_40_test']
    result['actual_train_test_canonical_overlap']=0
    result['scope']='Offline symbolic verification only; prefix quotas deliberately incomplete; no media generated.'
    write(HERE/'VERIFICATION.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
