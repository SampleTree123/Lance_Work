# Character Factory 里程碑日志

> 文档角色：`append_only_milestone_log`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：只追加的已完成事件和证据索引
> 上级入口：[`README.md`](./README.md)
> 上游：已完成并验收的工作
> 下游：Current Status、ADR 和不可变快照
> 最近核验：2026-08-22
> 建立日期：2026-08-06

本文件只追加已经发生且有证据的事件。当前能力以 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md) 为准，未来工作以 [`../planning/ROADMAP.md`](../planning/ROADMAP.md) 为准。修正旧条目时追加一条更正，不静默改写历史。

## 2026-07-24：八个 BodyFit 冻结

- 男女各四个 Lean/Average/Athletic/Heavy 源项目完成。
- 采用源 `.ccProject` 加 hash 锁定，不再用少量宏 Morph 猜测重建。
- Head Scale 与 Neck Height 后续经过独立视觉矩阵校准。

## 2026-07-25：眼球与眉毛资产池

- 12 套眼球确认以 `Material Only` 使用，避免替换眼球几何和眼骨支撑。
- 眉毛候选完成性别/兼容登记。
- 眼球中性、闭眼和视线检查成为硬门禁。

## 2026-07-26：睫毛、皮肤与年龄验证

- 9 套 HD Natural 睫毛纳入成人候选池并完成动态检查。
- 青年皮肤按性别和色素档案筛选。
- `Full Face Elder` 的 0/0.5/1 三档被接受为可选面部年龄变体。
- Undo 与 Replace/Material Only 弹窗被纳入自动化停止条件。

## 2026-07-27：胡须、头发与 Face V3

- 5 套男性胡须验证完成。
- 头发目录完成性别呈现分数、风险和兼容登记，当前池 58 套。
- Face V3 固化为完整主 seed + Facial Profile + 安全局部 Morph；不再清零未知面部参数。
- 当前配置形成 20 seed、17 个生产主原型和 200 条配方；配方实际使用动态筛选后的 28 个安全局部 Morph。

## 2026-07-28 至 2026-07-31：完整装配与流程收口

- 角色 registry 固化身体、脸、皮肤、年龄、眼眉睫、牙齿、毛发、色素和 QA 顺序。
- 完整角色装配、截图、项目保存和人工联系表在代表批次上通过。
- 决定每个角色准备三套已适配发型，胡须至少支持有/无；服装按 BodyFit × Look 管理。

## 2026-08-02 至 2026-08-03：短体型与十体型展示

- 新增 `M05_Short_Average` 与 `F05_Short_Average`，成人 BodyFit 增至 10 个。
- 当前身高为 M05 159.89 cm、F05 152.53 cm。
- 10 个完整展示角色由用户人工验收；机器 JSON 的视觉状态仍有同步债务。

## 2026-08-04：CC→UE 与动画阶段 1–3

- M02 FBX/JSON 通过 Reallusion Auto Setup 2.03 导入 UE 5.8。
- 完整角色拆为 20 个 Skeletal Mesh Component，19 个 follower 使用 Body Leader Pose。
- 建立两条 Body-only 动作和可复用面部片段。
- v003 使用 `cc_base_facialbone` 分层，排除 head/neck；Rig Logic 曲线拥有眼球最终姿态。
- `2 body × 5 face` 共 10/10 通过。
- Elder Morph 快照后备路线通过 0/0.5/1、Blink、Smile 和 Jaw Open Pilot。

## 2026-08-05：质量基准与材质阶段 5A

- Aaron 与 M02 完成同条件几何、外观和动态比较。
- 主要差距定位在身份原型质量、眼部/泪线、皮肤响应和次级结构，而非单一全局材质参数。
- `cc_face_material_quality_v1` 通过四套完整角色和多灯光回归，进入 `production_approved`。
- 下一阶段改为 Headshot 离线 4 人 smoke，再决定 10/20 原型规模。

## 2026-08-06：文档体系重组

- 六份旧入口按原字节复制到 `history/legacy_2026-08-06` 并记录 SHA-256。
- 建立 `full_process` 总入口、CC/Bridge/传输/UE/验证技术层、Roadmap、Backlog、ADR、参考索引和里程碑日志。
- 旧路径改为兼容入口，不再承担并行权威职责。
- 本次只修改 Markdown 和链接，不修改 Python、JSON 或 Unreal 资产。
- 收口校验覆盖 50 份当前入口文档、6 个归档哈希、16 项机器配置事实和 8 个关键本地路径；结果为 0 断链、0 锚点错误、0 哈希差异。

## 2026-08-06：文档可执行性修订

- Master 第 3 节新增按十个目录划分的完整索引，覆盖 `full_process` 当前与历史共 46 份 Markdown。
- Validation 从抽象能力矩阵扩展为具体执行 Runbook，登记 CC Bridge、BodyFit、完整角色、M02 v002 Morph 广播、v003 动画矩阵和 Elder Morph 的真实代码、命令、输入输出与通过字段。
- 明确区分 UE Python Remote Execution 与 Unreal MCP；计划能力统一标记为“无可执行入口”。
- 披露 `ue_validate_m02_modular_blueprint.py` 仍指向 v001，以及两个 UE Pilot wrapper 固定输出目录的技术债务。
- 实际执行纯 Python 回归：CC 脚本 154 项、Bridge 客户端 1 项全部通过；39 份当前文档共检查 265 个本地链接/锚点，错误为 0；六份不可变归档哈希保持不变。

## 2026-08-06：生命周期文档树与自动审计

- 建立 `WF-00` 至 `WF-09` 的零起点生命周期主线，从会话预检、CC 角色定义与装配，一直延伸到 UE 场景、渲染和数据集封装；未实现的后两阶段明确标记为 `planned`。
- 将验证体系拆分为 Gate 地图、机器验证目录、视觉验收和故障恢复四层，并为 `GATE`、`VAL`、`VIS`、`REC`、`RM` 建立唯一编号和回跳路径。
- Master 改为唯一总入口；各目录 README 登记直属文档的用途和阅读时机，技术详情、项目状态、规划、ADR 与历史证据不再混写。
- 重构前 37 份现行 Markdown 原字节归档到 `history/pre_lifecycle_restructure_2026-08-06`，并用文件大小与 SHA-256 固化。
- 新增只读审计器 `check_character_factory_docs.py` 及 9 项单元测试，覆盖元数据、链接与锚点、Master 可达性、目录索引、十阶段结构、编号引用、计划阶段命令块和归档哈希。
- 终态审计覆盖 54 份现行文档、349 个本地链接、56 个已定义编号和 43 份归档文件，结果为 0 错误；CC 侧 154 项与 Bridge 侧 1 项既有测试继续通过。

## 2026-08-06：行号级文档递归追踪

- 新增 `reference/DOCUMENT_LINK_TRACE.md`，按目录和文件列出每一次真实入站链接、源行号、用途原句及从 Master 出发的根链。
- 双向导航造成的循环不被隐藏：返回已出现节点的路径标记为回链；所有最短根前缀均展开，非最短人为绕行不重复枚举。
- 两个 Manifest 和其登记的 43 份不可变归档正文也纳入路径清单。
- 新增生成器 `generate_character_factory_link_trace.py`，文档链接或行数变化后可机械重建；文档工具回归增至 11 项。
- 终态结果为 55/55 份现行文档可达、336 次直接提及、544 条展开链、59 条显式回链，文档结构审计继续通过。

## 2026-08-07：用户输入权威边界与 Headshot QA 定位

- 用户明确独立负责资产、插件、安装包、输入数据及其许可、来源和对外发布边界；Agent 不再依据包内说明或来源措辞阻塞技术任务。
- Agent 的评估范围保留为兼容性、完整性、运行安全、稳定性、资源消耗、可复现性和项目功能价值。
- Headshot 2.x 确认为 `RM-05B` 的生成依赖；HD Face Control 定位为可选的 CC5 HD Facial Profile 人工 QA 工具，不是 Headshot 生成依赖。

## 2026-08-07：Headshot 与 HD Face Control 加载核验

- 当前 `CharacterCreator.exe` 进程实际加载 `CCHeadshot.dll`；注册信息为 Headshot 2.0，Product Build `2.0.0824.1`。
- HD Face Control 以 `OpenPlugin/CCFaceboard` 安装，当前进程实际加载 `main.pyd`、`facialrig.pyd` 与 `custom_widgets.pyd`。
- 当前 Lance CC Bridge 心跳健康且 `ping` 成功，结果位于 `00_engine/outputs/character_creator_bridge/results/plugin_check_20260807_2225.json`。
- 本次只证明安装、进程加载与 CC/RLPy 会话健康；尚未证明两个插件面板可打开，也未完成 Headshot 生成、保存和重载 Smoke。

## 2026-08-08：Headshot 两例生成与基础动态检查

- 用户用两张 2444×1718 正面图分别生成并保存女性、男性 `RL_CC3_Plus` 原始项目；项目大小约 101.44 MB 与 100.23 MB。
- Bridge 对两项目分别生成正面、3/4、侧面、全身、Blink、Smile、Jaw Open 和中性恢复八张 1536 证据，结果均为 `8/8`。
- 两项目的中性眼球、表情后恢复和快照恢复一致；检查期间无弹窗，检查前后项目 SHA-256 不变。
- 两项目均为 `CC4 Extended / 160`，基础表情可用，但缺少 CC5 HD Blink Corrective 与独立睫毛修正通道；当前只标 `smoke_candidate`，未晋级生产 seed。
- 质量检查器新增基础 Profile 兼容解析，同时保留生产身份安全门对完整 CC5 修正通道的严格要求；相关单元测试 `50/50` 通过。
- `RM-05B` 当前进度为 `2/4`；机器汇总位于 `00_engine/outputs/character_creator_bridge/artifacts/headshot_project_inspection/summary_20260808_v1.json`。

## 2026-08-08：Headshot 自然微笑人工复核修正

- 用户在原分辨率 Smile 证据中发现男女两例均有明显嘴角线性拉伸和唇周联动不自然。
- 复核确认检查器使用的是 `Mouth_Smile_L/R=0.8 + Jaw_Open=0.18` 合成压力姿态；它能验证通道驱动和严重穿模，但不能代表自然微笑质量。
- 原 `8/8` 保留为机器结构 smoke；自然微笑人工门禁改为 `0/2`，两例状态改为 `machine_smoke_only`，不得晋级生产 seed。
- 工作顺序改为先在现有男女派生副本验证 CC5 HD Facial Profile、Corrective 和三级自然微笑，再继续补齐 Headshot 4 人输入。

## 2026-08-08：Headshot CC5 Profile 派生升级

- 女性和男性冻结来源保持 `CC4 Extended / 160`；两个独立派生项目均成功加载并在重载后保持 `CC5 MetaHuman / 379`。
- 静态 Morph、眼球结构、材质分配、来源项目 SHA-256 和中性恢复均保持；bounds 最大绝对差分别为 `0.00034332275390625` 与 `0.0003108978271484375`。
- Blink、轻笑、中笑、满笑和 Jaw Open 机器门禁通过，两个升级批次均未匹配到 Undo 警告。
- 本轮证明 Facial Profile 派生升级可行，不等价于完整 CC5 HD 角色转换；最终身份和表情自然度仍待用户视觉接受。

## 2026-08-08：Headshot 烘焙身份原型包

- 存储探针发现两个 Headshot 来源均枚举 `2837` 个 shaping Morph，但非零权重为 `0`；身份不能由 slider 向量复建。
- 接受 `.ccProject` 保存身份几何、`.ccFacialProfile` 保存动态配置的规范原型包，建立 `F_HS_001` 与 `M_HS_001` 两个候选及中央注册表。
- 原型包哈希验证通过：`prototype_count=2`、`production_enabled_count=0`；project-seed 装配尚未实现，当前 Face V3 不变。
- `AvatarPresetAll` 实验写出约 `73.8 MB` 文件后保存 API 超过 30 分钟未返回，使当时 CC 实例保持 busy；该格式不进入生产路线，实例需由用户手动重启。
- 收口回归通过 CC 脚本 `158/158`、Bridge `1/1`、文档工具 `11/11`；文档审计为 58 份现行文档、376 个本地链接、0 错误、0 警告。

## 2026-08-08：AvatarPresetAll 实验终态更正

- 用户关闭“未创建 Morph Slider，角色形状不会保留”的弹窗后，原实验作业在约 `2 小时 46 分` 后正式返回 `succeeded`；Bridge 恢复 `healthy/idle`，队列为空。
- 该成功只表示约 `73.8 MB` 的 `.ccAvatarPreset` 文件被写出，不表示 Headshot 身份几何得到保留；弹窗内容直接否定其身份载体资格。
- 当前规范继续使用 `.ccProject` 承载烘焙身份、`.ccFacialProfile` 承载动态配置；不再推进 AvatarPreset 身份载体路线。

## 2026-08-09：Headshot 四人 Smoke 输入补齐

