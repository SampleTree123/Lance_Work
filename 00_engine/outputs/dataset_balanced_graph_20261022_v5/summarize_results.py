"""Summarize saved evidence; never changes historical or candidate datasets."""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
AXES=('identity','hair','hair_color','wardrobe','action','camera','site')
LABELS=dict(zip(AXES,('人物身份','发型','发色','服装','动作','镜头','场景')))

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sessions(p):return [json.loads(x) for x in (p/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
def brief(p):
    ss=sessions(p);m=read(p/'metrics.json');use=Counter((s['source'],s['target']) for c in ss for s in c['steps'])
    axes=Counter(s['axis'] for c in ss for s in c['steps'])
    distinct={a:len({(s['source'],s['target']) for c in ss for s in c['steps'] if s['axis']==a}) for a in AXES}
    means={}
    for kind in ('all','linear','fork'):
        means[kind]={}
        for length in range(2,6):
            rows=[c for c in ss if c['length']==length and (kind=='all' or c['kind']==kind)]
            means[kind][str(length)]=sum(len({s['axis'] for s in c['steps']}) for c in rows)/len(rows)
    return {'nodes':m['nodes'],'sessions':len(ss),'edit_steps':sum(axes.values()),'axis_counts':dict(axes),
            'axis_unique_edges':distinct,'axis_average_reuse':{a:axes[a]/distinct[a] for a in AXES},
            'reuse_histogram':dict(sorted(Counter(use.values()).items())),
            'used_edges':len(use),'average_reuse':sum(axes.values())/len(use),'length_distinct_axes':means}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',default='candidate_c_seed1');ap.add_argument('--seeds',nargs='+',default=['candidate_c_seed1','candidate_c_seed2','candidate_c_seed3']);args=ap.parse_args()
    baseline=HERE.parent/'dataset_sequence_graph_20261021_v4'/'rotated'
    comparison={s:{'baseline':brief(baseline/s),'candidate':brief(HERE/args.candidate/s)} for s in ('train','test')}
    stability={}
    for name in args.seeds:
        a=read(HERE/name/'audit.json');stability[name]={'passed_hard_checks':a['passed_hard_checks']}
        for s in ('train','test'):
            r=a[s];summary=brief(HERE/name/s)
            stability[name][s]={'sessions':r['counts']['sessions'],'unused_nodes':r['counts']['unused_nodes'],
                'six_axis_max_deviation':max(r['six_nonidentity_relative_deviation'].values()),
                'introduced_core':r['wardrobe']['introduced_core_target_coverage']['distinct'],
                'four_use_edge_fraction':r['soft_targets']['four_use_edge_fraction'],
                'conditional_single_fraction':r['wardrobe']['formal_single_eligible_single_fraction'],
                'axis_average_reuse':summary['axis_average_reuse'],'length_distinct_axes':summary['length_distinct_axes']}
    write(HERE/'comparison.json',comparison);write(HERE/'sampling_stability.json',stability)
    a=read(HERE/args.candidate/'audit.json')
    lines=['# 编辑链构建实验结果（2026-10-22）','',f'主候选：`{args.candidate}`。旧对照：v4 `rotated`。此报告是离线配置图与链条结果，尚未渲染视频。','',
           '## 规模与覆盖','',f"训练使用{a['train']['counts']['used_nodes']}个节点、12000条链；测试使用{a['test']['counts']['used_nodes']}个节点、2400条链。两边完整视频配置重合数为{a['canonical_train_test_overlap']}。",'',
           '训练实际用到的节点覆盖全部可用人物、发型、发色、服装来源组与搭配组、动作、镜头、拍摄点及239件核心服装。具体覆盖及频数见候选audit.json。',
           f"训练中真正通过服装编辑新换入的核心件为{a['train']['wardrobe']['introduced_core_target_coverage']['distinct']}/239。",'',
           '测试不要求全部取值覆盖，其实际覆盖如下：','', '| 属性 | 测试已覆盖 | 目录总数 |','|---|---:|---:|']
    names={**LABELS,'family':'服装来源组','group':'合法搭配组','core_asset':'核心服装单件'}
    for attr,r in a['test']['coverage_used_nodes'].items():
        if attr=='sex':continue
        lines.append(f"| {names.get(attr,attr)} | {r.get('distinct',r.get('actual','?'))} | {r.get('expected','?')} |")
    for split,label in [('train','训练集'),('test','测试集')]:
        c=comparison[split]['candidate'];old=comparison[split]['baseline'];r=a[split]
        lines+=['',f'## {label}编辑次数与边复用','', '| 编辑属性 | 次数 | 不同有向边 | 平均使用次数 | 旧版平均使用次数 |','|---|---:|---:|---:|---:|']
        for axis in AXES:lines.append(f"| {LABELS[axis]} | {c['axis_counts'][axis]} | {c['axis_unique_edges'][axis]} | {c['axis_average_reuse'][axis]:.3f} | {old['axis_average_reuse'][axis]:.3f} |")
        lines+=['',f"六类非身份编辑相对均值的最大偏差：{max(r['six_nonidentity_relative_deviation'].values()):.2%}；要求不超过10%。",
                f"边使用次数分布：{c['reuse_histogram']}。使用4次的边占比{r['soft_targets']['four_use_edge_fraction']:.2%}。",
                f"条件允许单件更换的服装编辑中，单件占{r['wardrobe']['formal_single_eligible_single_fraction']:.2%}；只允许整套更换的源已排除。"]
    lines+=['','## 一条链平均涉及多少种编辑属性','','| 编辑次数 | 旧训练 | 新训练 | 旧测试 | 新测试 |','|---|---:|---:|---:|---:|']
    for length in map(str,range(2,6)):
        vals=[comparison[s][v]['length_distinct_axes']['all'][length] for s,v in [('train','baseline'),('train','candidate'),('test','baseline'),('test','candidate')]]
        lines.append('| '+length+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    initial={}
    for split in ('train','test'):
        m=read(HERE/args.candidate/split/'metrics.json')
        counts=m['start_camera_counts'];front=sum(counts.get(c,0) for c in ('front_head','front_upper','dolly_in_front','dolly_out_front'))
        initial[split]={'counts':counts,'identity_eligible_fraction':front/m['sessions']}
    write(HERE/'initial_camera_distribution.json',initial)
    lines+=['','直链与分叉链分别统计见comparison.json及各候选audit.json。','',
            '## 尚需明确的取值分布范围','',
            '本轮硬性均衡指标针对六种编辑维度的次数，不等于每种衣服、人物、动作或镜头的出现次数均匀。',
            f"四个允许身份编辑的镜头合计占起始视频的比例：训练{initial['train']['identity_eligible_fraction']:.2%}、测试{initial['test']['identity_eligible_fraction']:.2%}。",
            '有限图的节点分布与初始人物平衡会影响该比例，不能把局部镜头权重1.5当成全目录镜头概率已经兑现。当前前向镜头较集中，详细频数保存在initial_camera_distribution.json；这是候选的分布局限，未宣称全属性取值均匀。',
            '测试仅覆盖8个人物、8个服装组等上述子集，且本候选的单件服装测试边只涉及上衣；因此不声称测试已评估全部衣服或全部部位的单件编辑。完整训练集有上衣、外套、裤子、连体服装的单件编辑。','',
            '## 稳定性与方法','',
            '在同一张最终图上使用三个不同采样种子；这验证采样稳定性，不代表完成了不同构图种子的稳定性验证。每次均保存完整链清单并独立核验。',
            '构图从合法编辑扩展节点：训练先构建多属性编辑块，再补齐核心单件与单件编辑出口；测试使用相同规则的较小图，不强求全值覆盖。',
            '采样保留既定长度、直链/分叉任务，使用六类终局配额约束、身份基础权重2和软目标、整段历史0.5^n衰减、低复用边优先。少量首步覆盖任务确保可引入的核心服装确实被换入，任务类型、长度、分叉时刻及历史来源不变。',
            '每类平均复用约2是降低重复的优化目标；低于2不通过额外重复样本强行补到2。服装条件单件约50:50，报告实际偏差，不声称恰好一半。','',
            '## 复现','',
            '在本目录运行：','', '```powershell',
            'C:/ProgramData/anaconda3/python.exe -B build_balanced.py --variant candidate_b',
            f'C:/ProgramData/anaconda3/python.exe -B run_sampling.py --graph candidate_b --output {args.candidate} --seed 2026102251',
            f'C:/ProgramData/anaconda3/python.exe -B audit_candidate.py --root {args.candidate}',
            '```','', '其余采样种子为2026102271、2026102291，测试在各自训练种子上加1。复现依赖版本和输入哈希见INPUTS_AND_METHODS.json。']
    (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(HERE/'CURRENT_CANDIDATE.json',{'candidate':args.candidate,'graph':'candidate_b','status':'offline_candidate_verified_not_rendered','audit':f'{args.candidate}/audit.json','baseline':str(baseline),'stability_runs':args.seeds})

if __name__=='__main__':main()
