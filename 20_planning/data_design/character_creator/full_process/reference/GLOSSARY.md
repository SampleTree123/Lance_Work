# 术语表

> 文档 ID：`REFERENCE-GLOSSARY`
> 文档类型：`reference`
> 生命周期：`current`
> 权威范围：项目核心术语、ID 和状态含义
> 最近核验：2026-08-25

| 术语 | 本项目含义 |
| --- | --- |
| Workflow (`WF-*`) | 长期、按顺序执行的阶段契约；定义输入、步骤、输出、验证和 Exit Gate，不保存滚动运行日志 |
| Technical | 某项能力的可复现实现权威；负责代码/命令、参数、恢复、验证实现和输出产生方式 |
| Validation (`VAL-*`) | 稳定验证契约；定义触发条件、最低证据、通过/失效语义和状态落点 |
| Output Contract (`OUT-*`) | 稳定逻辑输出契约；定义生产阶段、内容、存储类别、最低 Manifest 和晋升条件，不等于某次实际目录 |
| Run Root | 一次具体运行的独立根目录；包含运行 Manifest、attempt、媒体/数据、日志和状态，禁止覆盖另一次正式运行 |
| Technical Owner | 对某项实现、命令和输出产生方式负责的唯一 Technical 文档，不等于文件系统所有者 |
| Status | 当前已验证事实、证据、缺口和唯一下一 Gate；不保存未来愿望或完整历史日志 |
| Plan | 尚未完成的目标、需求状态和验收条件；完成后迁入 History，不代替当前状态 |
| ADR | 已接受、被取代或撤销的长期架构/语义决定；不记录普通运行进度 |
| BodyFit | 哈希锁定的完整身体源 `.ccProject`；不是几项 Morph 的简称 |
| Identity | 可追溯的面部身份状态及描述，不包含服装 |
| Face seed/recipe | 完整主原型加受控局部 Morph 的确定性身份配方 |
| Head profile | 低频头骨外形类别，不替代身份局部面部特征 |
| Appearance | 皮肤、眼球、眉毛、睫毛、牙齿和毛发等外观组件 |
| Outfit Family | 服装兼容边界；未授权时禁止跨 Family 单件混搭 |
| Look | 可直接渲染的身份、BodyFit、服装和外观组合 |
| FullReference | 角色及服装/毛发烘焙为完整 Skeletal Mesh 的导入形式 |
| Modular Pilot | 多组件 Leader Pose/Morph 的实验性角色，不自动等于生产能力 |
| Registry | 机器可读的资产、版本、策略和状态登记 |
| Manifest | 一次批次/运行冻结的具体输入、哈希和输出契约 |
| Vendor | UE 中原位保存外部导入资产的内容层 |
| DataMake | UE 中本项目自有 Blueprint、派生动画、Sequence 和配置层 |
| Node | 所有节点语义字段都确定的一条唯一可渲染视频状态 |
| Atomic Edge | 同兼容域内恰好改变一个允许编辑轴的有向边 |
| Compatibility Domain | 可通过合法原子边互达的一组节点；当前按性别分域 |
| Chain | 3–5 条连续原子边构成的多轮编辑路径 |
| Progressive Shortest | 每轴最多一次、无回退、长度等于语义差异数的链策略 |
| Freeform Walk | 允许重复轴、连续同轴、回退和闭环的链策略 |
| Render Job | 对一个唯一 Node 的渲染调度记录，不等同于 Chain |
| Sidecar | 与媒体绑定的节点配置、环境、规格、哈希和 QA 元数据 |
| Gate | 阶段退出条件；文件存在或退出码 0 不自动代表通过 |
| Workflow Status | 长期阶段的能力成熟度，不等于某批次完成度 |
| Batch Status | 某次冻结批次的资产、节点、媒体和发布进度 |
| Pilot | 在明确对象/边界内验证成功，不能自动推广到全库 |
| authoritative | 不可随意删除的机器真值或正式交付资产 |
| retained_evidence | 支撑当前结论、仍需保留的报告/图像/日志 |
| superseded | 已被新版本取代但暂留供审计的产物 |
| disposable | 可重建且无未解决故障依赖的临时产物 |
| passed | 当前输入、版本和环境下满足验证契约，且证据仍有效 |
| passed_with_accepted_risk | 已满足主要契约，但当前 Plan/Batch 明确接受了有范围的例外；必须记录例外和决定 |
| pending | 尚未获得足够证据，不能描述为通过 |
| failed | 已获得违反契约的证据，必须修复或由正式决定改变契约 |
| expired | 曾通过，但输入、版本、环境或会话变化使旧证据不再证明当前状态 |
| not_applicable | 条件验证在当前批次不适用；必须记录原因，不等于未执行 |
| current / queued / paused | Plan 生命周期：唯一当前主计划、已排队计划、暂时搁置计划 |
| completed / cancelled | Plan 生命周期：完成并迁入 History，或正式取消并保留关闭原因 |
| MRQ | Unreal Movie Render Queue |
| GT | 从确定性合成配置/引擎输出获得的 Ground Truth |

状态词的约束由其所有者维护：[Validation Catalog](../technical/validation/VALIDATION_CATALOG.md) 定义验证结果，[Plan 规则](../project_management/plans/README.md) 定义计划生命周期。本页只提供统一释义，不保存对象的当前取值。
