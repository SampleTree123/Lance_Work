"""Materialize and independently check a history-aware candidate. Offline only."""
from pathlib import Path
import copy, importlib.util, json, shutil, sys, types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent
BASE=OUT/'dataset_distributed_graph_20261022_v10/aspect_work/selected_candidate'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def main():
    candidate=ROOT/'selected_candidate';candidate.mkdir(exist_ok=False)
    for split in ('train','test'):
        target=candidate/split;target.mkdir()
        for name in ('nodes.json','edges.json'):shutil.copyfile(ROOT/'trial2'/split/name,target/name)
        shutil.copyfile(BASE/split/'render_requests.json',target/'render_requests.json')
        sessions=[json.loads(x) for x in (ROOT/'trial2'/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
        for c in sessions:
            if 'selection_origin' in c:c['baseline_selection_origin']=c.pop('selection_origin')
            c['selection_origin']={'method':'history_weighted_suffix_resampling_and_constrained_whole_chain_acceptance','source':str(BASE/split/'sessions.jsonl'),'baseline_session_id':c['id'],'optimization':str(ROOT/'trial2'/f'{split}_optimization.json')}
        (target/'sessions.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False,separators=(',',':'))+'\n' for c in sessions),encoding='utf-8')
    rules=read(BASE.parent/'RULES.json');rules['schema_version']=11;rules['rule_set_id']=ROOT.name;rules['status']='history_return_control_offline_candidate_not_rendered'
    rules['scope']['document']='CURRENT_CANDIDATE.json; REPORT.md'
    policy={'definition':'edited target axis equals an ancestor value along selected source ancestry; implicit fork inheritance is not a return edit','proposal_target_weights':{'new_value':1.0,'immediately_replaced_value':.05,'older_ancestor_value':.20,'other_branch_seen_value':.35},'axis_decay':.4,'axis_target_availability':'multiply axis proposal by mean target novelty weight, then sample a target using novelty, capacity and exposure weights','weights_are_not_final_probabilities':True,'whole_chain_acceptance':'preserve all baseline nodes and actual target coverage; retain .5-1.5 history frequency bounds; soft preference against explicit returns, chronological repeats and full-node revisits; no global prohibition on natural repeats','per_chain_distinct_axes':'not below that same baseline chain','initial_nodes_and_parent_positions':'exactly fixed per chain','identity_edit_count_max_relative_drift_from_v10':.02,'each_nonidentity_axis_max_relative_drift_from_v10':.05,'six_nonidentity_max_relative_deviation_from_mean':.10,'formal_single_opportunity_fraction_guard':[.47,.53],'maximum_directed_edge_use':4,'four_use_edge_fraction_max':.005,'implicit_unedited_fork_resets_penalized':False,'train_and_test_policy_identical':True}
    rules['attribute_return_control']=policy
    rules['actual_implementation']={'source':str(BASE),'candidate':str(candidate),'nodes_and_graph_edges_byte_identical_to_v10':True,'histories_resampled':True,'new_main_render_nodes':0,'initial_nodes_and_parent_positions_fixed':True,'camera_trajectory_template_not_final_world_trajectory':True}
    rules['optimization']={'scope':'new suffix path proposals on the unchanged v10 graph; actual legal source-target edges only','inputs':str(ROOT/'trial2'),'frequency_balance_required_separately_per_aspect':False,'claims_global_optimum':False,'production_media_generated':False}
    rules['local_target_support']['candidate_sampling_implementation']='v11 history-aware suffix proposals with .4 axis decay and explicit old-target preference, followed by constrained whole-chain acceptance; v10 node/edge graph and whole-component aspect assignment retained'
    write(ROOT/'RULES.json',rules)
    audit=load('return_audit',ROOT/'audit_returns.py');ret=audit.audit(candidate,BASE);write(ROOT/'return_audit.json',ret);assert ret['passed_checks']
    freq=load('frequency_audit',OUT/'dataset_distributed_graph_20261022_v10/audit_work/audit_distributed.py').audit(candidate,ROOT/'frequency_audit.json');assert freq['passed']
    inherited=load('inherited_audit',OUT/'dataset_distributed_graph_20261022_v10/audit_work/audit_inherited_contract.py').audit(candidate,ROOT/'inherited_audit.json');assert inherited['passed']
    sys.path.insert(0,str(OUT/'dataset_trial_build_20261021_v1'))
    from plan_references import Planner,pin,stable
    planner=Planner(candidate,20261022);planner.rules=rules;planner.inputs.append(pin(ROOT/'RULES.json'));references=planner.run()
    helper=types.ModuleType('materialize');helper.ROOT=ROOT;helper.read=read;helper.write=write;helper.lines=lambda p:[json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()];helper.token=stable;helper.pin=pin;sys.modules['materialize']=helper
    load('reference_checker',OUT/'dataset_dual_aspect_20261022_v7/check_references.py').main()
    preservation={}
    for split in ('train','test'):
        preservation[split]={name:pin(BASE/split/name)['sha256']==pin(candidate/split/name)['sha256'] for name in ('nodes.json','edges.json','render_requests.json')}
    assert all(all(x.values()) for x in preservation.values())
    write(ROOT/'PRESERVATION.json',{'passed':True,'byte_identical_to_v10':preservation,'all_nodes_still_used':True,'initial_nodes_and_parent_topology':'return_audit.json baseline_preservation','train_test_content_overlap':freq['canonical_content_train_test_overlap'],'shared_ue_modified':False})
    summary={}
    for split in ('train','test'):
        trial=read(ROOT/'trial2'/f'{split}_optimization.json');summary[split]={'baseline':trial['baseline'],'final':trial['final'],'nodes':len(read(candidate/split/'nodes.json')),'edit_count':sum(trial['final']['axis_counts'].values()),'six_axis_max_deviation':freq['splits'][split]['six_nonidentity_max_relative_deviation'],'average_edge_reuse':freq['splits'][split]['semantic_directed_edge_reuse']['mean']}
    current={'status':'offline_candidate_ready_for_review_not_rendered','candidate':str(candidate),'previous_candidate':str(BASE),'rules':str(ROOT/'RULES.json'),'report':str(ROOT/'REPORT.md'),'summary':summary,'reference_counts':references['unique_reference_items_by_kind'],'reference_image_total':references['unique_images'],'reference_video_total':references['unique_motion_clips'],'main_video_total':sum(s['nodes'] for s in summary.values()),'extra_main_videos':0,'rendered':False,'all_requested_offline_checks_passed':True,'checks':{n:str(ROOT/n) for n in ('return_audit.json','frequency_audit.json','inherited_audit.json','reference_binding_check.json','PRESERVATION.json')},'selected_file_pins':[pin(candidate/s/f) for s in ('train','test') for f in ('nodes.json','edges.json','sessions.jsonl','render_requests.json')],'claims_global_optimum':False,'claims_media_quality_acceptance':False,'selection':'trial2 tighter baseline edit-mixture and conditional-single guards; trial1 not selected'}
    write(ROOT/'CURRENT_CANDIDATE.json',current)
    lines=['# v11：降低链内属性回换','', '当前为离线可审查候选，没有启动UE、渲染或训练。用户批准降低回换偏好；本轮不增加视频节点。','', '## 实现', '', '沿实际选择的历史源版本追溯属性。新值权重1，刚换掉的值0.05，更早祖先值0.20，其他分支已出现的值0.35。保留属性重复衰减0.4；这些是提议权重，不是最终概率。合法目标的历史偏好也参与属性选择，避免选中仅有A/B的属性后被迫反向修改。', '', '新路径在原图内生成，整链验收保持全量属性和实际编辑目标覆盖、频次范围、单边上限等条件；每条链的不同属性数不低于原链。初始节点、长度、直链/分叉类型、分叉轮次与source_position、画幅全部保留。分叉导致未编辑属性恢复历史源状态，是完整继承语义，不作为回换惩罚。', '', '没有把所有回换禁止，也没有新设统一的“每条链至少修改几种属性”的门槛；保持不低于原链的属性多样性是本轮路径替换条件。优化偏好更少回换，最终分布由图的可达目标和全局约束共同决定。', '', '## 结果','', '|指标|训练v10|训练v11|测试v10|测试v11|','|---|---:|---:|---:|---:|']
    for title,key in [('回换编辑次数','return_events'),('含回换的链数','return_chains'),('完整节点重复出现次数','full_node_repeats')]:lines.append('|'+title+'|'+'|'.join(str(summary[s][which][key]) for s in ('train','test') for which in ('baseline','final'))+'|')
    lines+=['', '|长度|训练v10含回换链比例|训练v11比例|测试v10比例|测试v11比例|','|---|---:|---:|---:|---:|']
    for length in range(2,6):
        row=[str(length)]
        for s in ('train','test'):
            for which in ('baseline','final'):
                v=summary[s][which]['by_length'][str(length)];row.append(f"{v['return_chains']/v['chains']:.2%}")
        lines.append('|'+ '|'.join(row)+'|')
    lines+=['', '## 原有要求与成本','',f"主视频仍为训练 {summary['train']['nodes']}、测试 {summary['test']['nodes']}，合计 {current['main_video_total']}。",f"更新后的参考需求为 {references['unique_images']} 张图片、{references['unique_motion_clips']} 段动作参考视频（均未渲染）。",'', '节点配置、图边和主视频渲染请求与v10逐字节相同；所有节点仍在链中使用。独立频次、继承语义、实际目标覆盖、源位置绑定、参考链接检查通过。训练完整覆盖和每个动作至少10种有效镜头保持。', '', '## 比较与限制','', '第一轮虽通过原有检查，但单件服装编辑占合法机会比例下降至约45%，身份编辑数下降约5%。因此选第二轮：单件比例限制47%–53%，身份次数相对v10偏移最多2%，其他各属性次数偏移最多5%，六类总体仍满足均值±10%。这些是本轮保护既有混合比例的实现条件，不是新增用户硬性数据契约。', '', '回换不为零；剩余回换集中在较长链。隐式分叉恢复可能增加，意味着被放弃分支与历史源的差异更大，不等同于新增显式回换。没有证明全局最优或多随机种子稳定性。旧v10及试验均保留，未覆写旧结果。', '', '## 证据与复现','', '- CURRENT_CANDIDATE.json：当前候选及文件哈希。','- RULES.json：继承的规则及回换控制。','- return_audit.json：按属性/链长/类型及隐式恢复的独立统计。','- frequency_audit.json、inherited_audit.json：原有要求复核。','- reference_binding_check.json：52,560次编辑的参考需求绑定。','- trial2/*_optimization.json：来源、实际尝试数、采样记录。','- optimize_returns.py：用相同source、seed及--max-attempts重放；训练450000次、测试150000次。','- optimize_returns_trial1_snapshot.py：第一轮代码快照，历史未选中。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'summary':summary,'references':current['reference_counts'],'candidate':str(candidate)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
