# 数据集离线试构建：已确认规则

日期：2026-10-21。此文件记录用户本轮确认的规则，与同目录 `rules.json` 配套。适用范围为本次离线试构建；不调用 UE、不渲染主视频或参考媒体，不表示媒体已可用、视觉已验证或生产 Gate 已通过。

正式实现与状态所有者为 `technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md` 及项目状态文件。本运行根记录本轮规则与试构建证据，不回写两轮夜间研究快照。以下当前规则优先于旧研究报告中的建议；未冻结项见末节。

## 1. 主视频预算与划分

| split | 去重后的主视频节点 | 结构会话 |
| --- | ---: | ---: |
| train | 2,500 | 12,000 |
| test | 500 | 2,400 |

参考图片和参考 clip 独立统计，不占这 3,000 个主视频预算。会话重复使用已有节点，不额外增加视频预算。

train/test 只要求**完整 canonical 主视频节点不重合**。不按 scene、person、动作、服装、属性值或编辑类别留出，不再以本次划分主张未见场景／人物泛化。同 split 可复用同一节点、编辑边、属性值及场景。两个 split 中若完整 canonical state 相同，必须识别为同一节点并拒绝跨 split 重叠，不能只靠不同字符串 ID 避免碰撞。canonical state 必须包含实际决定主视频的全部状态；具体渲染规格尚未冻结，不以旧 10 秒／30 帧自动补齐。

## 2. 图构造与继承

先采样合法编辑，从源 state 扩展目标 state，再按完整 state 去重视频节点；不先撒随机完整节点再找链。每条边只修改一个语义轴，其余 state 完整继承**选中的 parent**。服装整套替换属于一次 wardrobe 语义编辑，可联动该轴内多个核心部件与合法鞋子。

历史时间顺序和源 parent 的历史出现位置必须分别保存。同一 canonical 节点可在一个会话内再次出现，不能把视频 ID 当作唯一历史位置。历史分叉时不从最新结果或弃支合并任何属性。

同轴连续修改、恢复先前值、回到先前完整 state 均允许自然发生，不要求至少两个编辑轴，不强制无环或状态不回访，不人为给这些现象新增比例。文本改写或参考载体变体不构成新结构会话。

## 3. 会话配额与分叉

`L` 为编辑次数，不包含初始视频；允许 2、3、4、5 次编辑。直链与分叉会话比例为 2:1。

| 类型 | L=2 | L=3 | L=4 | L=5 |
| --- | ---: | ---: | ---: | ---: |
| linear 长度比例 | 25% | 25% | 25% | 25% |
| fork 长度比例 | 10% | 20% | 35% | 35% |
| train linear 数量 | 2,000 | 2,000 | 2,000 | 2,000 |
| train fork 数量 | 400 | 800 | 1,400 | 1,400 |
| test linear 数量 | 400 | 400 | 400 | 400 |
| test fork 数量 | 80 | 160 | 280 | 280 |

linear 每轮选最新历史位置。fork 会话恰好一次选择非最新历史位置：先均匀选择分叉编辑轮次 `t ∈ {2,…,L}`，再在 `parent_index ∈ {0,…,t−2}` 中均匀选择；第 0 个历史位置为初始视频，第 t 次编辑前的最新位置为 t−1。其余轮次沿最新结果继续。允许最后一轮分叉，不要求分叉后还有一轮，也不固定根／中间源比例。均匀规则是条件在所选 L、t 上的采样规则，不要求有限样本每个小桶完全相等。

## 4. 初始状态与编辑轴采样

初始男／女各 50%；在各 sex 内均匀选择 identity。身份编辑只在相同性别身份之间进行。

初始 scene、action、hair、color 在合法候选中均匀选择；服装采用下一节的层级均匀规则。相机 `front_head`、`front_upper`、`dolly_in_front`、`dolly_out_front` 各权重 1.5，其余合法相机各权重 1。已保存的场景／动作／镜头组合排除始终生效。

编辑轴权重：identity=2；hair、color、wardrobe、action、camera、site 各=1。先根据当前源 state 计算合法且存在有效目标的轴，再在可选轴上按权重采样；无合法目标的轴不可选。目标必须实际改变该语义轴，不能生成 no-op 边。合法域内目标均匀；服装遵循专门的分层选择规则。

