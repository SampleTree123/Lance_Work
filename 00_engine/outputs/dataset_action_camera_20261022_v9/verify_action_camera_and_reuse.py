"""Experimental independent used-node coverage and content-edge reuse audit.

Technical owner: DATASET_DESIGN_EXPLORATION_20261021.md.
Does not replace formal state/edge legality or aspect checks.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUTPUTS=ROOT.parent

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def content(n):
    s=dict(n['state']);s.pop('aspect',None)
    return json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def run(candidate):
    cat=read(OUTPUTS/'dataset_trial_build_20261021_v1/catalog.json')
    actions={a['id']:a['label'] for a in cat['actions']}
    result={'scope':'actual used nodes; camera types ignore aspect and sex; directed edge reuse aggregates aspects by full content state', 'candidate':str(candidate),'splits':{},'errors':[],'soft_target_warnings':[],'inputs':[]}
    content_sets={}
    for split in ['train','test']:
        np=candidate/split/'nodes.json'; sp=candidate/split/'sessions.jsonl'
        nodes={n['id']:n for n in read(np)}
        sessions=[json.loads(l) for l in sp.read_text(encoding='utf-8').splitlines() if l]
        for p in [np,sp]:result['inputs'].append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        canonical={i:content(n) for i,n in nodes.items()}
        used={i for s in sessions for i in s['history']};content_sets[split]={canonical[i] for i in used}
        usage=collections.Counter(); axis_edges=collections.defaultdict(set);axis_events=collections.Counter()
        pairs=collections.defaultdict(set);pair_contents=collections.defaultdict(set);action_contents=collections.defaultdict(set)
        target_pairs=collections.defaultdict(set);repeatmax=collections.Counter();distinct_by_len=collections.defaultdict(list)
        for i in used:
            state=nodes[i]['state'];a,c=state['action'],state['camera'];pairs[a].add(c)
            pair_contents[a,c].add(canonical[i]);action_contents[a].add(canonical[i])
        for s in sessions:
            ac=collections.Counter(t['axis'] for t in s['steps']);repeatmax[max(ac.values())]+=1;distinct_by_len[len(s['steps'])].append(len(ac))
            for t in s['steps']:
                u,v=canonical[t['source']],canonical[t['target']];e=(u,v);usage[e]+=1;axis_edges[t['axis']].add(e);axis_events[t['axis']]+=1
                if t['axis']=='action':
                    state=nodes[t['target']]['state'];target_pairs[state['action']].add(state['camera'])
        rows=[]
        for a,label in actions.items():
            row={'action':a,'label':label,'camera_count':len(pairs[a]),'cameras':sorted(pairs[a]),'content_nodes':len(action_contents[a]),'actual_action_target_camera_count':len(target_pairs[a]),'per_camera_content_nodes':{c:len(pair_contents[a,c]) for c in sorted(pairs[a])}}
            rows.append(row)
            if split=='train' and len(pairs[a])<10:result['errors'].append(f'{split}: {a} only {len(pairs[a])} used cameras')
        avg=sum(usage.values())/max(1,len(usage));four=sum(v==4 for v in usage.values())
        result['splits'][split]={'sessions':len(sessions),'used_render_nodes':len(used),'registered_nodes':len(nodes),'content_nodes':len(content_sets[split]),'action_rows':rows,'action_camera_pair_count':sum(len(v) for v in pairs.values()),'edit_events':sum(usage.values()),'distinct_content_edges':len(usage),'mean_content_edge_reuse':avg,'max_content_edge_reuse':max(usage.values()),'four_use_edges':four,'four_use_fraction':four/max(1,len(usage)), 'by_axis':{a:{'events':axis_events[a],'edges':len(axis_edges[a]),'mean_reuse':axis_events[a]/len(axis_edges[a])} for a in axis_events},'max_same_axis_occurrences_distribution':dict(repeatmax),'mean_distinct_axes_by_length':{k:sum(v)/len(v) for k,v in distinct_by_len.items()}}
        if max(usage.values())>4:result['errors'].append(f'{split}: edge cap exceeded')
        if len(used)!=len(nodes):result['errors'].append(f'{split}: unused registered nodes')
        if len(sessions)!= {'train':12000,'test':2400}[split]:result['errors'].append(f'{split}: chain quota mismatch')
        if four/max(1,len(usage))>.005:result['soft_target_warnings'].append(f'{split}: four-use edge fraction exceeds retained soft target .5%')
    result['cross_split_content_overlap']=len(content_sets['train'] & content_sets['test'])
    if result['cross_split_content_overlap']:result['errors'].append('cross split content overlap')
    result['passed']=not result['errors']
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,default=ROOT/'selected_candidate');p.add_argument('--output',type=Path,default=ROOT/'used_coverage_reuse_check.json');args=p.parse_args()
    r=run(args.candidate)
    args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':r['passed'],'errors':r['errors'],'soft_target_warnings':r['soft_target_warnings'],'splits':{s:{k:v for k,v in x.items() if k not in ['action_rows','by_axis']} for s,x in r['splits'].items()}}))
