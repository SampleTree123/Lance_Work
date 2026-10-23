"""Check aspect-specific symbolic reference bindings on the selected actual steps."""
from collections import Counter,defaultdict
from materialize import ROOT,read,write,lines,token,pin

def main():
    candidate=ROOT/'selected_candidate'; manifest=read(candidate/'reference_manifest.json')
    req={r['id']:r for r in manifest['requirements']}; seen=set(); errors=[]
    nodes={s:{n['id']:n for n in read(candidate/s/'nodes.json')} for s in ('train','test')}
    sessions={s:{c['id']:c for c in lines(candidate/s/'sessions.jsonl')} for s in ('train','test')}
    for link in manifest['reference_links']:
        key=(link['split'],link['session_id'],link['edit_round'])
        if key in seen: errors.append(['duplicate_step_link',key])
        seen.add(key)
        c=sessions[key[0]][key[1]];step=c['steps'][key[2]-1]
        target=nodes[key[0]][step['target']]['state']
        if any(link[a]!=step[b] for a,b in [('source_node','source'),('target_node','target'),('source_history_occurrence','source_position'),('axis','axis')]):
            errors.append(['step_mismatch',key])
        for rid in link['reference_ids']:
            r=req[rid]
            if r['kind'] in ('motion','scene'):
                k=r['key']
                if any(k[f]!=target[f] for f in ('action','camera','sex')) or k['symbolic_aspect']!=c['aspect']:
                    errors.append(['reference_context_mismatch',key,rid])
                if r['kind']=='scene' and k['site']!=target['site']: errors.append(['scene_mismatch',key,rid])
        if step['axis']=='action' and not any(req[r]['kind']=='motion' for r in link['reference_ids']): errors.append(['missing_motion',key])
        if step['axis']=='site' and not any(req[r]['kind']=='scene' for r in link['reference_ids']): errors.append(['missing_scene',key])
    expected=sum(len(c['steps']) for d in sessions.values() for c in d.values())
    if len(seen)!=expected: errors.append(['missing_step_links',len(seen),expected])
    collapsed=defaultdict(set);actual=Counter();aspect=defaultdict(Counter)
    for r in req.values():
        actual[r['kind']]+=1;k={f:v for f,v in r['key'].items() if f!='symbolic_aspect'}
        collapsed[r['kind']].add(token(k))
        if 'symbolic_aspect' in r['key']:aspect[r['kind']][r['key']['symbolic_aspect']]+=1
        if r['media_path'] is not None:errors.append(['unexpected_generated_media',r['id']])
    result={'passed':not errors,'errors':errors[:30],'checked_step_links':len(seen),
        'actual_reference_counts':dict(actual),'by_aspect':dict(aspect),
        'content_requirements_collapsed_without_aspect':{k:len(v) for k,v in collapsed.items()},
        'aspect_additional_requirements':{k:actual[k]-len(v) for k,v in collapsed.items()},
        'scope':'symbolic demand matching only; exact scene camera transform and final media profile pending',
        'inputs':[pin(candidate/f) for f in ('reference_manifest.json','reference_summary.json')]}
    write(ROOT/'reference_binding_check.json',result)
    print(token({k:v for k,v in result.items() if k!='inputs'}))
    assert not errors

if __name__=='__main__':main()