- 新增冻结来源 `RL_CC3_Plus Female2.ccProject` 与 `RL_CC3_Plus Male2.ccProject`，来源项目检查均为 `8/8`，检查前后 SHA-256 不变且未匹配 Undo 警告。
- 两个新派生副本均由 `CC4 Extended / 160` 升级并重载为 `CC5 MetaHuman / 379`；静态 Morph、眼球结构、材质、bounds、中性恢复和来源哈希门禁通过。
- Blink、三级 Smile 与 Jaw Open 的机器门禁通过；人工预检未发现眼球外露、闭眼穿插或明显口腔穿插，最终审美状态仍保留 `pending_user_review`。
- 建立 `F_HS_002` 与 `M_HS_002` 规范原型包，中央注册表扩展为 4 个候选；离线完整性校验为 `prototype_count=4`、`production_enabled_count=0`。
- `RM-05B` 的原始输入与机器升级达到 `4/4`；剩余任务是四例统一用户视觉验收和 `headshot_project_seed_then_bodyfit_v1` 男女平均体型 Pilot。

## 2026-08-09：Headshot 头型单轴安全区间

- 使用 `F_HS_002` 与 `M_HS_002` 对 7 个头部/颅骨 Morph 做扩大范围单轴扫描，共 `30/30` 案例和 `90/90` 张 1536 图；Bridge 两批均成功且受控 Morph 精确恢复。
- 用户接受 `Head Width`、`Head Depth`、`Skull Height`、`Skull Width`、`Skull Depth` 与 `Skull Peak` 的扫描范围。
- `Skull Back Depth` 的生产候选范围由扫描证据中的 `[-0.70, +0.70]` 收紧为 `[-0.50, +0.50]`。
- 新增唯一机器源 `cc_headshot_skull_safe_ranges_v1.json`；当前只批准单轴区间，多轴极值组合仍须受约束 Pilot。
- 可视化 run `2026-08-09-headshot-skull-axis-sweep-v2` 从 `pending_review` 更新为 `approved`，历史扫描图片和 manifest 保持不改写。
- 用户决定头型辨识度属于次级变量；规范头型池限制为全局最多 4 个，包含 `H00` 默认和最多 3 个差异化变体。男女优先共享 recipe ID，生产只选择已验证档案，不再自由随机 7 个轴。
- 用户确定长期生产身份池在 Headshot 通过质量、多样性、动态和装配门禁后切换为 Headshot-only；Face V3 保留为回归、兼容和历史对照，不参与默认混合抽样。当前生产默认值暂不改变。
- 新增 `cc_headshot_skull_composition_candidates_v1.json`：`C00` 默认加 8 个候选，在 `F_HS_002/M_HS_002` 上共享，共 18 个案例、54 张静态图。每个候选最多 3 轴，归一化联合幅度满足 `L1 <= 2.0`、`L2 <= 1.2`。
- 多轴运行有效结果为 `18/18`：男性 `9/9`，女性主批次 `6/9`，修复 CC 临时 signed-bounds 误报后的恢复批次 `3/3`。所有成功案例均精确复原受控 Morph，三个 Undo 守卫均未点击窗口。
- 七个已有正负单轴证据的头型 Morph 已加入执行器的受限 signed-runtime allowlist；未知 Morph 的运行时边界规则不变。角色工厂 `167` 项测试与可视化门户 `4` 项测试通过。
- 用户从多轴候选中选择 `C00 Base`、`C03 Long Deep`、`C06 Low Flat`、`C08 Narrow Shallow`，并依次固化为 `H00..H03`；选择记录写入 `cc_headshot_skull_profile_selection_v1.json`，候选门户 run 更新为 `approved`。
- 新增 `cc_build_headshot_skull_profile_library_v1.py` 和规范库：4 个 recipe 在 `F_HS_002/M_HS_002` 上生成 8 个确定性案例，不再自由随机七个头型轴。
- 动态机器门禁 `8/8` 通过，共 72 张图、40 个表情姿态；全部保持 `CC5 MetaHuman / 379`，liveness、中性眼球一致性、表情期间头型 Morph 不变、结束后 Morph 精确恢复均通过，Undo 点击为 `0`。
- 动态结果登记为 `2026-08-09-headshot-skull-profile-dynamic-gate-v1`，状态为 `pending_review`。Agent 视觉预检未发现明显穿插，但用户视觉签字和 project-seed 装配 Pilot 仍是生产前硬门禁。

## 2026-08-10：Headshot Project-seed + BodyFit 最小 Pilot

- 用户接受 `H00 Base`、`H01 Long Deep`、`H02 Low Flat`、`H03 Narrow Shallow` 的两性动态结果；规范头型机器记录更新为动态机器与用户验收通过。
- 新增 `cc_headshot_project_seed_bodyfit_pilot_v1.json`，固定 `F_HS_002 + H00 + F02_Average` 与 `M_HS_002 + H00 + M02_Average` 两个案例；Headshot `.ccProject` 作为身份起点，不再尝试从零 Morph 向量重建身份。
- `cc_validate_body_reconstruction.py` 新增 `headshot_project_seed_bodyfit_pilot`：按 Body/Junction、规范头型、Head Scale、Neck Height 顺序装配，保护 Face/Other、材质与眼球结构，保存重载后执行五姿态动态门禁。
- 完整权威运行 `run_20260810_v4` 为 `2/2`：两例均保持 `CC5 MetaHuman / 379`，BodyFit 目标、比例顺序、受保护 Morph、材质、眼球、保存重载、动态 liveness 与中性恢复全部通过，Undo 点击为 `0`。
- v4 的全身图因角色移到全身机位而灯光未同步，不能用于视觉曝光比较。执行器随后把 7 盏可移动灯与角色同步平移并在截图后恢复；女性和男性修正灯光单例均成功。女性父请求只在逐案例成功后的汇总变量作用域处失败，失败证据保留；修复后男性显式子集完整成功。
- 新增男女装配、动态和重载审查图，登记门户 run `2026-08-10-headshot-project-seed-bodyfit-pilot-v1`。机器状态为通过，生产状态仍为 `false`，等待用户视觉验收。
- CC 脚本完整回归为 `171/171`，可视化门户回归为 `4/4`；本轮结束时 Bridge `healthy/idle`、队列为空，CC private memory 约 `13.49 GB`。

## 2026-08-10：RM-05B 人工验收通过

- 用户检查门户 `2026-08-10-headshot-project-seed-bodyfit-pilot-v1` 后明确确认“检查没问题，可以通过”；门户状态更新为 `approved`。
- `cc_headshot_project_seed_bodyfit_pilot_validation_v1.json` 更新为 `machine_and_user_visual_passed_pilot_accepted`：F02/M02 两例保持 `2/2` 机器通过，`pilot_approved=true`，但 `production_approved=false`。
- `F_HS_001`、`F_HS_002`、`M_HS_001`、`M_HS_002` 四个原型 manifest 的视觉状态统一更新为 `passed`；中央注册表更新为 `rm05b_accepted_candidate_registry_not_in_production`。
- 原型注册表离线校验通过：`prototype_count=4`、`production_enabled_count=0`、`error_count=0`。本次验收只批准 Pilot，不提前启用 Headshot 生产身份池。
- `RM-05B` 正式关闭，活动 Roadmap 起点推进到 `RM-05C`：先比较 10 个原型的质量、多样性和成本，再依据身份覆盖收益决定是否扩展到 20；之后仍须通过 `RM-06` 和生产配方集成。
- 收口回归通过：CC 脚本 `172/172`、可视化门户 `4/4`、文档工具 `12/12`；文档审计为 59 份现行文档、382 个本地链接、0 错误、0 警告。Bridge 保持 `healthy/idle`、队列为空，CC private memory 约 `13.49 GB`。

## 2026-08-10：Headshot 十原型机器候选池过程记录

- 用户补齐 `RL_CC3_Plus Female3..5.ccProject` 与 `Male3..5.ccProject`，使 Headshot 来源达到 5 女 + 5 男共 10 个。
- 新增六个来源项目均完成 `8/8` 静态/基础动态检查，来源 SHA-256 在检查和升级前后保持不变，Undo 精确匹配守卫点击数为 0。
- 六个派生副本均完成 `CC4 Extended / 160 -> CC5 MetaHuman / 379` Profile 升级；Morph、眼球结构、材质、bounds、中性恢复、Blink、三级 Smile 和 Jaw Open 机器门禁通过。
- 新增 `cc_headshot_rm05c_source_batch_v1.json` 与 `cc_stage_headshot_rm05c_prototypes_v1.py`，将 `F_HS_003..005`、`M_HS_003..005` 暂存为不可变候选包；中央 Registry 扩展到 10 人并通过独立哈希校验，生产启用数保持 0。
- 收口审计发现 RM-05C 报告只保存 Morph 升级 delta，未保存新增六例的精确非零 shaping Morph 总数；manifest 改为显式未测量状态，Registry 校验器新增生产门禁并由 4 个专项测试覆盖，避免把经验结论写成机器事实。
- `.ccProject` 中无法可靠反推出用户当时使用的原照片文件名；新增六例明确标记 `pending_user_mapping`，验证器禁止在 source 未映射时把视觉状态设为通过。
- 建立门户 run `2026-08-10-headshot-identity-pool-10-v1`，提供男女各 5 人的中性、3/4、闭眼、三级 Smile 与 Jaw Open 横向对比。原 4 人保留已接受状态，新增 6 人等待 source 映射和用户视觉验收。
- 本事件不关闭 `RM-05C`：身份重复率、覆盖收益、成本、Aaron/M02 同条件比较以及是否扩展到 20 仍待完成。

## 2026-08-10：Headshot 十原型来源闭环与路线调整

- 用户提供新增六例的原始照片；经文件名和人物身份视觉核对，建立 `F_HS_003 -> CFD-MF-318-022-N`、`F_HS_004 -> CFD-MF-320-002-N`、`F_HS_005 -> CFD-MF-324-031-N`、`M_HS_003 -> CFD-IM-719-221-N`、`M_HS_004 -> CFD-MM-313-002-N`、`M_HS_005 -> CFD-WM-229-129-N` 的一一映射。
- 新增 `cc_headshot_rm05c_source_reference_mapping_v1.json` 与幂等执行器 `cc_attach_headshot_source_references.py`；六张照片复制为各规范包的 `source_reference.jpg`，复制前后 SHA-256 一致，manifest 与中央 Registry 原子更新。
- 注册表 v4 校验通过：`prototype_count=10`、`source_reference_mapped_count=10`、`production_enabled_count=0`、`error_count=0`。原 4 人保持视觉通过；新增 6 人仍等待用户视觉验收，且精确 shaping Morph 计数证据仍待未来生产激活前补测。
- 门户新增 `2026-08-10-headshot-identity-pool-10-v2`，在原动态对比基础上加入原照片与生成中性正面的逐人身份匹配页。
- 用户决定暂停 10/20 比较和更多 Headshot 扩容。`RM-05C` 只在新增六例视觉接受/淘汰后冻结暂存十原型候选池；Face V3 保持生产默认，Headshot 生产启用数保持 0。
- 当前开发优先级改为 `RM-08` 服装 Look 与十体型适配，再执行 `RM-09` 动画资产和道具验证；完成后才回到 `RM-06` 评估 Headshot 扩容、配方和生产迁移。
- 收口回归通过：CC 脚本 `178/178`、可视化门户 `4/4`、文档工具 `12/12`；文档审计为 59 份现行文档、382 个本地链接、0 错误，门户本地 HTTP 返回 200。

## 2026-08-11：首批服装手工载入门禁

- 用户在 `M02_Average/F02_Average` 和作者项目中完成首轮服装载入检查。女性 Summer、Anita 4、Jumpsuit 与 Necklace/Ring 在 F02 静态无明显问题；男性 Casual 01/02 可加载但需要 Conform 尺寸修正，Casual 01 Jacket 的当前值为 `Increase Size = 1`。
- 1920s Jacket/Pants/Shoes/Shirt Vest 在 `Keep Cloth Shape` 模式下可加载；遗漏的 `fedora_1.ccAcc` 已定位到包内 `Accessory/Head/Sckript/SilverScreen/Men`。
- 男 `PO_01/03/04/06` 与女 `PO_08/09/10/12` 作者项目均能打开，但只证明来源可读。PO_06 作者胖体项目自身有明显穿模；全部职业 Look 仍需枚举组件并在 M02/F02 重建。
- 男性运动探索混用 A/E/B 后缀且 Jacket 与 Pull D 严重穿模；女性运动 Look 同时使用 Towel/Shirt 时两个代际转换选项均有穿模。两者均不批准，分别改为无外套同后缀组和移除 Towel 后逐件复测。
- `All Star` 五个服装文件均只有约 `6-7 KiB` 且无法加载，确认是占位/索引壳文件并拒绝。源盘点器新增 `<64 KiB` Wearable 占位检测和 `pilot_candidate` 门禁。
- 手工证据写入 `clothing_pilot_validation/manual_load_gate_20260811_v1/result.json`；当前没有服装 Look 通过保存/重载、动作、十体型或 UE 门禁。

