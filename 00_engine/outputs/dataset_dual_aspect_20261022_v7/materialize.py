"""Project complete v6 chains into fixed-aspect render variants without editing history."""
from pathlib import Path
from collections import Counter
import argparse, copy, hashlib, json, sys

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'dataset_compact_graph_20261022_v6/selected_seed1'
PLAN=ROOT.parent/'production_workflow_20261017_v1/camera_library/production10/camera_plan.json'
sys.path.insert(0,str(ROOT.parent/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules, token

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def lines(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines()]
def digest(x): return hashlib.sha256(token(x).encode()).hexdigest()
def pin(p): return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}

def build(assignment_root,output):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    rules=Rules()
    shots={(s['motion_id'],s['camera_id'],s['orientation']):s for s in read(PLAN)['shots']}
    result={}; inputs=[pin(PLAN),pin(Path(__file__))]
    for split in ('train','test'):
        old_nodes=read(SOURCE/split/'nodes.json'); old_chains=lines(SOURCE/split/'sessions.jsonl')
        source_edges={(e['source'],e['target']):e for e in read(SOURCE/split/'edges.json')}
        ap=assignment_root/split/'assignment.jsonl'; assignments=lines(ap)
        by_chain={a['id']:a['aspect'] for a in assignments}
        assert len(by_chain)==len(assignments)==len(old_chains)
        assert set(by_chain)=={s['id'] for s in old_chains}
        assert set(by_chain.values())=={'landscape','portrait'}
        needed=sorted({(by_chain[c['id']],n) for c in old_chains for n in c['history']})
        mapping={k:i for i,k in enumerate(needed)}
        nodes=[]; requests=[]
        for (aspect,original),i in mapping.items():
            old=old_nodes[original]; state=copy.deepcopy(old['state']); state['aspect']=aspect
            assert not rules.valid_state(state)
            content=copy.deepcopy(state); content['aspect']='content_without_aspect'
            nodes.append({'id':i,'canonical_id':'node_'+digest(rules.canonical(state))[:24],
                'content_id':'content_'+digest(rules.canonical(content))[:24],
                'original_node_id':original,'original_canonical_id':old['canonical_id'],
                'state':state,'projection':{'source_split':str(SOURCE/split),
                'method':'verified_v6_content_with_fixed_render_aspect',
                'original_created_by':old.get('created_by')}})
            shot=shots[(state['action'],state['camera'],aspect)]
            binding={k:shot[k] for k in ('shot_id','motion_id','camera_id','orientation','width','height','trajectory_sha256')}
            binding['plan_path']=str(PLAN)
            requests.append({'node_id':i,'original_node_id':original,'aspect':aspect,
                'state':state,
                'content_id':nodes[-1]['content_id'],'camera_binding':binding,
                'camera_binding_scope':'existing orientation-specific trajectory template; adapt to saved site and final media profile',
                'source_preset_is_final_render_spec':False,'status':'planned_not_rendered',
                'final_resolution':None,'final_fps':None,'final_duration_seconds':None})
        chains=[]; used_edges={}
        for original in old_chains:
            c=copy.deepcopy(original); aspect=by_chain[c['id']]
            c['original_session_id']=c['id']; c['aspect']=aspect
            c['history']=[mapping[(aspect,n)] for n in original['history']]
            for step in c['steps']:
                pair=(step['source'],step['target'])
                edge=copy.deepcopy(source_edges[pair]); edge['original_source'],edge['original_target']=pair
                for field in ('source','target'):
                    step[field]=mapping[(aspect,step[field])];edge[field]=step[field]
                used_edges[(edge['source'],edge['target'])]=edge
            chains.append(c)
        folder=output/split; folder.mkdir()
        write(folder/'nodes.json',nodes);write(folder/'edges.json',list(used_edges.values()))
        write(folder/'render_requests.json',requests)
        (folder/'sessions.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False,separators=(',',':'))+'\n' for c in chains),encoding='utf-8')
        result[split]={'content_nodes':len(old_nodes),'render_nodes':len(nodes),
            'additional_render_nodes':len(nodes)-len(old_nodes),
            'chain_count':len(chains),'chain_count_by_aspect':dict(Counter(c['aspect'] for c in chains)),
            'render_count_by_aspect':dict(Counter(n['state']['aspect'] for n in nodes)),
            'edit_count':sum(len(c['steps']) for c in chains),'all_original_chains_preserved_once':True}
        inputs.extend(pin(SOURCE/split/f) for f in ('nodes.json','edges.json','sessions.jsonl'))
        inputs.append(pin(ap))
    write(output/'ASSEMBLY.json',{'method':'whole-chain aspect assignment; duplicate only shared content nodes',
        'source':str(SOURCE),'assignment_source':str(assignment_root),'inputs':inputs,'counts':result,
        'rendered':False,'new_edit_axis_added':False,'new_structural_chains_created':False})
    write(output/'SUMMARY.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--assignment-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(build(a.assignment_root.resolve(),a.output.resolve()),ensure_ascii=False))