| 编辑轴 | 当前确认的限制 |
| --- | --- |
| identity | 同 sex；源相机仅允许 front_head、front_upper、dolly_in_front、dolly_out_front；其他 state 继承。身份可包含全身肤色与体型变化，参考仍为一张正面 face。 |
| action | 除 front_head 外均可选，仍须通过当前场景／动作／相机合法性规则。保持镜头规则，允许跟拍轨迹响应动作派生。 |
| hair | 所有相机均可选。Rugged 无发型服装从本次候选剔除。 |
| color | 七色为 original、black、gold、silver_white、red、blue、pink。任意不同颜色间均允许；original→gold 禁令已撤回。 |
| wardrobe | 按第 5 节执行。 |
| camera | 保持其余 state，并通过组合规则；轨迹可以依其规则和动作派生。 |
| site | 按第 6 节执行。 |

## 5. 服装初始采样与编辑

`family` 指服装来源系列，`group` 指该系列内合法搭配组。初始服装按 **family → 合法 group → core pieces → 合法 shoe** 逐层均匀选择；不得将所有搭配摊平后均匀抽样，导致组合多的系列获得额外概率。赤脚只有现行白名单允许时才进入合法 shoe 候选。

单件编辑只在当前 group 内：先均匀选一个存在合法替代值的核心 slot，再均匀选该 slot 的其他合法值，鞋保持不变。鞋不是独立编辑轴／slot；仅鞋变化不算服装编辑。

当前存在合法单件编辑时，single piece 与 whole outfit 各 50%；没有合法 single piece 时，whole outfit 为 100%。所有分支仍必须存在合法非 no-op 目标；若某分支无目标，不可生成非法目标或只换鞋来补数。

whole outfit 只从其他 family 中选择，再选目标 family 的合法 group／core options／shoe；不做同 family 跨 group 的整套编辑。目标鞋在合法 shoe 候选中随机，可含白名单赤脚。场景组合排除保留；无合法目标的 wardrobe 不可选。

| 当前相机范围 | 可用服装编辑 |
| --- | --- |
| front_head | 禁止服装编辑。 |
| upper：正、侧、背、斜前、斜后上半身 | single 仅可改可见上半身核心单件；禁止下装 single。允许 whole，但上半部分必须实际发生变化。 |
| 其余 full、dolly、orbit | 允许合法 core 单件或 whole。 |

upper 的 whole 仍更新**完整目标服装 state**（含未入镜的下半身和鞋），不只更新可见片段；参考也提供整套目标核心部件与鞋，见第 7 节。

## 6. 场景、相机与曝光

场景目标必须有 saved point，目标 scene/action/camera 组合必须合法，并遵守现用 source camera rule；scene 编辑保持其他语义轴。camera 编辑同样维持其余 state，并遵守现有合法域和已保存排除。

“保持镜头”指保持镜头规则，不承诺逐帧相同世界坐标轨迹。动作改变或规则应用后，允许派生对应相机轨迹。场景使用 map 中已保存的曝光继承设置，因此 scene 改变允许伴随该 map 的 lighting/exposure 变化，不另记成第二个编辑轴。

## 7. 参考媒体契约

参考按实际需求去重汇总，与 main 节点预算分开；此处定义需求，不表示参考文件已生成。

| 类型 | 已确认参考 |
| --- | --- |
| identity | 每 identity 一张正面 face。目标身份可改变全身肤色与体型；具体文本及实现方式仍未冻结。 |
| hair | 每 hair 随机选两个库内 carrier；每 carrier 拍 front/back，统一黑发，共 4 photos/hair。一次输入随机选同一 carrier 的 front/back 一对，不混配两个 carrier；载体选择不新增结构链。 |
| motion | 对实际需要的每个 action×camera 提供对应参考 clip，保持同镜头 rule、phase、speed、duration。carrier 暂未定，不自动沿用旧规范单机位示范或旧 50 段方案。 |
| scene | 每个所需场景／相机提供一张 empty background，匹配目标 camera initial frame，无人物；不做背景 clip。 |
| wardrobe single | garments only，无 body，保持衣物 3D 形状，neutral background；每 piece 拍 front/back，只输入目标单件 pair。 |
| wardrobe whole | 所有目标 core pieces 加目标 shoe 各自 front/back；赤脚无 shoe image，指令明确 barefoot。upper whole 仍给完整目标整套参考并更新完整 state。 |

