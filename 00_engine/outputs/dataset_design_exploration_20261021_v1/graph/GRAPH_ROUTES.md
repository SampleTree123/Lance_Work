# 离线配置图路线探索（2026-10-21）

## 结论与证据范围

**3000个唯一视频状态承载15k多轮session，在严格历史继承约束下离线可行。** 最终主候选是 `main_scene_holdout_*`：2500训练节点、500测试节点，分别12k/3k唯一session；训练16场景、测试另外5场景，双方使用全部40人物、25动作、21镜头。全部起点、中间和输出都计入节点预算。直链:一次分叉精确2:1；每条2–5轮；每个分叉后至少继续一轮。

这是**真实catalog约束的synthetic topology实验**，不是UE渲染结果、资产兼容全验、最终生产清单，也不是模型结构设计。六轴状态是 `(identity, action, camera, aspect, site, hair_color)` 的语义投影；完整生产配置还必须固定或登记服装、发型、表情、渲染档案、动作窗口、站位/曝光版本等。这里的 `simn_` 哈希只作模拟去重，不冒充完整生产 `node_id`。

主候选固定landscape，**没有靠改横竖画幅凑编辑数**。早期六轴比较把aspect作为探索轴，不表示用户已确认它是编辑任务。未见人物32/8是另一个敏感性，不是40人物都进入训练的方案；最终主候选为未见场景16/5，身份集合重叠，节点集合不重叠。具体哪16/5只是checkpoint顺序下的可复现候选，未冻结。

## 最终主候选

| 分区 | 节点/唯一session | 已登记/实际使用有向边 | 边覆盖 | node复用 mean/P95/max/Gini | 已用edge复用 mean/P95/max/Gini |
|---|---:|---:|---:|---|---|
| train | 2500 / 12000 | 11800 / 10104 | 85.6% | 22.720 / 30 / 45 / 0.095 | 4.434 / 10 / 23 / 0.360 |
| test | 500 / 3000 | 4166 / 2240 | 53.8% | 28.400 / 45 / 65 / 0.210 | 5.000 / 14 / 26 / 0.454 |

node复用按所有时间occurrence计算；严格主候选没有重复state，所以也等于该节点进入不同session的次数。edge主表仅统计实际使用边；含零边的均值/P95/max/Gini另在JSON。Gini越高表示越集中，不能拿节点复用均值单独评优，因为该均值主要由预算和长度配额决定。

精确长度配额如下。直链在2/3/4/5轮各25%；分叉只在3/4/5轮按20/40/40分配。

| 分区 | 直链L2/L3/L4/L5 | 分叉L3/L4/L5 | 总L2/L3/L4/L5 | 编辑总数 | occurrence总数 |
|---|---|---|---|---:|---:|
| train | 2000/2000/2000/2000 | 800/1600/1600 | 2000/2800/3600/3600 | 44800 | 56800 |
| test | 500/500/500/500 | 200/400/400 | 500/700/900/900 | 11200 | 14200 |

主候选质量约束逐条成立：

- 100% session的所有输出state互异，比“至少90%不重复”更严格；没有即时反向或颜色来回构成的闭环。
- 每条至少涉及两个编辑轴；纯单轴轨道不进入主样。
- 分叉恰好一次选择非最新历史occurrence，完整继承该源；其余轮接最新。每轮保存 `parent_occurrence_indices_gt`。
- 分叉源state在当前历史中唯一，且与最新版本不同。
- 旧源与最新版本至少有一个**本轮不编辑的属性**仍不同，因此把同一编辑施于latest无法得到target；“红衣旧版/蓝衣新版，改成绿衣”这类覆盖全部源差异的伪选源被拒绝。
- 人物替换限同sex兼容域。训练两个分量各1250节点，测试各250节点；不要求男女域人为连通。
- 全部2500/500节点均进入交付session；对应分区全部40人物、25动作、21镜头和16/5场景均被引用。

## 三条路线：先区分数量与质量

以下是修复兼容域边后、seed=20261021的**capacity-only基线**，每路线都完成2500/500节点和12k/3k唯一session。此处用人物32/8拆分，fork长度3/4/5等分，不等同主候选20/40/40；允许state回访。

