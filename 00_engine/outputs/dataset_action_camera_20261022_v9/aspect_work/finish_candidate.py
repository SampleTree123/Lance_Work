"""V9 whole-chain aspect projection and symbolic references; no UE or render.

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
V8=OUTPUTS/'dataset_decay04_20261022_v8'

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
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--passes',type=int,default=24);parser.add_argument('--train-only',action='store_true');parser.add_argument('--reuse-train',action='store_true');args=parser.parse_args()
    source=args.source.resolve();started=time.time()
    assert source!=ROOT and ROOT not in source.parents
    assert not (ROOT/'selected_candidate').exists(), 'Never overwrite an already materialized candidate'
    input_pins=[pin(source/split/name) for split in ('train','test') for name in ('nodes.json','edges.json','sessions.jsonl')]
    dump(ROOT/'INPUT_SOURCE.json',{'source':str(source),'inputs':input_pins,'history_decay':.4,'edge_reuse_soft_target':2.5})
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
    p=loadmod('v9_aspect_partition',V7/'partition_agent/partition.py');p.SOURCE=source;p.HERE=ROOT
    axis_profile=dict(weight={'total':2,'sex':.5,'camera':.03,'sex_camera':.005,'axis':3,'edit':.001},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.20,.80),'sex_camera':(.15,.85),'axis':(.49,.51),'edit':(.25,.75)},bound_weight=150,temperature=.12,bound_weight_by_feature={'axis':3000,'camera':50,'sex_camera':10,'edit':5},record_distribution=True)
    trials={};selected={}
    for split in ('train','test'):
        if args.train_only and split=='test':continue
        if args.reuse_train and split=='train':
            assert read(ROOT/'selected_assignment/train/INPUTS.json')==[pin(source/split/name) for name in ('nodes.json','edges.json','sessions.jsonl')]
            selected[split]=read(ROOT/'selected_assignment/SOURCES.json')[split]
            trials[split]=read(ROOT/'partition_trials.json')[split]
            print('REUSED_TRAIN',selected[split]['stats']['render_jobs'],flush=True)
            continue
        d=p.load(split);initial=p.spectral(d,6101)
        x,trace=p.optimize(d,initial,6101,p.PROFILES['economy'],args.passes)
        report=p.save(d,split,'economy',p.chain_labels(d,x),{'seed':6101,'profile':p.PROFILES['economy'],'trace':trace,'method':'v7 exact shared-node cost with chain and node-star moves'})
        name='economy';trials[split]={'economy':{'render_jobs':report['render_jobs'],'six_axis_max_relative_deviation':sixdev(report)}}
        if max(sixdev(report).values())>.10:
            x,trace=p.optimize(d,x,6107,axis_profile,args.passes)
            report=p.save(d,split,'axis_balanced',p.chain_labels(d,x),{'seed':6107,'profile':axis_profile,'trace':trace,'method':'strong per-axis allocation refinement; all original chains retained'})
            name='axis_balanced';trials[split][name]={'render_jobs':report['render_jobs'],'six_axis_max_relative_deviation':sixdev(report)}
        assert max(sixdev(report).values())<=.10,(split,sixdev(report))
        assert .45<=report['portrait']['chain_fraction']<=.55
        assert report['all_start_cameras_covered_both'] and report['all_7_axes_covered_both'] and report['all_sexes_covered_both']
        target=ROOT/'selected_assignment'/split;target.mkdir(parents=True,exist_ok=True)
        for filename in ('assignment.jsonl','stats.json','method.json','node_requirements.json'):
            shutil.copyfile(ROOT/name/split/filename,target/filename)
        selected[split]={'source':str(ROOT/name/split),'max_relative_axis_deviation':sixdev(report),'stats':report}
        dump(target/'INPUTS.json',[pin(source/split/name) for name in ('nodes.json','edges.json','sessions.jsonl')])
        dump(ROOT/'partition_trials.json',trials)
    dump(ROOT/'selected_assignment/SOURCES.json',selected)
    if args.train_only:
        print('TRAIN_PARTITION_READY',selected['train']['stats']['render_jobs'],flush=True)
        return
    materialize=loadmod('v9_materialize',V7/'materialize.py');materialize.ROOT=ROOT;materialize.SOURCE=source
    counts=materialize.build(ROOT/'selected_assignment',ROOT/'selected_candidate')
    coverage=action_camera(ROOT/'selected_candidate');dump(ROOT/'action_camera_coverage.json',coverage)
    content_audit=loadmod('v9_used_content_audit',ROOT.parent/'verify_action_camera_and_reuse.py')
    content_verified=content_audit.run(ROOT/'selected_candidate')
    content_verified['soft_target_warnings']=[e for e in content_verified['errors'] if 'four-use edge fraction exceeds retained soft target' in e]
    content_verified['hard_errors']=[e for e in content_verified['errors'] if e not in content_verified['soft_target_warnings']]
    content_verified['passed_hard_checks']=not content_verified['hard_errors']
    content_verified['soft_target_policy']='Report any four-use edge fraction above .5%; this remains a soft target and does not invalidate preserved structural candidate.'
    dump(ROOT/'used_coverage_reuse_check.json',content_verified)
    assert content_verified['passed_hard_checks'],content_verified['hard_errors']
    formal=read(V8/'RULES.json');formal['schema_version']=9;formal['rule_set_id']=ROOT.parent.name
    formal['status']='action_camera_expanded_decay04_dual_aspect_offline_candidate_verified_not_rendered'
    formal['scope']['document']='aspect_work/CURRENT_CANDIDATE.json; action_camera_coverage.json'
    formal['reuse']['per_axis_mean_reuse_soft_target']=2.5
    formal['reuse']['content_edge_aggregation_ignores_aspect']=True
    formal['coverage']['train']['each_action_minimum_camera_types_on_actual_used_nodes']=10
    formal['coverage']['train']['action_camera_coverage_combines_aspects']=True
    formal['local_target_support']['candidate_sampling_implementation']='v9: exact chain/start-camera quotas; full-history 0.4**n; actual action-camera target coverage; cap3 reuse available from first attempts with weighted low-count support; max4 retained as rare late fallback'
    formal['actual_implementation']={'source':str(source),'candidate':str(ROOT/'selected_candidate'),'counts':counts,'history_decay':.4,'edge_reuse_soft_target':2.5,'all_new_structural_sessions_preserved_exactly_once':True,'selected_assignments':str(ROOT/'selected_assignment'),'camera_trajectory_template_not_final_world_trajectory':True}
    formal['optimization']={'baseline':str(V8/'selected_candidate'),'scope':'new content graph for action-camera coverage, .4 sampling, whole-chain aspect partition','selected_policy':trials,'train_minimum_actual_cameras_per_action':coverage['train']['minimum_cameras_per_action'],'train_action_count':coverage['train']['action_count']}
    dump(ROOT/'RULES.json',formal)
    sys.path.insert(0,str(OUTPUTS/'dataset_trial_build_20261021_v1'))
    from plan_references import Planner
    planner=Planner(ROOT/'selected_candidate',20261022);planner.rules=formal;planner.inputs.append(pin(ROOT/'RULES.json'))
    references=planner.run()
    doc=ROOT/'selected_candidate/REFERENCES.md'
    doc.write_text(doc.read_text(encoding='utf-8').replace('分辨率、帧率、时长、画幅，','分辨率、帧率、时长，')+'\n本候选每条链固定横屏或竖屏，参考需求按实际目标画幅重算。最终像素尺寸、帧率、时长尚未冻结。\n',encoding='utf-8')
    audit=loadmod('v9_projection_audit',V7/'audit_agent/audit_dual_aspect.py')
    verified=audit.audit(ROOT/'selected_candidate',source,1,True);dump(ROOT/'aspect_audit.json',verified)
    assert verified['passed'],verified['error_counts']
    sys.modules['materialize']=materialize
    refcheck=loadmod('v9_reference_check',V7/'check_references.py');refcheck.main()
    dump(ROOT/'CURRENT_CANDIDATE.json',{'status':formal['status'],'candidate':str(ROOT/'selected_candidate'),'structural_source':str(source),'history_decay':.4,'rules':str(ROOT/'RULES.json'),'counts':counts,'aspect_audit':str(ROOT/'aspect_audit.json'),'action_camera_coverage':str(ROOT/'action_camera_coverage.json'),'used_coverage_reuse_check':str(ROOT/'used_coverage_reuse_check.json'),'reference_binding_check':str(ROOT/'reference_binding_check.json'),'rendered':False})
    assert input_pins==[pin(source/split/name) for split in ('train','test') for name in ('nodes.json','edges.json','sessions.jsonl')], 'Immutable input changed during projection'
    dump(ROOT/'INPUTS_AND_METHODS.json',{'inputs':input_pins+[pin(__file__),pin(V7/'partition_agent/partition.py'),pin(V7/'materialize.py'),pin(V7/'audit_agent/audit_dual_aspect.py'),pin(V7/'check_references.py')],'partition_trials':trials,'counts':counts,'references':references,'history_decay':.4,'edge_reuse_soft_target':2.5,'single_seed_pair_only':True,'elapsed_seconds':time.time()-started})
    print('FINISHED',json.dumps({'counts':counts,'partition_trials':trials,'action_camera':coverage['train']['camera_count_by_action'],'references':references},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
