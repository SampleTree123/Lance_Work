"""Publish a concise offline delivery report and hash-bound selected evidence."""
from datetime import datetime,timezone
from pathlib import Path
from materialize import ROOT,SOURCE,read,write,pin

def main():
    c=ROOT/'selected_candidate'; summary=read(c/'SUMMARY.json')
    audit=read(ROOT/'audit_agent/audit_selected.json')
    refs=read(c/'reference_summary.json'); refcheck=read(ROOT/'reference_binding_check.json')
    assert audit['passed'] and refcheck['passed']
    assert audit['cross_split_overlap_ignoring_aspect']==0
    assert audit['cross_split_structural_chain_overlap_ignoring_aspect']==0
    dist=read(ROOT/'partition_agent/distribution_detail.json')
    rows={'train':dist['economy']['train'],'test':dist['axis_balanced']['test']}
    alternatives=read(ROOT/'partition_agent/summary.json')
    base=4552; total=sum(s['render_nodes'] for s in summary.values())
    assert total==6150
    comparison=[]
    for name in ('random_baseline','spectral_baseline','economy','compromise_budget','tight'):
        v=alternatives[name];n=sum(v[s]['render_jobs'] for s in ('train','test'))
        comparison.append({'candidate':name,'train':v['train']['render_jobs'],
            'test':v['test']['render_jobs'],'total':n,'increase_fraction':n/base-1,
            'all_original_chains_retained':True})
    comparison.append({'candidate':'selected_candidate','train':4963,'test':1187,'total':total,
        'increase_fraction':total/base-1,'all_original_chains_retained':True})
    comparison.append({'candidate':'resampled_repair_not_selected','train':4200,'test':1099,'total':5299,
        'increase_fraction':5299/base-1,'all_original_chains_retained':False,
        'not_selected_reason':'formal single-slot support and conditional garment balance regress'})
    write(ROOT/'comparison.json',comparison)
    lines=['# 双画幅结果：保留全部原链，增加1598个主视频','',
        '推荐入口为`selected_candidate`。本轮仅生成离线配置、相机模板引用和参考需求，未操作UE、未渲染。',
        '原4552种不同内容配置与12000/2400条编辑链全部保留。为其中1598种配置增加另一画幅，实际主视频总数6150，比4552增加35.11%；比全量双份9104少2954个视频。', '',
        '| 集合 | 原内容配置 | 横屏视频 | 竖屏视频 | 实际视频合计 | 横屏链 | 竖屏链 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for split,label in [('train','训练'),('test','测试')]:
        s=summary[split];n=s['render_count_by_aspect'];q=s['chain_count_by_aspect']
        lines.append(f"| {label} | {s['content_nodes']} | {n['landscape']} | {n['portrait']} | {s['render_nodes']} | {q['landscape']} | {q['portrait']} |")
    lines+=['','训练视频增加1211（32.28%）；测试增加387（48.38%）。训练仍低于旧5000上限，测试超过旧800；用户已允许双画幅适度增量，这里按实际4552基准披露成本，未用旧上限掩盖增幅。参考图片与动作参考视频另计。','',
        '## 为什么选这一版','',
        '| 做法 | 主视频数 | 主要结果 |','|---|---:|---|',
        '| 全部内容都渲染横竖两份 | 9104 | 成本最高；不是本轮选择 |',
        '| 原链随机分配画幅（固定种子试算） | 9071 | 共享太多，几乎没有省下渲染 |',
        '| 按共享关系优化，经济档 | 6085 | 原链全保留，但测试两画幅内部编辑频次偏差仍较大 |',
        '| **当前选择** | **6150** | 只比经济档多65个，测试两画幅内部六类编辑频次也达到10%以内 |',
        '| 原链保留，起始镜头更接近逐个均分 | 6843 | 分布更齐，但本轮不为精确均分支付这部分成本 |',
        '| 改子图并重新生成链的便宜备选 | 5299 | 合法性与覆盖通过，但单件服装选择再次明显偏斜，未选 |','',
        '便宜重采样版本训练外套实际编辑次数比当前来源允许部位的条件期望高约67%，合法单件部位机会缺边明显增加。4条横竖重复结构已另存修复，但没有消除服装分布回归。失败与修复记录都保留，不作为当前入口。','',
        '## 保留了什么，哪些分布仍不完全相等','',
        '- 每条原链恰好保留一次；顺序、编辑属性、长度、分叉时刻与完整历史父引用不变。整链含全部分支固定一种画幅。',
        '- 训练/测试12000/2400条、43800/8760次编辑不变；训练全属性值和239件核心衣物的真实编辑目标覆盖不变。',
        '- 两种画幅各自都有男女、21种起始镜头和七类编辑。训练/测试去掉画幅后依然没有相同内容节点或相同完整链。',
        '- 由于全部原编辑步骤保留，整体六类编辑次数、单件服装条件分布、链内不同属性数、同内容边复用都与v6一致；没有靠分画幅重新计算来掩盖旧边的复用。',
        '- 横竖屏视频数不必相等：共享结构不同导致一边可能需要更多视频。链数则接近各半。','',
        '| 每画幅六类非身份编辑的最大频次偏差 | 横屏 | 竖屏 |','|---|---:|---:|']
    for split,label in [('train','训练'),('test','测试')]:
        lines.append(f"| {label} | {rows[split]['landscape']['six_axis_max_relative_deviation_pct']:.2f}% | {rows[split]['portrait']['six_axis_max_relative_deviation_pct']:.2f}% |")
    lines+=['',
        '同一镜头分到竖屏的比例仍大约19%—81%，不是每个镜头各半；所有镜头在两种画幅都有实际样本。上述10%只描述六类编辑的次数偏差，不表示具体人物、衣服、场景或服装部位频次相等。五轮链不同属性数仍为训练4.215、测试3.813；这次没有重新抽链。',
        '在来源允许单件替换时，单件编辑比例为训练横50.02%/竖47.40%、测试横53.08%/竖50.79%。原整体部位实际数和条件期望完全保留，但拆开画幅后仍有部位偏差：例如训练外套横93次（条件期望119.5）、竖71次（期望46.5）。未声称每画幅的每个衣物部位都已均衡，详细诊断见audit_agent/selected_per_aspect_diagnostics.json。','',
        '## 参考素材与渲染接入','',
        f"已按52560次真实编辑重新生成参考需求：{refs['unique_images']}张图片与{refs['unique_motion_clips']}段动作参考视频，均尚未制作。",'',
        '| 参考类型 | 当前数量 | 画幅引入的额外需求 |','|---|---:|---:|']
    labels={'identity':'人物正面','hair':'发型','wardrobe_piece':'服装及鞋等单件','motion':'动作视频','scene':'空背景图片'}
    for k,label in labels.items():
        lines.append(f"| {label} | {refcheck['actual_reference_counts'][k]} | {refcheck['aspect_additional_requirements'][k]} |")
    lines+=['',
        '新增参考需求相对同一内容需求去掉画幅后的去重结果计算；这些是符号拍摄需求，不是已经渲染出的文件。场景参考还保留动作/镜头/性别，因为它们可能影响初始取景。实际世界相机变换确定后需最终绑定。',
        '每个主节点已有render_requests.json条目，关联对应横屏或竖屏相机库模板。模板的宽高/局部轨迹哈希可追溯，但不表示采用production10旧片长、帧率，也不表示已完成新画幅在场景点位上的视觉检查。',
        '下一步可以冻结分辨率、帧率、片长和参考拍摄实施，再做少量横竖屏实际样片。当前不启动正式批量渲染。','',
        '## 文件与复现','',
        '- 当前入口：CURRENT_CANDIDATE.json、selected_candidate/{train,test}。',
        '- 规则与选择：RULES.json、selected_assignment/SOURCES.json、selected_candidate/ASSEMBLY.json。',
        '- 独立审核：audit_agent/audit_selected.json；参考逐步骤检查：reference_binding_check.json。',
        '- 试验对照：comparison.json、partition_agent/README.md、resample_agent/REPORT.md。',
        '- 代码：materialize.py、assemble_selection.py、check_references.py、report_selection.py；具体分配脚本及参数在partition_agent/。',
        '- 文件指纹：DELIVERY_MANIFEST.json。旧v6及未选试验保持原样。','']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    runtime=[]
    for old in read(SOURCE.parent/'INPUTS_AND_METHODS.json')['runtime_source_pins']:
        current=pin(Path(old['path']));current['matches_v6_capture']=current['sha256']==old['sha256'];runtime.append(current)
    write(ROOT/'INPUTS_AND_METHODS.json',{'scope':'offline content-preserving aspect projection',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'baseline':str(SOURCE),'source_bindings':read(c/'ASSEMBLY.json')['inputs'],
        'assignment_selection':read(ROOT/'selected_assignment/SOURCES.json'),
        'runtime_source_pins':runtime,'runtime_sources_match_baseline':all(p['matches_v6_capture'] for p in runtime),
        'reproduction':'Use partition_agent scripts/recorded parameters for assignments; materialize.py accepts a fresh output path. assemble_selection.py is the exact selected assembly recipe and refuses existing output directories.',
        'reference_planner':str(ROOT.parent/'dataset_trial_build_20261021_v1/plan_references.py'),
        'reference_effective_rules':str(ROOT/'RULES.json'),
        'partition_and_audit_code_pins':[pin(p) for directory in ('partition_agent','audit_agent') for p in sorted((ROOT/directory).glob('*.py'))],
        'shared_reference_planner_rules_overridden_by_assemble_selection':True,
        'media_parameters_unfrozen':True,'rendered':False})
    assert all(p['matches_v6_capture'] for p in runtime), 'Changed runtime source requires review'
    files=[p for p in c.rglob('*') if p.is_file()]
    files.extend(p for p in (ROOT/'selected_assignment').rglob('*') if p.is_file())
    for f in ('PLAN.md','RULES.json','REPORT.md','README.md','CURRENT_CANDIDATE.json','INPUTS_AND_METHODS.json',
              'comparison.json','reference_binding_check.json','documentation_result_sync.json',
              'materialize.py','assemble_selection.py','check_references.py','report_selection.py',
              'audit_agent/audit_selected.json','audit_agent/selected_per_aspect_diagnostics.json',
              'audit_agent/INTEGRATION_RESEARCH.md','audit_agent/RESAMPLED_REVIEW.md',
              'partition_agent/verification.json','partition_agent/summary.json','partition_agent/distribution_detail.json'):
        if (ROOT/f).exists(): files.append(ROOT/f)
    write(ROOT/'DELIVERY_MANIFEST.json',{'status':'offline_verified_pending_user_adoption_not_rendered',
        'scope':'selected materialized candidate, effective rules and evidence; not all exploratory artifacts',
        'files':[pin(p) for p in files],'self_hash_excluded':True})
    print({'total_render_nodes':total,'extra_nodes':total-base,'manifest_files':len(files),
           'independent_audit_passed':audit['passed'],'reference_bindings_passed':refcheck['passed']})

if __name__=='__main__':main()