服装图片不以人物试穿图替代；同件前后视图属于一组参考，不计算为新的编辑或结构会话。

## 8. 对旧夜间研究约束的替代关系

下表中的旧规则只是相应实验候选的局部条件，历史证据保留。此表不宣称旧研究结论全部无效；只界定本次试构建不得继续套用的约束。

| 旧候选／建议 | 本次替代规则 |
| --- | --- |
| train 12k／test 3k 会话，或旧 V1 640 节点／4k 直链 | train 2,500 节点／12k 会话；test 500 节点／2,400 会话。 |
| main_scene_holdout、16/5 场景、场景点或环境隔离；未见场景／类型主张 | 仅完整 canonical 主视频节点跨 split 不重合；scene/person 等不留出。 |
| root 40%／中间 60%，偏向根源或人为均衡历史源 | 先 t 均匀 2…L，再 parent 均匀 0…t−2。 |
| 分叉后必须继续至少一次；不允许末轮分叉；仅 3–5 次分叉 | 允许 terminal fork 与 L=2；fork 恰好一次；长度 10/20/35/35%。 |
| 至少两个编辑轴、禁止状态回访／循环，限制同属性修订 | 同轴连续修改、return/revisit 自然允许，无新增专项配额。 |
| 要求错误选最新源必须产生可辨差异、所有历史源结果互不等价 | 不增加这些强制筛选；按本次 t/parent 规则与合法原子编辑执行，诊断可统计但不私自改分布。 |
| 七轴小任务族／女 16 套男 5 裤的局部编辑域、方格或跨身份节点比例 | 读取当前合法候选，按本文件层级与权重采样；不冻结旧局部域或构造配额。 |
| 服装一轮只能改一件；整套和单件二选一待讨论 | wardrobe 为一个语义轴，按合法条件 single/whole 50/50 或 whole 100%，whole 只换其他 family。 |
| 同 family 跨 group 整套、鞋独立编辑、仅换鞋也算 edit | 本次均不采用；single 保鞋，whole 重选合法鞋。 |
| Rugged 保留但禁发型 | Rugged 无发型服装从本次候选剔除；不改源资产。 |
| 原色不能改金色 | 禁令撤回，七色任意异色可改。 |
| 所有参考必须独立于目标、或旧 mixed reference routes 及旧预算可直接复用 | 以第 7 节实际确认的各类参考契约为准，按本次实际图重新算需求。 |
| 精确背景 clip／规范动作单机位／旧 50 段压缩示范 | scene 单张 empty initial frame；motion 按实际 action×camera 对应 clip。 |
| 固定全局相机世界路径、动作变更仍逐帧保持相机绝对轨迹 | 保持镜头 rule，允许派生跟拍路径。 |
| 旧 production10 的 10 秒／30 帧或成本表候选规格 | resolution、fps、duration、aspect 均未冻结。 |
| 12 条会话／65 节点小样或两轮旧 graph/参考数量可直接提交渲染 | 本次独立离线构建，旧数量不能直接拼接；不启动渲染。 |

旧源入口：

- [第一轮讨论回顾](../dataset_design_exploration_20261021_v1/DISCUSSION_RECAP.md)
- [第二轮简报](../dataset_design_exploration_20261021_round2/MORNING_BRIEF.md)
- [第二轮衣柜域研究](../dataset_design_exploration_20261021_round2/wardrobe_domains/WARDROBE_DOMAINS.md)
- [第二轮参考研究](../dataset_design_exploration_20261021_round2/references/REFERENCE_ROUTES_ROUND2.md)

## 9. 未冻结项与验收边界

identity、hair、wardrobe、motion 等参考的具体生成实现、具体 text／指令模板尚未冻结；motion carrier 尚未定。resolution、fps、duration、aspect 尚未冻结。motion 的“同 duration”是相对目标 clip 的一致性要求，不是已冻结具体秒数。

试构建只能检查符号 state、父指针、单轴差异、合法候选、去重、划分、会话配额和参考需求清单。未渲染，不可写成“视觉 verified”；合法目录／结构检查也不能替代实际衣服可见性、穿模、动作、身份效果或 reference 质量验收。不因本轮试构建提升生产 Gate。