| 路线/分区 | 登记有向边 | node复用 mean/P95/max/Gini | edge复用 mean/P95/max/Gini | 重复state session占比 |
|---|---:|---|---|---:|
| chain_first / train | 6472 | 22.400 / 29 / 51 / 0.075 | 6.798 / 11 / 25 / 0.226 | 85.9% |
| chain_first / test | 1290 | 27.998 / 38 / 55 / 0.074 | 8.526 / 13 / 29 / 0.225 | 85.5% |
| dense_neighborhoods / train | 10992 | 22.400 / 32 / 66 / 0.093 | 4.003 / 9 / 26 / 0.314 | 71.0% |
| dense_neighborhoods / test | 2172 | 27.998 / 40 / 55 / 0.084 | 5.064 / 11 / 31 / 0.289 | 71.1% |
| hybrid / train | 7966 | 22.400 / 31 / 59 / 0.089 | 5.523 / 10 / 26 / 0.293 | 79.8% |
| hybrid / test | 1494 | 27.998 / 41 / 71 / 0.100 | 7.362 / 13 / 28 / 0.275 | 80.0% |

`chain_first` 每次从已有端点继续编辑扩展，偏向最新端点形成稀疏骨架；`dense_neighborhoods` 从已有状态建立每轴少量取值的局部邻域，72节点左右换附着点；`hybrid` 先用约60%预算长骨架，再用余量补局部邻域。所有路线都先由编辑产生端点，不会随机采完整配置后碰运气等待相邻状态。

各节点选好后，通过“除一个轴外相同”的索引登记已有节点间所有合法有向边；相同语义状态用规范化哈希合并，反向边单独计数。这不是要求再渲染笛卡尔积。

dense边更多，但测试只覆盖14/25动作、16/21镜头和14/21场景；chain与hybrid覆盖较广，却有大量重复状态session。故三种路线均不能只凭“15k采出来了”直接进入生产。最终hybrid增加按轴取值的逐边覆盖骨架、无回访和反事实选源约束，才形成上面的主候选。

主候选登记边11800/4166，实际用了10104/2240；有些合法边不适合无回访、至少两轴等session约束，所以不强求100%边覆盖。

## 仍未收敛的两个偏差

**历史源偏根版本。** 主候选训练4000个fork有3358个选择根（84.0%），测试1000个有861个选根（86.1%）。它证明能回历史，但大多是撤回到初始版，对“选择一个中间版本”的覆盖不足。

已额外做 `sourcebalanced_scene_*` 敏感性，不改主候选四个已审查文件。保持同一节点图、精确长度、无重复state、至少两轴和反事实可辨，让fork根源40%、中间源60%，仍得到完整12k/3k和全节点覆盖：训练1600根+2400中间，测试400根+600中间。训练中间源occ1/occ2分别2100/300，测试524/76。节点复用Gini变为0.118/0.240；主候选为0.095/0.210。它支持历史能力配额可行，但不自动取代主候选，也不代表所有历史距离已均衡。

纯低频优先采样曾停在2983测试session：剩余17条是直链，不是fork预算不足。增加25%随机起点探索和20%随机邻接探索后填满，同时保留结构质量检查。这是采样器搜索偏差，不是不可满足的容量下界。主候选两轮异轴直链另用合法路径精确枚举无放回抽样，训练/测试可选33582/9020条，避免将拒绝采样超时误报为容量不足。

**覆盖不等于均衡。** 下表是唯一节点分配，不是session条数：

| 分区 | 轴 | 值数 | 最少/最多唯一节点 | 最多值占分区节点 |
|---|---|---:|---:|---:|
| train | identity | 40 | 12 / 177 | 7.1% |
| train | action | 25 | 45 / 326 | 13.0% |
| train | camera | 21 | 41 / 301 | 12.0% |
| train | site | 16 | 15 / 502 | 20.1% |
| train | hair_color | 7 | 283 / 652 | 26.1% |
| test | identity | 40 | 1 / 83 | 16.6% |
| test | action | 25 | 2 / 96 | 19.2% |
| test | camera | 21 | 2 / 136 | 27.2% |
| test | site | 5 | 33 / 223 | 44.6% |
| test | hair_color | 7 | 24 / 219 | 43.8% |

测试有身份仅1个视频，也有身份83个；一个场景占223/500节点。复用采样只能均衡已有节点，不能弥补某身份或场景本来就视频不足。下一步应把图生长目标从“每值至少一次”改为每值的最少节点数/最大占比与交互覆盖缺口；按site、identity、motion、camera的缺额选合法编辑，而不只追求节点引用次数接近。测试报告还应按场景分别列出并做场景宏平均。这里没有擅自冻结均衡阈值。