## 2026-08-11：服装 2022 日期门禁与安全重组

- 新增 `cc_reorganize_clothing_by_date_v1.py`，以 ZIP 为完整包、以产品根为散装包，读取 CC 资产最后修改时间执行 `<2022-01-01` 包级门禁；预览、说明和 ZIP 下载时间不参与判断。
- 140 个物理包归并为 131 个逻辑包：54 个通过、55 个过时、22 个日期不明。22 个散装包的 2026-08-07 时间与下载/解压时段重合，因此隔离为 `_date_unknown`，没有误当作新资产。
- 九个跨男女目录的载荷一致包归并到 `both`：帽子、Modern Glasses、服装1、Ancient Rome、末日幸存者、潮牌服装、狂徒、职业装和运动服；九个均早于 2022，进入 `both\_outdated`。
- 原始 `D:\BaiduNetdiskDownload\人物和服装` 保持不动；结果原子发布到 `D:\BaiduNetdiskDownload\人物和服装_2022plus_sorted`。
- 新增 `cc_validate_clothing_date_reorganization_v1.py`。全量验证 131 个逻辑包、1309 个载荷文件、`36,213,453,075` 字节，源/目标路径、大小和 SHA-256 全部一致，0 错误。
- 下一步改为人工逐包审查 54 个通过包；日期不明包单独决策，过时包默认不再使用。旧八来源 Pilot 只保留弹窗和穿模经验。

## 2026-08-11：服装 newest-50 v2 重组

- 固定 2022 门禁只保留 5 个女性已知日期包，不能支撑后续人工筛选；根据用户决策，当前策略改为在 `female`、`male`、`both` 三组内分别保留已知日期较新的约 50%，边界同时间包一并保留。
- 日期不明包不参与百分位排序，继续隔离到 `_date_unknown`。三组主队列分别为 20/31/5，共 56 包；较旧半区分别为 19/30/4，共 53 包；日期不明为女性 21、男性 1，共 22 包。
- 三组日期边界分别为：female `2021-03-28T09:22:32`、male `2022-08-18T11:16:12`、both `2021-03-10T18:17:32`。这是一条相对排名策略，不代表边界年份本身是质量标准。
- 当前结果发布到 `D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted`；原始目录保持不动，`D:\BaiduNetdiskDownload\人物和服装_2022plus_sorted` 作为 v1 历史回退保留。
- 全量验证覆盖 131 个逻辑包、1309 个载荷文件和 `36,213,453,075` 字节；源/目标路径、大小与 SHA-256 全部一致，0 错误。
- 已发布 78 行人工审查队列：56 个主队列包优先检查，22 个日期不明包作为补充；53 个较旧半区包默认不进入本轮。

## 2026-08-12：服装人工精选与六槽位物理规范

- 用户完成 newest-50 结果的人工去留和来源族整理，保留 13 个女性服装族、28 个男性服装族；`both` 保留 6 个共享鞋、帽子、眼镜和细碎配件来源，暂不进入本轮规范。
- 统一主体目录为 `Coats/Shirts/Pants/Skirts/Full-body/Shoes`，只创建实际使用的槽位；21 个尚未归入共享池的组件隔离到 `_Accessories-Pending`。
- `Casual 01..04` 归并为一个族并平铺为编号变体。`Elise`、`Misaki` 和赛博朋克套装各自只有一个多文件锁定整体，放入 `Full-body/Locked-Bundle`；其他 `Full-body` 直属文件各自代表独立单件候选。
- 新增 `cc_normalize_outfit_directories_v1.py`。共移动 288 个文件，移动前后 SHA-256 一致；当前 male/female 合计 349 个可穿戴资产，结构违规、空目录和后置待移动文件均为 0。
- 本事件只完成物理规范，没有生成服装族 JSON，也没有批准任何新组合。下一步定义统一 Schema，并为 41 个服装族登记 `explicit_looks`、`slot_groups` 或 `locked_bundle`。

## 2026-08-12：首批确定服装族 JSON

- 修正男女 `Rugged & Trendy Collection`：两件扩展名为 `.ccShoes`、语义上为完整服装的资产移动至 `Full-body`。原文件名、扩展名和 SHA-256 保持不变；JSON 使用 `semantic_slot_override=true` 留下解释。
- 新增 schema 1、确认/延后规则表、原子生成器和独立验证器。规则表必须完整覆盖 41 个 male/female family，不能遗漏或重复。
- 只为关系完全明确的 24 个 family 写入 `outfit_family.json`，覆盖 142 个资产：19 个 `explicit_looks`、2 个 `slot_groups`、3 个 `locked_bundle`。每个 confirmed family 的可穿戴资产覆盖率为 100%。
- 其余 17 个 family 因子套装边界、编号对应或配件必需/可选关系不明确而延后；验证器确认这些目录均无 JSON，没有根据文件名猜测组合。
- 生成后独立重算路径、大小、SHA-256 与当前规则，结果为 24/24、0 错误；新增 4 项 family JSON 单元测试，连同目录规范化 4 项测试全部通过。
- 证据位于 `character_creator_bridge/artifacts/outfit_family_rules/run_20260812_v1`。下一步是逐族与用户确认 17 个 deferred family，再进入 F02/M02 静态与动作门禁。

## 2026-08-12：家族专用服装配饰规则

- 用户确认五个原 deferred family。`Jumpsuits & Accessories` 的 Belt/Necklace 均可独立选择；`Mercenery` 的 Scarf 可选；`Owen` 的 Neck 必需；`Vacation` 删除 Hat 后 Waist Bag 可选。`Hippasuta` 实际只有 Shirt/Pants/Shoes，先前关于 Neck string 的判断错误，改为普通固定三件套。
- 家族专用配饰继续物理存放在 `_Accessories-Pending`，但 JSON 语义为 `slot=family_accessory`、`component_scope=family_local`，并禁止跨 family 使用。`optional_assets` 采用 `independent_subset`：允许不选、单选或全选；存在依赖关系时不得使用该模式。
- 用户清理后 male/female 当前共 341 个可穿戴资产、13 个 `_Accessories-Pending` 组件；其中 5 个已进入 confirmed family，另 8 个仍在 deferred family。
- 当前 family JSON 增至 29 份、覆盖 162 个资产；24 个 `explicit_looks`、2 个 `slot_groups`、3 个 `locked_bundle`。其余 12 个 family 无 JSON。独立验证 29/29、0 错误，规则与目录测试合计 9/9 通过。
- v2 证据位于 `character_creator_bridge/artifacts/outfit_family_rules/run_20260812_v2_family_accessories`。

## 2026-08-13：全部服装族组装规则收口

- 用户确认剩余 12 个复杂服装族的组装关系，并删除无法找到合理兼容关系的 9 个资产；male/female 当前保留 41 个 family、332 个可穿戴资产。
- `潮牌服装` 明确拆成六个互斥组：单件 Full-body、Pants+Shirts、Pants 分别搭配 CasualJacket/WarriorCloak/Windbreaker，以及 Skirts+Shirts。Shirts 与三个 Coats 子类不得同时出现。
- 生成器允许同一资产在多个互斥 slot group 中复用，并新增 group 级必需/可选家族配饰语义；补充两个专项测试后，Family JSON 测试为 7/7 通过。
- 其余 Anita、Bikini、连衣裙、漂亮裙子、Jiving、Lift & Haul、Oahu、redsoul、Streetstyle、White Tie 和 1920s 男装规则均按用户确认写入；13 个 `_Accessories-Pending` 组件全部成为禁止跨族的 family-local 资产。
- 当前 41 个 family 全部生成 `outfit_family.json`：24 个 `explicit_looks`、13 个 `slot_groups`、4 个 `locked_bundle`；deferred 数为 0。独立验证 41/41、0 错误。
- v3 证据位于 `character_creator_bridge/artifacts/outfit_family_rules/run_20260813_v3_all_confirmed`。下一步进入 F02/M02 保存/重载、静态和动作门禁；`both` 共享配件仍单独延后。
- 收口完整回归共运行 197 项，服装专项 7/7 通过；其中 3 项因同一个既有问题失败：`M02_Average.ccProject` 的大小和 SHA-256 已偏离生产锁。十体型只读盘点确认其余 9 个项目仍匹配；未自动接受新哈希，男性服装门禁在该漂移解决前暂停。

## 2026-08-13：M02 当前项目锁显式迁移

- 用户确认保留当前 `M02_Average.ccProject`；权威锁从 `35,662,791 bytes / 0cd6b730...e3de` 迁移为 `35,708,143 bytes / 9f1487c5...3457`。
- 通过 CC Bridge 只读加载 M02 并执行单体 BodyFit 复核，结果 `1/1`：5 个 Body Morph、0 个 Junction Morph、Body/Junction 组合指纹均与原锁定版本一致；旧身高和体型参数证据继续有效。证据位于 `character_creator_bridge/artifacts/bodyfit_m02_refresh_20260813_v1`。
- `cc_body_preset_library_v1.json`、派生 `cc_body_preset_library_v2.json` 与 `cc_headshot_project_seed_bodyfit_pilot_v1.json` 已同步新锁；旧验证报告继续保留当时哈希，不改写历史证据。
- male/female 共 41 个一级服装族均已有 `outfit_family.json`；目录与规则规范阶段只剩 `both` 下 6 个共享组件来源。

## 2026-08-14：共享鞋池第一轮规范

- 对照 41 个 `outfit_family.json` 和 `both/shoes` 实际文件，发现 2 双男鞋遗漏在原 family 目录，并发现 4 份 SHA-256 完全相同的冗余副本。
- 补回遗漏鞋且只合并完全相同副本，未删除外观相似但文件不同的候选；最终得到 58 双唯一鞋：女性 17、男性 41。
- 活动目录规范为 `Female/<Style>/F###_*.ccShoes` 与 `Male/<Style>/M###_*.ccShoes`，取消 Unisex；女性编号 `F001-F017`，男性编号 `M001-M041`。
- 58 个落盘文件哈希与计划集合完全一致；迁移前完整目录及两个外部补回来源保存在 `character_creator_bridge/artifacts/shoe_library_organization/run_20260814_v1/source_backup`。
- 当前样式分类仍需用户视觉复核和去相似。41 个 family JSON 的鞋路径进入有意失效的过渡状态，待鞋池冻结后统一迁移为共享鞋 ID，不改写历史 v3 证据。

## 2026-08-14：共享鞋池用户筛选与连续重编号

- 用户完成鞋池视觉筛选和分类调整，删除 6 双不进入生产池的男鞋；保留资产为女性 17 双、男性 35 双，共 52 双。
- 女性规范为 `Flats 1 / Heels 16`，编号 `F001-F017`；男性规范为 `Boots 7 / Casual 12 / Formal 6 / Sandals 4 / Sport 6`，编号 `M001-M035`。
- 52 个文件全部重新生成类别一致的文件名；独立复核确认 ID 连续、路径唯一、文件名类别与目录一致、哈希集合与保留来源完全相同。
- `shoe_inventory.json` 升级为 schema 2，记录 52 个当前资产、6 个删除项和下游迁移状态。完整旧新映射、执行报告及筛选后重编号前备份位于 `character_creator_bridge/artifacts/shoe_library_organization/run_20260814_v2_curated_reindex`。
- 当前 family JSON 的旧鞋路径仍有意失效；下一步先做 CC 适配门禁，再建立共享鞋注册表并统一迁移为共享 ID 引用。

## 2026-08-14：共享鞋与家族原配鞋边界修正

- 用户明确修正策略：family 自有 `Shoes` 是原配池；共享池只承担跨套装候选。共享副本被删除不影响原配鞋，无原配鞋套装可配置包含多个 ID 的共享候选池。
- 用户从男性池复制 8 双适合女性的鞋。schema 3 共享清单现含 60 个性别资产、52 套唯一几何：女性 25、男性 35；8 对同几何拥有男女独立 ID，同性别内无重复。
- 女性规范为 `Boots 2 / Flats 3 / Heels 16 / Sandals 4`，连续编号 `F001-F025`；男性分类和 `M001-M035` 保持不变。
- 发现早期迁移误将 `male.redsoul` 与 `male.cyberpunk_locked` 两双原配鞋移入备份，现已复制回 family `Shoes` 目录；共享池仍不包含这两双。
- 重新验证 41 个 family JSON 中的 51 双原配鞋，路径、大小和哈希全部通过；完整验证结果 `41/41`、0 错误。证据位于 `character_creator_bridge/artifacts/shoe_library_organization/run_20260814_v3_cross_sex`。

## 2026-08-14：缺鞋 family 待填写清单

- 机器扫描 41 个 family，26 个含原配 `slot=shoes` 并排除；其余 15 个进入共享鞋分配草稿，其中女性 11、男性 4。
- 草稿为每个 family 保留 `shoe_resolution`、`allowed_shared_shoe_ids`、`default_shared_shoe_id`、`allow_barefoot`、`look_overrides` 和备注，允许用户配置多双候选；`allow_barefoot` 可与共享鞋池同时启用，`barefoot_only` 只表示必须赤脚。
- Elise、Misaki 及男女 Rugged & Trendy 共 4 个 family 标记为先检查集成鞋；Bikini 与 Pyjamas 标记赤脚可能合理。
- 可编辑文件发布到 `both/shared_shoe_assignment_draft.json`；机器原件位于 `character_creator_bridge/artifacts/shoe_assignment/draft_20260814_v1`，生成器默认不覆盖已有文件。

