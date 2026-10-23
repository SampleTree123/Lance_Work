"""Assemble the round-two research entry point without touching graph snapshots."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib
import json
import experiments as ex

HERE=Path(__file__).resolve().parent
SOURCES=['stage1_metrics.json','stage2_motif_metrics.json','multiseed_a5_metrics.json','stage3_a7_metrics.json',
         'strict_a5_metrics.json','strict_a7_metrics.json','strict_multiseed_a7_metrics.json','budget_a5_metrics.json',
         'strict_budget_a7_metrics.json','strict_family_a7_metrics.json']
if (HERE/'bridge_metrics.json').is_file():SOURCES.append('bridge_metrics.json')
records=[]
for filename in SOURCES:
    d=ex.read(filename)
    for raw in d['records']:
        r={**raw,'source_file':filename,'experiment_settings':d['settings']}
        r['fulfilled_all_requirements']=r['sampling']['sampled_unique_sessions']==r['sampling']['requested'] and r['all_nodes_referenced']
        records.append(r)
main=ex.read('strict_family_a7_metrics.json')['records']
sampling=ex.read('sampling_study_metrics.json')
verification=ex.read('sampling_study_verification.json')
stable={}
for split in ('train','test'):
    stem=f'motif_a7_f5_n3000_s20261021_{split}_uq1_ab3'
    stable[split]={suffix:{'path':stem+'_'+suffix,'sha256':hashlib.sha256((HERE/(stem+'_'+suffix)).read_bytes()).hexdigest()}
                   for suffix in ('graph.json','sessions.jsonl','examples.json')}
status={
 'hybrid':'历史对照：边际严重偏斜；不作为新主候选',
 'balanced':'被motif取代：单值均衡有效，但单轴密集团/热点严重；一个seed未引用全部节点',
 'motif_a5':'有效结构对照：三seed全量；未加全历史选源唯一的版本保留等价源诊断',
 'motif_a7_strict_f1':'全历史源结果唯一的较宽身份任务候选；三seed通过，但测试pair覆盖受预算限制',
 'motif_a7_strict_f5':'稳定可取用的局部任务库候选；identity值对覆盖上限15.8%，不能宣称全面优于大组件或统计独立',
 'sampling_study':'共享有限候选池的标注重分配；新索引单独交付，不替换稳定15k',
 'smoke_n600':'下界诊断：100测试节点不能满足单根全值覆盖；hybrid旧函数预覆盖超预算报错；不计正式成功',
 'identity_context_expansion_5_10pct':'同预算追加候选：扩展跨身份context，不等于连接原媒体组件；分别报告注册/实际使用value pairs和context集中度',
}
summary={'kind':'catalog_constrained_synthetic_topology_NOT_UE_or_model_training','stable_candidate':stable,
 'stable_metrics':main,'route_status':status,'research_records':records,'sampling_study':sampling,
 'verification':verification,'main_note':'small families are a bounded local-task candidate, not an unconditional global optimum',
 'input_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('inventory_landscape.json','site_checkpoint.json','appearance_catalog.json')},
 'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('experiments.py','quality_kernel_round1.py','sampling_study.py')}}
if (HERE/'bridge_verification.json').exists():summary['bridge_verification']=ex.read('bridge_verification.json')
if (HERE/'bridge_context_analysis.json').exists():summary['bridge_context_analysis']=ex.read('bridge_context_analysis.json')
ex.write(HERE/'SUMMARY.json',summary)
ex.write(HERE/'ROUTE_STATUS.json',status)

def dist(d):return f"{d['mean']:.2f}/{d['p95']}/{d['max']}/{d['gini']:.3f}"
def pick(name,split='test',family=1,seed=20261021,budget=3000):
    return next(r for r in records if r['source_file']==name and r['split']==split and r['family_count_per_sex']==family and r['seed']==seed and r['total_node_budget']==budget)
def cv(r,a):return r['node_factor_balance'][a]['distribution_including_missing']['cv']

lines=['# 第二轮：图结构、内容预算与会话采样研究','',
'本轮直接挑战第一轮的数量结论：15k会话可行不等于节点内容均衡、身份替换范围充分、历史源可唯一判断，也不等于15k条都增加新的原子编辑。全部实验是现行catalog约束的离线合成拓扑，未启动UE、改资产、渲染或做模型训练。',
'', '## 稳定入口与范围', '',
'稳定候选采用 `motif_a7_f5_n3000_s20261021_{train,test}_uq1_ab3_*`，保留原四份图/会话快照；新采样结果单独以 `sampling_*_indices.json` 交付。它是局部任务范围有取舍的候选，不是最终冻结，也不是无条件最优图。', '',
'主候选仍为2500训练/500测试唯一视频状态、12k/3k唯一会话，包含全部根/中间/输出；场景16/5隔离，双方40人物、25动作、21镜头。固定landscape，7个可编辑轴为身份、动作、镜头、场景、发色、单slot服装、发型。8个state字段中的aspect固定，不算第8编辑轴。服装不把整套preset当单件：女性16件同slot全身服装，鞋固定；男性5条同slot裤子，其他衣服与鞋固定。', '',
'每条2–5轮，直链:fork=2:1；直链各长度25%，fork长度3/4/5按20/40/40。fork源根40%/中间版60%，恰好一次非最新父指针，其后至少一轮；所有state不重复，每条至少两轴。strict额外要求当前编辑结果在所有历史输入中仅一个源能得到，而非仅排除latest。', '',
'| 分区 | 唯一节点/session | 独特有向原子边（全部被引用） | node复用 mean/P95/max/Gini | edge复用 mean/P95/max/Gini |',
'|---|---:|---:|---|---|']
for r in main:
    lines.append(f"| {r['split']} | {r['unique_nodes']}/{r['sampling']['sampled_unique_sessions']} | {r['registered_directed_edges']} | {dist(r['node_reuse'])} | {dist(r['sampling']['used_directed_edge_reuse'])} |")
lines+=['', '## 1. 单值平衡不是图可用性：双轴方格是新的构造单位','',
'factor-balanced从已有端点做单轴编辑，按身份/场景/动作/镜头的缺额、生成轴缺额和已有邻居数选择新节点。相比第一轮hybrid，测试identity CV从1.383降到0.054，scene从0.652降到0.017；但257/500测试节点只有一种邻接轴，节点复用Gini升到0.288，且另一个seed出现15k已采出但训练节点未全部引用。奖励邻居数量会长出单轴密集团。', '',
'motif从已有锚点扩展两个不同轴构成2×2方格：A→B、A→C、B→D，共计最多3个新视频；相同state仍哈希合并，不随机采整套配置等待成图。按所有新端点的单值缺额和身份×场景、动作×镜头、场景×动作的新组合选择方格。它让新节点同时拥有两个编辑方向，避免只靠一条颜色边挂住。', '',
'| 路线（3000预算，测试500节点） | identity CV | site CV | 仅一种邻接轴节点 | node复用Gini | identity×site覆盖 | action×camera覆盖 |',
'|---|---:|---:|---:|---:|---:|---:|']
for name,label,f in [('stage1_metrics.json','hybrid',1),('stage1_metrics.json','balanced',1),('stage2_motif_metrics.json','motif',1),('stage2_motif_metrics.json','motif',5)]:
    rows=[r for r in records if r['source_file']==name and r['route']==label and r['split']=='test' and r['family_count_per_sex']==f]
    r=rows[0]
    lines.append(f"| {label}, 每sex {f} family | {cv(r,'identity'):.3f} | {cv(r,'site'):.3f} | {r['nodes_with_only_one_edit_axis']} | {r['node_reuse']['gini']:.3f} | {r['pair_coverage']['identity__site']['coverage']:.1%} | {r['pair_coverage']['action__camera']['coverage']:.1%} |")
lines+=['', 'motif五轴三个seed均得到完整12k/3k并引用全部节点。训练身份×场景与动作×镜头达到全部合法组合；测试仍只覆盖部分组合，不把单值全覆盖冒称组合全覆盖。原始balanced第一阶段parents=24，后续对照parents=16；详细参数均保存在各metrics.settings中，不把参数变化混为同一随机重复。', '',
'## 2. 小family的收益与无法忽略的代价','',
'每sex五个family各含4个身份；训练每family250节点、测试50节点，实际图为10个分量。它仍能容纳15k严格会话，故“两大图才有多轮容量”不成立。分量之间没有共享媒体节点，但共享场景、动作、服装与发型资产，不能宣称统计独立。场景编辑仍存在，并非每场景一张孤立图。', '',
'但分组把身份替换限制在四人内部。训练小family实际身份替换值对120/760=15.8%，恰好达到该分组的上限；两大组件为642/760=84.5%。测试分别82/760=10.8%与126/760=16.6%。这是任务范围的真实损失，增加会话不能补回未登记边。身份×场景边际均衡并不能发现它。', '',
'| 7轴strict布局 | train identity transition覆盖 | test identity transition覆盖 | test site transition覆盖 | test identity CV |',
'|---|---:|---:|---:|---:|']
for name,f in [('strict_a7_metrics.json',1),('strict_family_a7_metrics.json',5)]:
    tr=pick(name,'train',f);te=pick(name,'test',f)
    lines.append(f"| 每sex {f} family | {tr['axis_value_transition_coverage']['identity']['coverage']:.1%} | {te['axis_value_transition_coverage']['identity']['coverage']:.1%} | {te['axis_value_transition_coverage']['site']['coverage']:.1%} | {cv(te,'identity'):.3f} |")
lines+=['', '## 3. 全历史源唯一性比latest反事实更强','',
'即使没有重复state，且把本轮编辑作用于latest得不到GT，其他旧版本仍可能只在本轮要覆盖的轴上不同，编辑后与GT相同。原motif测试有112/1000个fork存在这种等价源，训练621/4000。它不是原子继承bug，而是无法仅凭结果唯一归因到某个历史occurrence。strict按“除编辑轴以外的完整state”比较全部历史，要求等价源集合恰为GT父指针。', '',
'五轴和七轴strict都在3000节点内达到完整15k、root40/nonroot60、零等价源歧义。七轴strict两大组件又以20261021/22/23三个seed通过；没有靠循环凑数。双轴方格方便构成交换顺序与选源诊断，但也会制造等价源；必须分别记录，不能因为方格漂亮而忽略这项歧义。', '',
'## 4. 更多视频买的是内容覆盖，不是15k容量门槛','',
'同一7轴strict规则、同一15k会话目标，只改变总视频预算，训练/测试按5:1分配：', '',
'| 总视频预算 | train/test节点 | test identity CV | test identity×site覆盖 | test action×camera覆盖 | 完整12k/3k且全节点引用 |',
'|---|---|---:|---:|---:|---|']
for n,name in [(2000,'strict_budget_a7_metrics.json'),(3000,'strict_a7_metrics.json'),(4000,'strict_budget_a7_metrics.json')]:
    tr=pick(name,'train',budget=n);te=pick(name,'test',budget=n)
    lines.append(f"| {n} | {tr['unique_nodes']}/{te['unique_nodes']} | {cv(te,'identity'):.3f} | {te['pair_coverage']['identity__site']['coverage']:.1%} | {te['pair_coverage']['action__camera']['coverage']:.1%} | 是 |")
lines+=['', '2000视频也可构成15k会话，不能据此直接下调用户预算：它的测试内容明显更少、更不均匀。3000不是已证明的最少节点数，也不是最优点。4000提升多因素组合覆盖，节点复用Gini却不保证单调变好。100测试节点的小试还暴露覆盖下界：同sex一根的单轴连通生长，为覆盖全部取值至少需两域合计148个五轴节点，七轴需200个左右；旧hybrid先覆盖再检查预算时直接超预算报错，这个小试不算成功。', '',
'服装/发型均衡按合法sex域计算：女性16服装、男性5服装，男女视频各一半时，全21服装的均匀分布本来就不可能。不能把混合后CV约0.62当作失败；metrics另给条件CV与按合法域期望计数的加权CV。', '',
'## 5. 固定图后重分配会话，比继续堆同类会话更有信息','',
'冻结稳定7轴小family图，共有9094训练与1466测试原子边。构建共享、按完整state序列及父指针去重的有限候选池：训练52550、测试12092条，来自原会话与两种proposal各两次。所有池内会话逐条通过strict。均匀策略仅指在该有限池的相同长度/根源分层内均匀抽取，不冒称整个合法会话空间均匀。', '',
'三个主策略保持完全一致的长度、2:1与root40/60：uniform候选会话；edge_uniform偏向曝光少的原子边；edge_content_joint在边均衡上增加未见root-final对和未见axis-parent顺序。另补joint_reserved_swap，保留两轴独立编辑交换顺序探针，不把同终点的不同过程自动当冗余删除。', '',
'| 分区/策略 | 12k或3k下独特edge | edge曝光Gini | 独特root-final对 | 交换顺序额外会话 |',
'|---|---:|---:|---:|---:|']
for rec in sampling['records']:
    s=next(s for s in rec['snapshots'] if s['session_budget_multiplier']==1)
    lines.append(f"| {rec['split']} / {rec['policy']} | {s['unique_atomic_edges_used']} | {s['edge_exposure_including_zeros']['gini']:.3f} | {s['unique_root_final_pairs']} | {s['commuting_order_excess']} |")
lines+=['', '只用一半标注量（6k/1.5k），edge均衡已覆盖全部9094/1466边；uniform仅8249/1425。倍增到24k/6k几乎不再增加原子边，主要增加组合与曝光。这里不推断训练收益或要求下调15k：相同原子边的不同上下文、父指针和编辑顺序仍有任务价值。', '',
'joint在原预算下可让12k/3k各自有12k/3k个不同端点对，但将交换顺序配对降到0。独立编辑A→B与B→A同终点，内容覆盖等价、过程任务不等价；这正是需要显式探针的原因。reserved策略在10%的L2直链中保留互换对：train100对/test25对；仍全边覆盖，独特端点对11880/2968。该10%只是有限敏感性，不擅自冻结数据配比。', '',
'建议将标注目标分开：先保证原子边覆盖与长尾曝光，再购买不同组合与历史结构；显式保留同终点的交换/反事实探针。node均衡、edge均衡、编辑轴均衡并非同一目标，metrics保留各轴曝光频次，不能从edge_uniform名称推断七种编辑任务都等量。', '',
'## 6. 配置可辨与媒体可辨仍有距离','',
'父任务独立观察性检查见 `../observability/semantic_visibility.json`。无发发色别名假设被否定：kernel已限制none只配original，没有无发颜色边或冗余别名。但稳定训练图有18条被使用的男性裤子边，其稀疏lower-body代理均不入镜，影响102会话；这只是构图代理警讯，不是像素层无效证明。原色发型边可能带来资产自带颜色耦合，身份边缺少高质量正面头部证据也不自动无效。', '',
'因此这里的strict是配置历史源唯一，不是视频像素证明。不能把全部发型或身份边一刀切删除，也不能把结构验证写成UE实机验收。真实服装/头发几何、原色语义、遮挡、阴影和曝光仍需要少量针对性媒体验证。', '',
'## 7. 状态、复算与有限验证','',
'`SUMMARY.json`为机器入口，包含稳定文件hash、全部矩阵、采样结果与输入hash；`ROUTE_STATUS.json`列出已取代、限定候选与诊断失败。原第一轮未覆盖，当前主图也未被新采样索引覆盖。稳定图和候选池只做相关检查，没有全库审计。', '',
f"`sampling_study_verification.json`逐条核验64642候选会话及四策略全部0.5×/1×/2×索引：哈希、真实排除、合法原子边、sex域、全历史源唯一、精确配额与计数重算通过。选中的同一池会话跨策略复用是比较设计，不算额外独立训练样本。", '',
'```powershell',
'python 00_engine/outputs/dataset_design_exploration_20261021_round2/graph/experiments.py --routes motif --axes 7 --families 5 --unique-source-result --axis-balance 3 --parents 16 --output replay_metrics.json',
'python 00_engine/outputs/dataset_design_exploration_20261021_round2/graph/sampling_study.py --add-reserved',
'python 00_engine/outputs/dataset_design_exploration_20261021_round2/graph/verify_sampling_study.py',
'python 00_engine/outputs/dataset_design_exploration_20261021_round2/graph/assemble_report.py',
'```', '',
'第一条默认不保存/覆盖图快照，只复算指标；主图输入完全来自本目录固定JSON，源pin在SUMMARY中。`sampling_study.py`完整运行会重建候选池与新索引，不改变稳定图；需要保留已审查采样索引时先复制本目录。预算/seed曲线是构造证据，不是最优化或训练有效性的证明。']
if (HERE/'bridge_metrics.json').is_file():
    bridge=ex.read('bridge_metrics.json')
    lines+=['','## 8. 真实跨family桥接（独立追加，不改稳定主图）','',
            '桥接预留总节点预算的5%/10%，先生成更小的十family底图，再用真实同sex identity编辑与另一编辑轴形成跨family方格；新增节点均计费，不通过改family标签制造连通或独立性。', '',
            '| 身份扩展比例/分区 | 节点/session | 实际组件数 | identity注册/实际使用值对 | identity CV | 混合身份组标签会话 |',
            '|---|---|---:|---|---:|---:|']
    for r in bridge['records']:
        v=r['axis_value_transition_coverage']['identity']
        lines.append(f"| {r['bridge_fraction']:.0%}/{r['split']} | {r['unique_nodes']}/{r['sampling']['sampled_unique_sessions']} | {len(r['graph_components'])} | {v['observed_value_pairs']}/760 注册，{v['used_value_pairs']}/760 使用 | {cv(r,'identity'):.3f} | {r['cross_family_sessions']} |")
    lines+=['', '四组都满足完整12k/3k、全节点引用、严格历史源唯一与原配额；`bridge_verification.json`额外核验四图/30k会话。5%训练注册760/760，但实际会话仅600/760=78.9%；10%实际647/760=85.1%。不能把注册全覆盖写成实际训练全覆盖。', '',
            '实际组件仍为10个：新视频把其他身份资产放进现有上下文，没有连到该身份原先那套完整视频state。混合身份组标签不等于媒体组件合并；这不是通过重命名得到的独立性，新增节点和真实原子边均有生成父指针。代码历史名称bridge保留，准确含义是跨身份上下文扩展。', '',
            '便宜身份覆盖存在集中代价。5%测试的25个新增视频只落在5个非identity完整上下文，分配7/6/6/3/3；10%的50个新视频落在9个上下文。5%训练已使用的600个identity值对中275个仅在一个上下文出现，10%为207/647。它是变宽的身份对集合，不是同等宽的上下文证据。完整分布在 `bridge_context_analysis.json`。', '',
            '其他任务也有机会成本：测试动作×镜头co-occurrence覆盖由稳定小family的30.1%变为5%扩展29.7%、10%扩展26.7%；实际使用camera transition覆盖由29.5%变为27.1%和25.2%。10%测试虽把identity使用覆盖提高到53.9%，并不全面支配5%或原图。训练/测试原子边覆盖也不再全为100%。', '',
            '结论是：小family的身份任务上限并非只能靠巨型连通图解决；少量真实上下文复制可在相同视频预算扩大换人任务。但若要求全部身份对实际进入训练，应另给identity value-pair使用配额，并增加上下文，而不是只增加注册边或相同上下文的曝光。本轮不追加冻结策略。', '',
            '追加复算：`python .../graph/bridge_families.py`、`python .../graph/analyze_bridge_contexts.py`、`python .../graph/verify_bridges.py`；此类命令写独立bridge文件，不改稳定主图。']
(HERE/'RESEARCH_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(HERE/'RESEARCH_REPORT.md')
