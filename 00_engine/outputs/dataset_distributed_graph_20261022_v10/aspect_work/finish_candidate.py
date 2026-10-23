"""V10 distributed-graph whole-chain aspect projection; no UE or render.

Only writes beside this script. Input structural candidate is immutable.
Run Python with -B to suppress bytecode outside this owned output folder.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, copy, hashlib, importlib.util, json, shutil, sys, time
import numpy as np

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
OUTPUTS=ROOT.parents[1]
V7=OUTPUTS/'dataset_dual_aspect_20261022_v7'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def lines(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pin(path):
    path=Path(path).resolve();return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def sixdev(report):
    result={}
    for aspect in ('landscape','portrait'):
        counts={k:v for k,v in report[aspect]['axis_steps'].items() if k!='identity'}
        assert len(counts)==6
        result[aspect]=max(abs(v*6/sum(counts.values())-1) for v in counts.values())
    return result
def action_camera(candidate):
    report={}
    for split in ('train','test'):
        nodes=read(candidate/split/'nodes.json');chains=lines(candidate/split/'sessions.jsonl')
        used={n for c in chains for n in c['history']}
        actionsets=defaultdict(set);aspectsets=defaultdict(lambda:defaultdict(set))
        for node in nodes:
            if node['id'] not in used:continue
            st=node['state'];actionsets[st['action']].add(st['camera']);aspectsets[st['aspect']][st['action']].add(st['camera'])
        report[split]={'actual_used_nodes':len(used),'action_count':len(actionsets),'camera_count_by_action':{a:len(c) for a,c in sorted(actionsets.items())},'cameras_by_action':{a:sorted(c) for a,c in sorted(actionsets.items())},'minimum_cameras_per_action':min(map(len,actionsets.values())),'by_aspect':{aspect:{a:len(c) for a,c in sorted(values.items())} for aspect,values in aspectsets.items()}}
    assert report['train']['action_count']==25
    assert report['train']['minimum_cameras_per_action']>=10, report['train']['camera_count_by_action']
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--ready-audit',type=Path,required=True);parser.add_argument('--rules',type=Path,default=ROOT.parent/'RULES.json');parser.add_argument('--resume-materialized',action='store_true');args=parser.parse_args()
    source=args.source.resolve();started=time.time()
    readiness=read(args.ready_audit)
    assert readiness.get('passed_hard_checks',readiness.get('passed',False)), 'New v10 structural distribution audit must pass before projection'
    inherited_path=ROOT.parent/'structural_inherited_audit.json'
    inherited=read(inherited_path)
    assert inherited.get('passed',False), 'New v10 inherited semantics/target/start-quota audit must also pass'
    formal=read(args.rules)
    assert source!=ROOT and ROOT not in source.parents
    assert args.resume_materialized or not (ROOT/'selected_candidate').exists() or not any((ROOT/'selected_candidate').iterdir()), 'Never overwrite an already materialized candidate'
    input_pins=[pin(source/split/name) for split in ('train','test') for name in ('nodes.json','edges.json','sessions.jsonl')]
    dump(ROOT/'INPUT_SOURCE.json',{'source':str(source),'inputs':input_pins,'history_decay':.4,'edge_reuse_soft_target':2.5,'readiness_audit':pin(args.ready_audit),'formal_rules':pin(args.rules),'frequency_scope':'combined train content and chain history; no separate per-aspect .5-1.5 requirement'})
    sys.path.insert(0,str(OUTPUTS/'dataset_balanced_graph_20261022_v5'))
    from audit_candidate import Rules
    rules=Rules();mask={'schema':'dual_aspect_portrait_eligibility_mask_v1','rule':'formal Rules.valid_state(state with aspect=portrait)','splits':{}}
    for split in ('train','test'):
        nodes=read(source/split/'nodes.json');chains=lines(source/split/'sessions.jsonl')
        bad={n['id']:rules.valid_state(dict(n['state'],aspect='portrait')) for n in nodes}
        bad={key:value for key,value in bad.items() if value}
        badchains=[c['id'] for c in chains if any(n in bad for n in c['history'])]
        mask['splits'][split]={'portrait_forbidden_node_ids':list(bad),'portrait_forbidden_chain_ids':badchains,'reasons_by_node_id':bad,'node_count':len(nodes),'session_count':len(chains)}
    dump(ROOT/'portrait_eligibility_mask.json',mask)
    if (ROOT/'selected_assignment/SOURCES.json').exists():
        selected=read(ROOT/'selected_assignment/SOURCES.json');trials=read(ROOT/'partition_trials.json')
        for split in ('train','test'):
            assert read(ROOT/'selected_assignment'/split/'method.json')['source_files']==[pin(source/split/f) for f in ('nodes.json','edges.json','sessions.jsonl')]
        print('REUSED_ZERO_COPY_COMPONENT_ASSIGNMENTS',flush=True)
    else:
        component=loadmod('v10_component_partition',ROOT/'component_partition.py')
        selected,trials=component.partition(source,ROOT)
    materialize=loadmod('v10_materialize',ROOT/'materialize_snapshot.py');materialize.ROOT=ROOT;materialize.SOURCE=source
    if args.resume_materialized:
        counts=read(ROOT/'selected_candidate/SUMMARY.json')
        for split in ('train','test'):
            target=ROOT/'selected_candidate'/split
            nodes=read(target/'nodes.json');edges=materialize.project_source_provenance(source/split,nodes)
            materialize.write(target/'nodes.json',nodes);materialize.write(target/'edges.json',edges)
        assembly=read(ROOT/'selected_candidate/ASSEMBLY.json')
        assembly['provenance_policy']='Preserve genuine source created_by and remap parent ids; retain all actual source graph edges within each whole component'
        assembly['provenance_materializer']=pin(ROOT/'materialize_snapshot.py')
        dump(ROOT/'selected_candidate/ASSEMBLY.json',assembly)
    else:counts=materialize.build(ROOT/'selected_assignment',ROOT/'selected_candidate')
    coverage=action_camera(ROOT/'selected_candidate');dump(ROOT/'action_camera_coverage.json',coverage)
    formal=copy.deepcopy(formal);formal['schema_version']=10;formal['rule_set_id']=ROOT.parent.name
    formal['status']='from_scratch_distributed_decay04_dual_aspect_offline_candidate_not_rendered'
    formal['scope']['document']='aspect_work/CURRENT_CANDIDATE.json; action_camera_coverage.json'
    formal['reuse']['per_axis_mean_reuse_soft_target']=2.5
    formal['reuse']['content_edge_aggregation_ignores_aspect']=True
    formal['coverage']['train']['each_action_minimum_camera_types_on_actual_used_nodes']=10
    formal['coverage']['train']['action_camera_coverage_combines_aspects']=True
    formal['local_target_support']['candidate_sampling_implementation']='v10 from-scratch distributed content graph and actual new chain sampling; full-history 0.4**n; user frequency rules assessed on combined train unique content and chain history; original structural histories preserved by aspect projection'
    formal['actual_implementation']={'source':str(source),'candidate':str(ROOT/'selected_candidate'),'counts':counts,'history_decay':.4,'edge_reuse_soft_target':2.5,'all_new_structural_sessions_preserved_exactly_once':True,'selected_assignments':str(ROOT/'selected_assignment'),'camera_trajectory_template_not_final_world_trajectory':True}
    formal['optimization']={'scope':'from-scratch distributed content graph; .4 sampling; zero-duplication whole-connected-component aspect feasibility assignment','selected_policy':trials,'train_minimum_actual_cameras_per_action_including_head_diagnostic':coverage['train']['minimum_cameras_per_action'],'train_action_count':coverage['train']['action_count'],'frequency_balance_required_separately_per_aspect':False,'readiness_audit':pin(args.ready_audit),'inherited_readiness_audit':pin(inherited_path),'global_frequency_preserved_by_unchanged_histories':True}
    dump(ROOT/'RULES.json',formal)
    sys.path.insert(0,str(OUTPUTS/'dataset_trial_build_20261021_v1'))
    from plan_references import Planner
    planner=Planner(ROOT/'selected_candidate',20261022);planner.rules=formal;planner.inputs.append(pin(ROOT/'RULES.json'))
    references=planner.run()
    doc=ROOT/'selected_candidate/REFERENCES.md'
    doc.write_text(doc.read_text(encoding='utf-8').replace('分辨率、帧率、时长、画幅，','分辨率、帧率、时长，')+'\n本候选每条链固定横屏或竖屏，参考需求按实际目标画幅重算。最终像素尺寸、帧率、时长尚未冻结。\n',encoding='utf-8')
    audit=loadmod('v10_projection_audit',V7/'audit_agent/audit_dual_aspect.py')
    verified=audit.audit(ROOT/'selected_candidate',source,1,True);dump(ROOT/'aspect_audit.json',verified)
    assert verified['passed'],verified['error_counts']
    frequency_audit=loadmod('v10_projected_frequency_audit',ROOT.parent/'audit_work/audit_distributed.py')
    projected_frequency=frequency_audit.audit(ROOT/'selected_candidate',ROOT/'projected_frequency_audit.json')
    assert projected_frequency['passed']
    inherited_audit=loadmod('v10_projected_inherited_audit',ROOT.parent/'audit_work/audit_inherited_contract.py')
    projected_inherited=inherited_audit.audit(ROOT/'selected_candidate',ROOT/'projected_inherited_audit.json')
    assert projected_inherited['passed']
    sys.modules['materialize']=materialize
    refcheck=loadmod('v10_reference_check',V7/'check_references.py');refcheck.main()
    dump(ROOT/'CURRENT_CANDIDATE.json',{'status':formal['status'],'candidate':str(ROOT/'selected_candidate'),'structural_source':str(source),'history_decay':.4,'rules':str(ROOT/'RULES.json'),'counts':counts,'aspect_audit':str(ROOT/'aspect_audit.json'),'action_camera_coverage':str(ROOT/'action_camera_coverage.json'),'structural_readiness_audit':str(args.ready_audit.resolve()),'projected_frequency_audit':str(ROOT/'projected_frequency_audit.json'),'projected_inherited_audit':str(ROOT/'projected_inherited_audit.json'),'reference_binding_check':str(ROOT/'reference_binding_check.json'),'rendered':False})
    assert input_pins==[pin(source/split/name) for split in ('train','test') for name in ('nodes.json','edges.json','sessions.jsonl')], 'Immutable input changed during projection'
    extra=[source/'SOURCES.json'] if (source/'SOURCES.json').exists() else []
    dump(ROOT/'INPUTS_AND_METHODS.json',{'inputs':input_pins+[pin(p) for p in extra]+[pin(__file__),pin(ROOT/'component_partition.py'),pin(ROOT/'materialize_snapshot.py'),pin(args.ready_audit),pin(inherited_path),pin(args.rules),pin(V7/'partition_agent/partition.py'),pin(V7/'audit_agent/audit_dual_aspect.py'),pin(V7/'check_references.py')],'partition_trials':trials,'counts':counts,'references':references,'history_decay':.4,'edge_reuse_soft_target':2.5,'frequency_balancing_scope':'combined train; no separate per-aspect .5-1.5 requirement','single_seed_pair_only':True,'elapsed_seconds':time.time()-started})
    print('FINISHED',json.dumps({'counts':counts,'partition_trials':trials,'action_camera':coverage['train']['camera_count_by_action'],'references':references},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