## 2026-08-14：缺鞋 family 分配填写完成

- 用户完成全部 15 个缺鞋 family 的选择；输入中的数字简写已规范化为 `F###/M###`，对应空解析状态已设为 `shared_pool`。
- 最终静态分布为 13 个 `shared_pool`、2 个 `integrated_footwear`，共 116 个引用和 43 个唯一共享鞋 ID；库存 ID、性别、实体文件、默认值、赤脚逻辑及字段结构校验均为 0 错误。
- Bikini 与 Pyjamas 保留可选赤脚；男女 Rugged & Trendy 使用扫描到的集成脚部资产，不叠加共享鞋。
- 当前 `look_overrides` 全部为空，下一步进入 CC 中的实际 `Look × Shoe` 兼容性门禁。本次静态通过不代表已经完成穿模和动作验证。

## 2026-08-14：固定 Look 规则统一迁移为槽位池

- 用户澄清当前普通服装族不保留按文件名或编号推断的固定搭配；`Shirts`、`Pants`、`Shoes` 等分别形成槽位池并在所属逻辑组内自由选择，`Full-body` 同样形成单件池且每次只选一件。
- 新增 `cc_migrate_explicit_outfits_to_slot_groups_v1.py` 及其测试，将原有 24 个 `explicit_looks` family 全部迁移为 `slot_groups`；真正由多个文件共同构成且不可拆的 4 个 family 继续使用 `locked_bundle`。
- 当前 41 个 family 的模式分布为 37 个 `slot_groups`、4 个 `locked_bundle`，共 51 个逻辑组、332 个登记资产、0 个 deferred；独立验证为 41/41、0 错误。
- 迁移前规则、41 份旧 manifest、共享鞋分配草稿、迁移报告、dry-run、执行报告和验证报告均保存在 `character_creator_bridge/artifacts/outfit_family_rules/run_20260814_v4_all_slot_groups`。
- 下一轮视觉门禁从每个逻辑组抽取一套代表组合，并在五个同性 BodyFit 上测试，共 255 次装配；本轮不穷举每个槽位池的全部笛卡尔积。

## 2026-08-15：服装极端体型门禁首批与内存分片

- 用户最终把首轮兼容压力面从五个同性 BodyFit 收敛为瘦、胖、矮三个极端体型。确定性门禁清单覆盖 51 个逻辑组、153 个案例和 765 张标准五视角图片；每个体型使用已验收完整角色，而不是灰模 BodyFit 项目。
- CC 执行器新增精确 `Apply Cloth Options` 处理、逐资产 inventory 变化验证、来源项目逐例重载、动作清除、毛发保留、动态全身构图和逐例检查点。女性简单服装与男性 1920s 多层服装两个 Pilot 均通过。
- 首次长批次完成 39/153、机器通过 39、失败 0、图片 195，对应 13/51 个完整 Look。CC 私有内存从约 11 GiB 增至约 30.49 GiB；为避免整机崩溃，在完整案例检查点受控停止，CC 仍保持打开和可响应。
- 新增 `cc_build_outfit_compatibility_resume_plan_v1.py`，自动验证已完成图像并排除 39 例；剩余 114 例按每批 5 个完整 Look 拆成 8 批，批次间必须由用户离线重启 CC。恢复计划为 `cc_outfit_compatibility_resume_plan_20260815_v1.json`。
- 部分结果已登记到门户 run `2026-08-15-outfit-compatibility-gate-partial-v1`：13 张三体型 × 五视角总览板，并保留 195 张原图。该 run 状态为 `blocked`，只表示机器门禁部分通过，不表示人工穿模验收完成。

## 2026-08-15：服装门禁首个重启分块与证据修正

- 用户离线重启 CC 后执行首个恢复分块，完成 5 个完整 Look、15/15 案例和 75/75 图片；机器失败 0、Undo 精确守卫匹配与点击均为 0。CC 私有内存约由 3.53 GiB 增至 16.29 GiB。
- 累计进度达到 54/153、18/51 个完整 Look 和 270 张图。新增累计门户 `2026-08-15-outfit-compatibility-gate-progress-v1`；分组标签改为按内容完整显示，大图弹窗支持按钮/滚轮缩放及拖拽平移，门户回归为 5/5。
- 用户初查未见重大服装问题；头发与头巾、兜帽、高领等头部半包裹服饰的相交被登记为后续兼容规则问题，本轮不擅自修改资产。
- 自动图像复核发现全部 18 个已跑 F01 右侧图存在固定离体黑色几何，其他 36 例同区域为 0；它对应 F01 源项目唯一的 `GetAccessories/Double Bubble Braids`。执行器改为服装门禁前清除源配饰并保留 `GetHairs`。新进程单例 Smoke 确认删除 1 个配饰、保留 3 个头发对象且右侧离体物消失；用户决定旧图不重拍，新逻辑只用于后续案例。
- 恢复计划改为合并多个检查点，确认已完成 54 例并只调度剩余 99 例；当前 33 个 Look 拆为 `outfit_compatibility_chunks_20260815_r2` 下 7 批，使用独立 `run_20260815_chunks_v2` 输出根和 `outfit_gate_20260815_r2_*` Job ID。已执行 `v1/chunk_01` 的清单保留旧配饰策略作为历史证据。

## 2026-08-15：F01 源配饰修复与第 19 个 Look

- 单例 Smoke 精确移除 F01 的 `GetAccessories/Double Bubble Braids`，保留 3 个 `GetHairs`；新 `right_profile` 无离体黑色几何，5/5 图齐全，Undo 0。
- 用户决定保留既有 18 个 F01 旧图，不执行修正版重拍；原四个修复分片已标记 `canceled_by_user_do_not_execute`。
- 在同一低内存进程追加 `female.off_shoulder_dresses::default` 三体型微批，3/3 成功、15/15 图齐全，新 F01 再次确认无离体物。
- 累计门户刷新为 57/153、19/51 个完整 Look、285 图。恢复计划合并第三个检查点，剩余 96 例、32 个 Look，拆为 `r3` 的 7 批且无重复重放。

## 2026-08-15：服装门禁自适应批处理

- 同一 CC 进程在 F01 Smoke 后继续完成 15 个正式案例：露肩连衣裙 3 例、非洲女性休闲装三个 Look 共 9 例、男性 Casual 01-04 共 3 例；正式案例 15/15、图片 75/75、Undo 0。
- 进程私有内存最终为 14.93 GiB，证明合理边界是每次重启运行 12–15 个案例或内存接近 16–18 GiB，而不是每个案例重启。
- 累计门户更新为 69/153、23/51 个完整 Look、345 图。恢复计划合并 5 个检查点，剩余 84 例、28 个 Look，拆为 `r4` 的 6 批且无重复重放。

## 2026-08-15：资源联合门禁与第 26 个 Look

- 在同一 CC 进程继续完成 Cheer Leader、Dash、Dawkins 三个男性 Look，共 9/9 案例、45/45 图片、机器失败 0、Undo 0；该进程累计为 24 个正式案例和 1 个 Smoke，没有逐例重启。
- 处理期间 Private Bytes 从 14.97 GiB 增至约 19.84 GiB 峰值，任务结束后回落为 19.64 GiB；Working Set 最终仅 5.67 GiB，可用物理内存 11.94 GiB，证明 Private Bytes 是缓存/高水位指标，不能单独作为固定重启条件。
- 显存从约 7.48 GiB 已用增长到 10.63/12.28 GiB，余量 1.36 GiB，成为本轮实际停止原因。批处理策略改为每个完整 Look 后联合检查 RAM、commit 与 VRAM；单进程目标为 12–24 例，Private 24/30 GiB、可用物理内存 8 GiB、commit 75%/85%、显存余量 2048/1024 MiB 为软/硬参考。
- 累计门户更新为 78/153、26/51 个完整 Look、390 图。恢复计划合并 8 个检查点，剩余 75 例、25 个 Look，拆为 `r5` 的 5 批且无重复重放。

## 2026-08-15：不重启资源释放探针与 Hippasuta

- 新增 `resource_release_probe`：删除当前一次性测试角色、清空 Qt 图片缓存并执行三轮 Python GC；两次执行均成功、Undo 0，RLPy 未发现公开的原生 cache/purge/release API。
- 第一次清理使 CC Private 从 19.63 降到 18.43 GiB、显存可用从 1.37 增到 2.44 GiB；随后 Hippasuta 三体型 3/3 成功、15/15 图齐全、Undo 0。
- Hippasuta 结束时显存仅余 0.66 GiB；第二次清理后恢复到 1.80 GiB，Private 从 21.29 降到 19.99 GiB。清理能释放当前场景约 1.1 GiB 显存，但清理后基线仍下降约 0.64 GiB，证明独特服装的 CC 原生缓存仍会累计。
- 累计门户更新为 81/153、27/51 个完整 Look、405 图。恢复计划合并 9 个检查点，剩余 72 例、24 个 Look，拆为 `r6` 的 5 批且无重复重放。

## 2026-08-15：Cheer Leader 缺裤纠错与服装门禁 v2

- 用户在累计网页中发现 Cheer Leader 没有裤子。回查旧案例确认 `Pants 02` 曾成功加入 inventory，但随后加载混编号 `Shirt 01` 时被移除；反向加载时裤子同样会移除上衣。清空选择并只选 Avatar 后问题仍可复现，因此根因是资产组合冲突，而非门户截图或选择状态。
- 三组作者同编号组合 `01/01/01`、`02/02/02`、`03/03/03` 均可稳定共存。Cheer Leader 规则由一个自由 `default` 组拆为 `matched_01/02/03`，当前服装库由 51 增为 53 个逻辑组，门禁 v2 为 159 例、795 图。
- `outfit_compatibility_gate` 执行器增加两项硬约束：每个资产加载前清空选择并只选择 Avatar；后加载资产若驱逐任何先前已应用的必选对象，案例立即失败。旧门禁只检查单次 inventory 是否变化而产生的假阳性不再可通过。
- 正式纠正批次覆盖三组 × M01/M04/M05，结果 9/9 案例、45/45 图片、Undo 0、必选件驱逐 0。累计门户刷新为 87/159、29/53 个完整 Look、435 图；旧 `male.cheer_leader::default` 三例由门户和恢复计划明确忽略。
- 当前恢复计划为 `outfit_compatibility_chunks_20260815_r7`：剩余 72 例、24 个 Look、5 个资源门禁批次；历史 `r6` 状态保留作纠错前证据。

## 2026-08-15：`r7/chunk_01` 完成与分片资源策略收紧

- 在 Cheer 修复后的同一 CC 进程继续执行 `r7/chunk_01`，完成 Jiving、Kilt、Lederhosen、Lift & Haul、Lincoln 五个 Look：15/15 案例、75/75 图片、机器失败 0、必选件驱逐 0、选择重置失败 0、Undo 0。
- 累计门户更新为 102/159、34/53 个完整 Look、510 图；HTTP 入口返回 200，门户回归测试 5/5。
- 分片起始时 CC Private 约 15.33 GiB、显存余量约 4.3 GiB；后期显存余量最低约 0.23 GiB，虽然 CC 始终响应并完成作业，但证明“12–24 例/进程”不能作为所有服装的默认目标。
- 作业后资源释放探针删除当前角色并清空 Python/Qt 缓存，显存余量由约 0.69 GiB 回升到 1.77 GiB，Private 由约 23.52 GiB 降至 22.29 GiB；因仍低于 2 GiB 软边界，本进程不再提交服装作业。
- 恢复计划收紧为 `r8`：剩余 57 例、19 个 Look、10 个小分片；每个作业 1–2 个完整 Look（3–6 例），单 CC 进程通常 6–12 例，资源清理后只有全部指标恢复到软边界以上才继续。

## 2026-08-15：固定套装复审与 `r8` 前两分片

- 用户复审迁移前具有一一对应关系的服装 family：Cheer Leader 保持已修复的 `matched_01/02/03`，其余候选批准维持当前自由搭配；审核清单 9/9 已闭合。
- 新 CC 进程执行 `r8/chunk_01-02`，完成 Mercenery、Mesh it Up、Oahu、Owen 四个 Look：12/12 案例、60/60 图片、机器失败 0、必选件驱逐 0、Undo 0；Owen 固定配饰在三种 BodyFit 中均完成四次资产应用。
- 累计门户更新为 114/159、38/53 个完整 Look、570 图。门户生成器默认 gate 修正为 v2，并从 resume plan 发现 Cheer 等独立检查点后自动追加新分片；回归测试 6/6。
- 12 例边界时 CC Private 13.54 GiB、可用物理内存约 12.0 GiB、commit 63.4%、显存余量约 5.59 GiB。恢复计划更新为 `r9`：剩余 45 例、15 个 Look、8 个小分片。

