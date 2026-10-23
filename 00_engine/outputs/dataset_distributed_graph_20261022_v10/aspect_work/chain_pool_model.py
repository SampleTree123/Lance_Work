"""Read-only pool diagnostics and OPTIONAL MILP LP-file export. NEVER solves.

Run --graph fixed_graph/train --pool candidate/train/sessions.jsonl.
Default: inspect and write an owned report only. --emit-lp additionally builds
the selection model after basic necessary conditions pass. No candidate/current
is written. A subsequently solved selection still needs independent auditing.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, hashlib, importlib.util, json, math, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
V10=HERE.parent;OUT=V10.parent
FIELDS=('identity','action','hair','hair_color','site')
AXES=('action','camera','hair','hair_color','site','wardrobe')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def pin(path):return {'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def frequency(counts,pool):
    keys=sorted(pool);total=sum(counts[k] for k in keys);n=len(keys)
    below=[k for k in keys if counts[k]==0 or 2*n*counts[k]<total]
    above=[k for k in keys if 2*n*counts[k]>3*total]
    return {'passed':bool(keys) and not below and not above,'value_count':n,'total':total,'below_half':below,'above_1_5':above}

def extract(graph,pool,total):
    sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
    from audit_candidate import Rules,UPPER,ID_CAMERAS,quota_counts
    rules=Rules();nodes={n['id']:n['state'] for n in read(graph/'nodes.json')}
    edges={(e['source'],e['target']):e for e in read(graph/'edges.json')}
    clothes={n:rules.clothes(s) for n,s in nodes.items()}
    visible={n:set() if s['camera']=='front_head' else set(clothes[n]['core'])&set(clothes[n]['upper']) if s['camera'] in UPPER else set(clothes[n]['core']) for n,s in nodes.items()}
    canonical=[json.dumps({k:v for k,v in s.items() if k!='aspect'},sort_keys=True,separators=(',',':')) for s in nodes.values()]
    assert len(canonical)==len(set(canonical)), 'Fixed graph must contain unique content states'
    graphfreq={f:Counter(s[f] for s in nodes.values()) for f in FIELDS}
    graphfreq['core_asset']=Counter(a for values in visible.values() for a in values)
    action_cameras=defaultdict(Counter);core_actions=defaultdict(set);core_cameras=defaultdict(set)
    for n,s in nodes.items():
        if s['camera']!='front_head':action_cameras[s['action']][s['camera']]+=1
        for asset in visible[n]:core_actions[asset].add(s['action']);core_cameras[asset].add(s['camera'])
    graphchecks={f:frequency(graphfreq[f],rules.pools[f]) for f in graphfreq}
    graphcamera={a:frequency(cs,set(cs)) for a,cs in action_cameras.items()}
    missingcontexts={a:{'actions':len(core_actions[a]),'cameras':len(core_cameras[a])} for a in rules.pools['core_asset'] if len(core_actions[a])<3 or len(core_cameras[a])<3}
    rows=defaultdict(dict);chains=[];signatures=set();duplicates=0;bad=[];slotcache={}
    def record(key,ci,value=1):
        if value:rows[key][ci]=rows[key].get(ci,0)+value
    for text in pool.read_text(encoding='utf-8-sig').splitlines():
        if not text.strip():continue
        chain=json.loads(text);h=chain['history'];steps=chain['steps']
        signature=(h[0],tuple((s['source_position'],s['target']) for s in steps))
        if signature in signatures:duplicates+=1;continue
        signatures.add(signature);ci=len(chains);chains.append(chain)
        assert len(h)==len(steps)+1==chain['length']+1
        record(('kind',f"{chain['kind']}_{chain['length']}"),ci)
        record(('start',nodes[h[0]]['camera']),ci)
        for node in set(h):record(('node',node),ci)
        for node in h:
            state=nodes[node]
            for field in FIELDS:record(('freq',field,state[field]),ci)
            for asset in visible[node]:record(('freq','core_asset',asset),ci)
            record(('total_core',),ci,len(visible[node]))
            if state['camera']!='front_head':
                record(('action_camera',state['action'],state['camera']),ci)
                record(('total_action_camera',state['action']),ci)
        for turn,step in enumerate(steps,1):
            u,v=step['source'],step['target'];pos=step['source_position']
            assert 0<=pos<turn and h[pos]==u and h[turn]==v
            assert (u,v) in edges and edges[u,v]['axis']==step['axis']
            record(('edge',u,v),ci);record(('axis',step['axis']),ci)
            target=nodes[v]
            if step['axis']!='wardrobe':record(('target',step['axis'],target[step['axis']]),ci)
            else:
                w=target['wardrobe'];record(('target','family',w['family_id']),ci)
                record(('target','group',w['family_id']+'/'+w['group_id']),ci)
                for asset in set(clothes[v]['core'])-set(clothes[u]['core']):record(('target','core_asset',asset),ci)
                if u not in slotcache:slotcache[u]={r['slot'] for r in rules.singles(nodes[u])}
                slots=slotcache[u]
                if slots:record(('mode_soft',),ci,(1 if step['mode']=='single_piece' else 0)-.5)
                if step['mode']=='single_piece':
                    for slot in slots:record(('slot_soft',slot),ci,-1/len(slots))
                    record(('slot_soft',step['slot']),ci,1)
    quota=quota_counts(total)
    cameras=[c if isinstance(c,str) else c['id'] for c in rules.cat['cameras']]
    weights={c:1.5 if c in ID_CAMERAS else 1 for c in cameras}
    exact={c:total*weights[c]/sum(weights.values()) for c in cameras};cq={c:math.floor(exact[c]) for c in cameras}
    for c in sorted(cameras,key=lambda c:-(exact[c]-cq[c]))[:total-sum(cq.values())]:cq[c]+=1
    targetkeys=[('target',field,value) for field,poolvalues in rules.pools.items() for value in poolvalues]
    targets_missing=[list(k[1:]) for k in targetkeys if k not in rows]
    short_kind={k:{'pool':len(rows.get(('kind',k),{})),'need':v} for k,v in quota.items() if len(rows.get(('kind',k),{}))<v}
    short_start={k:{'pool':len(rows.get(('start',k),{})),'need':v} for k,v in cq.items() if len(rows.get(('start',k),{}))<v}
    edgekeys=[k for k in rows if k[0]=='edge'];nnz=sum(len(v) for v in rows.values())
    expected_edits=sum(int(k.split('_')[-1])*v for k,v in quota.items());history_total=total+expected_edits
    report={'solver_invoked':False,'graph':str(graph.resolve()),'pool':str(pool.resolve()),'inputs':[pin(graph/'nodes.json'),pin(graph/'edges.json'),pin(pool)],'unique_pool_chains':len(chains),'duplicate_pool_rows_discarded':duplicates,'target_chains':total,'fixed_history_occurrences_when_quotas_met':history_total,'fixed_edit_occurrences_when_quotas_met':expected_edits,'registered_nodes':len(nodes),'available_graph_edges':len(edges),'pool_distinct_edges':len(edgekeys),'feature_rows':len(rows),'feature_nonzeros':nnz,'missing_node_pool_support':sorted(n for n in nodes if ('node',n) not in rows),'missing_actual_target_support':targets_missing,'kind_length_support_shortages':short_kind,'start_camera_support_shortages':short_start,'fixed_graph_unique_frequency':graphchecks,'fixed_graph_action_camera_frequency':graphcamera,'fixed_graph_core_context_shortages':missingcontexts,'fixed_graph_action_camera_minimum':{a:len(cs) for a,cs in action_cameras.items()},'selection_cannot_change_unique_content_frequency_if_all_registered_nodes_required':True,'simple_edge_capacity_upper_bound_at_cap3':sum(min(3,sum(rows[k].values())) for k in edgekeys),'simple_edge_capacity_upper_bound_at_cap4':sum(min(4,sum(rows[k].values())) for k in edgekeys),'graph_edge_capacity_by_axis_at_cap3':dict(Counter(e['axis'] for e in edges.values())),'model_size_estimate':{'chain_binary_variables':len(chains),'edge_continuous_auxiliaries':2*len(edgekeys),'total_variables_upper_approx':len(chains)+2*len(edgekeys)+40,'edge_rows_approx':4*len(edgekeys)+1,'node_coverage_rows':len(nodes),'frequency_range_rows':2*(sum(len(rules.pools[f]) for f in FIELDS)+len(rules.pools['core_asset'])+sum(len(cs) for cs in action_cameras.values())),'actual_target_coverage_rows':len(targetkeys),'wardrobe_mode_and_slot_are_soft_objective_terms':True},'scope':'Necessary-condition inspection and optional model export only; no semantic acceptance, no chain resampling, no solver or current-candidate change'}
    report['necessary_conditions_passed']=len(chains)>=total and not short_kind and not short_start and not targets_missing and not report['missing_node_pool_support'] and all(v['passed'] for v in graphchecks.values()) and all(v['passed'] for v in graphcamera.values()) and not missingcontexts and all(len(cs)>=10 for cs in action_cameras.values())
    return report,rows,chains,rules,nodes,quota,cq,action_cameras,targetkeys

def export_model(output,data,relax=False):
    import pulp
    report,rows,chains,rules,nodes,quota,cq,action_cameras,targetkeys=data
    if not report['necessary_conditions_passed']:raise ValueError('Necessary conditions failed: enlarge or repair the pool/graph first')
    model=pulp.LpProblem('fixed_graph_chain_selection',pulp.LpMinimize)
    x=[pulp.LpVariable(f'x_{i}',0,1,cat='Continuous' if relax else 'Binary') for i in range(len(chains))]
    def expr(key):return pulp.lpSum(value*x[i] for i,value in rows.get(key,{}).items())
    serial=0
    def add(constraint):
        nonlocal serial
        model.addConstraint(constraint,f'c_{serial}');serial+=1
    for k,value in quota.items():add(expr(('kind',k))==value)
    for k,value in cq.items():add(expr(('start',k))==value)
    for node in nodes:add(expr(('node',node))>=1)
    use=[];four=[]
    for ei,key in enumerate(k for k in rows if k[0]=='edge'):
        y=pulp.LpVariable(f'used_{ei}',0,1);z=pulp.LpVariable(f'four_{ei}',0,1);ce=expr(key)
        add(ce<=3*y+z);add(ce>=y);add(ce>=4*z);add(z<=y)
        use.append(y);four.append(z)
    add(200*pulp.lpSum(four)<=pulp.lpSum(use))
    # These edge auxiliaries may stay continuous: integer chain selections
    # force y=z=1 at count4, and y=z=0 at count0. Fractional y only tightens
    # the denominator, never permits more than .5% actual four-use edges.
    tcore=pulp.LpVariable('total_visible_core',lowBound=0);add(tcore==expr(('total_core',)))
    history=report['fixed_history_occurrences_when_quotas_met']
    for field in FIELDS:
        n=len(rules.pools[field])
        for value in rules.pools[field]:
            value_expr=expr(('freq',field,value));add(2*n*value_expr>=history);add(2*n*value_expr<=3*history)
    n=len(rules.pools['core_asset'])
    for value in rules.pools['core_asset']:
        value_expr=expr(('freq','core_asset',value));add(2*n*value_expr>=tcore);add(2*n*value_expr<=3*tcore)
    for action,cameras in action_cameras.items():
        total=pulp.LpVariable(f'action_total_{len(model.variables())}',lowBound=0);add(total==expr(('total_action_camera',action)));n=len(cameras)
        for camera in cameras:
            value_expr=expr(('action_camera',action,camera));add(2*n*value_expr>=total);add(2*n*value_expr<=3*total)
    six=pulp.LpVariable('six_axis_total',lowBound=0);add(six==pulp.lpSum(expr(('axis',axis)) for axis in AXES))
    for axis in AXES:add(60*expr(('axis',axis))>=9*six);add(60*expr(('axis',axis))<=11*six)
    for key in targetkeys:add(expr(key)>=1)
    soft=[]
    for i,key in enumerate(k for k in rows if k[0] in ('mode_soft','slot_soft')):
        d=pulp.LpVariable(f'wardrobe_deviation_{i}',lowBound=0);add(d>=expr(key));add(d>=-expr(key));soft.append(d)
    model+=100*pulp.lpSum(four)+pulp.lpSum(soft)
    model.writeLP(str(output))
    return {'exported_lp':str(output),'variables':len(model.variables()),'constraints':len(model.constraints),'relaxation':relax,'solver_invoked':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True);p.add_argument('--pool',type=Path,required=True);p.add_argument('--target',type=int,default=12000);p.add_argument('--name',default='pool_study');p.add_argument('--emit-lp',action='store_true');p.add_argument('--relax',action='store_true');args=p.parse_args()
    assert args.name.replace('_','').replace('-','').isalnum()
    data=extract(args.graph,args.pool,args.target);report=data[0]
    if args.emit_lp:report['model_export']=export_model(HERE/(args.name+'.lp'),data,args.relax)
    dump(HERE/(args.name+'.json'),report)
    print(json.dumps({k:report[k] for k in ('solver_invoked','unique_pool_chains','registered_nodes','available_graph_edges','pool_distinct_edges','feature_nonzeros','necessary_conditions_passed','kind_length_support_shortages','model_size_estimate')},indent=2))

if __name__=='__main__':main()
