"""Summarize measured offline candidates; never promotes them to render jobs."""
import json
from pathlib import Path
from build_trial import HERE,read,write

def main():
    names=['full_walk','full_squares','full_squares_camera_first','full_squares_uniform_nodes']
    comparison={name:read(HERE/name/'SUMMARY.json') for name in names}
    write(HERE/'comparison.json',comparison)
    selected='full_squares_uniform_nodes';m=comparison[selected];probe=read(HERE/'requested_sampling_probe/SUMMARY.json')
    v=read(HERE/f'verification_{selected}.json');refs=read(HERE/selected/'reference_summary.json')
    rows=[]
    for name in names:
        a,b=comparison[name]['train'],comparison[name]['test']
        rows.append(f'| {name} | {a["axis_percent"]["identity"]:.2f}% / {b["axis_percent"]["identity"]:.2f}% | {a["used_edges"]} / {b["used_edges"]} | {100*a["sessions_with_revisited_node"]/a["sessions"]:.1f}% / {100*b["sessions_with_revisited_node"]/b["sessions"]:.1f}% |')
    axes={'identity':'人物身份','hair':'发型','hair_color':'发色','wardrobe':'服装','action':'动作','camera':'镜头','site':'场景'}
    axisrows=[f'| {label} | {probe["axis_percent"][a]:.2f}% | {m["train"]["axis_percent"][a]:.2f}% | {m["test"]["axis_percent"][a]:.2f}% |' for a,label in axes.items()]
    usedrows=[]
    for split,label in [('train','训练'),('test','测试')]:
        r=m[split];usedrows.append(f'| {label} | {r["nodes"]} | {r["nodes"]-r["unused_nodes"]} | {r["sessions"]} | {r["edit_steps"]} | {r["used_edges"]} |')
    report='\n'.join([
    '# 第一轮节点与编辑链试构建', '',
    '**结论：规则已落地，目标数量的结构链可以生成；当前预算受限候选的分布还不适合冻结渲染。** 主要问题是先限制节点、后从已有邻边采样，迫使编辑反复返回少数状态，也使某些条件概率失真。不能把这个问题归因于用户允许重复编辑，更不能由本次算法失败证明3,000节点预算一定不够。','',
    '本轮只读当前资产与点位目录，没有调用UE、修改资产或渲染视频。训练和测试共享资产类别，仅完整主视频状态隔离。当前符号试算使用landscape以应用已存排除；画幅、时长、帧率、分辨率、表达式/动作相位/速度的最终媒体配置未冻结，不能直接提交正式渲染。','',
    '## 阅读顺序','',
    '1. [已确认规则](CONFIRMED_RULES.md)：本轮讨论的完整决定，覆盖夜间旧假设。',
    '2. [11个实际案例](ADVERSARIAL_CASES.md)：半身整套换装后转全身、单件保鞋、三类回溯、四种身份镜头等。',
    '3. [参考素材需求](full_squares_uniform_nodes/REFERENCES.md)：只对应当前诊断候选，后续构图变动后重算。',
    '4. [独立结构验证](verification_full_squares_uniform_nodes.json)：结构与服装合法性通过，不等于分布达标或视觉通过。','',
    '## 当前输入','',
    '当前正式目录：40个人物、37个服装来源组、45个合法搭配组、33个性别适配发型条目（28个unique hair ID）、7发色、25动作、21镜头、21用户点位。1428条保存排除同时包含横竖画幅，本次按横屏对应项过滤。Rugged已被正式入口移除；没有从旧目录恢复。4个锁定衣柜保留真实整套结构。来源路径/哈希见catalog.json，704组×发型采样及衣物变换检查见catalog_verification.json。','',
    '## 先检查不受节点预算限制的抽样','',
    f'另生成1,000条诊断链，前100条作为小规模样本（requested_sampling_probe/first_100_sessions.json）。每条链从独立随机初始状态开始，再严格按合法属性权重延伸，共使用{probe["nodes"]}个去重节点、{probe["edit_steps"]}步编辑。不是主数据，也不是节点预算下界，因为没有主动跨链共享上下文。','',
    f'身份编辑{probe["axis_percent"]["identity"]:.2f}%，有回访节点的链{100*probe["sessions_with_revisited_node"]/1000:.1f}%；与此前约7%的身份理论比例、自然随机下少量回访的预期相符。这里的1,000样本不是统计显著性证明，目标域与排除条件也会影响比例。','',
    '## 预算受限候选','',
    '比较自然扩展、两属性闭合扩展，以及不同起点采样方式。新节点均由实际合法编辑产生；闭合扩展会先生成两次合法变化，再补充可复用的交叉状态。已有节点间只在独立规则允许时登记边。候选都保留2:1直链/分叉和确认的长度配额，分叉轮次/父历史位置在重试前固定，未强行调整V0占比。','',
    '| 候选 | 身份比例：训练 / 测试 | 不同使用边：训练 / 测试 | 有节点回访的链：训练 / 测试 |','| --- | ---: | ---: | ---: |',*rows,'',
    '`full_squares_uniform_nodes`仅选作最便于诊断的代表：使用边更多、孤立未用节点较少、训练属性分布接近预期；它不是已接受的最终数据。uniform_nodes是图内起点均匀的实验，**不满足用户确认的男女及身份等层级均匀初始抽样**。层级抽样候选也保留，但其在稀疏图上会受可用支持集限制，不等价于全目录层级均匀。','',
    '| 集合 | 候选节点池 | 实际被链引用的节点 | 链数 | 编辑步骤 | 不同使用边 |','| --- | ---: | ---: | ---: | ---: | ---: |',*usedrows,'',
    '池内未引用节点不应渲染，不能把候选池数量当作全部有效训练视频数量。所有12,000/2,400条链均按历史父位置与目标状态判断结构唯一，没有用文本改写凑链数。','',
    '| 属性 | 不受预算限制的诊断链 | 代表候选训练 | 代表候选测试 |','| --- | ---: | ---: | ---: |',*axisrows,'',
    '## 发现的三个构造问题','',
    '1. **反复返回过多。** 代表候选训练8,394/12,000（69.95%）、测试1,628/2,400（67.83%）有相同节点再次出现，而独立抽样诊断仅4.3%。允许自然改回旧值没有问题，问题在于小图常只剩返回原路的选项。这一测量包含分叉产生的回访，不等同于所有都是无效训练样本。','',
    '2. **条件权重被可用邻边扭曲。** 训练有合法单件替换的5,098次服装编辑中，图中同时具有单件和整套目标的只有465次；另外2,631次只剩整套，2,002次只剩单件。即使总体单件比例看起来接近一半，也没有实现“每个有单件可换的源，以0.5选择方式”。人物起点男女也变成58.54%/41.46%。已允许编辑但缺少目标节点，不能在生产中悄悄解释成“该编辑不合法”。','',
    '3. **覆盖与分叉信息量不够。** 测试节点池只覆盖31/40身份、27/37服装来源组、23/25动作、20/21场景；不要求每个组合都出现，但这些缺口要先看。训练1,755/4,000、测试355/800个分叉，所选旧源与最新状态在本次编辑之外的保留属性没有区别，错误选源可能得到相同结果；这不违反已确认允许回访规则，但削弱历史选择的监督。','',
    '以上只是本次候选的诊断，不新增“禁止回访”“分叉必须改变最终结果”或“至少两个编辑属性”的硬规则。','',
    '## 参考素材和拍摄准备','',
    f'只对代表候选实际使用的边计算需求：{refs["unique_images"]}张去重参考图、{refs["unique_motion_clips"]}段动作参考视频，全部media_path为空。素材不占主视频节点预算，但要计入未来拍摄成本。','',
    '衣物每单件正背两图，无人体；整套给全部目标衣物与鞋，单件替换不提供鞋图；赤足只允许正式白名单且用文本标明。发型各两个随机适配载体、各正背两图，输入随机同一载体的一对。身份正面一图。场景为空背景初始帧，保留动作/镜头等实际取景依赖。动作按动作×镜头×性别适配版本列出需求，载体尚未确定。','',
    '## 本轮交付与下一轮建议','',
    '已经完成：规则文档和机器配置、当前目录快照、100条起步样本及1,000条独立抽样对照、四个目标规模候选、不同边与复用统计、11个完整规则案例、参考需求投影、独立结构合法性核验。未完成：满足全部确认分布的正式候选、媒体参数冻结、文本指代模板、真实参考拍摄与视频渲染。','',
    '下一轮优先改“节点和链联合构造”：以源状态所需的合法编辑机会为单位分配节点预算，预留单件/整套两类目标，控制覆盖后再复用已有完整编辑片段；每次复用要重新统计条件概率和回访率。先在现有预算下修构造方式，不立即要求扩大预算或削减链数；若仍达不到，再用实际边际收益讨论预算。用户确认规则保持不变。','',
    '推荐讨论的下一问题是：接受在相同视频预算下减少重复链，还是追加视频以增加真正不同的编辑内容；本次证据尚不能给出最低必需视频数。','',
    '## 复现与边界','',
    '所有脚本为experimental、由正式探索Technical拥有。命令在本目录执行：','',
    '```powershell',
    'python normalize_catalog.py --export',
    'python build_trial.py --scale smoke --policy squares',
    'python build_trial.py --scale full --policy walk',
    'python build_trial.py --scale full --policy squares',
    'python build_trial.py --scale full --policy squares --start-policy camera_first',
    'python build_trial.py --scale full --policy squares --start-policy uniform_nodes',
    'python probe_requested_sampling.py',
    'python verify_trial.py --candidate full_squares_uniform_nodes',
    'python plan_references.py --candidate full_squares_uniform_nodes',
    'python build_adversarial_cases.py',
    'python assemble_trial_report.py',
    '```','',
    '脚本使用当前只读正式contract，目录变化后必须更新catalog并重跑；本轮source pins与限定验证见delivery_verification.json。没有执行全仓审计、全库测试或媒体验收。历史两轮探索保留原样，不能将其旧500/3000、场景留出、固定服装域和参考数量混入本轮。',''])
    (HERE/'TRIAL_REPORT.md').write_text(report+'\n',encoding='utf-8')
    write(HERE/'trial_status.json',{'status':'offline_trial_delivered_distribution_revision_needed','rules_confirmed':True,'structural_integrity_passed':v['integrity_success'],
         'production_candidate_accepted':False,'render_started':False,'diagnostic_candidate':selected,
         'scope':'symbolic_landscape_one_pending_media_profile','budgets':{'train_nodes':2500,'test_nodes':500,'train_sessions':12000,'test_sessions':2400},
         'all_confirmed_sampling_rules_satisfied':False,'reference_images':refs['unique_images'],'reference_clips':refs['unique_motion_clips'],
         'next_action':'Revise joint node/session construction within the existing budget; do not render these candidates or change agreed sampling rules silently.'})
    print(HERE/'TRIAL_REPORT.md')
if __name__=='__main__':main()
