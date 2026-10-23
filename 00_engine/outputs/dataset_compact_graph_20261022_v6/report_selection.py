"""Build a readable report from independent saved-artifact audits."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
V5=ROOT.parent/'dataset_balanced_graph_20261022_v5'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pct(v):return f'{100*v:.2f}%'
def l5(r):
    return sum(r['per_length_kind_sequence_means'][k]['distinct_axes']*r['length_kind_counts'][k]
               for k in ('linear_5','fork_5'))/sum(r['length_kind_counts'][k] for k in ('linear_5','fork_5'))
def compact(r):
    return {'nodes':r['counts']['nodes'],'used_nodes':r['counts']['used_nodes'],
            'chains':r['counts']['sessions'],'edits':r['counts']['edit_steps'],
            'six_axis_max_deviation':max(r['six_nonidentity_relative_deviation'].values()),
            'four_use_fraction':r['soft_targets']['four_use_edge_fraction'],
            'single_fraction':r['wardrobe']['formal_single_eligible_single_fraction'],
            'l5_distinct_axes':l5(r),'overall_edge_reuse':r['edge_reuse']['mean'],
            'slot_tv':r.get('single_slot_diagnostic',{}).get('conditional_actual_vs_expected_total_variation'),
            'max_slot_deviation':max((abs(v['relative_deviation_when_expected_positive'] or 0)
                                     for v in r.get('single_slot_diagnostic',{}).get('slots',{}).values()),default=None),
            'passed_hard_checks':r['passed_hard_checks']}

def main():
    spec=read(ROOT/'FINAL_SELECTION.json')
    audits=[read(ROOT/x['audit']) for x in spec['sampling_seeds']]
    old=read(V5/'candidate_c_seed1/audit.json');first=audits[0]
    summary=[{'candidate':row['assembled_candidate'],'audit':row['audit'],
              'passed':a['passed_hard_checks'],'canonical_overlap':a['canonical_train_test_overlap'],
              **{s:compact(a[s]) for s in ('train','test')}} for row,a in zip(spec['sampling_seeds'],audits)]
    write(ROOT/'sampling_stability.json',summary)
    comparison={s:{'v5':compact(old[s]),'v6':compact(first[s])} for s in ('train','test')}
    write(ROOT/'comparison.json',comparison)
    t,e=first['train'],first['test'];ts,es=compact(t),compact(e)
    removed=old['train']['counts']['nodes']+old['test']['counts']['nodes']-ts['nodes']-es['nodes']
    lines=['# 第六轮结果：减少节点，修正起始镜头与单件服装分布','',
      '本页只总结离线节点、编辑边和链条清单；没有操作UE、渲染视频或训练模型。',
      f"当前推荐为 `{spec['sampling_seeds'][0]['assembled_candidate']}`。另外两组种子用于稳定性检查，不能合并成更多训练/测试样本。",'',
      f"训练从4670降到{ts['nodes']}个节点；测试为{es['nodes']}个节点。总计减少{removed}个待渲染主视频（{pct(removed/5438)}）。训练仍完整覆盖239件核心衣物及全部已确认属性值，且都实际成为过相应编辑的目标。",'',
      '## 主要结果','',
      '| 指标 | 训练 | 测试 |','|---|---:|---:|',
      f"| 唯一视频节点 | {ts['nodes']} | {es['nodes']} |",
      f"| 编辑链 / 编辑次数 | {ts['chains']} / {ts['edits']} | {es['chains']} / {es['edits']} |",
      f"| 六类非身份编辑的最大次数偏差 | {pct(ts['six_axis_max_deviation'])} | {pct(es['six_axis_max_deviation'])} |",
      f"| 有合法单件选择时，单件编辑占比 | {pct(ts['single_fraction'])} | {pct(es['single_fraction'])} |",
      f"| 单件部位相对条件期望的最大偏差 | {pct(ts['max_slot_deviation'])} | {pct(es['max_slot_deviation'])} |",
      f"| 5轮链平均修改的不同属性数 | {ts['l5_distinct_axes']:.3f} | {es['l5_distinct_axes']:.3f} |",
      f"| 平均有向编辑边复用次数 | {ts['overall_edge_reuse']:.3f} | {es['overall_edge_reuse']:.3f} |",
      f"| 使用4次的边占比 | {pct(ts['four_use_fraction'])} | {pct(es['four_use_fraction'])} |",'',
      '21种起始镜头按原先确认的权重执行整数配额：四种可进行身份编辑的镜头各1.5，其余各1。覆盖补偿同样占用这些配额，不再让某些镜头的缺额转移到其他镜头。',
      '单件服装的“平衡”按当前来源实际允许替换的部位计算；不会强行让五个部位各占20%，也没有放开上半身镜头中仅替换下装的非法编辑。','',
      '## 单件服装明细','',
      '| 部位 | 训练实际 / 条件期望 | 测试实际 / 条件期望 |','|---|---:|---:|']
    for slot,label in [('shirts','上衣'),('coats','外套'),('pants','裤子'),('skirts','裙子'),('full_body','连体服')]:
        vals=[]
        for r in (t,e):
            z=r['single_slot_diagnostic']['slots'][slot]
            vals.append(f"{z['actual_single_edit_count']} / {z['formal_conditional_expected_given_actual_single_events']:.1f}")
        lines.append(f"| {label} | {' | '.join(vals)} |")
    lines+=['','## 编辑次数与边复用','',
      '| 属性 | 训练编辑次数 | 训练不同边数 | 训练复用均值 | 测试编辑次数 | 测试不同边数 | 测试复用均值 |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for axis,label in [('identity','人物身份'),('hair','发型'),('hair_color','发色'),('wardrobe','服装'),('action','动作'),('camera','镜头'),('site','场景')]:
        parts=[]
        for r in (t,e):
            n=r['axis_counts'][axis];u=r['axis_unique_directed_edges'][axis]
            parts.extend([str(n),str(u),f'{n/u:.3f}'])
        lines.append(f"| {label} | {' | '.join(parts)} |")
    lines+=['','## 三个随机种子','',
      '| 种子组 | 硬要求 | 训练 / 测试5轮不同属性数 | 训练 / 测试4次边比例 |',
      '|---|---|---:|---:|']
    for i,s in enumerate(summary,1):
        lines.append(f"| {i} | {'全部通过' if s['passed'] else '未通过'} | {s['train']['l5_distinct_axes']:.3f} / {s['test']['l5_distinct_axes']:.3f} | {pct(s['train']['four_use_fraction'])} / {pct(s['test']['four_use_fraction'])} |")
    decay=spec['sampling_configuration']['history_decay']
    lines+=['','完整检查包括：合法单属性边、服装组合、历史源继承、最多一次分叉、精确链类型/长度配额、完整链去重、完整节点跨训练/测试隔离、实际目标覆盖、次数平衡与复用上限。三个种子复用同一份图及采样代码。','',
      '## 这次具体改变了什么','',
      '1. 用能连续修改多种属性的局部组合构图，替代过度稀疏的组合；把需要一起存在的上衣/裤子等合法替换组合补齐。',
      '2. 起始镜头使用精确配额。起点选择先排除编辑额度已经耗尽的节点，末段必要时扩大到该镜头全部仍有容量的节点，避免仅为均衡身份而卡住最后几条链。',
      '3. 覆盖补偿检查真正编辑进来的目标值。人物仅作为起始视频出现，不再冒充已经完成身份替换覆盖。',
      f'4. 本轮统一使用 {decay}^n 的链内重复属性衰减；n仍统计整段已有历史，包括被弃分支。重复编辑和自然回到旧值依然允许。',
      '5. 删除正面面部镜头下多余的完整配置上下文，同时保护覆盖节点及其合法来源。继续压缩到3664节点会显著提高四次边比例，已放弃。','',
      '## 取舍与下一步','',
      '测试节点上限800全部使用，比上一版768略多，换来21种起始镜头和五类单件服装都有实际支持。测试不要求全目录取值覆盖；它与训练按完整视频配置隔离，不是未见场景或人物的泛化测试。',
      f"上一版5轮链平均不同属性数为训练{l5(old['train']):.3f}、测试{l5(old['test']):.3f}。本版训练更丰富；测试在镜头覆盖、合法换装和800节点预算之间仍有取舍，具体数字见上表，不能宣称所有指标均优于上一版。",
      '“平均复用约2”仍是软目标；各轴存在差异，具体值已列出。小样本部位应同时看实际次数差，不能只看相对百分比。',
      '全取值覆盖不等于每个人物、发型或衣物被编辑的次数相等；本轮均衡目标是六类编辑次数、起始镜头和来源允许的单件部位。部分长尾取值仍只出现少量目标编辑，逐值计数保存在独立检查报告中。',
      '当前可进入渲染参数与参考素材清单的讨论。视频渲染及视觉检查尚未执行。','',
      '具体文件入口见CURRENT_CANDIDATE.json；方法与文件校验记录见INPUTS_AND_METHODS.json及DELIVERY_MANIFEST.json；未采用的试验见ITERATIONS.md。','']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