## 2026-08-15：无重启释放后完成 Pop Style 与 Pyjamas

- 在 12 例边界运行资源释放探针：删除当前临时角色，Private `13.54→12.28 GiB`，显存余量约 `5.59→6.5 GiB`，随后继续执行 `r9/chunk_01`。
- Pop Style 与 Pyjamas 共 6/6 案例、30/30 图片、21 次资产应用、机器失败 0、必选件驱逐 0、Undo 0；未复现 Cheer Leader 的组件互相替换。
- 累计门户更新为 120/159、40/53 个完整 Look、600 图。进程累计 18 个正式案例后，清理前 commit 72.5%、显存余量约 2.8 GiB，达到停止继续叠加的安全边界。
- 再次清除当前临时角色后生成 `r10` 恢复计划：剩余 39 例、13 个 Look、7 个小分片；下一轮必须由用户离线重启 CC 后继续。

## 2026-08-15：Rugged & Trendy 通过与 redsoul 顺序修正

- 用户观察到系统内存自行释放后，在资源门禁允许范围内执行 `r10/chunk_01`。Rugged & Trendy 在 M01/M04/M05 上 3/3 通过并生成 15/15 图；累计门户更新为 123/159、41/53 个完整 Look、615 图。
- 同批 redsoul 三例均在 `SHSV_S02MA_gloves.ccGloves` 返回状态码 1，Undo 匹配为 0。失败记录未进入累计门户，也未被提升为机器通过。
- 回查确认 `locked_bundle.required_assets` 的人工顺序为 `suit → boots → gloves → harness → pockets → hood`，旧 gate 生成器却按通用槽位重排。生成器现只排序 `slot_groups`，对 `locked_bundle` 保留权威顺序；新增顺序回归测试并通过。
- 新 `r11` 恢复计划为 36 个未完成案例、12 个单 Look 分片；`chunk_01` 只复测 redsoul。作业后资源释放探针仍未让 commit 和显存余量同时恢复至软边界，因此复测必须等待用户以离线方式重启 CC。

## 2026-08-16：Redsoul 扩展名调度兼容与门禁推进至 141/159

- 新 CC 进程中的专项探针确认：`SHSV_S02MA_gloves.ccGloves` 内容本身没有损坏，但 CC5 公开 RLPy 加载入口在 `.ccGloves` 扩展名分支返回状态码 1。加载顺序、选择、Undo、`LoadObject` 和组件重存储均不能解决。
- 将同一文件按字节复制并只把文件名扩展改为 `.ccCloth` 后，控制资产和 Redsoul 目标共同通过 2/2、阻塞弹窗 0。来源与别名均为 22,819,257 bytes，SHA-256 均为 `ee5472b654601dc717c535a344749004af6d6965ab5eda435a5aa9c8fbb3fc7e`。
- 建立 `cc_outfit_compatibility_aliases_20260816_v1` 注册表；生产策略只允许 `extension_dispatch_alias_only`，要求来源不可变、来源/别名字节完全相同，并在每次 gate 构建时重新校验大小和 SHA-256。未注册 `.ccGloves` 会被拒绝。
- `r12/chunk_01` 的 Redsoul 正式通过 3/3、15/15 图；随后 Streetscape、Streetstyle、Summer、Underbelly、Vacation 通过 15/15、75/75 图。累计门户更新为 141/159、47/53 个完整 Look、705 图，新增五个总览完成视觉抽查。
- 门户重建器现在会删除不再被当前 run 引用的旧编号汇总图，解决同一 Look 在 `sheets` 目录残留多个序号的问题。
- 当前进程在完成 18 个正式案例后空闲显存一度降至 914 MiB；释放探针后仅恢复到 2021 MiB，仍低于 2048 MiB 软边界。新 `r14` 恢复计划剩余 18 例、6 个单 Look 分片，等待用户离线重启 CC 后执行。

## 2026-08-16：服装极端体型静态机器门禁完成 159/159

- `r14/chunk_01..06` 完成 White Tie、Workout、Wrinkled、1920s full-body、1920s separates 和 Cyberpunk：18/18 案例、90/90 图、机器失败 0、必选件驱逐 0、Undo 0。
- 最终复核计划 `cc_outfit_compatibility_resume_plan_20260816_v6.json` 合并 28 个检查点，确认完整 gate 为 159/159、53/53 个 Look、0 未完成、0 恢复分片。
- 累计门户 `2026-08-15-outfit-compatibility-gate-progress-v1` 重建为 795 张原图和 53 张三体型 × 五视图总览；最后六张总览已检查人物居中、视图完整和无明显缺装。
- 当前完成的是 `VAL-CC-07` 静态机器门禁，不是 `VIS-CC-05` 人工穿模批准。下一阶段为累计门户人工审查、静态/动作压力测试、头发与头巾/兜帽/高领兼容规则、全部十体型和 UE 门禁。

## 2026-08-16：服装静态视觉接受与动作压力门禁启动

- 用户审查累计门户后确认服装-身体及服装层级未见明显静态穿模；决定固化为 `cc_outfit_visual_review_20260816_v1.json`，受审的 159 案例、53 Look、795 图索引冻结为 `reviewed_index_20260816_v1.json` 并保持 SHA-256 锁。
- 头发与头巾、兜帽、高领等头部相邻服装相交登记为 `deferred_known_issue`：不阻断当前快速贯通所需的动作压力门禁，但阻断最终生产批准。后续采用 head-occupancy 分类、hat-safe/compact 发型集、隐藏头皮毛发或专用变体。
- 新增 `cc_build_outfit_motion_stress_gate_v1.py` 和回归测试；门禁为 53 个 Look 各选同性重体型，每例采集 1 张静态参考、Walk 五个归一化时间点和 Full Body Calibration 五个归一化时间点，总计划 583 图，拆成 27 个小分片。
- 执行器新增 `outfit_motion_stress_gate` 支持。首个失败 Smoke 暴露 Windows 临时图像路径过长，随后以短确定性案例目录修复；第二轮暴露固定帧只覆盖长动画开头，随后改为按实际片段长度换算归一化时间点。
- 最终单例 `smoke_04` 为 1/1、动作图 10/10、Undo 0；步行和全身校准姿态均有可见变化且人物完整居中。两条动作只作为诊断负载，不构成后续生产动画池。

## 2026-08-16：动作压力网页与正式执行断点固化

- 新增 `build_outfit_motion_stress_run.py`：递归合并动作分片，严格校验每例 1 张静态参考、5 张 Walk 和 5 张 Full Body Calibration，并为每个 Look 生成固定两行的 11 图总览。真实 `smoke_04` 已完成网页构建验证；门户测试为 9/9。
- 正式动作批次未提交，进度保持 0/53。空场景资源释放探针 v2 成功，但 commit 仍为 77.65%，高于 75% 软边界；按既定安全策略不得继续加载资产。
- 建立 `cc_outfit_motion_stress_execution_state_20260816_v1.json`，冻结 gate SHA-256、27 个待执行分片、唯一续跑点 `chunk_01`、执行/发布命令和资源证据。下一步必须由用户按离线许可流程重启 CC，再复核 Bridge 与四项资源指标。
- 生产动画池保持 `not_started`；只有用户审查动作压力网页后，才单独进入 `RM-09`。诊断 Walk/Calibration 不得作为生产动画登记。

## 2026-08-16：动作压力 v3 与 20/53 资源断点

- 正式动作执行暴露 Elise 锁定 Bundle 的预期对象替换：后加载资产会以同名对象替换先加载资产。简单的“任何必选件驱逐都失败”会误判已由用户接受的静态装配；Misaki 还暴露 manifest 顺序与已接受静态应用顺序不一致。
- 门禁升级到 `cc_outfit_motion_stress_gate_20260816_v3`。生成器读取冻结的 `reviewed_index_20260816_v1.json`，逐 Look 保存实际静态应用顺序、静态证据中已观察到的精确替换和最终 inventory 签名。执行器只放行完全匹配该证据的替换，并在动作采样前要求最终 inventory 完全一致；Elise v3 重试和 Misaki 顺序回归均通过。
- 当前累计完成 20/53 Look、20 张静态参考、200 张动作图，机器失败 0；统一门户已更新为 20/53。第 20 个 Look 后资源释放探针成功，但 commit 静置后仍为 75.57%，因此停在完整 Look 边界并冻结续跑点为 v3 `chunk_11`。
- 生产动画池继续保持 `not_started`；必须先完成剩余动作压力门禁并由用户审查网页。

## 2026-08-16：动作压力 40/53 第二资源断点

- v3 正式批次累计完成 40/53 Look、40 张静态参考和 400 张动作图；所有已完成案例机器成功、冻结静态 inventory 匹配，统一门户已更新为 40/53。
- 第 40 个 Look 后执行资源释放探针：当前角色、Qt 图像缓存和 Python 引用均成功清理，但静置后的可用物理内存仍只有 3761 MiB，低于 8 GiB 软边界；因此在完整 Look 边界停止，唯一续跑点为 v3 `chunk_21`。
- 生产动画池仍为 `not_started`，不得因动作压力机器进度增加而提前进入 `RM-09`。

## 2026-08-17：动作压力机器批次 53/53 完成

- 用户按离线流程重启 CC 后从 v3 `chunk_21` 续跑；27 个正式分片最终覆盖 53/53 Look。全量去重审计为 53 张静态参考、530 张动作图、共 583/583 图，机器失败 0、最终 inventory 匹配 53/53、缺失或空文件 0。
- `chunk_22` 首例完成后曾因 Windows 短暂文件占用导致总检查点原子替换失败；执行器的 JSON 写入已增加 10 次有限退避重试。该首例及三个早期缺少新版 inventory 证据字段的案例均通过独立补证作业生成完整检查点，未伪造或回填运行结果。
- 统一门户 `2026-08-16-outfit-motion-stress-gate-v1` 已重建并注册：53 个分组、53 个唯一 `preset_id`，状态 `pending_review`。机器完成不代表动态视觉穿模通过；用户仍需逐 Look 审查。
- 最终资源释放探针删除当前一次性角色、清空 Qt 图片缓存并执行 Python GC，桥接恢复 `healthy/idle`。生产动画池继续保持 `not_started`，只有用户完成动作压力视觉审查后才进入 `RM-09`。

## 2026-08-17：动作压力用户抽查接受

- 用户抽查统一动作压力门户后报告未发现问题。该决定以 `cc_outfit_motion_visual_review_20260817_v1.json` 固化，冻结权威 gate 与累计 review index 的 SHA-256，并明确没有记录抽查数量、不能伪写成 53 个 Look 逐项人工签字。
- `cc_outfit_motion_stress_execution_state_20260816_v1.json` 更新为 `complete_user_spot_check_accepted`；动作压力网页生成器开始默认读取该决定，门户和注册表均重建为 `approved`，以后重复发布不会退回 `pending_review`。
- 当前动作压力等待状态关闭，生产动画池转为 `ready_not_started`，下一操作焦点为 `RM-09`。Walk 与 Full Body Calibration 仍只是诊断动作，不自动进入生产池；头发-头部服装冲突、全部十体型和 UE 门禁继续阻断最终服装生产批准。

## 2026-08-17：动画源包 P0-P3 初筛与物理整理

- 用户删除早期临时解压目录后，将 `D:\BaiduNetdiskDownload\iclone动作` 确认为当前动画源根。根目录原有 57 个顶层包条目，递归包含 57 个压缩包和 113 个既有 `.rlMotion`。
- 新增一次性整理器 `cc_organize_animation_pack_tiers_v1.ps1`。在严格核对预期源清单、目标根边界和零碰撞后，将源包按候选审查优先级物理整理为 P0 日常核心 11、P1 扩展写实 10、P2 道具/交互锁定 6、P3 特殊/风格化 30。
- 整理后核验为 `target_missing=0`、`stale_sources=0`、根目录额外项 0；递归压缩包和 `.rlMotion` 数量保持 57 与 113。操作没有解压或删除资产，源根清单与输出证据副本 SHA-256 一致。
- P0-P3 是包级候选审查顺序，不是单条动画语义或生产批准。逐条动作的性别适配、时长、循环、Root Motion、面部通道、道具依赖和人工验收尚未开始；正式生产动画池当前仍为 0。

## 2026-08-17：P0 动画只读静态 inventory

- 当前动画 Pilot 范围收敛为 P0。新增 `cc_inventory_p0_animation_sources_v1.py`，使用 Python `zipfile` 与本机 UnRAR 只读列出 11 个压缩包成员，不提取或修改源资产；对应回归测试为 3/3。
- 权威 v3 inventory 发现 611 个 `.rlMotion` 与 56 个 `.iMotion`，共 667 条。11/11 个包和压缩包可读，唯一 ID 与未批准状态校验通过；性别文件名提示为女 302、男 267、未知 98。
- 保守文件名启发式将 85 条列为 `standalone_first`、152 条列为语境动作、430 条列为道具/场景/双人依赖延后项。规则迭代修正了 `Walk_Calling`、`Walk_HoldItem`、购物/办公/家居环境和 `Photo_DSLR` 等早期漏判；v1/v2 只保留为诊断输出。
- 所有 667 条仍为 `not_reviewed/not_approved`，正式生产池为 0。下一步从 85 条中选择 10–20 条均衡 Pilot，只提取所选成员并在 CC 中实际播放后，才能登记时长、循环、Root Motion、面部通道和最终依赖。
## 2026-08-17：P0 动画动态 Pilot 冻结与 Gate 准备

