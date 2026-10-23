# CC角色创建统一自动化计划

> 文档 ID：`PLAN-2026-10-CC-CHARACTER-CREATION-AUTOMATION`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-30`；`WF-40/WF-50`仅后续交付边界，本轮不执行
> 完成条件：统一两入口及可恢复串行作业，一个代表全程实际跑通、另一入口最小接入验证，必要测试及文档同步；明确男女参数支持的实测范围
> 最近核验：2026-10-05（两入口机器代表完成、当前male完成跳过通过；归档16独立/跨层文档审计实际通过）

## 目标与边界

统一照片输入和`rawHeadshot.ccProject`输入：照片入口从对应男女CC5 Average SubD0 starter独立副本开始，以Headshot Current + Clean Soft生成；raw项目入口跳过照片生成，接入后续Average/固定头皮修正及必要烘焙。两者都复用已验精简基础外观装配，在独立路径保存基础人物，并记录照片/原项目、starter与参考、参数、随机配方、来源SHA、作业状态及恢复。

不重做身份研究，不修改正式男女参考或UE资产，不导出、不做UE导入或渲染，不装配头发/服装/表演动作。复用现有生成、修正、烘焙、装配模块，不建立一套平行实现。默认prepare-only，只有显式--execute提交当前CC，root统一串行驱动；子agents只做相互独立的代码/测试工作，不同时操作CC。

一个代表全程真实跑通及集中检查，另一入口只做最小真实接入验证；批量仅轻量失败检测、几何保护、日志和恢复，不逐角色重复全套人工/表情/细分验证。男女参数配置与资产支持按实测范围说明，代码或测试不能自动视为男女视觉接受。旧基础装配完成计划及证据保持，不重开。

## 需求落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| R01 | 两入口配置、starter/参考及源SHA绑定 | WF-30 | completed | photo/raw类型明确，sex、输入、参考和参数可追溯，原始项目不覆盖 | 两入口请求/源/starter/参考/实现SHA闭包已核验，creation_validation_summary_v1.json |
| R02 | photo入口复用SDK执行Current + Clean Soft | WF-30 | completed | 对应CC5 Average SubD0独立starter生效、生成结果保留来源；不需要重做路线研究 | PHOTO_FEMALE_001/attempt_002真实Current + Clean Soft照片全程；male照片SDK未实跑 |
| R03 | 参数化Average/固定头皮修正与必要烘焙 | WF-30 | completed | 两入口均可接入、gender参数准确；源/规范参考不改，必要几何结果可核对 | female photo与male raw最终numeric均通过，逐角色标定/目标/必要female lateBake回执保留 |
| R04 | 接入既有精简装配、R06及only眉毛颜色 | WF-30 | completed | 不重建已验装配，保留精确几何policy/颜色契约及牙齿口腔，基础人物独立保存 | 两代表各8项装配R06、眉毛only及保存通过；v1female8.2/v2male14原生704点规则，Skin .002不变 |
| R05 | 默认prepare-only与显式执行、串行durable作业及恢复 | WF-30 | completed | 同job pending续查不重提、failed新attempt、completed校验后跳过；配置/配方/源/结果可恢复 | 当前male attempt002 completed_resume_check_v1.json：禁止提交的advance及同请求CLI完成跳过，0新增/state SHA不变；旧版本漂移拒绝 |
| R06 | 代表完整实跑、另一入口最小接入、必要测试/文档 | WF-30 | completed | 实际一次端到端成功及集中审查，另一入口轻量验证；明确未验男性/全池/真实batch边界，必要回归与审计通过 | creation_validation_summary_v1.json集中读取两入口真实machine终态、源/结果SHA及622character/307必要测试；新人工/实际batch/UE不在范围 |

## 实现与输出所有者

新pipeline、Headshot runtime adapter、生成/修正编排及系统CLI统一由[BodyFit/Identity/Age11](../../../technical/character_creator/BODYFIT_IDENTITY_AGE.md#11-cc角色创建统一自动化2026-10-05)拥有。已经验证的外观编译、CC装配、capture/invariants和asset限定native-lash policy继续由[Assembly9](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)拥有；新pipeline调用它们，不重复取得实现所有权。

Run Root：`%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_character_creation_20261005_v1/`，归BodyFit11及`OUT-WF30-CC-ASSETS`。计划输出包括source/config与SHA、每阶段回执、独立中间/最终项目、装配配方、controller/attempt/job状态、失败恢复及必要代表/测试证据；并非Transfer Bundle。新代码入口已在限定两入口机器范围落实，生命周期validated_pilot；准确模块/CLI/字段/恢复归BodyFit11。真实女性photo/男性raw及当前male完成跳过证据已取得，不扩为本次新人工或实际batch接受。

## 停止与恢复

未知阻塞弹窗、必要部件或参数错误、生成/修正超限、保存失败时停止具体角色与阶段、保留失败attempt和原始输入。已完成项不重复整套验证；不由prepare成功写CC已运行，不由API成功写视觉接受。原规范项目和正式UE资产不覆盖，不自动重启CC或联网。

## 已完成交付与范围

R01–R06completed。女性照片入口PHOTO_FEMALE_001/attempt_002使用扩展男性policy前的冻结v1代码/规则，男性raw入口PROJECT_MALE_001/attempt_002使用当前v2完整tail；两者各8装配gate、最终几何和独立保存通过，原输入SHA保持。当前male完成恢复/跳过真实核验0新增提交，状态SHA不变；不能宣称当前代码可恢复哈希漂移的旧female完成attempt。

集中机器验收由creation_validation_summary_v1.json绑定实际两角色来源/结果、几何、装配及本轮622character_creator测试（含此前115针对性，不重复相加）和独立307必要回归。既有单女性装配人工/表情证据只作为复用模块范围，不宣称这两个新成品获得新的人工视觉接受；没有male照片入口、新female在当前v2完整实跑、全外观池、真实batch、导出/UE/渲染接受。

新脚本/solver/controller为validated_pilot，非production。失败male attempt001及诊断保留；v2只新增male原生704点具名14mm边界，female8.2/所有Skin .002不变。没有覆盖规范参考/正式UE，CC留在男性装配后独立项目，保持现有离线环境。

计划归档后显式idle_after_completed_plan/current_plan_id=null、零current。下一步等待用户选择/授权批量CC或独立导出/UE接入计划，不自动启动。Catalog/Inventory最终重建后，Run Root documentation_audit_final_v1.json实际16独立子系统及跨层全部通过，0错误/0警告；不把缺少新的逐角色人工验收当成当前交付仍未完成的必做任务。
