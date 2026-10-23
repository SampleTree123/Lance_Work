"""Actual main-chain support and exposure, with no extra balance threshold."""
from pathlib import Path
from collections import Counter,defaultdict
import json
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    result={'definition':'Camera types ignore aspect. Main content nodes must appear in actual chain history. Node occurrences count revisits; chain counts count each action-camera at most once per chain. Action target counts include only action edits, camera target counts include only camera edits. No new frequency balance gate.','splits':{}}
    for split in ('train','test'):
        root=ROOT/'structural_candidate'/split
        nodes={n['id']:n['state'] for n in read(root/'nodes.json')}
        sessions=[json.loads(x) for x in (root/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
        used={u for c in sessions for u in c['history']};pairs=defaultdict(set)
        for u in used:pairs[nodes[u]['action'],nodes[u]['camera']].add(u)
        occurrences=Counter();chains=Counter();action_targets=Counter();camera_targets=Counter()
        for c in sessions:
            ps=[(nodes[u]['action'],nodes[u]['camera']) for u in c['history']]
            occurrences.update(ps);chains.update(set(ps))
            for st in c['steps']:
                p=(nodes[st['target']]['action'],nodes[st['target']]['camera'])
                if st['axis']=='action':action_targets[p]+=1
                if st['axis']=='camera':camera_targets[p]+=1
        actions=defaultdict(dict)
        for (a,cam),us in sorted(pairs.items()):
            actions[a][cam]={'content_nodes':len(us),'history_occurrences':occurrences[a,cam],'chains_containing_pair':chains[a,cam],'action_edit_targets':action_targets[a,cam],'camera_edit_targets':camera_targets[a,cam]}
        result['splits'][split]={'action_count':len(actions),'action_camera_pair_count':len(pairs),'minimum_cameras_per_action':min(map(len,actions.values())),'minimum_content_nodes_per_pair':min(map(len,pairs.values())),'minimum_history_occurrences_per_pair':min(occurrences.values()),'minimum_chains_per_pair':min(chains.values()),'actions':{a:{'camera_count':len(cams),'content_nodes':sum(v['content_nodes'] for v in cams.values()),'history_occurrences':sum(v['history_occurrences'] for v in cams.values()),'action_edit_targets':sum(v['action_edit_targets'] for v in cams.values()),'per_camera':cams} for a,cams in actions.items()}}
    (ROOT/'structural_action_camera_frequency.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({s:{k:v for k,v in r.items() if k!='actions'} for s,r in result['splits'].items()}))
if __name__=='__main__':main()