## 历史父指针与同state回访

一条k轮session始终按时间记录k+1个occurrence。例父指针 `[null,0,1,1,3]`：先o0→o1→o2，第3轮回到o1形成o3，再从o3得到o4。o2仍是已显示过的弃支结果，仍计视频预算和历史；绝不能把它从时间序列删除，或把分叉错误改成o2→o3。

在诊断基线中若state A出现为o0、o2，二者复用同一个node/video，但它们是两个历史位置。以后选择o0或o2的相同state，继承出来的配置完全一样；只保存node_id无法判定哪个occurrence是GT。主候选通过state不回访消除此类别名。若未来加入专门闭环轨道，必须明确版本索引指代或接受等价GT，不能假装有唯一视觉源答案。`*_examples.json` 保留基线闭环与主候选fork代表样例。

“分叉后至少继续一轮”使两轮fork不可能：最早第2轮才有非最新历史源，继续一轮至少需第3轮。允许末轮fork会少验证一次分叉状态的后续继承；这里选择严格版本。等分3/4/5的旧质量实验只作长度敏感性，不冒称20/40/40。

## 真实约束与单件衣服扩展

清单来自真实40人导入delivery、正式26动作契约移除CAND007后的25动作双sex变体、现行21镜头ID、checkpoint已选21点和7发色。未把历史53点全部纳入，也未把旧静态catalog中的29/30动作当现行输入。全部源路径和SHA在 `topology_inventory*.json`。

节点有效性按checkpoint保存排除 `(site,action,camera,aspect)` 过滤，现用1428项排除得到尊重；它不表示其余组合经过UE实机验收。场景选点/曝光仅作输入版本，不触碰UE或资产。

8轴扩展额外使用父任务只读导出的 `appearance_catalog.json`：女性streetwear/full_body选16件同槽服装，鞋F001和其他项固定；男性1920s/separates选5条裤子，衬衫、外套、鞋固定。**整套preset替换不自动当单件编辑。** 发型按真实sex目录，染色只在有发型时合法；无发型只允许original，避免无视觉变化的颜色状态。选定服装域允许发型，禁止发型的服装不靠暗中清空hair/color接边。

该扩展三个路线均完成原预算，训练有向边为5916/8316/6852，测试1126/1668/1306；是单slot兼容结构的可行性，不代表152个整套preset、全服装家族、全部发型/人物的几何兼容均已验证。

## 可复现与文件入口

PowerShell在仓库根执行：

```powershell
python 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/export_topology_inventory.py
python 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/export_topology_inventory.py --fixed-landscape
python 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/explore_graph_routes.py --inventory 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/topology_inventory_landscape.json --quality --routes hybrid --split-policy scene --fork-length-policy 20_40_40 --artifact-tag replay_scene_holdout_ --output 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/replay_scene_holdout_metrics.json
python 00_engine/outputs/dataset_design_exploration_20261021_v1/graph/verify_artifacts.py
```

默认seed=20261021。加 `--source-balanced --artifact-tag replay_sourcebalanced_` 复现40/60历史源敏感性。默认不带quality、用topology_inventory.json可复现三路线capacity基线；加 `--appearance ../inventory/appearance_catalog.json` 时须使用实际完整相对路径。

最终图/链：`main_scene_holdout_hybrid_{train,test}_graph.json` 和 `_sessions.jsonl`；代表样例 `_examples.json`。图有完整六轴state和生成父节点，session以该图的node index引用，GT父指针引用时间occurrence index；session ID由完整有序模拟node哈希与父指针生成。唯一直链walk容量由有限图DP精确计算（允许回访），fork只报告实采唯一session下界，不声称穷尽容量。

定向落盘验证通过 **16 graphs / 120000 sessions**，包含3路线、单slot扩展、main和sourcebalanced；检查哈希、排除、原子边、同sex兼容、源继承、精确配额、无跨split节点以及主候选质量。父任务独立复验见 `../splits/INDEPENDENT_GRAPH_REVIEW.md`。没有运行全库测试，没有启动UE、改资产、渲染或更新全局Status/Plan/Catalog。

早期三seed实验发现诱导identity边跨sex的缺口，已修复并重跑最终一seed。旧文件保留且在 `EXPERIMENT_STATUS.json` 明确SUPERSEDED；它们不得和修复后指标混用。当前一seed证明构造可行，不证明跨seed稳健性；覆盖均衡和全资产渲染验收仍是下一阶段。
