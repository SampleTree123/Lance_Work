"""Zero-duplication whole-component aspect assignment for the audited v10.

Small feasibility MILP only: one binary variable per graph component. Never
splits a component/chain and never modifies the structural source.
"""
from pathlib import Path
from collections import Counter
import hashlib, importlib.util, json, sys, time
import numpy as np
import pulp
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]
ASPECTS=('landscape','portrait');SIX=('action','camera','hair','hair_color','site','wardrobe')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def lines(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pin(path):return {'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}

def partition(source,root):
    sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
    from audit_candidate import Rules
    rules=Rules();mask={'schema':'dual_aspect_portrait_eligibility_mask_v1','rule':'formal Rules.valid_state(state with aspect=portrait)','splits':{}}
    for split in ('train','test'):
        nodes=read(source/split/'nodes.json');chains=lines(source/split/'sessions.jsonl')
        bad={n['id']:rules.valid_state(dict(n['state'],aspect='portrait')) for n in nodes};bad={k:v for k,v in bad.items() if v}
        badchains=[c['id'] for c in chains if any(n in bad for n in c['history'])]
        mask['splits'][split]={'portrait_forbidden_node_ids':list(bad),'portrait_forbidden_chain_ids':badchains,'reasons_by_node_id':bad,'node_count':len(nodes),'session_count':len(chains)}
    dump(root/'portrait_eligibility_mask.json',mask)
    p=loadmod('v10_component_statistics',OUT/'dataset_dual_aspect_20261022_v7/partition_agent/partition.py');p.HERE=root;p.SOURCE=source
    selected={};trials={}
    for split in ('train','test'):
        started=time.time();d=p.load(split);nodes=d['nodes'];chains=d['chains'];edges=read(source/split/'edges.json')
        parent=list(range(len(nodes)))
        def find(x):
            while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
            return x
        for edge in edges:parent[find(edge['source'])]=find(edge['target'])
        roots=sorted({find(i) for i in range(len(nodes))});ri={r:i for i,r in enumerate(roots)}
        component=[ri[find(i)] for i in range(len(nodes))];nc=len(roots)
        features=[Counter() for _ in roots];component_nodes=[[] for _ in roots]
        for n,ci in enumerate(component):component_nodes[ci].append(n)
        for chain in chains:
            ci=component[chain['history'][0]];assert all(component[n]==ci for n in chain['history'])
            st=nodes[chain['history'][0]]['state'];f=features[ci]
            f['chains']+=1;f['sex:'+st['sex']]+=1;f['start:'+st['camera']]+=1
            for step in chain['steps']:f['axis:'+step['axis']]+=1
        totals=sum(features,Counter());forced={component[n] for n in mask['splits'][split]['portrait_forbidden_node_ids']}
        model=pulp.LpProblem('zero_copy_component_aspects_'+split,pulp.LpMinimize)
        x=[pulp.LpVariable(f'portrait_component_{i}',cat='Binary') for i in roots]
        def expr(key):return pulp.lpSum(f[key]*var for f,var in zip(features,x) if f[key])
        model += 0
        model += expr('chains')>=.45*len(chains);model += expr('chains')<=.55*len(chains)
        for key,value in totals.items():
            if key.startswith(('sex:','start:','axis:')):model += expr(key)>=1;model += expr(key)<=value-1
            if key.startswith('sex:'):model += expr(key)>=.4*value;model += expr(key)<=.6*value
        six_total=pulp.lpSum(expr('axis:'+axis) for axis in SIX);all_six=sum(totals['axis:'+axis] for axis in SIX)
        for axis in SIX:
            count=expr('axis:'+axis);all_count=totals['axis:'+axis]
            model += 60*count>=9*six_total;model += 60*count<=11*six_total
            model += 60*(all_count-count)>=9*(all_six-six_total);model += 60*(all_count-count)<=11*(all_six-six_total)
        for ci in forced:model += x[ci]==0
        log=root/'solver_logs'/f'{split}_cbc.log';log.parent.mkdir(parents=True,exist_ok=True)
        solver=pulp.PULP_CBC_CMD(msg=True,timeLimit=20,threads=1,logPath=str(log),options=['maxSolutions 1','randomSeed 6101'])
        status=model.solve(solver)
        values=[pulp.value(var) for var in x]
        assert all(v is not None and abs(v-round(v))<1e-6 for v in values),('No integer component assignment',pulp.LpStatus[status],str(log))
        for constraint in model.constraints.values():
            assert constraint.valid(1e-5),('Invalid returned feasibility assignment',constraint.name)
        component_labels=[int(round(v)) for v in values]
        labels=np.array([component_labels[component[c['history'][0]]] for c in chains],dtype=np.int8)
        metadata={'method':'whole-connected-component assignment; zero duplicated nodes; CBC feasibility only','component_count':nc,'component_node_sizes':list(map(len,component_nodes)),'component_chain_counts':[f['chains'] for f in features],'component_aspect':{str(i):ASPECTS[label] for i,label in enumerate(component_labels)},'portrait_forced_landscape_components':sorted(forced),'solver_status':pulp.LpStatus[status],'solver_seconds':time.time()-started,'solver_log':str(log),'six_axis_balance_target':.10,'source_files':[pin(source/split/f) for f in ('nodes.json','edges.json','sessions.jsonl')]}
        report=p.save(d,split,'component_assignment',labels,metadata)
        assert report['shared_nodes']==0 and report['render_jobs']==len(nodes)
        assert .45<=report['portrait']['chain_fraction']<=.55
        assert report['all_start_cameras_covered_both'] and report['all_sexes_covered_both'] and report['all_7_axes_covered_both']
        deviations={a:max(abs(6*v/sum(n.values())-1) for v in n.values()) for a in ASPECTS for n in [{k:v for k,v in report[a]['axis_steps'].items() if k!='identity'}]}
        assert max(deviations.values())<=.10+1e-12
        folder=root/'selected_assignment'/split;folder.mkdir(parents=True,exist_ok=True)
        import shutil
        for filename in ('assignment.jsonl','stats.json','method.json','node_requirements.json'):shutil.copyfile(root/'component_assignment'/split/filename,folder/filename)
        selected[split]={'source':str(root/'component_assignment'/split),'max_relative_axis_deviation':deviations,'per_aspect_axis_target_met':True,'stats':report}
        trials[split]={'whole_components':{'component_count':nc,'shared_nodes':0,'render_jobs':len(nodes),'six_axis_max_relative_deviation':deviations,'solver_status':pulp.LpStatus[status]}}
        dump(root/'selected_assignment'/split/'COMPONENTS.json',{'node_component':component,'component_aspect':metadata['component_aspect']})
        print('ZERO_COPY',split,nc,report['render_jobs'],deviations,flush=True)
    dump(root/'selected_assignment/SOURCES.json',selected);dump(root/'partition_trials.json',trials)
    return selected,trials
