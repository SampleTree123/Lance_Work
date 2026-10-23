# 有限局部目标图：构造子任务结果

2026-10-21。仅离线读取现用目录与正式衣柜规则；没有调用UE、修改资产、渲染或修改正式文档。

最新交给主任务重采样的是 `camera_balanced/train` 与 `camera_balanced/test`，它保留密集块与身份预算，修正下述 `dense_diverse` 强制所有初始根为身份镜头的问题。训练2,500／测试500节点，有向边16,962／1,812；初始40根中四类身份镜头合计10根（25%，权重1.5对应理论组质量6/23≈26.1%），并覆盖全部21镜头。完整节点中四类镜头占29.48%／28.80%。身份桥仅从实际位于允许镜头的源产生，非允许镜头根不被强制改镜头。每身份仍训练62或63节点、测试12或13节点。

最新候选独立语义检查通过、训练测试完整节点重合0、无孤点。训练覆盖全部目录；测试覆盖40身份、37服装来源组、28发型、7发色、25动作、21镜头、20点位，缺 `site_98aac485de`。按主任务要求限定单次镜头修正，没有为名字覆盖继续搜索参数。正式single可用源同时支持single／whole为训练1,330/1,752、测试114/325，仍需披露模式缺口。最终抽样由主任务负责。

此前交接的 `dense_diverse` 训练2,500节点、测试500节点，分别15,940／1,848条有向合法边；两组全目录覆盖、无孤点，独立验证通过。但它的初始根全位于身份镜头，继承后导致源镜头分布偏斜，因此作为历史对照保留。

## 构造方式

为40身份分别生成不同上下文的初始根；初始根以外的每个节点都从已有源沿一条合法单属性边产生。身份编辑只在正式允许的四镜头中、同sex克隆完整源上下文，身份抽样权重2不再被误用为“优先多建身份维度”。每身份节点预算固定，避免仅少数身份拥有大量可编辑上下文。

训练每身份先建三个属性可交叉组合的有限块，再用完整的两属性三值块补足余量；少于8个节点的尾部才逐边补齐。普通块以三值为主，早期方案另有部分四值块。服装块以不同family的真实whole和同family/group的真实single构成，不把鞋或附件变化当单件服装编辑。尾部发现正式single可用时优先补图里缺失的single／whole模式。`Graph.add`为相同端点自动连接全部合法单属性边。

所有节点保留完整衣物、鞋和不可见状态；相机／动作／点位使用现用排除表。未新增全局禁令或回访限制。同轴连续、完整状态回访、末轮分叉自然保留。所有候选仍用临时landscape标签，媒体画幅／时长／fps未冻结。

## 实测与局限

下表是同一个v1邻边诊断抽样器的结果，均完成12,000／2,400条结构不重复会话，长度／直链／分叉配额完成；这是诊断对照，主任务另行均衡采样。

| 候选 | 训练边数／回访链 | 测试边数／回访链 | 说明 |
|---|---:|---:|---|
| candidate | 21,036／41.68% | 4,502／37.08% | 两个主要上下文扩展，身份编辑机会集中；均衡身份起点后暴露严重偏差 |
| wardrobe_spines | 21,994／40.14% | 4,528／39.58% | 早期服装维度优先对照，同样未解决身份上下文集中 |
| diverse | 12,878／56.26% | 1,772／69.00% | 40身份均分；尾部单边节点过多 |
| dense_diverse | 15,940／47.96% | 1,848／68.13% | 最后一次实质改进；训练可交叉边增加，测试预算仍紧 |

`dense_diverse`正式允许single的训练1,611节点中，1,189同时有single和whole，396缺single、415缺whole；测试274节点中92同时有两种模式，150缺single、153缺whole。两类缺口会交叠。没有将这些图内缺口伪称正式不合法；主任务需在最终抽样报告里继续披露。节点名字全覆盖也不代表每个源的全目录条件均匀。测试回访仍高，不能把该方案描述为已消除回访偏差。

初步会话校验包含节点衣柜／头发正式兼容、合法单边、完整父状态继承、历史位置、分叉恰好一次、结构去重、配额与预算；只检查离线语义，不代表媒体／视觉验证。

## 可调用入口

- `build_blocks.load_graph(path, domain=None) -> Graph`：从保存节点重建可直接重采样的图。
- `build_diverse.grow_diverse(domain, budget, seed, forbidden=None, dense=True) -> (Graph, metadata)`：最终构造；`forbidden`传训练图canonical keys可隔离测试节点。
- 最新镜头均衡构造追加 `camera_balanced=True`；命令 `python 00_engine/outputs/dataset_local_support_20261021_v3/blocks/build_diverse.py --camera-balanced`。
- `build_blocks.grow_blocks(domain, budget, seed, forbidden=None, wardrobe_spine=False)`：早期局部块对照。
- `build_blocks.support_diagnostics(graph)`：目录覆盖、孤点、正式轴缺边、服装模式支持诊断。
- 重现最终候选：`python 00_engine/outputs/dataset_local_support_20261021_v3/blocks/build_diverse.py --dense`。
- 独立限定验证：`python 00_engine/outputs/dataset_local_support_20261021_v3/blocks/verify_blocks.py dense_diverse`。

节点、边、初步会话、构造块、provenance及支持缺口均在各split的 `nodes.json`、`edges.json`、`sessions.jsonl`、`metrics.json`。`dense_diverse/independent_validation.json`记录独立检查。保存的图已固定交接；主任务重采样产物需另存，避免将这里的初步会话当成最终方案。
