"""Fresh structural summaries and identifier/render-binding checks; read only candidate."""
from pathlib import Path
from collections import Counter, defaultdict
import json, sys, hashlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=ROOT.parent
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules, token
sys.path.insert(0,str(ROOT))
from audit_returns import audit_split as returns_audit

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(v):return hashlib.sha256(token(v).encode()).hexdigest()[:24]
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

rules=Rules();result={'scope':'actual selected candidate; supplemental independent starts/aspect/fork/identifier/render binding statistics; no candidate mutation','splits':{}}
keys={}
for split in ('train','test'):
    p=ROOT/'selected_candidate'/split
    nodes=read(p/'nodes.json');states={n['id']:n['state'] for n in nodes}
    edges=read(p/'edges.json');requests=read(p/'render_requests.json')
    chains=[json.loads(x) for x in (p/'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    errors=Counter();start_sex=Counter();start_aspect=Counter();sex_aspect=Counter();start_cameras=defaultdict(Counter)
    axis_aspect=defaultdict(Counter);axis_sequences=Counter();parent_shapes=Counter();fork=defaultdict(Counter)
    distinct=Counter();repeated_axis_chains=0;consecutive_axis_chains=0;full_repeated=0
    content={};canons={}
    for n in nodes:
        s=n['state'];canonical=rules.canonical(s);k=rules.canonical(dict(s,aspect='content_without_aspect'))
        content[n['id']]=k;canons[n['id']]=canonical
        if n['canonical_id']!='node_'+digest(canonical):errors['canonical_identifier']+=1
        if n['content_id']!='content_'+digest(k):errors['content_identifier']+=1
    keys[split]=set(content.values())
    plan_cache={};request_ids=Counter()
    for r in requests:
        n=r['node_id'];request_ids[n]+=1;s=states[n]
        if r['state']!=s or r['aspect']!=s['aspect']:errors['render_request_state_aspect']+=1
        if r['content_id']!='content_'+digest(content[n]):errors['render_request_content_id']+=1
        b=r['camera_binding'];path=Path(b['plan_path'])
        if path not in plan_cache:plan_cache[path]={x['shot_id']:x for x in read(path)['shots']}
        source=plan_cache[path].get(b['shot_id'])
        if source is None or any(b[k]!=source[k] for k in ('shot_id','motion_id','camera_id','orientation','width','height','trajectory_sha256')):errors['camera_template_binding']+=1
        if (b['motion_id'],b['camera_id'],b['orientation'])!=(s['action'],s['camera'],s['aspect']):errors['camera_template_state']+=1
    if set(request_ids)!=set(states) or any(v!=1 for v in request_ids.values()):errors['request_node_bijection']+=1
    for c in chains:
        h=c['history'];s=states[h[0]];a=s['aspect'];sequence=tuple(st['axis'] for st in c['steps'])
        start_sex[s['sex']]+=1;start_aspect[a]+=1;sex_aspect[a+'/'+s['sex']]+=1;start_cameras[a][s['camera']]+=1
        if c['aspect']!=a:errors['session_declared_aspect']+=1
        for st in c['steps']:axis_aspect[a][st['axis']]+=1
        axis_sequences[sequence]+=1
        shape=tuple(st['source_position'] for st in c['steps']);parent_shapes[(c['kind'],c['length'],shape)]+=1
        distinct[(c['length'],len(set(sequence)))]+=1
        if len(set(sequence))<len(sequence):repeated_axis_chains+=1
        if any(x==y for x,y in zip(sequence,sequence[1:])):consecutive_axis_chains+=1
        if len(set(canons[u] for u in h))<len(h):full_repeated+=1
        for turn,st in enumerate(c['steps'],1):
            parent=st['source_position']
            if parent<turn-1:fork[c['length']][(turn,parent)]+=1
    fork_rows={}
    for length,c in sorted(fork.items()):
        total=sum(c.values());rounds=Counter();parents=Counter()
        for (t,p0),v in c.items():rounds[t]+=v;parents['root' if p0==0 else 'intermediate']+=v
        fork_rows[str(length)]={'chains':total,'round_counts':dict(sorted(rounds.items())),'round_expected_each':total/(length-1),
            'round_parent_joint_counts':{f't{t}_p{p0}':v for (t,p0),v in sorted(c.items())},'parent_counts':dict(parents),
            'terminal_forks':rounds[length],'expected_terminal_forks':total/(length-1)}
    repeat_result,_,_=returns_audit(p,rules)
    result['splits'][split]={'inputs':[pin(p/f) for f in ('nodes.json','edges.json','sessions.jsonl','render_requests.json')],
        'errors':dict(errors),'start_sex':dict(start_sex),'sessions_by_aspect':dict(start_aspect),'start_sex_by_aspect':dict(sex_aspect),
        'used_nodes_by_aspect':dict(Counter(s['aspect'] for s in states.values())),
        'used_nodes_by_sex':dict(Counter(s['sex'] for s in states.values())),
        'start_cameras_by_aspect':{k:dict(sorted(v.items())) for k,v in start_cameras.items()},
        'edit_axes_by_aspect':{k:dict(sorted(v.items())) for k,v in axis_aspect.items()},
        'fork_topology':fork_rows,'unique_parent_topologies':len(parent_shapes),
        'unique_axis_sequences':len(axis_sequences),'maximum_axis_sequence_reuse':max(axis_sequences.values()),
        'distinct_axis_histogram_by_length':{str(l):{str(d):v for (ll,d),v in sorted(distinct.items()) if ll==l} for l in range(2,6)},
        'repeated_axis_chains':repeated_axis_chains,'consecutive_same_axis_chains':consecutive_axis_chains,'full_node_repeat_chains':full_repeated,
        'fresh_repeat_audit':{k:repeat_result[k] for k in ('passed_structural_checks','counts','strict_explicit_ancestor_returns','chronological_edited_target_repeats','other_branch_edited_target_repeats','implicit_unedited_axis_resets_vs_latest','full_node_repeats','distinct_axes','edge_reuse_histogram')}}
result['cross_split_complete_content_overlap_ignoring_aspect']=len(keys['train']&keys['test'])
result['passed_supplemental_checks']=not result['cross_split_complete_content_overlap_ignoring_aspect'] and all(not s['errors'] and s['fresh_repeat_audit']['passed_structural_checks'] for s in result['splits'].values())
(HERE/'structure_findings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':result['passed_supplemental_checks'],'splits':{k:{x:v[x] for x in ('errors','start_sex','sessions_by_aspect','start_sex_by_aspect','used_nodes_by_aspect','fork_topology','repeated_axis_chains','consecutive_same_axis_chains','full_node_repeat_chains','distinct_axis_histogram_by_length')} for k,v in result['splits'].items()}},ensure_ascii=False))
