"""Build and check a .4 history-decay candidate using pinned existing methods.

Run sampling first, then this script. Existing inputs are read only.
"""
from pathlib import Path
from collections import Counter
import copy, hashlib, importlib.util, json, sys, time
import numpy as np

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
V6=OUT/'dataset_compact_graph_20261022_v6'
V7=OUT/'dataset_dual_aspect_20261022_v7'
SOURCE=ROOT/'structural_candidate'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def pin(p): return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def maxdev(report):
    return {a:max(abs(6*v/sum(n.values())-1) for v in n.values()) for a in ('landscape','portrait')
            for n in [{k:v for k,v in report[a]['axis_steps'].items() if k!='identity'}]}

def main():
    started=time.time()
    assert read(SOURCE/'SUMMARY.json')['train']['construction']['sampling']['complete']
    assert read(SOURCE/'SUMMARY.json')['test']['construction']['sampling']['complete']
    # Existing independent semantic auditor, with diagnostics routed only here.
    ac=loadmod('decay04_compact_audit',V6/'audit_compact.py')
    ac.write_diagnostic=dump
    structural=ac.audit_compact(SOURCE,ROOT/'structural_audit.json')
    print('structural_audit',structural['passed_hard_checks'],flush=True)
    assert structural['passed_hard_checks']
    sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
    from audit_candidate import Rules
    rules=Rules()
    mask={'schema':'dual_aspect_portrait_eligibility_mask_v1','rule':'formal Rules.valid_state with aspect=portrait','splits':{}}
    for split in ('train','test'):
        nodes=read(SOURCE/split/'nodes.json');chains=[json.loads(x) for x in (SOURCE/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
        bad={n['id']:rules.valid_state(dict(n['state'],aspect='portrait')) for n in nodes}
        bad={k:v for k,v in bad.items() if v}
        badchains=[c['id'] for c in chains if any(n in bad for n in c['history'])]
        mask['splits'][split]={'portrait_forbidden_node_ids':list(bad),'portrait_forbidden_chain_ids':badchains,'reasons_by_node_id':bad,'node_count':len(nodes),'session_count':len(chains)}
    dump(ROOT/'portrait_eligibility_mask.json',mask)
    p=loadmod('decay04_partition',V7/'partition_agent/partition.py');p.SOURCE=SOURCE;p.HERE=ROOT
    selected={}; trials={}
    axis_profile=dict(weight={'total':2,'sex':.5,'camera':.03,'sex_camera':.005,'axis':3,'edit':.001},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.20,.80),'sex_camera':(.15,.85),'axis':(.49,.51),'edit':(.25,.75)},bound_weight=150,temperature=.12,bound_weight_by_feature={'axis':3000,'camera':50,'sex_camera':10,'edit':5},record_distribution=True)
    for split in ('train','test'):
        d=p.load(split);initial=p.spectral(d,6101)
        x,trace=p.optimize(d,initial,6101,p.PROFILES['economy'],24)
        report=p.save(d,split,'economy',p.chain_labels(d,x),{'seed':6101,'profile':p.PROFILES['economy'],'trace':trace,'method':'v7 economy whole-chain bundled hypergraph partition'})
        trials[split]={'economy':{'renders':report['render_jobs'],'six_axis_max_relative_deviation':maxdev(report)}}
        name='economy'
        if max(maxdev(report).values())>.10:
            x,trace=p.optimize(d,x,6107,axis_profile,24)
            report=p.save(d,split,'axis_balanced',p.chain_labels(d,x),{'seed':6107,'profile':axis_profile,'trace':trace,'method':'v7 per-axis balanced refinement of economy assignment'})
            trials[split]['axis_balanced']={'renders':report['render_jobs'],'six_axis_max_relative_deviation':maxdev(report)};name='axis_balanced'
        assert max(maxdev(report).values())<=.10, (split,maxdev(report))
        assert report['all_start_cameras_covered_both'] and report['all_7_axes_covered_both'] and report['all_sexes_covered_both']
        selected[split]={'source':str(ROOT/name/split),'stats':report,'max_relative_axis_deviation':maxdev(report)}
        import shutil
        target=ROOT/'selected_assignment'/split;target.mkdir(parents=True,exist_ok=True)
        for f in ('assignment.jsonl','stats.json','method.json','node_requirements.json'):shutil.copyfile(ROOT/name/split/f,target/f)
        dump(ROOT/'partition_trials.json',trials)
    dump(ROOT/'selected_assignment/SOURCES.json',selected)
    m=loadmod('decay04_materialize',V7/'materialize.py');m.ROOT=ROOT;m.SOURCE=SOURCE
    counts=m.build(ROOT/'selected_assignment',ROOT/'selected_candidate')
    # All .2 -> .4 edits are restricted to the actual history policy fields.
    r=read(V7/'RULES.json');r['schema_version']=8;r['rule_set_id']=ROOT.name
    r['status']='dual_aspect_decay04_offline_candidate_verified_not_rendered'
    r['scope']['document']='REPORT.md; CURRENT_CANDIDATE.json'
    for k,v in r.items():
        if isinstance(v,dict):
            if 'history_axis_penalty_base' in v:v['history_axis_penalty_base']=.4
            if 'history_axis_penalty_formula' in v:v['history_axis_penalty_formula']='base_axis_weight * (0.4 ** prior_axis_occurrence_count)'
            if 'candidate_sampling_implementation' in v:v['candidate_sampling_implementation']=v['candidate_sampling_implementation'].replace('0.2**n','0.4**n')
    r['inherited_rule_snapshot']=str(V7/'RULES.json')
    r['actual_implementation']={'source':str(SOURCE),'same_graph_source':str(V6/'selected_seed1'),'candidate':str(ROOT/'selected_candidate'),'counts':counts,'new_sampler_invoked_for_selected_candidate':True,'history_decay':.4,'sampling_seeds':{'train':2026102261,'test':2026102262},'all_new_structural_sessions_preserved_exactly_once':True,'selected_assignments':str(ROOT/'selected_assignment'),'camera_trajectory_template_not_final_world_trajectory':True}
    r['stability']={'this_candidate':'one actual seed pair; three-seed .4 stability not assessed','baseline':'v6 .2 three seeds; v7 frozen .2 selected_seed1 projection'}
    r['optimization']={'baseline':str(V7/'selected_candidate'),'baseline_render_nodes':{'train':4963,'test':1187},'scope':'same explicit content graph; resample with .4, then whole-chain aspect partition','selected_policy':trials,'retained_v6_sampling_parameters_except_history_decay':True}
    r['aspect_policy']['selection_policy']={'initial':'v7 economy','refine_if':'any aspect six-nonidentity-axis deviation exceeds 10%','trials':'partition_trials.json'}
    dump(ROOT/'RULES.json',r)
    sys.path.insert(0,str(OUT/'dataset_trial_build_20261021_v1'))
    from plan_references import Planner
    planner=Planner(ROOT/'selected_candidate',20261022);planner.rules=r;planner.inputs.append(pin(ROOT/'RULES.json'))
    references=planner.run()
    doc=ROOT/'selected_candidate/REFERENCES.md';txt=doc.read_text(encoding='utf-8').replace('分辨率、帧率、时长、画幅，','分辨率、帧率、时长，')
    doc.write_text(txt+'\n本候选每条链固定横屏或竖屏，参考需求按实际目标画幅重算。最终像素尺寸、帧率、时长尚未冻结。\n',encoding='utf-8')
    audit=loadmod('decay04_aspect_audit',V7/'audit_agent/audit_dual_aspect.py')
    verified=audit.audit(ROOT/'selected_candidate',SOURCE,1,True);dump(ROOT/'aspect_audit.json',verified)
    assert verified['passed'],verified['error_counts']
    sys.modules['materialize']=m
    refcheck=loadmod('decay04_reference_check',V7/'check_references.py');refcheck.main()
    dump(ROOT/'CURRENT_CANDIDATE.json',{'status':r['status'],'candidate':str(ROOT/'selected_candidate'),'structural_source':str(SOURCE),'history_decay':.4,'rules':str(ROOT/'RULES.json'),'counts':counts,'structural_audit':str(ROOT/'structural_audit.json'),'aspect_audit':str(ROOT/'aspect_audit.json'),'reference_binding_check':str(ROOT/'reference_binding_check.json'),'rendered':False})
    inputs=[pin(__file__),pin(V7/'partition_agent/partition.py'),pin(V7/'materialize.py'),pin(V7/'audit_agent/audit_dual_aspect.py'),pin(V6/'sample_compact_v68_snapshot.py'),pin(V6/'audit_compact.py'),pin(V7/'RULES.json')]
    inputs += [pin(V6/'selected_seed1'/s/f) for s in ('train','test') for f in ('nodes.json','edges.json','sessions.jsonl')]
    dump(ROOT/'INPUTS_AND_METHODS.json',{'history_decay':.4,'same_graph':str(V6/'selected_seed1'),'baseline_aspect_candidate':str(V7/'selected_candidate'),'sampling_parameters':read(SOURCE/'SAMPLER_CODE.json'),'inputs':inputs,'partition_trials':trials,'counts':counts,'references':references,'single_seed_pair_only':True,'elapsed_finish_seconds':time.time()-started})
    print('FINISHED',json.dumps({'counts':counts,'trials':trials,'references':references},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