- 从 P0 静态审查队列的 85 条 `standalone_first` 中冻结 16 条均衡 Pilot：F02/M02 各 8 条，11 条 `.rlMotion`、5 条 `.iMotion`。
- `cc_build_p0_animation_pilot_v1.py` 只提取被选 ZIP 成员，并验证源包 SHA-256、成员 CRC/大小、输出 SHA-256 与内容唯一性；源压缩包保持不变，生产批准数固定为 0。
- 新增 `animation_p0_dynamic_gate` 执行模式和 Gate 生成器。计划按 F02/M02 各加载一次项目，每条动作采集 5 个归一化时间点，共 80 图，同时记录帧长、Root Motion 证据、面部轨道线索和场景 Prop 增量。
- 新增回归当前合计 9/9 通过。CC 当时未运行，因此动态 Gate 仍为 `pending_cc_dynamic_review`，没有伪造动态结果或视觉批准。

## 2026-08-17：P0 动画动态机器 Gate 16/16 完成

- 用户按离线许可流程启动 CC 后完成 P0 动态 Gate。首轮执行暴露两类基础设施问题：Sandbox 发布的 Pilot 文件没有向桌面 CC 继承读取 ACL，以及固定相机无法覆盖带 Root Motion 的后续采样帧；失败作业均保留为审计，不计入通过结果。
- 白名单提取器现会在原子发布前恢复继承 ACL。动态执行器增加无头发 Pilot 模式、有限垂直构图校正、`RL_BoneRoot` 优先级，以及“先采原始证据、临时平移角色截图、立即恢复”的移动动作跟随策略。该策略只改变截图构图，不改变 Root Motion 样本。
- 权威累计证据最初合并 `run_20260817_v3`、`run_20260817_v4_retry_framing` 和 `run_20260817_v6_capture_follow`。原图抽查随后发现 `Walk_Normal_M` 横向贴边、`Walk_Hurry_M` 下半身裁切；根因是不同动作的 `GetBounds` 坐标空间不一致，以及跟随参考使用了动作首帧 Root。执行器加入局部/世界 Bounds 自动判别并改用构图目标作为跟随参考，`run_20260817_v7_capture_alignment` 定向重采 2/2、10/10 图并覆盖旧案例。
- 最终累计结果为 16/16 动作、80/80 图、机器失败 0；7 个 `moving_candidate`、9 个 `in_place_candidate`、16 个 `facial_channel_class=none_detected`、隐藏 Prop 增量 0。代表性女性与男性移动动作均已复核五帧完整入镜；其余动作仍等待用户在门户作语义和动态质量决定。
- 新增 P0 动态门户生成器和 run `2026-08-17-cc-animation-p0-dynamic-gate-v1`。门户保持 `pending_review`，生产批准数保持 0；下一步由用户逐条审查动作语义、循环意图、脚滑、手部接触、自穿插和动态质量，再建立只包含接受项的 P0 候选注册表。

## 2026-08-18：P0 动画门户资源与明亮采集修复

- 门户中引用的原始 PNG 与 JSON 均实际存在；失效显示来自本地 HTTP 启动/验证链路，而不是素材丢失。新增 `visualization_portal\start_portal.ps1`，用 `-UseBasicParsing` 做健康检查并维护门户专用 PID；当前 run 的 96 个 PNG 与 3 个 JSON 已完成 99/99 HTTP 200 校验。
- 黑色剪影不是设计目标。根因是加载 Lightroom 后又加载独立 `Ref Cam`，相机被移动到固定灯光的逆光侧。动态 Gate 现在保留 Lightroom 当前相机和源项目 yaw，禁用旧自动全身构图；中性灰无服装角色仍是隔离动画质量的刻意设置，但必须保持可见照明。
- 正式重采 `animation_p0_dynamic_gate\run_20260818_v8_lit_review` 完成 16/16 动作、80/80 张明亮原图、机器失败 0、Undo 0。`p0_009_city_walk_normal_m` 另暴露非零首帧 Root，执行器增加动作首帧到源项目 Root 的对齐，并以 `animation_p0_lighting_scout\start_aligned_20260818_v1` 完成 1/1 定向覆盖。
- 新权威累计证据为 `animation_p0_dynamic_gate\cumulative_review_20260818_v2_lit\consolidated_validation.json`。门户 run id 保持不变并重建为最新证据，状态仍为 `pending_review`，生产批准数仍为 0。

## 2026-08-18：P0 全量视觉接受与详情视角修复

- 用户检查全部 16 条 P0 Pilot 动作并报告均成功、未发现不自然现象。结论固化为 `cc_p0_animation_visual_review_20260818_v1.json`，哈希绑定 v3 Gate、正式明亮主批和 `p0_009` 首帧 Root 对齐恢复批。
- 决定范围是完整 Pilot 的视觉自然度接受，但没有逐动作书面备注，也没有分配循环意图、复用策略或生产限制。门户转为 `approved`；`production_approved_count` 继续保持 0，下一步为 P0 候选注册表。
- 门户 A/B 详情区曾在切换动作组后继续使用首组帧键，例如从 `t050_f0113` 切换到实际只有 `t050_f0100` 的动作，导致 `img.src` 为空。前端现会在每次切组或切换方案时重算两方案共有帧键，并对缺失 URL 做防御处理。
- 前端版本提升为 `20260818d`，门户测试为 13/13；首组与末组的不同中间帧 URL 均经本地 HTTP 返回 200。

## 2026-08-18：P0 候选注册表与穿衣角色 UE Pilot 就绪

- 新增 `cc_p0_animation_candidate_policy_20260818_v1.json` 和注册表生成器；正式注册表哈希绑定 Pilot、动态累计证据、用户视觉决定、策略文件与每个动作源。
- 16 条动作登记为 3 条循环候选、13 条一次性动作、7 条保留源 Root Motion、9 条原地动作；16 条均未检测到面部通道并登记为 `replaceable`。候选注册完成不等于生产批准，批准数仍为 0。
- 新增 UE Pilot 规范与工作单生成器，固定使用已生成并穿衣的 `CCSHOW_F02_AVERAGE_001` 和 `CCSHOW_M02_AVERAGE_001`，禁止退回灰色基础体。
- 四动作 Pilot 包含女走路、男走路、原地循环和一次性手势；工作单状态为 `ready_for_cc_export`。注册表与工作单回归测试分别为 4/4 和 4/4。

## 2026-08-18：P0 穿衣角色 CC 导出 Bundle 完成

- 新增 `animation_p0_ue_runtime_export` 模式和 `cc_p0_animation_ue_export_20260818_v1.json`。执行器加载哈希锁定的 `CCSHOW_F02_AVERAGE_001` 与 `CCSHOW_M02_AVERAGE_001` 穿衣项目，只在当前 CC 场景临时移除预览时间线，不覆盖源项目。
- 完成 2 个完整参考角色与 4 个 Motion-only FBX 导出：女/男走路保留源 Root Motion，女性 Stand Idle 和男性 Understood 手势原地化。CC 批次为 2/2 Actor、4/4 Motion、失败 0、Undo 自动关闭 0。
- 首轮导出暴露 Bridge 允许输入根、源项目预览片段、Windows 长路径和完整角色 T-pose Morph 导出选项四项基础设施边界；均以哈希一致 Bridge 副本、严格时间线预期、短 staging 路径和已验证导出 flag 修复，失败作业不计入通过结果。
- `cc_patch_unreal_animation_fbx_ascii.py` 改为一次扫描，四条动作均精确修补 47 个辅助骨骼名；晋升重写和最终终检生成 `D:\UE\exports\character_creator\p0_ue_runtime_pilot_20260818_v1\export_bundle_manifest.json`。
- 最终 Bundle 状态为 `ready_for_ue_import`，生产状态仍为 `not_approved`。下一步必须在 `datatry_02` 完成 Skeleton、Root Motion、循环接缝、一次性结束、可复用面部层、服装形变和头发/服装冲突门禁。

## 2026-08-19：P0 剩余 69 条离线审查包完成

- 从 P0 的 85 条 `standalone_first` 中严格扣除既有 16 条 Pilot，冻结得到 69 条内容唯一候选；源清单、批次配置、动作内容和穿衣角色项目均由哈希约束。
- 候选按 18/17/17/17 分为四个可恢复批次，使用已生成穿衣 F02/M02 角色完成 CC 动态机器采证：69/69 动作、345/345 图、机器失败 0。所有样例均保留五个归一化时间点，代表性男女原图已确认人物居中、照明正常且不是黑色剪影。
- 可视化门户新增 `candidate_review` 模式，支持队列筛选、五帧时间线、接受/淘汰/暂缓、自然度、语义、性别倾向、道具依赖、备注、浏览器自动保存、决定 JSON 导入/导出和大图缩放。正式 run 为 `2026-08-18-cc-animation-p0-offline-review-v1`。
- 新增一键离线入口 `00_engine\visualization_portal\OPEN_OFFLINE_ANIMATION_REVIEW.cmd` 与操作说明 `OFFLINE_ANIMATION_REVIEW.md`。用户可关闭 CC、UE 与 Codex 后独立审查，并导出 `cc_p0_animation_remaining_69_review_decisions.json`。
- 门户前端语法检查通过，回归测试 16/16，通过本地 HTTP 验证 run、首图和注册表均可访问。机器采证不等于人工或生产批准；69 条保持 `pending_review/not_approved`，既有四动作 UE Runtime Pilot 继续作为工程主线下一步。

## 2026-08-19：P0 F02/M02 穿衣参考角色通过 UE Auto Setup

- `datatry_02` 中启用 Reallusion Auto Setup 2.03，并将 F02/M02 原始 FBX 分别导入 `/Game/Vendor/Reallusion/CC5/P0RuntimePilot/F02/FullReference` 与 `M02/FullReference`；同名 Auto Setup JSON、源文件字节数和 SHA-256 均通过 Bundle 预检。
- F02 最终为 113 个资产、32/32 材质实例槽、21 个 HQ/LWHQ 槽和 497 个 Morph；M02 最终为 127 个资产、36/36 材质实例槽、24 个 HQ/LWHQ 槽和 501 个 Morph。两者均生成 PhysicsAsset、2 个 AnimBlueprint、角色 Blueprint、IK Rig、IK Retargeter、PoseAsset 与 Skeleton。
- M02 导入警告列出的 9 根未加权 IK/辅助骨骼在最终 Skeletal Mesh 中全部存在，且 `toe share bone`、`ik_foot_*` 和 `ik_hand_*` 父子关系正确；不启用 `Use T0 as ref pose`，不执行重导。
- 验收器修正了“每个角色目录必须独立生成 SubsurfaceProfile”的过严假设，改为检查 Skeletal Mesh 实际绑定的 HQ/LWHQ 皮肤材质、全部实例槽、Morph 和 Rig 资产。F02/M02 最终报告均为 `success=true`。
- 两个参考角色阶段完成；四条 `_UE5_Patched.fbx` 仍未导入，Bundle 继续为 `not_approved`。本周汇报快照见 `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`。

## 2026-08-19：P0 四动作与 FullReference 身体/面部运行时矩阵通过

- 诊断确认 Bundle 内哈希锁定的四个 `_UE5_ASCII.fbx` 是本轮 UE 动作导入权威输入；`_UE5_Patched.fbx` 不再用于 P0 Runtime Pilot。四条动作分别绑定 F02/M02 Skeleton，60 fps、帧数、Root 位移政策、原地约束、循环候选和一次性结束检查通过。
- 新增 `ue_build_p0_runtime_composition.py`：为 F02/M02 各生成 Neutral、Natural Blink、Asymmetric Blink、Subtle Smile 四个零骨骼面部片段，一个身体/面部分层 AnimBP 和一个 FullReference Wrapper。
- FullReference 在同时启用 RL Post Process 与直接 Morph 曲线时会出现蓝白眼罩；控制实验确认直接 Morph 本身正确。正式 Wrapper 因此固定 `disable_post_process_blueprint=true`。该路线不声明 eye-bone gaze；模块化 M02 的 eye-bone + curve Hybrid 证据继续由既有 v003 Pilot 保留。
- `run_p0_runtime_validation.py` 完成四个身体状态 × 四个面部状态，共 16/16 组合、24/24 原图、自动错误 0；F02/M02 双眼闭合、单眼闭合和轻微微笑通过技术视觉复核，临时 Actor 清理 4/4。
- 证据位于 `OUTPUT_ROOT\unreal_character_import\p0_runtime_pilot_20260819_v1\runtime_review`；门户分支为 `2026-08-19-ue-p0-runtime-pilot-v1`。`dm_asset_index.json` 在线升级为 version 4。该结论只接受无道具 P0 技术 Pilot，生产批准仍为 0。

