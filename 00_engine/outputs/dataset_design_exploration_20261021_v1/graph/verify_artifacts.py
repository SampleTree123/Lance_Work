"""Necessary checks of persisted first-seed graph/session artifacts only."""
from collections import Counter
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
checkpoint=read(HERE.parents[1]/'review_progress_sync_20261021_v1/checkpoint.json')
excluded={(s['id'],e['action_id'],e['camera_id'],e['aspect']) for s in checkpoint['sites'] for e in s.get('manual_exclusions',[]) if e.get('decision') == 'excluded'}
sexes={r['id']:r['sex'] for r in read(HERE/'topology_inventory.json')['identities']}
results=[]
for tag in ('','appearance8_','main_scene_holdout_','sourcebalanced_scene_'):
    quality=tag in ('main_scene_holdout_','sourcebalanced_scene_')
    for route in (('hybrid',) if quality else ('chain_first','dense_neighborhoods','hybrid')):
        split_hashes={}
        for split,n_expected,s_expected in (('train',2500,12000),('test',500,3000)):
            base=HERE/f'{tag}{route}_{split}'
            graph=read(Path(str(base)+'_graph.json'))
            nodes=graph['nodes']
            assert len(nodes) == n_expected
            assert len({r['node_id'] for r in nodes}) == n_expected
            edges={(e['source_index'],e['target_index']):e['axis'] for e in graph['edges']}
            for n in nodes:
                st=n['state']
                assert (st['site'],st['action'],st['camera'],st['aspect']) not in excluded
                if tag == 'appearance8_' and st['hair'] == 'none': assert st['hair_color'] == 'original'
                assert n['node_id'] == 'simn_'+hashlib.sha256(json.dumps(st,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20]
            for (a,b),axis in edges.items():
                assert [k for k in nodes[a]['state'] if nodes[a]['state'][k] != nodes[b]['state'][k]] == [axis]
                assert sexes[nodes[a]['state']['identity']] == sexes[nodes[b]['state']['identity']]
            sessions=[json.loads(line) for line in Path(str(base)+'_sessions.jsonl').read_text().splitlines()]
            assert len(sessions) == s_expected
            assert len({s['session_id'] for s in sessions}) == s_expected
            used=set()
            signatures=set()
            quotas=Counter()
            for s in sessions:
                occ,par,axes=s['node_indices'],s['parent_occurrence_indices_gt'],s['edge_axes']
                k=len(axes)
                assert 2 <= k <= 5 and len(occ) == len(par) == k+1 and par[0] is None
                if quality:
                    assert len(set(occ)) == len(occ)
                    assert len(set(axes)) >= 2
                    assert all(nodes[o]['state']['aspect'] == 'landscape' for o in occ)
                branches=[]
                for t in range(1,k+1):
                    assert 0 <= par[t] < t
                    assert edges[(occ[par[t]],occ[t])] == axes[t-1]
                    if par[t] != t-1:
                        branches.append(t)
                        assert occ[par[t]] != occ[t-1]
                        assert occ[:t].count(occ[par[t]]) == 1
                        if quality:
                            latest=dict(nodes[occ[t-1]]['state'])
                            latest[axes[t-1]]=nodes[occ[t]]['state'][axes[t-1]]
                            assert latest != nodes[occ[t]]['state']
                assert len(branches) <= 1
                if branches: assert branches[0] < k
                quotas[(k,bool(branches))]+=1
                signatures.add((tuple(occ),tuple(par)))
                used.update(occ)
            assert len(signatures) == s_expected and len(used) == n_expected
            assert sum(n for (k,b),n in quotas.items() if b) == s_expected//3
            if quality:
                assert len({n['state']['action'] for n in nodes}) == 25
                assert len({n['state']['camera'] for n in nodes}) == 21
                assert len({n['state']['site'] for n in nodes}) == (16 if split == 'train' else 5)
                assert len({n['state']['identity'] for n in nodes}) == 40
                lin=s_expected*2//3
                br=s_expected//3
                assert all(quotas[(k,False)] == lin//4 for k in (2,3,4,5))
                assert [quotas[(k,True)] for k in (3,4,5)] == [br//5,br*2//5,br*2//5]
                if tag == 'sourcebalanced_scene_':
                    roots=sum(any(t and p == 0 and p != t-1 for t,p in enumerate(s['parent_occurrence_indices_gt'])) for s in sessions)
                    assert roots == br*2//5
            split_hashes[split]={n['node_id'] for n in nodes}
            results.append({'tag':tag,'route':route,'split':split,'nodes':n_expected,'sessions':s_expected,
                            'edges':len(edges),'checks':'passed','length_branch_quota':{str(k):v for k,v in sorted(quotas.items())}})
        assert not split_hashes['train'] & split_hashes['test']
output={'scope':'saved_first_seed_artifacts_only_not_UE_or_all_repo_tests','passed':True,
        'checked_graphs':len(results),'checked_unique_sessions':sum(r['sessions'] for r in results),'results':results}
(HERE/'verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in output.items() if k != 'results'}))
