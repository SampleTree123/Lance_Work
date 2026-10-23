# 四类新表情接入与无道具动作库扩充

> 文档 ID：`PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-40/WF-50`
> 最近核验：2026-10-09（R00–R05技术交付完成，用户自然度pending）

## 目标与执行顺序

用户已授权低风险清理以保障磁盘、扩充20–30条丰富类别的无道具动作，并完成五秒验证、入库与审查入口；来源优先`%ANIMATION_ROOT%`，不足时使用其他本机素材。基础完成后可以探索带道具动作，但它不是本计划完成的硬性条件。

用户追加优先要求：“在这之前，先把我们确定的新的表情替换掉之前的表情，容纳到刚才的审查关卡里”。因此先执行R00：将已接受的待机`idle`、带笑`smile`、不满`displeased`、低落`sad`四类五秒表情接入当前双人ModularReview关卡及面板。完成这一优先项后，才开始实际清理和动作扩充；不能把已有八段预览当作运行集成完成。

当前四类选择来源是前一Run的accepted_face_selection_v1.json，保留原用户反馈、八个代表asset/源窗及SHA。新发布独立版本并保留旧五类库与旧报告，不能覆盖旧接受历史或为来源变动改写历史SHA。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R00` | 四类原速五秒表情进入当前审查关卡 | `WF-50` | 当前男女面板只提供已接受四类及关闭选项；正确关卡/精确UE实例，五秒时序、眼口及代表身体组合正确；选择/关闭/配置保存恢复可用，旧来源与其他选择不丢失；新库/合同与实际适用动作明确，不凭替换标签算完成 | `completed` | N3/delivery_v1.json：数字验证、代表审看、smoke02、保存重载先读回及面板ready；human acceptance pending |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R01` | 低风险释放或确认足够工作空间 | `WF-50` | 先区分须保留内容、可重建/明确被替代材料及来源闭包，再执行获授权的低风险清理；记录路径、理由、前后空间及回执。已足够则不为清理数量删除；现用资产、证据和未知归属内容保持 | `completed` | M3/space_assessment_v1.json：131936124928字节约122.9GiB，足够下一批小规模工作；no_deletion，删除0 |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R02` | 盘点并筛选无道具丰富动作来源 | `WF-40/WF-50` | 优先本机动作分层目录与清单，登记精确来源/哈希、类别、时长、道具/交互依赖和选用理由；P0/P1名称本身不证明可用，P2/P3不自动混入基础无道具库 | `completed` | M3/final_accepted_candidates_v1.json、goal_source_space_evidence_v1.json：来源/SHA/语义及男女代表审看完成，用户连续自然度pending |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R03` | 20–30条无道具动作完成五秒技术验证 | `WF-40/WF-50` | 每条有可追溯源及明确五秒窗口/原速策略；导出导入、男女适用Skeleton、全身/头颈/脚部与源保护检查，区别实测和未覆盖范围；缺口如实记录，不以相似片段凑数或静止补帧伪装丰富动作 | `completed` | M3/ue_serial_runs/run_20261008T220450_af2fcc24/summary.json终态；final_inputs_v1/preparation_receipt_v1.json绑定入选原长/原速五秒与四表情矩阵；代表观察范围见Animation §9.8 |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R04` | 动作库发布并提供可用审查入口 | `WF-50` | 发布证据绑定的版本化动作清单，当前关卡/面板可切换、播放、停止和保存恢复；与新表情的兼容覆盖明确，未覆盖组合不默许加载；不把文件存在等同于审查通过 | `completed` | M3/runtime_delivery_v1.json绑定最终目录、smoke02、五秒SceneCapture/root实看/基线恢复及新面板21168 ready可见；用户自然度pending |
| `PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION/R05` | 完成必要验证和文档闭环 | `WF-40/WF-50` | 记录真实机器结果、agent代表观察与用户审查边界；最终实现稳定后执行必要回归、Catalog/Inventory与文档独立/跨层审计；无剩余必需执行项后归档 | `completed` | M3/tests/full_regression_host_v3_summary.json：932通过、371源码pin不变；Catalog/Inventory重建，归档终验见M3/documentation_final_audit_v2.json |

## 所有权与协作

- 四表情集成：[Runtime §3.19](../../../technical/unreal/CHARACTER_RUNTIME.md#319-四类五秒表情接入当前审查关卡)拥有N3和运行合同/面板证据。
- 动作扩充及磁盘检查：[Animation §9](../../../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#9-无道具动作库扩充)拥有M3；现成动作转移沿用[Motion Transfer](../../../technical/transfer/MOTION_TRANSFER.md)的来源/Skeleton规则。
- 当前落实：[WF-50](../../status/workflows/WF-50.md)；实际转移发生时再同步[WF-40](../../status/workflows/WF-40.md)。
- 两Run沿用`OUT-WF50-RUNTIME-ACCEPTANCE`，未作精确保留决定的产物按unclassified保护。
- root独占当前用户可见UE实例的写操作；后台UE保持，不因并行离线代码/文档工作擅自切换目标。节点/PID只是已核验会话快照，应用重启后重新核对。
- 用户已授权低风险清理，无需因泛化删除条款重复征求批准；必须先明确保留内容和可删除的具体对象，不扩大为未知来源或现用资产删除。

## 可选延伸与完成边界

带道具动作只在基础无道具库与必需交付完成后考虑，须单列道具/交互依赖和验证范围；没有完成可选项不阻塞本计划结项。身体动作、表情与面板机器交付均不能代替用户对所有组合的自然度/贴合接受。新增训练、渲染生产批次和其他未授权工作不在本计划内。

R00–R03已完成限定技术要求。R01确认空间足够且无删除，来源/保留闭包补见M3/goal_source_space_evidence_v1.json。R02/R03最终证据、语义限制及真实代表观察见[Animation §9.8](../../../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#98-最终筛选矩阵和目录构建现场交付待验)；034为站立到起跑，不虚称持续匀速跑。

R04最终交付已完成：runtime_delivery_v1.json（SHA 17ce830ca59be1dd8676f71ddff7e1b694dbedcd58c1e18fa0b2a2a66f7a9e44）及其18份引用绑定现场smoke02、真正五秒SceneCapture与root观察、基线恢复、新面板ready/可见/初始show及源保护。旧迟到Automation截图不作为五秒通过证据，失败和终态核对保留。R05采用修复后932回归和本次最终目录/文档审计，不再重跑完整测试。

## 证据与完成边界

机器总交付为M3/runtime_delivery_v1.json；来源及空间为goal_source_space_evidence_v1.json，导出闭包为export_delivery_v1.json，真实观察为final_accepted_candidates_v1.json及其引用；最终文档独立/跨层审计为documentation_final_audit_v2.json。runtime_delivery中的documentation_closure=pending保留当时事实，后续审计单独闭合。

## 未纳入与后续

用户连续自然度、所有40身份/全部衣发/所有组合逐帧贴合未代签；034只证明站立到起跑，不是持续五秒匀速跑循环。可选带道具动作deferred，未自动启动，也不阻碍既定技术计划完成。内部原型源不赋予发布或训练权。本计划归档后显式idle/current_plan_id=null，无下一项自动实施；旧证据与其他scope保持。