## 2026-08-19：第一批数据 Sprint 冻结与活动文档精简

- 冻结 2026-08-19 至 2026-08-26 的第一批数据范围：F02/M02、8 个身份、8 套服装、16 个稀疏 FullReference Look、6 条动作、3 条轻动态表情、1 个场景和 2 台相机。
- 采用“唯一节点只渲染一次、编辑链引用节点”的配置图方案：设计上限 384 个视频节点，目标 4,000、最低 3,000 条 3–5 轮原子编辑链；允许同因子重复编辑和精确回滚。
- 新增配置图 schema、多轮链采样规范和 Linux/NVIDIA UE 5.8 服务器运行手册；`WF-08/09` 在真实 Gate 通过前继续保持 `planned`。
- 活动入口收敛为 `Master -> Current Status -> Active Sprint -> Workflow`。已完成或被替代的兼容入口从活动层移除，仍有审计价值的旧内容只保留在日期化历史快照和本里程碑日志中。

## 2026-08-20：首批动作、三表情和配置图生成器完成机器门禁

- 更正 2026-08-19 Sprint 记录中的动作口径：首批实际冻结 12 个物理动作文件，女性 6 条、男性 6 条；每个 Look 只使用 6 条同性兼容动作，因此 `16 Looks × 6 Actions × 4 states = 384` 的节点预算不变。
- `cc_build_first_batch_action_gate_v1.py` 完成源路径、字节数和 SHA-256 冻结。CC 动态门禁为 12/12、60/60 图、机器失败 0、隐藏 Prop 0、全部 `facial_channel_class=none_detected`；门户 `2026-08-20-first-batch-actions-12-v1` 等待用户视觉审查。
- 首批动作导出工作单计划生成 2 个参考角色和 12 个 Motion-only FBX。CC 成功写出女性参考角色后，在首条动作导出前显示 `You must first purchase the content licenses in order to export FBX files.`；精确守卫只点击该消息的 `OK` 后，作业以 `failed` 正常返回。staging 为 1 个参考 FBX、0 个 Motion FBX，未晋升、未生成 Bundle、未进入 UE 门禁；`blocked_attempt_summary.json` 明确禁止晋升。该软件阻塞必须由用户处理内容授权/打包状态。
- `cc_undo_dialog_guard.ps1` 与执行器已增加 fail-fast 路径：只在标题、窗口类、精确消息以及 `OK/Buy` 两按钮全部匹配时点击 `OK`，写入 `fatal_dialog.json`，随后让导出失败；不会点击 `Buy` 或绕过内容检查。
- 为 F02/M02 各构建 Happy、Angry、Sad 三条 3 秒轻动态 Morph 表情，并建立 Body 动作 + Face additive 的审查 AnimBP/Wrapper。运行时机器门禁为 6/6 组合、18/18 图、自动错误 0；门户 `2026-08-20-ue-first-batch-expressions-v1` 等待用户视觉审查。
- 新增 `build_first_batch_config_graph_v1.py`。合成冻结输入可确定性生成 16 个稀疏 Look、384 节点、原子 E1/E2/E3/E7/E11 边、4,000 条 3–5 轮链和渲染作业，并验证 70/20/10 progressive/rollback/closed-cycle 目标。真实 8 身份、8 服装和场景资产 ID 尚未冻结，因此当前只算实现测试，不算正式第一批 Manifest。

## 2026-08-20：首批 8 身份与 16 个 FullReference Look 导出完成

- `F_ID01..04` 与 `M_ID01..04` 共 8 个身份均完成 CC 组装、保存和哈希验证。`cc_first_batch_full_reference_looks_20260820_v2.json` 以环形规则冻结每个身份两套服装，共 16 个 Look。
- 用户确认女性 O04 原 `Windbreaker_C` 与头发相交；v2 生成器加入哈希锁定覆盖，最终组合改为 `YogaPants_B + CasualJacket_C + Pump Heel_B`。只定向重做 `F_ID03_O04` 与 `F_ID04_O04`，其余 14 项不重跑。
- 首轮最后一项 `M_ID04_O01` 已正常写出项目、FBX、JSON 和 `.fbm`，但没有额外 `textures` 目录。检查确认其 JSON 中布料权重图引用为 0，而有该目录的案例均实际引用权重图；校验器因此修正为“`.fbm` 必需、`textures` 仅在被 JSON 引用时记录”，相关回归 6/6 通过。
- 最终生产根为 `D:\UE\exports\character_creator\first_data_batch_20260820_v1`：16 个 CC 项目、16 个 FBX、16 个 JSON、16 个非空 `.fbm`，0 个残留 partial 目录。合并审计 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_assembly\final_audit_20260820_v1.json` 为 16/16、失败 0；被替换或误报失败的旧产物保留在 `_superseded`，未静默删除。
- 首批动作同时升级为 v2：替换后的 12 个物理动作已冻结，5 秒审查 Manifest 为 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_full_preview\review_20260820_v2_5s\action_window_manifest.json`。9 条旧采集经哈希复用、3 条替换动作重采；Motion FBX Bundle 与 UE 门禁仍是下一阶段，不因角色 Bundle 成功而自动视为完成。

## 2026-08-21：首批 12 个动作导出与五秒窗口冻结完成

- 三条无法通过 CC 外部导出门禁的旧动作由 `Sexy Dance`、`Battle Dance`、`Cheer Hands & Step Dance` 替换；三条替换动作完成 CC 全时长动态门禁 3/3，机器失败 0。
- 女性 6、男性 6 个 Motion FBX 已全部导出、规范命名并写入 `cc_first_batch_action_registry_20260821_v4.json`；文件数量、非空状态、字节数和 SHA-256 为 12/12 一致。
- 用户签署完整 12 条五秒窗口：9 条继承窗口保持哈希一致，3 条新窗口分别为 `1.6..6.6 s`、`0.0..5.0 s`、`3.0..8.0 s`。冻结产物位于 `first_batch_action_window_selection\frozen_20260821_v4\frozen_action_windows.json`。
- `first_batch_required_exports_20260820_v1.json` 已重建，锁定 16 个 FullReference Look、12 个 Motion FBX 和三表情配置，状态提升为 `frozen_sources_ready_for_unreal_import`。生产批准仍为 0；下一门禁是 UE 导入、骨架绑定、动作时长、Root Motion、Morph、材质和服装变形。

## 2026-08-22：首批 16 个 FullReference Look 全部通过 UE 导入门禁

- 新增 `ue_import_first_batch_full_reference_looks.py`、`run_first_batch_full_reference_import.py` 和精确窗口守卫 `ue_reallusion_dialog_watcher.py`，对冻结 Bundle 做源文件哈希预检、FBX 导入、Reallusion Auto Setup、保存和后验收。守卫只处理已知 FBX/Auto Setup 对话框并等待窗口实际关闭；未知窗口仍失败停止。
- 16/16 Look 已导入 `/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks`，磁盘共 2,593 个 `.uasset`。每份独立报告的 `success`、`skeleton_reuse_contract_passed`、`mesh_contract_passed`、`auto_setup_materials_passed`、`rigging_contract_passed` 和 `skeleton_normalization.passed` 均为真，Morph 数量范围为 463–508。
- 女性所有 Skeletal Mesh 统一引用 `F_ID01_O01` Skeleton，男性统一引用 `M_ID01_O01` Skeleton；同性交付 Skeleton 复用已经从 Pilot 提升为首批 16 Look 的完整机器证据。
- 聚合报告 `OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_20260821_v1\aggregate_import_gate.json` 为 `success=true`、`passed_count=16`、`failed_count=0`。完整 Look 导入会产生较高内存峰值，因此本轮采用单 Look 执行、成对完成后受控重启 UE；后续 Motion-only 导入继续监控资源，但不默认沿用逐动作重启。
- Day 2 的角色导入部分完成。下一门禁收敛为 12 个 Motion FBX 的 UE 导入/五秒运行时验证，以及 Happy、Angry、Sad 的动态视觉签字。

## 2026-08-22：Day 02 动作/表情自动门禁与 32 Look 全矩阵完成

- `run_first_batch_day2_final_gate.py` 汇总静态运行时门禁和规范女/男各 Happy、Angry、Sad 的六个动态案例。最终证据为 `OUTPUT_ROOT\unreal_character_import\first_batch_day2_20260822_v1\day2_final_gate.json`：16 个基线 Look、12 个 Motion、6 个表情资产、6/6 动态案例、180 张图和 6 个 MP4，`automatic_success=true`；该机器报告生成时用户签字仍为 `pending_user_review`，随后由本节末尾的独立决定文件关闭。
- 按 `cc_first_batch_full_reference_missing_looks_20260822_v1.json` 执行 `run_20260822_missing16_v1`，新增 8 女 + 8 男 Look 为 16/16、失败 0。审计器修正了可选 `textures\` 目录的判定：只有记录本身声明存在或 JSON 实际引用额外权重图时才要求该目录；回归测试 3/3 通过。
- CC 合并审计 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_expansion\final_audit_20260822_v1.json` 为 32/32、失败 0、partial 目录 0。`first_batch_required_exports_20260822_v2.json` 成为当前 UE 机器清单，冻结 32 Look、12 Motion 和三表情配置。
- 首次尝试在同一 UE 进程连续导入剩余 15 个 Look：前 9 个通过，随后 UE private commit 累积到约 84–90 GB 并在 `M_ID02_O01` 阶段崩溃。该项没有残留 partial 资产，干净重启后单独通过，确认故障来自长批次资源累计而非资产损坏。
- 恢复策略改为每个 UE 会话最多导入 3 个新 Look、批间正常重启；窗口守卫与 UE 使用相同 Windows 权限级别，交互导入不使用 `--continue-on-error`。剩余两批各 3 项均为 3/3。
- 最终 `/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks` 为女性 16、男性 16，共 32 个目录。聚合报告 `OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json` 为源预检 32/32、既有目标 32、`passed_count=32`、`failed_count=0`。UE 已在验证后正常关闭；当前 Sprint 转入 WF-08 场景、相机、Sequence 与 32-Look 节点预算重冻结。
- 用户随后检查六个动态视频，确认 Happy/Angry/Sad 的差异可见但较轻微，并接受其用于第一批数据。决定写入 `OUTPUT_ROOT\unreal_character_import\first_batch_day2_20260822_v1\day2_dynamic_visual_review_20260822_v1.json`，Day 02 的人物、动画和面部表情门禁全部关闭。
- 用户冻结服务器全量策略：每个 Look 必须运行全部 6 个同性动作和 4 个镜头/表情状态，正式节点数为 `32 × 6 × 4 = 768`。本地只逐条验证 12 个动作及代表性镜头/表情组合，不本地渲染完整 768；性能不足时也不删减动作或节点。

## 2026-08-22：WF-08 四镜头顺序序列与 F02 五秒窗口试点通过

- 用户在 TokyoStylized 场景中固定测试角色锚点和 `near/far/high/side` 四台相机；`firstweek` 为 30 fps、0–600 帧，Camera Cut 顺序为 `0–150`、`150–300`、`300–450`、`450–600`。四相机均通过角色可见性和瞄准几何审计。
- 决定不使用 MRQ 同时渲染四相机，以降低本地峰值显存和内存；审核序列改为把同一个五秒动作窗口重复四次并依次切换镜头。总渲染量仍约为单视角四倍。
- 新增 `ue_build_first_batch_20s_sequence.py` 与 `run_first_batch_20s_sequence.py`。构建器复制 `firstweek`，不修改人工布局源；把冻结 JSON 起点转换为 UE 5.8 的 tick-resolution `first_loop_start_frame_offset`，并建立四个 150 帧动作 Section。
- 用户批准只有 `ACT_F02_CATCH_BREATH` 使用 InPlace 派生资产，F01/M01/M04 和其余动作均使用原始 BodyOnly。生成的 `LS_DM_FirstBatch_F02_20s_Pilot_v001` 结构审计与四段相同相对帧骨骼姿态一致性通过；F01 `1.6..6.6 s` 非零偏移也完成临时验证，临时 UE 资产随后删除。
- 当前审计证据为 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260822_v2\layout_motion_audit.json`，序列与布局均通过。F03/F04/M02/M03 的 Idle 补齐尚未实现，构建器会主动拒绝这些短动作；身体 Sequencer 轨道与三表情层的组合回归及用户视觉签字仍是 WF-08 的剩余门禁。

## 2026-08-23：F02 20 秒身体/表情组合回归通过

- 验证发现把 curve-only 表情作为同一 Skeletal Animation Track 的第二行不会提供与 AnimBP `Apply Additive` 等价的求值，机器曲线与 Morph 探针保持为零；该叠行方案被淘汰。
- 使用已批准的 F02 InPlace 身体资产生成 Happy、Angry、Sad 三条组合 AnimSequence。每条保留原身体的 108 条骨骼轨道、30 fps、391 帧、13.03 秒和规范女性 Skeleton，并分别嵌入 8、12、10 条循环 Morph 曲线。
- Python 空建 Section 在编辑器预览中曾停留于静态姿态。用户手工创建的可播放原生 Section 被固化为 `/Game/DataMake/Sequences/FirstBatch/Templates/LS_DM_NativeSkeletalAnimationSectionTemplate_v001`；正式构建器改用 `copy_sections/paste_sections` 复用该模板。
- `LS_DM_FirstBatch_F02_20s_Pilot_v001` 已重建为四个原生 150 帧 Section，依次播放 `Happy/Angry/Sad/Happy` 组合资产，同时保留 `near/far/high/side` 四段 Camera Cut。八项结构检查全部通过。
- 用户确认身体动作和面部表情均可见，评价表情仍较单调但当前可接受。决定记录为 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260823_v1\f02_20s_body_expression_visual_review_20260823_v1.json`；表情丰富度转为第一批后的改进项，WF-08 当前只剩短动作 Idle 补齐、其余组合资产和媒体拆分决定。

