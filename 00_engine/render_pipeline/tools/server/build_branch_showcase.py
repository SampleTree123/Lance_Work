"""Export eight complete branching sessions. Technical owner: SERVER_EXECUTION.md."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from build_chain_showcase import ROOT, AXES, EXCLUDED_ACTIONS, read, dump, labels, edge_description, link_media


def main():
    dataset=ROOT/'00_engine/outputs/data_v12_20261028'
    out=ROOT/'00_engine/render_pipeline/showcase/chain_examples_20261028'
    source=read(dataset/'chains.json'); nodes=read(dataset/'nodes.json')['nodes']
    actions={x['motion_id']:x['label_zh'] for x in read(ROOT/'00_engine/render_pipeline/workspace/00_engine/assets/character_creator/production_motion_library_20261017_v1.json')['motions']}
    old=read(out/'examples.json'); used=set(old['nodes']); scenes=set(); axes=Counter()
    candidates=[s for s in source['sessions'] if sum(e['is_branch'] for e in s['steps'])==1
                and len(set(s['history_node_ids']))==len(s['history_node_ids'])
                and all(nodes[k]['state']['wardrobe']['family_id']!='female.bikini_ruana'
                        and nodes[k]['state']['action'] not in EXCLUDED_ACTIONS for k in s['history_node_ids'])]
    selection=out/'branch_selection.json'
    if selection.exists():
        picks=read(selection)['examples']
    else:
        picks=[]
        for length in (5,4,3,2):
            for index,sex in enumerate(('female','male')):
                aspect=('landscape' if (length+index)%2==0 else 'portrait')
                pool=[s for s in candidates if len(s['steps'])==length and not used.intersection(s['history_node_ids'])
                      and nodes[s['root_node']]['state']['sex']==sex and nodes[s['root_node']]['state']['aspect']==aspect]
                def score(s):
                    states=[nodes[k]['state'] for k in s['history_node_ids']]
                    branch=next(e for e in s['steps'] if e['is_branch'])
                    return (25*len({e['axis'] for e in s['steps']}) + 12*sum(1/(1+axes[e['axis']]) for e in s['steps'])
                            + 15*(branch['source_history_occurrence']>0) + 8*len({n['site'] for n in states}-scenes)
                            + sum(4 if n['camera'].startswith(('front','dolly_out_front','orbit')) else -1 for n in states))
                if not pool:raise ValueError(f'No candidate {length}/{sex}/{aspect}')
                chosen=sorted(pool,key=lambda s:(-score(s),s['session_id']))[0]
                picks.append({'example_id':f'B{length}-{index+1:02d}','session_id':chosen['session_id'],'edit_count':length})
                used.update(chosen['history_node_ids']);scenes.update(nodes[k]['state']['site'] for k in chosen['history_node_ids']);axes.update(e['axis'] for e in chosen['steps'])
        picks.sort(key=lambda x:x['example_id']);dump(selection,{'policy':'8 complete branching sessions; 2 per edit length 2..5; no overlap with linear examples; original history occurrences retained','examples':picks})
    by_id={s['session_id']:s for s in source['sessions']}
    graph={(sp,e['source'],e['target'],e['axis']) for sp,es in source['graph_edges'].items() for e in es}
    cards={};samples=[]
    for pick in picks:
        s=by_id[pick['session_id']];ids=s['history_node_ids'];assert len(ids)==len(set(ids))==pick['edit_count']+1
        assert not set(ids).intersection(old['nodes'])
        for k in ids:
            n=nodes[k];cards[k]={'id':k,'dataset_video':n['video'],'state':n['state'],'output':n['output'],'labels':labels(n,actions),
                                'expression':'微笑（预制Smile动作）','animation_path':n['recorded_render']['animation_path']}
        steps=[];parents={}
        for i,e in enumerate(s['steps'],1):
            parent=e['source_history_occurrence'];assert 0<=parent<i and e['output_history_occurrence']==i
            assert e['source_node']==ids[parent] and e['target_node']==ids[i]
            assert e['is_branch']==(parent!=i-1)
            assert (s['split'],int(e['source_node'].split('_')[-1]),int(e['target_node'].split('_')[-1]),e['axis']) in graph
            steps.append({**e,'axis_label':AXES[e['axis']],'description':edge_description(e,cards[e['source_node']],cards[e['target_node']])});parents[i]=parent
        assert sum(e['is_branch'] for e in steps)==1
        leaves=[i for i in range(1,len(ids)) if i not in parents.values()];assert len(leaves)==2
        paths=[]
        for leaf in leaves:
            path=[leaf]
            while path[-1]!=0:path.append(parents[path[-1]])
            paths.append(list(reversed(path)))
        samples.append({**pick,'split':s['split'],'root_node':s['root_node'],'node_ids':ids,'steps':steps,'paths':paths})
    assert Counter(s['edit_count'] for s in samples)=={2:2,3:2,4:2,5:2}
    assert len(cards)==sum(len(s['node_ids']) for s in samples)==36
    data={'schema':'datamake_branch_showcase_v1','created_date':'2026-10-28','description_source':'源/目标节点属性差异，不是正式训练prompt',
          'source_sha256':{f:hashlib.sha256((dataset/f).read_bytes()).hexdigest() for f in ['chains.json','nodes.json']},
          'stats':{'chains':8,'videos':36,'edits':28,'branch_edits':8},'selection':read(selection),'chains':samples,'nodes':cards}
    dump(out/'branch_examples.json',data)
    (out/'branch_data.js').write_text('window.SHOWCASE_DATA = '+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n')
    link_media(out,dataset,data,copy_media=True)
    manifest=read(out/'media_manifest.json');records={v['node_id']:v for v in manifest['videos']}
    for k,n in cards.items():
        f=out/'media'/f'{k}.mp4';records[k]={'node_id':k,'path':f'media/{k}.mp4','bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'dataset_path':n['dataset_video'],'copy_verified':True}
    manifest.update(videos=list(records.values()),total_bytes=sum(v['bytes'] for v in records.values()));dump(out/'media_manifest.json',manifest)
    print(json.dumps(data['stats']),flush=True)

if __name__=='__main__':main()