## 2026-08-23：短动作、36 条组合资产与 1440p MRQ 单节点贯通

- F03、F04、M02、M03 四条不足五秒的动作使用 `symmetric_exact_endpoint_holds_v1` 生成精确 150 帧派生资产，分别在首尾保持 `7/7`、`1/2`、`24/24`、`18/18` 帧。108 条骨骼轨道保持不变，最大位移和缩放误差为 0；报告为 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260823_v1\idle_padding_build.json`。
- 12 个首批动作各生成 Happy、Angry、Sad 三条派生组合 AnimSequence，共 36/36 通过。源身体动作和表情 clip 继续独立保存，组合资产只作为 Sequencer 可重建交付缓存；报告为 `all_action_expression_composites.json`。
- MRQ 首次输出发现第 0 帧为 Bind Pose/T Pose。仅增加源窗口保护不足以修复；每个 Skeletal Animation Section 增加一帧 pre-roll 后首帧恢复正常，该初始化约束已写入构建器和 WF-08。
- 建立本地 MRQ 单节点入口，默认 Preset 为 `/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_1440p30_PNG_v001`。最终样例 `OUTPUT_ROOT\unreal_render\first_batch_local_sample_20260823_014930_v001` 输出 150/150 张 2560×1440 PNG、30 fps、5 秒 H.264，视频 SHA-256 为 `53b3f4f15434ab601162f442e9e3b96ce7bc92104e54daae7cc6af59a4496941`。
- 首/中/末帧视觉抽检确认分辨率、构图和首帧初始化正常；末帧深度前屈时夹克肩部和腰部存在身体穿出。该问题被分类为 Look/动作兼容性警告，样例状态为 `passed_with_visual_warning`，只批准渲染管线 Pilot，不批准完整节点视觉验收。

## 2026-08-23：首批 32 Look 面部白块根因与修复

- 男性表情渲染在额头和面颊出现随 Morph 强度逐渐增大的白块；同一场景中无表情动画正常，旧 M02 微笑资产也正常，因此先排除了场景光照、骨骼导入和单一表情曲线损坏。
- 同帧 A/B 显示：替换为旧 M02 已验证头部材质后白块完全消失；关闭 35 个皱纹规则权重不能解决问题，隐藏眉毛、胡须和头发覆盖层也不能解决问题。
- 进一步确认 32/32 首批导出 JSON 的 `Wrinkle.Textures` 为空，Auto Setup 因而把 `CM1..3`、`WM1..3`、`RM1..3`、`HM1_Flow..HM3_Flow` 和 `NormalMap_Blend` 绑定到 Share 占位图。表情求值时占位颜色被混入头部材质，形成白块。
- `ue_patch_first_batch_head_wrinkle_textures.py` 为 32 个 Look 补入已验证 M02 的标准 CC 皱纹贴图，保留每个角色自己的 Base Color、基础 Normal 和身份。修复结果为 32/32 Look、416/416 参数匹配、占位纹理 0；Happy、Angry、Sad 及恢复原始头部材质后的同帧 MRQ 均无白块。
- 后续任何重新导入或 Auto Setup 重建都必须重跑 `VAL-XFER-02`；脚本会在执行时临时生成审计报告和恢复备份。长期方案是在 CC 导出阶段携带非空动态皱纹贴图路径。完成验收后，本次 A/B 图片、备份、诊断脚本和 UE 测试资产均已清理，仅保留正式修复实现与本节根因说明。

## 2026-08-24：首批生产动作池收敛为 10 条，表情退出编辑轴

- 用户从生产集合删除女性 `ACT_F04_AUDIENCE_09` 与男性 `ACT_M03_AUDIENCE_12`。原始 v4 注册表、窗口、FBX 和 UE 验证证据继续作为历史来源保留；新建 `cc_first_batch_action_pool_20260824_v1.json`，冻结女性 5 条、男性 5 条的当前生产选择。
- Root Motion 契约明确为：只有 `ACT_F02_CATCH_BREATH` 使用 `/Game/DataMake/Animations/CC5/FirstDataBatch/Female/InPlaceCandidates/A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001`；其余 9 条全部保留源 Root Motion。Sequence 与组合构建器会拒绝不在活动池中的动作。
- Happy、Angry、Sad 继续作为可见渲染状态并参与 node ID，但不属于首批可编辑特征；配置图不再生成 `E11` 表情边，编辑链只允许 `E1/E2/E3/E7`。
- 当前机器清单 `first_batch_required_exports_20260824_v3.json` 为 32 Look、10 Motion、3 表情，状态 `frozen_sources_ready_for_unreal_import`。正式节点预算从 768 收敛为 `32 × 5 × 4 = 640`。
- 配置图生成器升级为完整 32 Look 矩阵、每性别 5 动作和 640 节点契约；12 项 dataset 单元测试通过，4,000 条 3–5 轮链仍满足原子边、回退、闭环和轴覆盖约束。

## 2026-08-24：32-Look 本地代表渲染矩阵通过并修复整段 T-pose

- 新增 `first_batch_local_render_matrix_20260824_v1.json`、`run_first_batch_render_matrix.py` 与 `run_first_batch_32_video_matrix.ps1`，把 Look staging、参数化 Sequence、MRQ、媒体检查、状态记录和断点续跑固化为一个入口。
- 首次批处理只有第一例正常，后续案例整段保持 T-pose。全新隔离 Sequence 仍可复现，排除了 Sequence 重用、相机、编码和动画资产损坏；根因是不同 Reallusion Blueprint 的默认动画模式不一致，而构建器未对所有性别显式强制 Custom Mode。
- `ue_build_first_batch_20s_sequence.py` 现对男女全部动画 Section 设置 `force_custom_mode=true`；矩阵执行器在提交 MRQ 和复用旧结果前，硬校验四段 Section、原生 Actor binding、目标 Actor 与 Custom Mode，并把结果写入每例 `automation_contract.pose_driver_contract`。该故障与一帧 pre-roll 修复的“仅第 0 帧 Bind Pose”是两个独立问题。
- 正式本地证据为 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002`：32/32 案例、32 个唯一 Look、10 动作全部覆盖、`near/far/high/side` 各 8 例、Happy/Angry/Sad 全覆盖；共 4,800 张 2560×1440 PNG 和 32 个 30 fps、150 帧、5 秒 H.264 MP4。
- 32/32 render report 与 pose-driver contract 通过；新增五时间点 temporal-motion 门禁后，32/32 可见运动通过，最小最大帧差为 `28.148507`（门槛 `2.0`）。OpenCV 独立复核所有 MP4 的分辨率、帧率和帧数无失败，联系表未见 T-pose。该里程碑只批准本地代表矩阵及其自动化，不等于正式 640 节点、GT/sidecar、多轮链或服务器数据集验收。

## 2026-08-24：配置图兼容域与双策略多轮链规范冻结

- 正式首批节点收口为 `32 Looks × 5 同性动作 × near/far/high/side 四相机 × Happy = 640`。Angry/Sad 保留为已验证候选和历史本地证据，但退出首批正式节点清单；本批继续禁止 `E11`。
- 640 节点按性别划为 `female_v1/male_v1` 两个兼容域，各 320 节点且必须分别连通。禁止跨域边与跨域链，不再要求男女形成单一全局连通分量。
- 链分类由旧 `progressive/rollback/closed_cycle` 收口为 `progressive_shortest/freeform_walk` 两种生成策略，各 2,000 条。每条链另保存并重算最短、重复轴、连续同轴、回退和返回起点五个事实标签。
- 冻结精确 4,000 条配额：男女域各 2,000；progressive 每域 500 条 length-3 + 500 条 length-4；freeform female 为 334/333/333，male 为 333/333/334 的 length-3/4/5。四个编辑轴全局目标各 25%，全部 640 节点至少被链引用一次。
- 首批采用 `full_pool` 完整渲染 640 节点；未来大规模生产采用 `referenced_nodes_plus_connectivity`，只渲染链引用节点并补充域连通桥接节点。不要求任意节点对的图距离等于语义 Hamming 距离。
- 决定已写入 `ADR-0014`、Config Graph Schema V1、Sampling V1、Sprint、WF-08/09 和验证门禁。旧规范原文保存于 `history/pre_chain_contract_rewrite_2026-08-24`；现有配置图生成器明确标记为迁移基线，尚未宣称符合新契约。

## 2026-08-24：正式 640 节点配置图与 4,000 条双策略链机器门禁通过

- 新增 `build_first_batch_graph_source_v1.py`，把 32-Look 导出清单与本地渲染矩阵合并为 `first_batch_graph_source_20260824_v1.json`。源清单冻结真实 TokyoStylized staging map、四相机、角色 Blueprint、10 条 Happy composite 和 1440p30 MRQ 引用；Angry/Sad 不进入正式节点。
- `build_first_batch_config_graph_v1.py` 已完成双兼容域新契约迁移。正式构建报告 `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\build_report.json` 为 `passed`：37 assets、32 Looks、640 nodes、8,320 same-domain atomic edges、4,000 chains、640 render jobs。
- female/male 各 320 节点且各只有一个连通分量；跨域边和链为 0。链配额精确满足双策略、双域和 3/4/5 长度矩阵，E1/E2/E3/E7 各 3,750 次、各占 25%，640/640 节点被引用，重复路径为 0。
- 生成器从节点路径独立重算 `is_semantic_shortest`、`has_repeated_axis`、`has_consecutive_same_axis`、`has_rollback`、`returns_to_start`，不直接信任链记录。源清单与配置图自动测试共 10/10 通过，并覆盖确定性重建和旧契约拒绝。
- 新增 `build_first_batch_chain_review_v1.py`，固定生成男女各 5 条的 10 链语义审查包，并选出 2 条 UE 链级视觉候选。机器结构门禁已经关闭；UE 链级视觉、正式 GT/sidecar、640 节点媒体与服务器发布门禁仍未关闭。
- 两条 UE 候选链已完成本地 smoke。路径共 11 次节点引用，去重后只渲染 9 个唯一节点；9/9 输出 150 帧、2560×1440、30 fps、5 秒 Happy 视频，pose-driver、temporal-motion 和视频 SHA-256 全部通过，最低最大帧差为 41.177483。
- `validate_first_batch_chain_visual_smoke_v1.py` 生成按链顺序展开的 `chain_review.html`，重复节点复用同一媒体并以金色边框标识。assistant 联系表预检未见 T-pose、面部白块或新严重服装故障；用户视觉签字仍待完成，因此不宣称 `VIS-DATASET-01` 关闭。

## 2026-08-24：代表链视觉签字与首批多轮文本层通过

- 用户检查两条代表链的顺序视频后确认“没有问题”。独立决定文件 `OUTPUT_ROOT\unreal_render\first_batch_chain_visual_smoke_20260824_v1\user_visual_review_20260824_v1.json` 为 `accepted`，关闭代表链视觉子门禁；它不代表正式 640 节点、GT/sidecar 或最终数据集被接受。
- 新增 `MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`、`prompt_catalog_first_batch_v1.json` 和 `build_first_batch_prompt_layer_v1.py`，把旧 `chains.jsonl.instructions` 明确降为内部审计字段，模型输入改为独立版本化文本层。
- 正式文本证据位于 `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v1`。`prompt_report.json` 为 `passed`：4,000 dialogs、15,000 turns、E1/E2/E3/E7 各 3,750，所有回合原子、`zh-CN/en` 完整、内部 ID 泄漏为 0。
- 每轮同时生成依赖多轮历史的 `dialogue` 和可单轮使用的 `standalone`。196 个回合恢复初始状态，369 个回合恢复先前轮次；模板选择与 ID 由冻结输入确定，重复生成字节一致。
- E1 当前采用 `paired_target_video/class_only`：文本只要求替换为另一位同性人物，精确身份由配对目标视频约束。该限制写入 manifest；后续可增加人工外貌描述或参考图 grounding，但不得在首批中声称文本本身唯一确定身份。
