# Character Factory 文档递归提及树

> 文档角色：`generated_link_trace`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：从 Master 到现行文档及历史 Manifest 的行号级导航证明
> 上级入口：`CHARACTER_FACTORY_MASTER_SPEC.md`
> 上游：现行 Markdown 链接与历史 `ARCHIVE_MANIFEST.md`
> 下游：全部现行文档和不可变历史快照
> 最近核验：2026-08-24
> 生成器：`00_engine/scripts/documentation/generate_character_factory_link_trace.py`

## 1. 读取规则

- 根节点固定为 `CHARACTER_FACTORY_MASTER_SPEC.md`。
- 每个“直接入站提及”对应源 Markdown 中一次真实链接，保留源文件、行号、链接文字和用途原句。
- 为避免 `子文档 → Master → 子文档` 造成无限递归，每次提及展开其源文件的**全部最短根路径**；会返回已经出现节点的链标为“回链”并停止。
- 因此本报告完整登记所有直接链接及全部最短前缀，但不枚举人为绕行的非最短循环路径。
- 报告自身不创建 Markdown 导航链接，避免生成结果反过来改变被统计的链接图。
- 历史快照不具有当前元数据，通过 Manifest 的路径行和 SHA-256 管理，在末尾单列。

## 2. 可达性结论

- 现行文档：`62` 份。
- 从 Master 可达：`62` 份。
- 不可达：`0` 份。
- 指向现行文档的直接提及：`407` 次。

## (root)

### `CHARACTER_FACTORY_MASTER_SPEC.md`

- 定位：递归根节点。
- 直接入站提及：`28` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L14`，链接文字 `如何使用本文`。
   - 用途原句：1. 如何使用本文
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L14` → `CHARACTER_FACTORY_MASTER_SPEC.md#1-如何使用本文` **[回链，不继续递归]**
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L15`，链接文字 `目标与当前边界`。
   - 用途原句：2. 目标与当前边界
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L15` → `CHARACTER_FACTORY_MASTER_SPEC.md#2-目标与当前边界` **[回链，不继续递归]**
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L16`，链接文字 `从零到数据集的完整主线`。
   - 用途原句：3. 从零到数据集的完整主线
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L16` → `CHARACTER_FACTORY_MASTER_SPEC.md#3-从零到数据集的完整主线` **[回链，不继续递归]**
4. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L17`，链接文字 `十个生产阶段`。
   - 用途原句：4. 十个生产阶段
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L17` → `CHARACTER_FACTORY_MASTER_SPEC.md#4-十个生产阶段` **[回链，不继续递归]**
5. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L18`，链接文字 `验证在流程中的位置`。
   - 用途原句：5. 验证在流程中的位置
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L18` → `CHARACTER_FACTORY_MASTER_SPEC.md#5-验证在流程中的位置` **[回链，不继续递归]**
6. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L19`，链接文字 `日常生产与系统扩展`。
   - 用途原句：6. 日常生产与系统扩展
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L19` → `CHARACTER_FACTORY_MASTER_SPEC.md#6-日常生产与系统扩展` **[回链，不继续递归]**
7. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L20`，链接文字 `完整文档树`。
   - 用途原句：7. 完整文档树
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L20` → `CHARACTER_FACTORY_MASTER_SPEC.md#7-完整文档树` **[回链，不继续递归]**
8. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L21`，链接文字 `环境与外部目录`。
   - 用途原句：8. 环境与外部目录
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L21` → `CHARACTER_FACTORY_MASTER_SPEC.md#8-环境与外部目录` **[回链，不继续递归]**
9. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L22`，链接文字 `状态、计划、决定与历史`。
   - 用途原句：9. 状态、计划、决定与历史
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L22` → `CHARACTER_FACTORY_MASTER_SPEC.md#9-状态计划决定与历史` **[回链，不继续递归]**
10. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L23`，链接文字 `恢复一个新对话`。
   - 用途原句：10. 恢复一个新对话
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L23` → `CHARACTER_FACTORY_MASTER_SPEC.md#10-恢复一个新对话` **[回链，不继续递归]**
11. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L24`，链接文字 `维护规则`。
   - 用途原句：11. 维护规则
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L24` → `CHARACTER_FACTORY_MASTER_SPEC.md#11-维护规则` **[回链，不继续递归]**
12. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L193`，链接文字 `CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：| `CHARACTER_FACTORY_MASTER_SPEC.md` | 唯一跨系统总入口和完整生命周期 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L193` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
13. **元数据提及**：`README.md:L9`，链接文字 `CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 下游：`CHARACTER_FACTORY_MASTER_SPEC.md` 与日期化汇报入口
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L9` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L9` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
14. **正文提及**：`README.md:L12`，链接文字 `CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：从 `CHARACTER_FACTORY_MASTER_SPEC.md` 开始。它说明完整生命周期、当前边界、十个阶段、验证位置和全部子文档。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L12` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L12` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
15. **索引表提及**：`README.md:L18`，链接文字 `Master`。
   - 用途原句：| 第一次了解项目 | Master → Current Status |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L18` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L18` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
16. **元数据提及**：`CURRENT_STATUS.md:L7`，链接文字 `CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
17. **元数据提及**：`DOCUMENTATION_RULES.md:L7`，链接文字 `CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
18. **元数据提及**：`workflow/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
19. **元数据提及**：`cc_details/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
20. **元数据提及**：`bridge_details/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
21. **元数据提及**：`cc_ue_transfer/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
22. **元数据提及**：`ue_details/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
23. **元数据提及**：`validation/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
24. **元数据提及**：`planning/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
25. **元数据提及**：`decisions/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
26. **元数据提及**：`reference/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
27. **元数据提及**：`history/README.md:L7`，链接文字 `../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：> 上级入口：`../CHARACTER_FACTORY_MASTER_SPEC.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L7` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**
28. **正文提及**：`history/reports/README.md:L16`，链接文字 `../../CHARACTER_FACTORY_MASTER_SPEC.md`。
   - 用途原句：这些报告是日期化快照，用于汇报和追溯，不覆盖当前流程。最新状态始终以 `../../CURRENT_STATUS.md` 为准，执行入口始终以 `../../CHARACTER_FACTORY_MASTER_SPEC.md` 和 `WF-*` 为准。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L16` → `CHARACTER_FACTORY_MASTER_SPEC.md` **[回链，不继续递归]**

### `README.md`

- 定位：`README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **元数据提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L192`，链接文字 `README.md`。
   - 用途原句：| `README.md` | `full_process` 的短导航和 Master 跳转 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md`

### `CURRENT_STATUS.md`

- 定位：`CURRENT_STATUS.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`15` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L58`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：当前唯一活动计划是 第一批多轮编辑数据 Sprint：使用 F02/M02、8 个身份、同性各 4 套服装、32 个烘焙 Look、10 个生产动作（每个角色使用同性 5 个）、固定 Happy 表情、1 个场景和 `near/far/high/side` 四台生产相机，在服务器完整渲染 640 个唯一节点，并生成精确 4,000 条 3–5 轮编辑链及 15,000 回合双语 prompt。节点按 female/male 分成两个各 320 节点的连通兼容域；链按 `progressive_shortest/f…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L194`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：| `CURRENT_STATUS.md` | 当前能力、版本、限制和同步债务 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L269`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：- 当前能做什么：`CURRENT_STATUS.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md`
4. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L281`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：2. 阅读 `CURRENT_STATUS.md`，确认当前已验证边界和未完成项。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md`
5. **索引表提及**：`README.md:L18`，链接文字 `Current Status`。
   - 用途原句：| 第一次了解项目 | Master → Current Status |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L18` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L18` → `CURRENT_STATUS.md`
6. **元数据提及**：`workflow/README.md:L8`，链接文字 `../CURRENT_STATUS.md`。
   - 用途原句：> 上游：`../CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L8` → `CURRENT_STATUS.md`
7. **正文提及**：`cc_details/OUTFIT_PIPELINE.md:L587`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：当前状态与执行顺序分别见 `CURRENT_STATUS.md` 和 `ROADMAP.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L179` → `cc_details/OUTFIT_PIPELINE.md:L587` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L210` → `cc_details/OUTFIT_PIPELINE.md:L587` → `CURRENT_STATUS.md`
8. **正文提及**：`validation/VALIDATION_CATALOG.md:L291`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：- 范围边界：两条动作只是诊断负载，不得写入生产动画池。后续动画盘点、P0 动态 Gate 和 UE Pilot 已另行完成；当前可用边界以 `CURRENT_STATUS.md` 为准，剩余扩展归入 `RM-09R`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L291` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L291` → `CURRENT_STATUS.md`
9. **元数据提及**：`planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8`，链接文字 `../CURRENT_STATUS.md`。
   - 用途原句：> 上游：`../CURRENT_STATUS.md`、F02/M02 P0 UE Runtime Pilot 与用户确认的本轮范围
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L8` → `CURRENT_STATUS.md`
10. **元数据提及**：`planning/ROADMAP.md:L8`，链接文字 `../CURRENT_STATUS.md`。
   - 用途原句：> 上游：`../CURRENT_STATUS.md` 与已接受 ADR
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L184` → `planning/ROADMAP.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/ROADMAP.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L271` → `planning/ROADMAP.md:L8` → `CURRENT_STATUS.md`
11. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L381`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：`dm_asset_index.json` 已在线核对并升级为 version 4，登记模块化 v002/v003 相关入口与 F02/M02 FullReference P0 v001。仍存在的债务是旧模块验证器硬编码 v001、两个旧 UE wrapper 使用固定输出目录，以及哈希锁定候选注册表尚未通过新版本迁移吸收本次 P0 结果。完整债务见 `CURRENT_STATUS.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L381` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L381` → `CURRENT_STATUS.md`
12. **正文提及**：`history/reports/README.md:L16`，链接文字 `../../CURRENT_STATUS.md`。
   - 用途原句：这些报告是日期化快照，用于汇报和追溯，不覆盖当前流程。最新状态始终以 `../../CURRENT_STATUS.md` 为准，执行入口始终以 `../../CHARACTER_FACTORY_MASTER_SPEC.md` 和 `WF-*` 为准。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L16` → `CURRENT_STATUS.md`
13. **正文提及**：`history/MILESTONE_LOG.md:L13`，链接文字 `../CURRENT_STATUS.md`。
   - 用途原句：本文件只追加已经发生且有证据的事件。当前能力以 `../CURRENT_STATUS.md` 为准，未来工作以 `../planning/ROADMAP.md` 为准。修正旧条目时追加一条更正，不静默改写历史。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `history/MILESTONE_LOG.md:L13` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/MILESTONE_LOG.md:L13` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L274` → `history/MILESTONE_LOG.md:L13` → `CURRENT_STATUS.md`
14. **元数据提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8`，链接文字 `../../CURRENT_STATUS.md`。
   - 用途原句：> 上游：`../MILESTONE_LOG.md`、`../../CURRENT_STATUS.md` 与本周机器报告
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `CURRENT_STATUS.md`
15. **索引表提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121`，链接文字 `CURRENT_STATUS.md`。
   - 用途原句：| 当前权威状态 | `CURRENT_STATUS.md` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L121` → `CURRENT_STATUS.md`

### `DOCUMENTATION_RULES.md`

- 定位：`DOCUMENTATION_RULES.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L32`，链接文字 `DOCUMENTATION_RULES.md`。
   - 用途原句：发生冲突时遵循 `DOCUMENTATION_RULES.md`：代码决定实际执行，机器 JSON 决定精确 ID/路径/参数，Master 决定被接受的跨系统流程。冲突未解释前停止生产。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L195`，链接文字 `DOCUMENTATION_RULES.md`。
   - 用途原句：| `DOCUMENTATION_RULES.md` | 文档角色、状态、ID、命令所有权和维护规则 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L292`，链接文字 `DOCUMENTATION_RULES.md`。
   - 用途原句：旧入口只能跳转，不能保留第二套当前命令；计划页不得出现看似可运行的伪命令。详细规则见 `DOCUMENTATION_RULES.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md`

## workflow

### `README.md`

- 定位：`workflow/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`16` 次。

1. **元数据提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L9`，链接文字 `workflow/README.md`。
   - 用途原句：> 下游：`workflow/README.md` 及所有领域、验证和规划文档
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L91`，链接文字 `workflow/README.md`。
   - 用途原句：完整阶段导航见 `workflow/README.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L199`，链接文字 `workflow/README.md`。
   - 用途原句：`workflow/README.md` 解释唯一执行顺序；`WF-00` 至 `WF-09` 分别对应第 4 节十个阶段。生产命令和阶段交付只在这些 Runbook 中维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md`
4. **索引表提及**：`README.md:L19`，链接文字 `Workflow`。
   - 用途原句：| 实际生成一个角色 | Workflow，从 `WF-00` 开始 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L19` → `workflow/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L19` → `workflow/README.md`
5. **元数据提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L7` → `workflow/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L7` → `workflow/README.md`
6. **元数据提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L7` → `workflow/README.md`
7. **元数据提及**：`workflow/WF-02-CC-ASSEMBLY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L7` → `workflow/README.md`
8. **元数据提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L7` → `workflow/README.md`
9. **元数据提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L7` → `workflow/README.md`
10. **元数据提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L7` → `workflow/README.md`
11. **元数据提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L7` → `workflow/README.md`
12. **元数据提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L7` → `workflow/README.md`
13. **元数据提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L7` → `workflow/README.md`
14. **元数据提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L7` → `workflow/README.md`
15. **正文提及**：`cc_details/README.md:L12`，链接文字 `workflow/README.md`。
   - 用途原句：日常生产不从本目录拼接流程，应走 `workflow/README.md`。只有需要理解约束、诊断或扩展资产池时进入这里。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L12` → `workflow/README.md`
16. **元数据提及**：`validation/README.md:L8`，链接文字 `../workflow/README.md`。
   - 用途原句：> 上游：`../workflow/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L8` → `workflow/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L8` → `workflow/README.md`

### `WF-00-SESSION-PREFLIGHT.md`

- 定位：`workflow/WF-00-SESSION-PREFLIGHT.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`7` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L28`，链接文字 `WF-00`。
   - 用途原句：本文是唯一的人类可读总入口。第一次阅读先看第 2 至第 5 节；实际生产从 `WF-00` 开始，并只按 `WF-00 → ... → WF-09` 前进。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L99`，链接文字 `WF-00-SESSION-PREFLIGHT.md`。
   - 用途原句：执行：`WF-00-SESSION-PREFLIGHT.md`。Bridge 机制：`BRIDGE_OPERATIONS.md`。失败：`RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md`
3. **索引表提及**：`workflow/README.md:L20`，链接文字 `WF-00-SESSION-PREFLIGHT.md`。
   - 用途原句：| `WF-00` 会话预检 | `WF-00-SESSION-PREFLIGHT.md` | `GATE-00 SESSION_READY` | `validated_pilot` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L20` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L20` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L20` → `workflow/WF-00-SESSION-PREFLIGHT.md`
4. **元数据提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L8`，链接文字 `WF-00-SESSION-PREFLIGHT.md`。
   - 用途原句：> 上游：`WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L8` → `workflow/WF-00-SESSION-PREFLIGHT.md`
5. **正文提及**：`bridge_details/README.md:L12`，链接文字 `WF-00`。
   - 用途原句：`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、命令语义和 Undo 守卫。每次会话的实际健康检查从 `WF-00` 进入，准确命令由 `VAL-BRIDGE-01` 定义，失败按 `REC-BRIDGE-01` 恢复。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L12` → `workflow/WF-00-SESSION-PREFLIGHT.md`
6. **元数据提及**：`bridge_details/BRIDGE_OPERATIONS.md:L9`，链接文字 `WF-00`。
   - 用途原句：> 下游：`WF-00`、`WF-02`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-00-SESSION-PREFLIGHT.md`
7. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L34`，链接文字 `WF-00`。
   - 用途原句：阶段所有者：`WF-00`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L34` → `workflow/WF-00-SESSION-PREFLIGHT.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L34` → `workflow/WF-00-SESSION-PREFLIGHT.md`

### `WF-01-CHARACTER-DEFINITION.md`

- 定位：`workflow/WF-01-CHARACTER-DEFINITION.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`8` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L105`，链接文字 `WF-01-CHARACTER-DEFINITION.md`。
   - 用途原句：执行：`WF-01-CHARACTER-DEFINITION.md`。规则：`BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md`、`APPEARANCE_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md`
2. **索引表提及**：`workflow/README.md:L21`，链接文字 `WF-01-CHARACTER-DEFINITION.md`。
   - 用途原句：| `WF-01` 角色定义 | `WF-01-CHARACTER-DEFINITION.md` | `GATE-01 MANIFEST_READY` | `validated_pilot` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L21` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L21` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L21` → `workflow/WF-01-CHARACTER-DEFINITION.md`
3. **元数据提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L9`，链接文字 `WF-01-CHARACTER-DEFINITION.md`。
   - 用途原句：> 下游：`WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L9` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L9` → `workflow/WF-01-CHARACTER-DEFINITION.md`
4. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L66`，链接文字 `WF-01`。
   - 用途原句：Bridge 组件、安全边界和安装方法见 `BRIDGE_OPERATIONS.md`，外部路径见 `EXTERNAL_DIRECTORIES.md`。通过后进入 `WF-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `workflow/WF-01-CHARACTER-DEFINITION.md`
5. **元数据提及**：`workflow/WF-02-CC-ASSEMBLY.md:L8`，链接文字 `WF-01-CHARACTER-DEFINITION.md`。
   - 用途原句：> 上游：`WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L8` → `workflow/WF-01-CHARACTER-DEFINITION.md`
6. **元数据提及**：`cc_details/BODYFIT_PIPELINE.md:L9`，链接文字 `WF-01`。
   - 用途原句：> 下游：`WF-01`、`WF-02`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-01-CHARACTER-DEFINITION.md`
7. **正文提及**：`validation/VALIDATION_CATALOG.md:L67`，链接文字 `WF-01`。
   - 用途原句：- 输入：由 `WF-01` 生成的 `$manifest`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L67` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L67` → `workflow/WF-01-CHARACTER-DEFINITION.md`
8. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L56`，链接文字 `WF-01`。
   - 用途原句：阶段所有者：`WF-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L56` → `workflow/WF-01-CHARACTER-DEFINITION.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L56` → `workflow/WF-01-CHARACTER-DEFINITION.md`

### `WF-02-CC-ASSEMBLY.md`

- 定位：`workflow/WF-02-CC-ASSEMBLY.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`9` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L111`，链接文字 `WF-02-CC-ASSEMBLY.md`。
   - 用途原句：执行：`WF-02-CC-ASSEMBLY.md`。Bridge 安全边界：`BRIDGE_OPERATIONS.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md`
2. **索引表提及**：`workflow/README.md:L22`，链接文字 `WF-02-CC-ASSEMBLY.md`。
   - 用途原句：| `WF-02` CC 装配 | `WF-02-CC-ASSEMBLY.md` | `GATE-02 ASSEMBLY_COMPLETE` | `validated_pilot` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L22` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L22` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L22` → `workflow/WF-02-CC-ASSEMBLY.md`
3. **元数据提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L9`，链接文字 `WF-02-CC-ASSEMBLY.md`。
   - 用途原句：> 下游：`WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
4. **正文提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L92`，链接文字 `WF-02`。
   - 用途原句：BodyFit、Face 和外观规则分别见 `BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md` 和 `APPEARANCE_PIPELINE.md`。通过后进入 `WF-02`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L92` → `workflow/WF-02-CC-ASSEMBLY.md`
5. **元数据提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L8`，链接文字 `WF-02-CC-ASSEMBLY.md`。
   - 用途原句：> 上游：`WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L8` → `workflow/WF-02-CC-ASSEMBLY.md`
6. **元数据提及**：`cc_details/BODYFIT_PIPELINE.md:L9`，链接文字 `WF-02`。
   - 用途原句：> 下游：`WF-01`、`WF-02`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
7. **元数据提及**：`bridge_details/BRIDGE_OPERATIONS.md:L9`，链接文字 `WF-02`。
   - 用途原句：> 下游：`WF-00`、`WF-02`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `workflow/WF-02-CC-ASSEMBLY.md`
8. **正文提及**：`validation/VALIDATION_CATALOG.md:L118`，链接文字 `WF-02 第 6 节`。
   - 用途原句：- 产生样本的准确命令：`WF-02 第 6 节`；汇总命令：`WF-03 第 6 节`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L118` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L118` → `workflow/WF-02-CC-ASSEMBLY.md`
9. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L80`，链接文字 `WF-02`。
   - 用途原句：阶段所有者：`WF-02`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L80` → `workflow/WF-02-CC-ASSEMBLY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L80` → `workflow/WF-02-CC-ASSEMBLY.md`

### `WF-03-CC-ACCEPTANCE.md`

- 定位：`workflow/WF-03-CC-ACCEPTANCE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`7` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L117`，链接文字 `WF-03-CC-ACCEPTANCE.md`。
   - 用途原句：执行：`WF-03-CC-ACCEPTANCE.md`。人工判定：`VISUAL_ACCEPTANCE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md`
2. **索引表提及**：`workflow/README.md:L23`，链接文字 `WF-03-CC-ACCEPTANCE.md`。
   - 用途原句：| `WF-03` CC 验收 | `WF-03-CC-ACCEPTANCE.md` | `GATE-03 CC_ACCEPTED` | `validated_pilot` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L23` → `workflow/WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L23` → `workflow/WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L23` → `workflow/WF-03-CC-ACCEPTANCE.md`
3. **元数据提及**：`workflow/WF-02-CC-ASSEMBLY.md:L9`，链接文字 `WF-03-CC-ACCEPTANCE.md`。
   - 用途原句：> 下游：`WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L9` → `workflow/WF-03-CC-ACCEPTANCE.md`
4. **正文提及**：`workflow/WF-02-CC-ASSEMBLY.md:L62`，链接文字 `WF-03`。
   - 用途原句：Bridge 安全边界见 `BRIDGE_OPERATIONS.md`，组装域规则见 `cc_details/`。结构完成后进入 `WF-03`，不得跳过人工视觉验收。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L62` → `workflow/WF-03-CC-ACCEPTANCE.md`
5. **元数据提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L8`，链接文字 `WF-03-CC-ACCEPTANCE.md`。
   - 用途原句：> 上游：`WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L8` → `workflow/WF-03-CC-ACCEPTANCE.md`
6. **正文提及**：`validation/VALIDATION_CATALOG.md:L118`，链接文字 `WF-03 第 6 节`。
   - 用途原句：- 产生样本的准确命令：`WF-02 第 6 节`；汇总命令：`WF-03 第 6 节`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L118` → `workflow/WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L118` → `workflow/WF-03-CC-ACCEPTANCE.md`
7. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L103`，链接文字 `WF-03`。
   - 用途原句：普通编译器尚无通用保存开关。阶段所有者：`WF-03`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L103` → `workflow/WF-03-CC-ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L103` → `workflow/WF-03-CC-ACCEPTANCE.md`

### `WF-04-CC-EXPORT-BUNDLE.md`

- 定位：`workflow/WF-04-CC-EXPORT-BUNDLE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`7` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L123`，链接文字 `WF-04-CC-EXPORT-BUNDLE.md`。
   - 用途原句：执行：`WF-04-CC-EXPORT-BUNDLE.md`。追溯规则：`ASSET_TRACEABILITY.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
2. **索引表提及**：`workflow/README.md:L24`，链接文字 `WF-04-CC-EXPORT-BUNDLE.md`。
   - 用途原句：| `WF-04` CC 导出 | `WF-04-CC-EXPORT-BUNDLE.md` | `GATE-04 BUNDLE_READY` | `validated_pilot` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L24` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L24` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L24` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
3. **元数据提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L9`，链接文字 `WF-04-CC-EXPORT-BUNDLE.md`。
   - 用途原句：> 下游：`WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L9` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
4. **正文提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L68`，链接文字 `WF-04`。
   - 用途原句：视觉检查定义见 `VISUAL_ACCEPTANCE.md`，追溯字段见 `ASSET_TRACEABILITY.md`。只有 `GATE-03` 通过后才能进入 `WF-04`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L68` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
5. **元数据提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L8`，链接文字 `WF-04-CC-EXPORT-BUNDLE.md`。
   - 用途原句：> 上游：`WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L8` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
6. **正文提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L116`，链接文字 `WF-04`。
   - 用途原句：2. 按 `WF-04` 导出同 Skeleton 资产，并用 `WF-05` 建立完整参考。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
7. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L247`，链接文字 `WF-04`。
   - 用途原句：当前已有首批 FullReference 的受控自动装配/导出路径；通用 Motion/任意角色导出仍依赖 CC UI 与资产状态。阶段所有者：`WF-04`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L247` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L247` → `workflow/WF-04-CC-EXPORT-BUNDLE.md`

### `WF-05-UE-IMPORT-REFERENCE.md`

- 定位：`workflow/WF-05-UE-IMPORT-REFERENCE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`10` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L129`，链接文字 `WF-05-UE-IMPORT-REFERENCE.md`。
   - 用途原句：执行：`WF-05-UE-IMPORT-REFERENCE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
2. **索引表提及**：`workflow/README.md:L25`，链接文字 `WF-05-UE-IMPORT-REFERENCE.md`。
   - 用途原句：| `WF-05` UE 参考导入 | `WF-05-UE-IMPORT-REFERENCE.md` | `GATE-05 UE_REFERENCE_ACCEPTED` | `first_batch_validated`，32/32 FullReference Look |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L25` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L25` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L25` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
3. **元数据提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L9`，链接文字 `WF-05-UE-IMPORT-REFERENCE.md`。
   - 用途原句：> 下游：`WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
4. **正文提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L75`，链接文字 `WF-05`。
   - 用途原句：追溯 schema 见 `ASSET_TRACEABILITY.md`，外部目录职责见 `EXTERNAL_DIRECTORIES.md`。通过后关闭或保留 CC 由资源情况决定，并进入 `WF-05`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L75` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
5. **元数据提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L8`，链接文字 `WF-05-UE-IMPORT-REFERENCE.md`。
   - 用途原句：> 上游：`WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L8` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
6. **正文提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L116`，链接文字 `WF-05`。
   - 用途原句：2. 按 `WF-04` 导出同 Skeleton 资产，并用 `WF-05` 建立完整参考。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L116` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
7. **正文提及**：`validation/VALIDATION_CATALOG.md:L321`，链接文字 `WF-05 第 6 节`。
   - 用途原句：- 准确导入步骤：`WF-05 第 6 节`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L321` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L321` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
8. **元数据提及**：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9`，链接文字 `../workflow/WF-05-UE-IMPORT-REFERENCE.md`。
   - 用途原句：> 下游：`../workflow/WF-05-UE-IMPORT-REFERENCE.md`、`../workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
9. **正文提及**：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115`，链接文字 `WF-05`。
   - 用途原句：使用 Reallusion Auto Setup 的 High Quality 流程，并保留同名 `.json` 与 `.fbm/` 在 FBX 旁。当前自动入口、三项小批次限制、同权限窗口守卫和崩溃恢复以 `WF-05` 为准；本节只保留手工回退。最终机器门禁为 32/32，不再需要重复导入。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L115` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
10. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L261`，链接文字 `WF-05`。
   - 用途原句：既有 M02 Pilot 首次导入由 UE UI 完成；P0 F02/M02 参考角色由 `ue_import_p0_runtime_pilot.py` 执行原始导入，并由用户在 Content Browser 运行 Reallusion Auto Setup 后进行严格后验收。首批 32 Look 使用 `run_first_batch_full_reference_import.py --expanded-matrix` 外层编排、精确窗口守卫和 `ue_import_first_batch_full_ref…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L261` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L261` → `workflow/WF-05-UE-IMPORT-REFERENCE.md`

### `WF-06-UE-CHARACTER-RUNTIME.md`

- 定位：`workflow/WF-06-UE-CHARACTER-RUNTIME.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L135`，链接文字 `WF-06-UE-CHARACTER-RUNTIME.md`。
   - 用途原句：执行：`WF-06-UE-CHARACTER-RUNTIME.md`。组件契约：`MODULAR_CHARACTER_RUNTIME.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
2. **索引表提及**：`workflow/README.md:L26`，链接文字 `WF-06-UE-CHARACTER-RUNTIME.md`。
   - 用途原句：| `WF-06` UE 角色运行时 | `WF-06-UE-CHARACTER-RUNTIME.md` | `GATE-06 RUNTIME_ACCEPTED` | `validated_pilot`，仅 M02 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L26` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L26` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L26` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
3. **元数据提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L9`，链接文字 `WF-06`。
   - 用途原句：> 下游：当前 Sprint 进入 `WF-08`；模块化研究进入 `WF-06`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L9` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
4. **正文提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L151`，链接文字 `WF-06`。
   - 用途原句：当前 Sprint 的 FullReference 基线已经完成，进入 `WF-08` 固定场景、角色锚点、相机和 Sequence。通用模块化角色研究仍由 `WF-06` 管理，不作为本批数据的前置条件。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L151` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
5. **元数据提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L8`，链接文字 `WF-06-UE-CHARACTER-RUNTIME.md`。
   - 用途原句：> 上游：`WF-06-UE-CHARACTER-RUNTIME.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L8` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
6. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L276`，链接文字 `WF-06`。
   - 用途原句：上述构建脚本硬编码 M02；其他体型不可复用。阶段所有者：`WF-06`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L276` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L276` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md`

### `WF-07-ANIMATION-AND-PROPS.md`

- 定位：`workflow/WF-07-ANIMATION-AND-PROPS.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`10` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L141`，链接文字 `WF-07-ANIMATION-AND-PROPS.md`。
   - 用途原句：执行：`WF-07-ANIMATION-AND-PROPS.md`。技术规则：`ANIMATION_AND_MORPH_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
2. **索引表提及**：`workflow/README.md:L27`，链接文字 `WF-07-ANIMATION-AND-PROPS.md`。
   - 用途原句：| `WF-07` 动画与道具 | `WF-07-ANIMATION-AND-PROPS.md` | `GATE-07 PERFORMANCE_ACCEPTED` | `validated_pilot`，无道具 P0 Runtime 已通过；生产池未完成 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L27` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L27` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L27` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
3. **元数据提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L9`，链接文字 `WF-07-ANIMATION-AND-PROPS.md`。
   - 用途原句：> 下游：`WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
4. **正文提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L65`，链接文字 `WF-07`。
   - 用途原句：组件契约、Morph 支持集合和变体边界由 `MODULAR_CHARACTER_RUNTIME.md` 定义。通过后进入 `WF-07`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L65` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
5. **元数据提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L8`，链接文字 `WF-07-ANIMATION-AND-PROPS.md`。
   - 用途原句：> 上游：`WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L8` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
6. **正文提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46`，链接文字 `WF-07`。
   - 用途原句：构建脚本用于维护现有 Pilot，不代表已经存在‘输入任意动画即可生成生产资产’的通用 API。正常组合顺序见 `WF-07`，准确验证命令见 `VALIDATION_CATALOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
7. **元数据提及**：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9`，链接文字 `../workflow/WF-07-ANIMATION-AND-PROPS.md`。
   - 用途原句：> 下游：`../workflow/WF-05-UE-IMPORT-REFERENCE.md`、`../workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L9` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
8. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L236`，链接文字 `WF-07`。
   - 用途原句：包级分类与静态文件名提示都不能替代逐条动作的 CC 播放、时长、循环、Root Motion、面部通道、隐藏依赖和动态质量门禁。剩余扩展见 `ROADMAP.md` 的 `RM-09R`，运行时组合规则见 `WF-07`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L236` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L236` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
9. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L298`，链接文字 `WF-07`。
   - 用途原句：生产动画源包已完成 P0-P3 包级整理，但逐条生产动画注册表、服装正式动态、三发型和道具仍没有完整实现文件。阶段所有者：`WF-07`；资产池开发状态见本页‘动画源发现与生产池开发’。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L298` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L298` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
10. **正文提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69`，链接文字 `WF-07`。
   - 用途原句：详细执行逻辑见 `WF-07` 和 `ANIMATION_AND_MORPH_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `workflow/WF-07-ANIMATION-AND-PROPS.md`

### `WF-08-SCENE-CAMERA-SEQUENCE.md`

- 定位：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`8` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L147`，链接文字 `WF-08-SCENE-CAMERA-SEQUENCE.md`。
   - 用途原句：阶段契约：`WF-08-SCENE-CAMERA-SEQUENCE.md`。当前范围：`FIRST_DATA_BATCH_SPRINT`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
2. **索引表提及**：`workflow/README.md:L28`，链接文字 `WF-08-SCENE-CAMERA-SEQUENCE.md`。
   - 用途原句：| `WF-08` 场景与相机 | `WF-08-SCENE-CAMERA-SEQUENCE.md` | `GATE-08 SCENE_READY` | `first_batch_local_matrix_validated`，30 个生产组合与 32-Look 四机位代表矩阵已通过 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L28` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L28` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L28` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
3. **元数据提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L9`，链接文字 `WF-08`。
   - 用途原句：> 下游：当前 Sprint 进入 `WF-08`；模块化研究进入 `WF-06`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L9` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
4. **正文提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L151`，链接文字 `WF-08`。
   - 用途原句：当前 Sprint 的 FullReference 基线已经完成，进入 `WF-08` 固定场景、角色锚点、相机和 Sequence。通用模块化角色研究仍由 `WF-06` 管理，不作为本批数据的前置条件。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L151` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
5. **元数据提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L9`，链接文字 `WF-08-SCENE-CAMERA-SEQUENCE.md`。
   - 用途原句：> 下游：`WF-08-SCENE-CAMERA-SEQUENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L9` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
6. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L130`，链接文字 `WF-08`。
   - 用途原句：通道分类和现有资产见 `ANIMATION_AND_MORPH_PIPELINE.md`，包级整理实现与证据见 `IMPLEMENTATION_INDEX.md` 的‘动画源发现与生产池开发’，Sprint 之后的动画池扩展见 `ROADMAP.md` 的 `RM-09R`。服装和变体边界见 `MODULAR_CHARACTER_RUNTIME.md`。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 `WF-08`，但其 Gate 通过前仍为 `planned`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L130` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
7. **元数据提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L8`，链接文字 `WF-08-SCENE-CAMERA-SEQUENCE.md`。
   - 用途原句：> 上游：`WF-08-SCENE-CAMERA-SEQUENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L8` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
8. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L321`，链接文字 `WF-08`。
   - 用途原句：F03、F04、M02、M03 四条短动作和历史 36 条组合资产已经完成；生产池排除 F04/M03 后，有效短动作是 F03/M02，有效组合是 30 条。源身体与表情资产保持分离，组合 AnimSequence 只是 Sequencer 的可重建交付缓存。参数化 5 秒 Sequence 和 32-Look 代表矩阵已通过；真实 scene/camera/Blueprint 稳定引用现已写入正式源清单。后续继续记录服装兼容性警告。阶段所有者：`WF-08`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L321` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L321` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md`

### `WF-09-RENDER-DATASET-PACKAGE.md`

- 定位：`workflow/WF-09-RENDER-DATASET-PACKAGE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`7` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L153`，链接文字 `WF-09-RENDER-DATASET-PACKAGE.md`。
   - 用途原句：阶段契约：`WF-09-RENDER-DATASET-PACKAGE.md`。数据契约：`CONFIG_GRAPH_SCHEMA_V1.md`、`MULTI_ROUND_CHAIN_SAMPLING_V1.md` 与 `MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
2. **索引表提及**：`CURRENT_STATUS.md:L109`，链接文字 `WF-09 Render Dataset Package`。
   - 用途原句：| 本地 32 视频怎么一键复现 | WF-09 Render Dataset Package |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L109` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L109` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L109` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L109` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
3. **正文提及**：`CURRENT_STATUS.md:L115`，链接文字 `WF-09`。
   - 用途原句：继续 `WF-09`：把现有执行器提升为按 `render_jobs.jsonl` 驱动的正式节点执行器，补齐 GT/sidecar、node_id 重试、媒体/配置哈希和文本回合媒体解析，再执行服务器预检、项目 smoke 与 10 节点性能基准。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L115` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L115` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L115` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L115` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
4. **索引表提及**：`workflow/README.md:L29`，链接文字 `WF-09-RENDER-DATASET-PACKAGE.md`。
   - 用途原句：| `WF-09` 渲染数据包 | `WF-09-RENDER-DATASET-PACKAGE.md` | `GATE-09 DATASET_ACCEPTED` | `in_progress`，图/链/15,000 回合文本层与代表链已通过；正式 640 节点媒体未验收 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L29` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L29` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L29` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
5. **元数据提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L9`，链接文字 `WF-09-RENDER-DATASET-PACKAGE.md`。
   - 用途原句：> 下游：`WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L9` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
6. **正文提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100`，链接文字 `WF-09`。
   - 用途原句：UE 资产边界见 `ADR-0007`，当前任务见 第一批数据 Sprint。本阶段实现并通过后进入 `WF-09`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`
7. **元数据提及**：`decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md:L9`，链接文字 `../workflow/WF-09-RENDER-DATASET-PACKAGE.md`。
   - 用途原句：> 下游：`CONFIG_GRAPH_SCHEMA_V1.md`、`MULTI_ROUND_CHAIN_SAMPLING_V1.md`、`../workflow/WF-09-RENDER-DATASET-PACKAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md:L9` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md`

## cc_details

### `README.md`

- 定位：`cc_details/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L205`，链接文字 `README.md`。
   - 用途原句：| `README.md` | CC 领域索引及进入时机 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md`
2. **元数据提及**：`cc_details/APPEARANCE_PIPELINE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md:L7` → `cc_details/README.md`
3. **元数据提及**：`cc_details/BODYFIT_PIPELINE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L7` → `cc_details/README.md`
4. **元数据提及**：`cc_details/FACE_IDENTITY_AND_AGE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md:L7` → `cc_details/README.md`
5. **元数据提及**：`cc_details/HEADSHOT_PIPELINE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md:L7` → `cc_details/README.md`
6. **元数据提及**：`cc_details/OUTFIT_PIPELINE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L179` → `cc_details/OUTFIT_PIPELINE.md:L7` → `cc_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L210` → `cc_details/OUTFIT_PIPELINE.md:L7` → `cc_details/README.md`

### `APPEARANCE_PIPELINE.md`

- 定位：`cc_details/APPEARANCE_PIPELINE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L105`，链接文字 `APPEARANCE_PIPELINE.md`。
   - 用途原句：执行：`WF-01-CHARACTER-DEFINITION.md`。规则：`BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md`、`APPEARANCE_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L178`，链接文字 `APPEARANCE_PIPELINE.md`。
   - 用途原句：| 新增皮肤、眼睛、毛发 | `APPEARANCE_PIPELINE.md` | 域兼容矩阵和 `VIS-CC-*` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md`
3. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L209`，链接文字 `APPEARANCE_PIPELINE.md`。
   - 用途原句：| `APPEARANCE_PIPELINE.md` | 皮肤、眼睛、牙齿、眉睫、胡须、头发、色素和材质规则 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md`
4. **正文提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L92`，链接文字 `APPEARANCE_PIPELINE.md`。
   - 用途原句：BodyFit、Face 和外观规则分别见 `BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md` 和 `APPEARANCE_PIPELINE.md`。通过后进入 `WF-02`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L92` → `cc_details/APPEARANCE_PIPELINE.md`
5. **索引表提及**：`cc_details/README.md:L19`，链接文字 `APPEARANCE_PIPELINE.md`。
   - 用途原句：| `APPEARANCE_PIPELINE.md` | 修改皮肤、眼睛、牙齿、眉睫、胡须、头发或材质 | 审核池、应用顺序、兼容性、色素和质量档案 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L19` → `cc_details/APPEARANCE_PIPELINE.md`

### `BODYFIT_PIPELINE.md`

- 定位：`cc_details/BODYFIT_PIPELINE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L105`，链接文字 `BODYFIT_PIPELINE.md`。
   - 用途原句：执行：`WF-01-CHARACTER-DEFINITION.md`。规则：`BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md`、`APPEARANCE_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L175`，链接文字 `BODYFIT_PIPELINE.md`。
   - 用途原句：| 新增/修改 BodyFit | `BODYFIT_PIPELINE.md` | `VAL-CODE-01`、`VAL-CC-01`，随后重验受影响角色 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md`
3. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L206`，链接文字 `BODYFIT_PIPELINE.md`。
   - 用途原句：| `BODYFIT_PIPELINE.md` | 十个 BodyFit、哈希、比例和身体不变量 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md`
4. **正文提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L92`，链接文字 `BODYFIT_PIPELINE.md`。
   - 用途原句：BodyFit、Face 和外观规则分别见 `BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md` 和 `APPEARANCE_PIPELINE.md`。通过后进入 `WF-02`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L92` → `cc_details/BODYFIT_PIPELINE.md`
5. **索引表提及**：`cc_details/README.md:L16`，链接文字 `BODYFIT_PIPELINE.md`。
   - 用途原句：| `BODYFIT_PIPELINE.md` | 选择、修改或新增 BodyFit | 十体型、源哈希、Head/Neck 比例和身体不变量 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L16` → `cc_details/BODYFIT_PIPELINE.md`

### `FACE_IDENTITY_AND_AGE.md`

- 定位：`cc_details/FACE_IDENTITY_AND_AGE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L105`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：执行：`WF-01-CHARACTER-DEFINITION.md`。规则：`BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md`、`APPEARANCE_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L176`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：| 新增 Face seed/recipe/年龄 | `FACE_IDENTITY_AND_AGE.md` | Face/眼口动态验证与 `WF-01..03` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md`
3. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L207`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：| `FACE_IDENTITY_AND_AGE.md` | Face V3、Facial Profile、局部 Morph、年龄和 Headshot 边界 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md`
4. **正文提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L92`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：BodyFit、Face 和外观规则分别见 `BODYFIT_PIPELINE.md`、`FACE_IDENTITY_AND_AGE.md` 和 `APPEARANCE_PIPELINE.md`。通过后进入 `WF-02`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L92` → `cc_details/FACE_IDENTITY_AND_AGE.md`
5. **索引表提及**：`cc_details/README.md:L17`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：| `FACE_IDENTITY_AND_AGE.md` | 生成/修改脸、年龄或 Headshot | Face V3、Facial Profile、局部 Morph 和年龄边界 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L17` → `cc_details/FACE_IDENTITY_AND_AGE.md`
6. **元数据提及**：`cc_details/HEADSHOT_PIPELINE.md:L9`，链接文字 `FACE_IDENTITY_AND_AGE.md`。
   - 用途原句：> 下游：`FACE_IDENTITY_AND_AGE.md`、`../validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md:L9` → `cc_details/FACE_IDENTITY_AND_AGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md:L9` → `cc_details/FACE_IDENTITY_AND_AGE.md`

### `HEADSHOT_PIPELINE.md`

- 定位：`cc_details/HEADSHOT_PIPELINE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L177`，链接文字 `HEADSHOT_PIPELINE.md`。
   - 用途原句：| 新增 Headshot 原型 | `HEADSHOT_PIPELINE.md` | `VAL-CC-03/04/05`、`VIS-CC-04`；接入前验证 project-seed 装配 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L208`，链接文字 `HEADSHOT_PIPELINE.md`。
   - 用途原句：| `HEADSHOT_PIPELINE.md` | Headshot 输入、原始项目冻结、CC5 Profile 晋级、原型包与 project-seed 接入契约 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md`
3. **索引表提及**：`cc_details/README.md:L18`，链接文字 `HEADSHOT_PIPELINE.md`。
   - 用途原句：| `HEADSHOT_PIPELINE.md` | 生成、检查、保存或晋级 Headshot 身份原型 | 输入冻结、CC5 Profile 门禁、规范原型包、哈希和 project-seed 接入契约 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L18` → `cc_details/HEADSHOT_PIPELINE.md`
4. **正文提及**：`cc_details/FACE_IDENTITY_AND_AGE.md:L115`，链接文字 `HEADSHOT_PIPELINE.md`。
   - 用途原句：`F_HS_001/002`、`M_HS_001/002` 状态为 `candidate_cc5_hd_rm05b_visual_accepted`；`F_HS_003..005`、`M_HS_003..005` 为机器通过、原照片已映射、等待人工视觉验收的候选。`headshot_project_seed_then_bodyfit_v1` 已在 F02/M02 上取得机器与用户 Pilot 通过；本轮只完成十原型候选池闭环和暂存，不做 10/20 比较，也不进入当前生产 seed 池。扩容、`RM-06` 配方…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `cc_details/HEADSHOT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `cc_details/HEADSHOT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `cc_details/HEADSHOT_PIPELINE.md`
5. **正文提及**：`validation/VALIDATION_CATALOG.md:L159`，链接文字 `HEADSHOT_PIPELINE.md`。
   - 用途原句：- 失败去向：`REC-CC-01`、`REC-DIALOG-01`，或回到 `HEADSHOT_PIPELINE.md` 的派生副本修正流程。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L159` → `cc_details/HEADSHOT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L159` → `cc_details/HEADSHOT_PIPELINE.md`
6. **元数据提及**：`decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md:L9`，链接文字 `../cc_details/HEADSHOT_PIPELINE.md`。
   - 用途原句：> 下游：`../cc_details/HEADSHOT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md:L9` → `cc_details/HEADSHOT_PIPELINE.md`

### `OUTFIT_PIPELINE.md`

- 定位：`cc_details/OUTFIT_PIPELINE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L179`，链接文字 `OUTFIT_PIPELINE.md`。
   - 用途原句：| 新增服装来源或 Look | `OUTFIT_PIPELINE.md` | `VAL-CC-06` 源盘点，随后平均体型静态/动态和十体型兼容验证 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L179` → `cc_details/OUTFIT_PIPELINE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L210`，链接文字 `OUTFIT_PIPELINE.md`。
   - 用途原句：| `OUTFIT_PIPELINE.md` | 服装源包、Look、替换组、层级互斥、十体型兼容和 UE 切换规则 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L210` → `cc_details/OUTFIT_PIPELINE.md`
3. **索引表提及**：`cc_details/README.md:L20`，链接文字 `OUTFIT_PIPELINE.md`。
   - 用途原句：| `OUTFIT_PIPELINE.md` | 盘点、筛选、适配或导出服装 | Source package、Look、层级互斥、十体型矩阵和 UE 切换边界 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L205` → `cc_details/README.md:L20` → `cc_details/OUTFIT_PIPELINE.md`
4. **正文提及**：`cc_details/APPEARANCE_PIPELINE.md:L195`，链接文字 `OUTFIT_PIPELINE.md`。
   - 用途原句：服装不等同于面部外观池。源盘点、Look、层级互斥、十体型网格、动作穿模和 UE 切换统一由 `OUTFIT_PIPELINE.md` 管理；不得在本文件扩写成无约束随机换装。未完成部分归入 Roadmap 的 `RM-08R`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md:L195` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md:L195` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md:L195` → `cc_details/OUTFIT_PIPELINE.md`
5. **正文提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45`，链接文字 `OUTFIT_PIPELINE.md`。
   - 用途原句：技术规则见 `OUTFIT_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L45` → `cc_details/OUTFIT_PIPELINE.md`

## bridge_details

### `README.md`

- 定位：`bridge_details/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L214`，链接文字 `README.md`。
   - 用途原句：`README.md` 是 Bridge 索引；`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、Undo 守卫和内部恢复边界。每日健康检查由 `WF-00` 调用。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md`
2. **元数据提及**：`bridge_details/BRIDGE_OPERATIONS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L7` → `bridge_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L7` → `bridge_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L7` → `bridge_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L7` → `bridge_details/README.md`

### `BRIDGE_OPERATIONS.md`

- 定位：`bridge_details/BRIDGE_OPERATIONS.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`8` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L99`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：执行：`WF-00-SESSION-PREFLIGHT.md`。Bridge 机制：`BRIDGE_OPERATIONS.md`。失败：`RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L111`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：执行：`WF-02-CC-ASSEMBLY.md`。Bridge 安全边界：`BRIDGE_OPERATIONS.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md`
3. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L180`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：| 修改 Bridge/API | `BRIDGE_OPERATIONS.md` | `VAL-CODE-01`、`VAL-BRIDGE-01` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md`
4. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L214`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：`README.md` 是 Bridge 索引；`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、Undo 守卫和内部恢复边界。每日健康检查由 `WF-00` 调用。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md`
5. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L66`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：Bridge 组件、安全边界和安装方法见 `BRIDGE_OPERATIONS.md`，外部路径见 `EXTERNAL_DIRECTORIES.md`。通过后进入 `WF-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `bridge_details/BRIDGE_OPERATIONS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `bridge_details/BRIDGE_OPERATIONS.md`
6. **正文提及**：`workflow/WF-02-CC-ASSEMBLY.md:L62`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：Bridge 安全边界见 `BRIDGE_OPERATIONS.md`，组装域规则见 `cc_details/`。结构完成后进入 `WF-03`，不得跳过人工视觉验收。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L62` → `bridge_details/BRIDGE_OPERATIONS.md`
7. **元数据提及**：`bridge_details/README.md:L9`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：> 下游：`BRIDGE_OPERATIONS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L9` → `bridge_details/BRIDGE_OPERATIONS.md`
8. **正文提及**：`bridge_details/README.md:L12`，链接文字 `BRIDGE_OPERATIONS.md`。
   - 用途原句：`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、命令语义和 Undo 守卫。每次会话的实际健康检查从 `WF-00` 进入，准确命令由 `VAL-BRIDGE-01` 定义，失败按 `REC-BRIDGE-01` 恢复。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L12` → `bridge_details/BRIDGE_OPERATIONS.md`

## cc_ue_transfer

### `README.md`

- 定位：`cc_ue_transfer/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L218`，链接文字 `README.md`。
   - 用途原句：`README.md` 是传输索引；`ASSET_TRACEABILITY.md` 定义来源映射；实际导出和导入分别由 `WF-04/05` 维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/README.md`
2. **元数据提及**：`cc_ue_transfer/ASSET_TRACEABILITY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `cc_ue_transfer/ASSET_TRACEABILITY.md:L7` → `cc_ue_transfer/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/ASSET_TRACEABILITY.md:L7` → `cc_ue_transfer/README.md`

### `ASSET_TRACEABILITY.md`

- 定位：`cc_ue_transfer/ASSET_TRACEABILITY.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L123`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：执行：`WF-04-CC-EXPORT-BUNDLE.md`。追溯规则：`ASSET_TRACEABILITY.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `cc_ue_transfer/ASSET_TRACEABILITY.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L218`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：`README.md` 是传输索引；`ASSET_TRACEABILITY.md` 定义来源映射；实际导出和导入分别由 `WF-04/05` 维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/ASSET_TRACEABILITY.md`
3. **正文提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L68`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：视觉检查定义见 `VISUAL_ACCEPTANCE.md`，追溯字段见 `ASSET_TRACEABILITY.md`。只有 `GATE-03` 通过后才能进入 `WF-04`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L68` → `cc_ue_transfer/ASSET_TRACEABILITY.md`
4. **正文提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L75`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：追溯 schema 见 `ASSET_TRACEABILITY.md`，外部目录职责见 `EXTERNAL_DIRECTORIES.md`。通过后关闭或保留 CC 由资源情况决定，并进入 `WF-05`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L75` → `cc_ue_transfer/ASSET_TRACEABILITY.md`
5. **正文提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L153`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：Vendor/DataMake 与追溯规则见 `ASSET_TRACEABILITY.md` 和 `ADR-0007`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L153` → `cc_ue_transfer/ASSET_TRACEABILITY.md`
6. **索引表提及**：`cc_ue_transfer/README.md:L14`，链接文字 `ASSET_TRACEABILITY.md`。
   - 用途原句：| `ASSET_TRACEABILITY.md` | CC 源、Manifest、Bundle、Vendor、DataMake 和证据的身份映射 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/README.md:L14` → `cc_ue_transfer/ASSET_TRACEABILITY.md`

## ue_details

### `README.md`

- 定位：`ue_details/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L222`，链接文字 `README.md`。
   - 用途原句：`README.md` 是 UE 领域索引；`MODULAR_CHARACTER_RUNTIME.md` 定义组件/Leader/Morph/变体契约；`ANIMATION_AND_MORPH_PIPELINE.md` 定义动画通道、复用政策和 Elder 边界。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/README.md`
2. **元数据提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L8`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L8` → `ue_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L8` → `ue_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L8` → `ue_details/README.md`
3. **元数据提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L8`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L8` → `ue_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L8` → `ue_details/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L8` → `ue_details/README.md`

### `ANIMATION_AND_MORPH_PIPELINE.md`

- 定位：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L141`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：执行：`WF-07-ANIMATION-AND-PROPS.md`。技术规则：`ANIMATION_AND_MORPH_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L182`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：| 新增动画/年龄 Morph | `ANIMATION_AND_MORPH_PIPELINE.md` | `VAL-UE-02/03`、`VIS-UE-02` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L222`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：`README.md` 是 UE 领域索引；`MODULAR_CHARACTER_RUNTIME.md` 定义组件/Leader/Morph/变体契约；`ANIMATION_AND_MORPH_PIPELINE.md` 定义动画通道、复用政策和 Elder 边界。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
4. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L130`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：通道分类和现有资产见 `ANIMATION_AND_MORPH_PIPELINE.md`，包级整理实现与证据见 `IMPLEMENTATION_INDEX.md` 的‘动画源发现与生产池开发’，Sprint 之后的动画池扩展见 `ROADMAP.md` 的 `RM-09R`。服装和变体边界见 `MODULAR_CHARACTER_RUNTIME.md`。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 `WF-08`，但其 Gate 通过前仍为 `planned`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L130` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
5. **索引表提及**：`ue_details/README.md:L15`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：| `ANIMATION_AND_MORPH_PIPELINE.md` | `WF-07` 分类或组合动画/年龄 | 身体与面部通道、复用政策、v003 和 Elder 边界 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/README.md:L15` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
6. **正文提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69`，链接文字 `ANIMATION_AND_MORPH_PIPELINE.md`。
   - 用途原句：详细执行逻辑见 `WF-07` 和 `ANIMATION_AND_MORPH_PIPELINE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L69` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md`

### `MODULAR_CHARACTER_RUNTIME.md`

- 定位：`ue_details/MODULAR_CHARACTER_RUNTIME.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L135`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：执行：`WF-06-UE-CHARACTER-RUNTIME.md`。组件契约：`MODULAR_CHARACTER_RUNTIME.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`
2. **索引表提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L181`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：| 新增模块槽位/变体 | `MODULAR_CHARACTER_RUNTIME.md` | `VAL-UE-01`、`VIS-UE-01` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L222`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：`README.md` 是 UE 领域索引；`MODULAR_CHARACTER_RUNTIME.md` 定义组件/Leader/Morph/变体契约；`ANIMATION_AND_MORPH_PIPELINE.md` 定义动画通道、复用政策和 Elder 边界。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`
4. **正文提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L65`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：组件契约、Morph 支持集合和变体边界由 `MODULAR_CHARACTER_RUNTIME.md` 定义。通过后进入 `WF-07`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L65` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`
5. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L130`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：通道分类和现有资产见 `ANIMATION_AND_MORPH_PIPELINE.md`，包级整理实现与证据见 `IMPLEMENTATION_INDEX.md` 的‘动画源发现与生产池开发’，Sprint 之后的动画池扩展见 `ROADMAP.md` 的 `RM-09R`。服装和变体边界见 `MODULAR_CHARACTER_RUNTIME.md`。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 `WF-08`，但其 Gate 通过前仍为 `planned`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L130` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`
6. **索引表提及**：`ue_details/README.md:L14`，链接文字 `MODULAR_CHARACTER_RUNTIME.md`。
   - 用途原句：| `MODULAR_CHARACTER_RUNTIME.md` | `WF-06` 构建、调试或扩展角色组件 | 20/19 组件、Leader Pose、Morph 广播、槽位和变体边界 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/README.md:L14` → `ue_details/MODULAR_CHARACTER_RUNTIME.md`

## validation

### `README.md`

- 定位：`validation/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`17` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L167`，链接文字 `validation/README.md`。
   - 用途原句：Gate 的组成与运行时机见 `validation/README.md`；准确测试命令和‘成功能/不能证明什么’见 `VALIDATION_CATALOG.md`；视觉姿态与标准见 `VISUAL_ACCEPTANCE.md`；每次视觉结果的网页登记、历史分支和 A/B 审查见 `VISUAL_REVIEW_PORTAL.md`；恢复步骤见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L226`，链接文字 `README.md`。
   - 用途原句：`README.md` 定义 Gate；`VALIDATION_CATALOG.md` 定义 `VAL-*`；`VISUAL_ACCEPTANCE.md` 定义 `VIS-*`；`VISUAL_REVIEW_PORTAL.md` 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；`RECOVERY_RUNBOOK.md` 定义 `REC-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md`
3. **索引表提及**：`README.md:L20`，链接文字 `Validation`。
   - 用途原句：| 查测试何时运行及意义 | Validation |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L20` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L20` → `validation/README.md`
4. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L58`，链接文字 `GATE-00 SESSION_READY`。
   - 用途原句：执行 `GATE-00 SESSION_READY`。CC 生产至少要求 `VAL-BRIDGE-01`；`VAL-CODE-01` 仅在代码或机器配置变化后强制执行。未使用的 UE 通道可以记为 `not_required`，不能记为通过。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L58` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L58` → `validation/README.md`
5. **正文提及**：`workflow/WF-01-CHARACTER-DEFINITION.md:L84`，链接文字 `GATE-01 MANIFEST_READY`。
   - 用途原句：执行 `GATE-01 MANIFEST_READY` 中的 `VAL-MANIFEST-01`。要求 `success=true`、请求数等于角色数、全部 request result 为 `compiled`，且无性别、资产审核或组合拒绝。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `workflow/WF-01-CHARACTER-DEFINITION.md:L84` → `validation/README.md`
6. **正文提及**：`workflow/WF-02-CC-ASSEMBLY.md:L54`，链接文字 `GATE-02 ASSEMBLY_COMPLETE`。
   - 用途原句：执行 `GATE-02 ASSEMBLY_COMPLETE`。要求 Bridge 终态成功、`failure_count=0`、单项 `error=null`、Body/Junction 未漂移、Facial Profile 和眼球完整性检查无错误。本门禁只证明装配结构完整，不证明角色视觉可接受。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `workflow/WF-02-CC-ASSEMBLY.md:L54` → `validation/README.md`
7. **正文提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L60`，链接文字 `GATE-03 CC_ACCEPTED`。
   - 用途原句：执行 `GATE-03 CC_ACCEPTED`：`VAL-CC-02` 报告通过，三项 `VIS-CC-*` 明确接受，规范项目保存状态和路径已记录。仅自动报告通过时 Gate 仍失败。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L60` → `validation/README.md`
8. **正文提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L67`，链接文字 `GATE-04 BUNDLE_READY`。
   - 用途原句：`GATE-04 BUNDLE_READY` 要求 `VAL-BUNDLE-01` 通过：FBX/JSON 同基名且来自本次导出，纹理存在，源项目与 Manifest 可追溯，目标版本和 Auto Setup 版本已记录。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L67` → `validation/README.md`
9. **正文提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L117`，链接文字 `GATE-05 UE_REFERENCE_ACCEPTED`。
   - 用途原句：执行 `GATE-05 UE_REFERENCE_ACCEPTED`，并要求每个 Look 同时满足：
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L117` → `validation/README.md`
10. **正文提及**：`workflow/WF-06-UE-CHARACTER-RUNTIME.md:L57`，链接文字 `GATE-06 RUNTIME_ACCEPTED`。
   - 用途原句：执行 `GATE-06 RUNTIME_ACCEPTED`。当前要求 `VAL-UE-01` 通过，并完成 `VIS-UE-01`：20/19 组件关系正确、13 个面部广播组件匹配、非面部隔离、材质和中性/Blink/Smile/Jaw Open 正常。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `workflow/WF-06-UE-CHARACTER-RUNTIME.md:L57` → `validation/README.md`
11. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L122`，链接文字 `GATE-07 PERFORMANCE_ACCEPTED`。
   - 用途原句：执行 `GATE-07 PERFORMANCE_ACCEPTED`。当前 M02 要求适用的 `VAL-UE-02`、`VAL-UE-03` 和 `VIS-UE-02` 通过。未使用 Elder 时 `VAL-UE-03=not_required`；服装、毛发或道具只要参与，就必须等待相应计划验证实现后才能声称完整 Gate 通过。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L122` → `validation/README.md`
12. **正文提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L92`，链接文字 `GATE-08 SCENE_READY`。
   - 用途原句：门禁为 `GATE-08 SCENE_READY`。它至少需要 `VAL-SCENE-01` 与 `VIS-SCENE-01`，覆盖地面接触、角色/场景/道具碰撞、全时段相机可见性、裁切、焦点、`30 fps`、无重叠 Camera Cut、JSON 窗口偏移以及身体/Happy 组合。结构审计位于 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260822_v2\layout_motion_audit.json`；补齐、组合和序列报告位于 `OU…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L92` → `validation/README.md`
13. **正文提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L88`，链接文字 `GATE-09 DATASET_ACCEPTED`。
   - 用途原句：门禁为 `GATE-09 DATASET_ACCEPTED`。32-Look 本地证据位于 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002\matrix_report.json`：32/32 案例、32 个唯一 Look、10 个动作、四台相机各 8 例、三种表情均覆盖，合计 4,800 张 PNG 与 32 个 MP4。每例均为 150 帧、2560×1440、30 fps、5 秒，32/32 pose-driver 与 te…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L88` → `validation/README.md`
14. **元数据提及**：`validation/RECOVERY_RUNBOOK.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `validation/RECOVERY_RUNBOOK.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/RECOVERY_RUNBOOK.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/RECOVERY_RUNBOOK.md:L7` → `validation/README.md`
15. **元数据提及**：`validation/VALIDATION_CATALOG.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L7` → `validation/README.md`
16. **元数据提及**：`validation/VISUAL_ACCEPTANCE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `validation/VISUAL_ACCEPTANCE.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_ACCEPTANCE.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_ACCEPTANCE.md:L7` → `validation/README.md`
17. **元数据提及**：`validation/VISUAL_REVIEW_PORTAL.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_REVIEW_PORTAL.md:L7` → `validation/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_REVIEW_PORTAL.md:L7` → `validation/README.md`

### `RECOVERY_RUNBOOK.md`

- 定位：`validation/RECOVERY_RUNBOOK.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`14` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L99`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：执行：`WF-00-SESSION-PREFLIGHT.md`。Bridge 机制：`BRIDGE_OPERATIONS.md`。失败：`RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `validation/RECOVERY_RUNBOOK.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L167`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：Gate 的组成与运行时机见 `validation/README.md`；准确测试命令和‘成功能/不能证明什么’见 `VALIDATION_CATALOG.md`；视觉姿态与标准见 `VISUAL_ACCEPTANCE.md`；每次视觉结果的网页登记、历史分支和 A/B 审查见 `VISUAL_REVIEW_PORTAL.md`；恢复步骤见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/RECOVERY_RUNBOOK.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L226`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：`README.md` 定义 Gate；`VALIDATION_CATALOG.md` 定义 `VAL-*`；`VISUAL_ACCEPTANCE.md` 定义 `VIS-*`；`VISUAL_REVIEW_PORTAL.md` 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；`RECOVERY_RUNBOOK.md` 定义 `REC-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/RECOVERY_RUNBOOK.md`
4. **索引表提及**：`README.md:L24`，链接文字 `Recovery Runbook`。
   - 用途原句：| 查失败恢复 | Recovery Runbook |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L24` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L24` → `validation/RECOVERY_RUNBOOK.md`
5. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L62`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：heartbeat 过期、CC 崩溃、未知弹窗、UE 恢复包或 Remote/MCP 离线时，按 `RECOVERY_RUNBOOK.md` 对应 `REC-*` 处理。恢复后重新执行整个 `WF-00`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L62` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L62` → `validation/RECOVERY_RUNBOOK.md`
6. **正文提及**：`cc_details/APPEARANCE_PIPELINE.md:L197`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：共用验证见 `VALIDATION_CATALOG.md` 与 `VISUAL_ACCEPTANCE.md`，弹窗恢复见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/RECOVERY_RUNBOOK.md`
7. **正文提及**：`cc_details/BODYFIT_PIPELINE.md:L93`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：失败恢复见 `RECOVERY_RUNBOOK.md`；准确回归入口见 `VAL-CC-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/RECOVERY_RUNBOOK.md`
8. **正文提及**：`bridge_details/README.md:L12`，链接文字 `REC-BRIDGE-01`。
   - 用途原句：`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、命令语义和 Undo 守卫。每次会话的实际健康检查从 `WF-00` 进入，准确命令由 `VAL-BRIDGE-01` 定义，失败按 `REC-BRIDGE-01` 恢复。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L12` → `validation/RECOVERY_RUNBOOK.md`
9. **元数据提及**：`bridge_details/BRIDGE_OPERATIONS.md:L9`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：> 下游：`WF-00`、`WF-02`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L9` → `validation/RECOVERY_RUNBOOK.md`
10. **正文提及**：`bridge_details/BRIDGE_OPERATIONS.md:L88`，链接文字 `REC-BRIDGE-01`。
   - 用途原句：准确恢复步骤见 `REC-BRIDGE-01` 和 `REC-DIALOG-01`。恢复后必须重做 `GATE-00`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
11. **正文提及**：`bridge_details/BRIDGE_OPERATIONS.md:L88`，链接文字 `REC-DIALOG-01`。
   - 用途原句：准确恢复步骤见 `REC-BRIDGE-01` 和 `REC-DIALOG-01`。恢复后必须重做 `GATE-00`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L88` → `validation/RECOVERY_RUNBOOK.md`
12. **元数据提及**：`validation/README.md:L9`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：> 下游：`VALIDATION_CATALOG.md`、`VISUAL_ACCEPTANCE.md`、`VISUAL_REVIEW_PORTAL.md`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L9` → `validation/RECOVERY_RUNBOOK.md`
13. **元数据提及**：`validation/VALIDATION_CATALOG.md:L9`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：> 下游：对应 Gate 或 `RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md:L9` → `validation/RECOVERY_RUNBOOK.md`
14. **元数据提及**：`validation/VISUAL_ACCEPTANCE.md:L9`，链接文字 `RECOVERY_RUNBOOK.md`。
   - 用途原句：> 下游：对应 Gate 或 `RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `validation/VISUAL_ACCEPTANCE.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_ACCEPTANCE.md:L9` → `validation/RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_ACCEPTANCE.md:L9` → `validation/RECOVERY_RUNBOOK.md`

### `VALIDATION_CATALOG.md`

- 定位：`validation/VALIDATION_CATALOG.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`19` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L167`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：Gate 的组成与运行时机见 `validation/README.md`；准确测试命令和‘成功能/不能证明什么’见 `VALIDATION_CATALOG.md`；视觉姿态与标准见 `VISUAL_ACCEPTANCE.md`；每次视觉结果的网页登记、历史分支和 A/B 审查见 `VISUAL_REVIEW_PORTAL.md`；恢复步骤见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VALIDATION_CATALOG.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L226`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：`README.md` 定义 Gate；`VALIDATION_CATALOG.md` 定义 `VAL-*`；`VISUAL_ACCEPTANCE.md` 定义 `VIS-*`；`VISUAL_REVIEW_PORTAL.md` 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；`RECOVERY_RUNBOOK.md` 定义 `REC-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VALIDATION_CATALOG.md`
3. **正文提及**：`workflow/README.md:L35`，链接文字 `../validation/VALIDATION_CATALOG.md`。
   - 用途原句：3. Workflow 中的普通命令是生产命令的唯一来源；Gate 的测试命令只在 `../validation/VALIDATION_CATALOG.md` 定义。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L35` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L35` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L35` → `validation/VALIDATION_CATALOG.md`
4. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L54`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：准确测试命令及其证明边界见 `VALIDATION_CATALOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L54` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L54` → `validation/VALIDATION_CATALOG.md`
5. **正文提及**：`cc_details/APPEARANCE_PIPELINE.md:L197`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：共用验证见 `VALIDATION_CATALOG.md` 与 `VISUAL_ACCEPTANCE.md`，弹窗恢复见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VALIDATION_CATALOG.md`
6. **正文提及**：`cc_details/BODYFIT_PIPELINE.md:L53`，链接文字 `VAL-CC-01`。
   - 用途原句：BodyFit 回归不属于每个角色的日常步骤。修改源项目、哈希、Head Scale、Neck Height 或库构建逻辑后，先从 `WF-00` 通过 Bridge 门禁，再执行 `VAL-CC-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L53` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L53` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L53` → `validation/VALIDATION_CATALOG.md`
7. **正文提及**：`cc_details/BODYFIT_PIPELINE.md:L93`，链接文字 `VAL-CC-01`。
   - 用途原句：失败恢复见 `RECOVERY_RUNBOOK.md`；准确回归入口见 `VAL-CC-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L93` → `validation/VALIDATION_CATALOG.md`
8. **正文提及**：`cc_details/FACE_IDENTITY_AND_AGE.md:L119`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：每个新主原型和完整角色必须覆盖正面、3/4、侧面、后脑、双/单眼闭合、四向视线、眯眼、睁大、眉毛、微笑、张嘴和中性恢复。机器检查见 `VALIDATION_CATALOG.md`，人工检查见 `VISUAL_ACCEPTANCE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VALIDATION_CATALOG.md`
9. **元数据提及**：`cc_details/HEADSHOT_PIPELINE.md:L9`，链接文字 `../validation/VALIDATION_CATALOG.md`。
   - 用途原句：> 下游：`FACE_IDENTITY_AND_AGE.md`、`../validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md:L9` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md:L9` → `validation/VALIDATION_CATALOG.md`
10. **正文提及**：`cc_details/HEADSHOT_PIPELINE.md:L396`，链接文字 `VAL-CC-03/04/05`。
   - 用途原句：完整验证定义见 `VAL-CC-03/04/05`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md:L396` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md:L396` → `validation/VALIDATION_CATALOG.md`
11. **正文提及**：`bridge_details/README.md:L12`，链接文字 `VAL-BRIDGE-01`。
   - 用途原句：`BRIDGE_OPERATIONS.md` 解释安装、协议、队列、allowlist、命令语义和 Undo 守卫。每次会话的实际健康检查从 `WF-00` 进入，准确命令由 `VAL-BRIDGE-01` 定义，失败按 `REC-BRIDGE-01` 恢复。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/README.md:L12` → `validation/VALIDATION_CATALOG.md`
12. **正文提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：构建脚本用于维护现有 Pilot，不代表已经存在‘输入任意动画即可生成生产资产’的通用 API。正常组合顺序见 `WF-07`，准确验证命令见 `VALIDATION_CATALOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L46` → `validation/VALIDATION_CATALOG.md`
13. **正文提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L114`，链接文字 `VAL-UE-02`。
   - 用途原句：v003 已通过 `2 body × 5 face state` 的 10 个组合。准确复跑入口只在 `VAL-UE-02` 维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L114` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L114` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L114` → `validation/VALIDATION_CATALOG.md`
14. **正文提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L131`，链接文字 `VAL-UE-04`。
   - 用途原句：FullReference P0 已通过 `4 body state × 4 face state` 的 16 个组合和 24 张截图；准确复跑入口由 `VAL-UE-04` 维护：
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L131` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L131` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L131` → `validation/VALIDATION_CATALOG.md`
15. **正文提及**：`ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L144`，链接文字 `VAL-UE-03`。
   - 用途原句：准确复跑入口只在 `VAL-UE-03` 维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L144` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L182` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L144` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/ANIMATION_AND_MORPH_PIPELINE.md:L144` → `validation/VALIDATION_CATALOG.md`
16. **索引表提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L41`，链接文字 `VAL-UE-01`。
   - 用途原句：| 当前复跑命令 | `VAL-UE-01` | 给出 UE Remote Execution 命令、输出报告和通过字段 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L41` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L41` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L41` → `validation/VALIDATION_CATALOG.md`
17. **索引表提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L42`，链接文字 `VAL-UE-02`。
   - 用途原句：| 组合结构覆盖 | `VAL-UE-02` | 在 2×5 PIE 矩阵中再次检查 20/19/Leader Pose |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L42` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L42` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L42` → `validation/VALIDATION_CATALOG.md`
18. **元数据提及**：`validation/README.md:L9`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：> 下游：`VALIDATION_CATALOG.md`、`VISUAL_ACCEPTANCE.md`、`VISUAL_REVIEW_PORTAL.md`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L9` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L9` → `validation/VALIDATION_CATALOG.md`
19. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L12`，链接文字 `VALIDATION_CATALOG.md`。
   - 用途原句：本文回答‘某个 Workflow 实际使用什么文件’。生产顺序和命令以对应 `WF-*` 为准，测试命令以 `VALIDATION_CATALOG.md` 为准，精确参数和 ID 以机器 JSON 为准。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L12` → `validation/VALIDATION_CATALOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L12` → `validation/VALIDATION_CATALOG.md`

### `VISUAL_ACCEPTANCE.md`

- 定位：`validation/VISUAL_ACCEPTANCE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`10` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L117`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：执行：`WF-03-CC-ACCEPTANCE.md`。人工判定：`VISUAL_ACCEPTANCE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `validation/VISUAL_ACCEPTANCE.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L167`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：Gate 的组成与运行时机见 `validation/README.md`；准确测试命令和‘成功能/不能证明什么’见 `VALIDATION_CATALOG.md`；视觉姿态与标准见 `VISUAL_ACCEPTANCE.md`；每次视觉结果的网页登记、历史分支和 A/B 审查见 `VISUAL_REVIEW_PORTAL.md`；恢复步骤见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_ACCEPTANCE.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L226`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：`README.md` 定义 Gate；`VALIDATION_CATALOG.md` 定义 `VAL-*`；`VISUAL_ACCEPTANCE.md` 定义 `VIS-*`；`VISUAL_REVIEW_PORTAL.md` 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；`RECOVERY_RUNBOOK.md` 定义 `REC-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_ACCEPTANCE.md`
4. **正文提及**：`workflow/README.md:L36`，链接文字 `../validation/VISUAL_ACCEPTANCE.md`。
   - 用途原句：4. 自动成功不代替 `../validation/VISUAL_ACCEPTANCE.md` 中要求的人工视觉判定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L36` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L36` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L36` → `validation/VISUAL_ACCEPTANCE.md`
5. **正文提及**：`workflow/WF-03-CC-ACCEPTANCE.md:L68`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：视觉检查定义见 `VISUAL_ACCEPTANCE.md`，追溯字段见 `ASSET_TRACEABILITY.md`。只有 `GATE-03` 通过后才能进入 `WF-04`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L117` → `workflow/WF-03-CC-ACCEPTANCE.md:L68` → `validation/VISUAL_ACCEPTANCE.md`
6. **正文提及**：`cc_details/APPEARANCE_PIPELINE.md:L197`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：共用验证见 `VALIDATION_CATALOG.md` 与 `VISUAL_ACCEPTANCE.md`，弹窗恢复见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L178` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L209` → `cc_details/APPEARANCE_PIPELINE.md:L197` → `validation/VISUAL_ACCEPTANCE.md`
7. **正文提及**：`cc_details/BODYFIT_PIPELINE.md:L55`，链接文字 `VIS-CC-01`。
   - 用途原句：单 preset smoke 默认使用 `M02_Average`；全库回归使用同一验证定义覆盖十个登记 ID。机器通过要求源 SHA-256/大小、Body/Junction 指纹、眼球基准和比例决策一致；视觉比例仍按 `VIS-CC-01` 判定。测试命令只在 Validation Catalog 维护。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/BODYFIT_PIPELINE.md:L55` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L175` → `cc_details/BODYFIT_PIPELINE.md:L55` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L206` → `cc_details/BODYFIT_PIPELINE.md:L55` → `validation/VISUAL_ACCEPTANCE.md`
8. **正文提及**：`cc_details/FACE_IDENTITY_AND_AGE.md:L119`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：每个新主原型和完整角色必须覆盖正面、3/4、侧面、后脑、双/单眼闭合、四向视线、眯眼、睁大、眉毛、微笑、张嘴和中性恢复。机器检查见 `VALIDATION_CATALOG.md`，人工检查见 `VISUAL_ACCEPTANCE.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md:L119` → `validation/VISUAL_ACCEPTANCE.md`
9. **元数据提及**：`validation/README.md:L9`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：> 下游：`VALIDATION_CATALOG.md`、`VISUAL_ACCEPTANCE.md`、`VISUAL_REVIEW_PORTAL.md`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L9` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L9` → `validation/VISUAL_ACCEPTANCE.md`
10. **元数据提及**：`validation/VISUAL_REVIEW_PORTAL.md:L8`，链接文字 `VISUAL_ACCEPTANCE.md`。
   - 用途原句：> 上游：各 Workflow 产生的截图、联系表、结果 JSON 和 `VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_REVIEW_PORTAL.md:L8` → `validation/VISUAL_ACCEPTANCE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_REVIEW_PORTAL.md:L8` → `validation/VISUAL_ACCEPTANCE.md`

### `VISUAL_REVIEW_PORTAL.md`

- 定位：`validation/VISUAL_REVIEW_PORTAL.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L167`，链接文字 `VISUAL_REVIEW_PORTAL.md`。
   - 用途原句：Gate 的组成与运行时机见 `validation/README.md`；准确测试命令和‘成功能/不能证明什么’见 `VALIDATION_CATALOG.md`；视觉姿态与标准见 `VISUAL_ACCEPTANCE.md`；每次视觉结果的网页登记、历史分支和 A/B 审查见 `VISUAL_REVIEW_PORTAL.md`；恢复步骤见 `RECOVERY_RUNBOOK.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/VISUAL_REVIEW_PORTAL.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L226`，链接文字 `VISUAL_REVIEW_PORTAL.md`。
   - 用途原句：`README.md` 定义 Gate；`VALIDATION_CATALOG.md` 定义 `VAL-*`；`VISUAL_ACCEPTANCE.md` 定义 `VIS-*`；`VISUAL_REVIEW_PORTAL.md` 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；`RECOVERY_RUNBOOK.md` 定义 `REC-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/VISUAL_REVIEW_PORTAL.md`
3. **索引表提及**：`README.md:L21`，链接文字 `Visual Review Portal`。
   - 用途原句：| 查看历次截图、参数和 A/B 结果 | Visual Review Portal |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L21` → `validation/VISUAL_REVIEW_PORTAL.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L21` → `validation/VISUAL_REVIEW_PORTAL.md`
4. **元数据提及**：`validation/README.md:L9`，链接文字 `VISUAL_REVIEW_PORTAL.md`。
   - 用途原句：> 下游：`VALIDATION_CATALOG.md`、`VISUAL_ACCEPTANCE.md`、`VISUAL_REVIEW_PORTAL.md`、`RECOVERY_RUNBOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L9` → `validation/VISUAL_REVIEW_PORTAL.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L9` → `validation/VISUAL_REVIEW_PORTAL.md`
5. **正文提及**：`validation/README.md:L47`，链接文字 `VISUAL_REVIEW_PORTAL.md`。
   - 用途原句：- 从 2026-08-09 起，任何产生截图或联系表的新视觉审查：机器完整性检查后、请求用户审查前，按 `VISUAL_REVIEW_PORTAL.md` 登记独立结果分支；人工结论写回 run 后才能汇总对应 `VIS-*`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L167` → `validation/README.md:L47` → `validation/VISUAL_REVIEW_PORTAL.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L226` → `validation/README.md:L47` → `validation/VISUAL_REVIEW_PORTAL.md`

## planning

### `README.md`

- 定位：`planning/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L230`，链接文字 `README.md`。
   - 用途原句：`README.md` 解释规划边界；`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 是当前唯一活动计划；`ROADMAP.md` 只保存 Sprint 之后未完成的 `RM-*`；`BACKLOG.md` 保存未承诺候选项。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md`
2. **元数据提及**：`planning/BACKLOG.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/BACKLOG.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L272` → `planning/BACKLOG.md:L7` → `planning/README.md`
3. **元数据提及**：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L7` → `planning/README.md` **[回链，不继续递归]**
4. **元数据提及**：`planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L7` → `planning/README.md`
5. **元数据提及**：`planning/ROADMAP.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L184` → `planning/ROADMAP.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/ROADMAP.md:L7` → `planning/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L271` → `planning/ROADMAP.md:L7` → `planning/README.md`

### `BACKLOG.md`

- 定位：`planning/BACKLOG.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L230`，链接文字 `BACKLOG.md`。
   - 用途原句：`README.md` 解释规划边界；`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 是当前唯一活动计划；`ROADMAP.md` 只保存 Sprint 之后未完成的 `RM-*`；`BACKLOG.md` 保存未承诺候选项。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/BACKLOG.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L272`，链接文字 `BACKLOG.md`。
   - 用途原句：- 尚未承诺什么：`BACKLOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L272` → `planning/BACKLOG.md`
3. **索引表提及**：`CURRENT_STATUS.md:L110`，链接文字 `Backlog`。
   - 用途原句：| 后续而非本周工作 | Roadmap / Backlog |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L110` → `planning/BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L110` → `planning/BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L110` → `planning/BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L110` → `planning/BACKLOG.md`
4. **正文提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L141`，链接文字 `../planning/BACKLOG.md`。
   - 用途原句：`ue_validate_m02_modular_blueprint.py` 的 Blueprint 路径仍是 v001。当前 v002 只由面部广播脚本和 v003 组合矩阵覆盖；这项限制已登记到 `../planning/BACKLOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L141` → `planning/BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L141` → `planning/BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L141` → `planning/BACKLOG.md`
5. **元数据提及**：`planning/README.md:L9`，链接文字 `BACKLOG.md`。
   - 用途原句：> 下游：活动 Sprint、`ROADMAP.md`、`BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L9` → `planning/BACKLOG.md`
6. **正文提及**：`planning/README.md:L15`，链接文字 `BACKLOG.md`。
   - 用途原句：- `BACKLOG.md`：尚未承诺或排期的研究、质量改进和技术债务。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L15` → `planning/BACKLOG.md`

### `FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`

- 定位：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **正文提及**：`planning/README.md:L13`，链接文字 `FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`。
   - 用途原句：- `FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`：已完成的 Day 2 UI 应急交接记录；保留 12 个动作 FBX 的人工导出步骤和 32 Look Auto Setup 的手工回退边界，当前状态以 Sprint、WF-05 和机器清单为准。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`
2. **正文提及**：`planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169`，链接文字 `FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`。
   - 用途原句：Day 2 的 CC 自动动作导出曾被内容许可交互阻塞，因此最终 12 个 Motion FBX 采用 `FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md` 的人工导出与机器验收路径；3 条许可受阻动作已替换，不再尝试绕过许可门禁。UE FullReference 导入阶段已经为已知 FBX 导入与 Auto Setup 对话框建立精确守卫，并完成 32/32 自动编排和机器验收；未知对话框仍必须停止交由用户处理。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`

### `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`

- 定位：`planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`18` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L58`，链接文字 `第一批多轮编辑数据 Sprint`。
   - 用途原句：当前唯一活动计划是 第一批多轮编辑数据 Sprint：使用 F02/M02、8 个身份、同性各 4 套服装、32 个烘焙 Look、10 个生产动作（每个角色使用同性 5 个）、固定 Happy 表情、1 个场景和 `near/far/high/side` 四台生产相机，在服务器完整渲染 640 个唯一节点，并生成精确 4,000 条 3–5 轮编辑链及 15,000 回合双语 prompt。节点按 female/male 分成两个各 320 节点的连通兼容域；链按 `progressive_shortest/f…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L147`，链接文字 `FIRST_DATA_BATCH_SPRINT`。
   - 用途原句：阶段契约：`WF-08-SCENE-CAMERA-SEQUENCE.md`。当前范围：`FIRST_DATA_BATCH_SPRINT`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L230`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：`README.md` 解释规划边界；`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 是当前唯一活动计划；`ROADMAP.md` 只保存 Sprint 之后未完成的 `RM-*`；`BACKLOG.md` 保存未承诺候选项。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
4. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L270`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：- 当前一周做什么：`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
5. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L282`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：3. 若 Sprint 仍活动，先读 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`，只执行其中当前日门禁。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
6. **索引表提及**：`README.md:L26`，链接文字 `第一批数据 Sprint`。
   - 用途原句：| 执行本周第一批数据任务 | 第一批数据 Sprint |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L26` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L26` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
7. **元数据提及**：`CURRENT_STATUS.md:L9`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：> 下游：`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 与各 Workflow
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L9` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L9` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L9` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L9` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
8. **正文提及**：`CURRENT_STATUS.md:L21`，链接文字 `第一批多轮编辑数据 Sprint`。
   - 用途原句：当前唯一活动目标是 第一批多轮编辑数据 Sprint：在服务器完整渲染 `32 Looks × 5 同性动作 × 4 相机 × 1 Happy 表情 = 640` 个唯一节点，并生成精确 4,000 条 3–5 轮编辑链。节点按 female/male 分为两个各 320 节点的兼容域，域内必须连通；链采用 `progressive_shortest/freeform_walk` 50/50。Angry/Sad 只保留为历史候选，不进入本批正式节点或编辑轴。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L21` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L21` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L21` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L21` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
9. **正文提及**：`CURRENT_STATUS.md:L84`，链接文字 `Sprint`。
   - 用途原句：这些项目的顺序和退出条件见 Sprint，不能从旧实验日志推断。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L84` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L84` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L84` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L84` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
10. **索引表提及**：`CURRENT_STATUS.md:L103`，链接文字 `第一批数据 Sprint`。
   - 用途原句：| 本周做什么 | 第一批数据 Sprint |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L103` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L103` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L103` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L103` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
11. **正文提及**：`workflow/README.md:L14`，链接文字 `第一批数据 Sprint`。
   - 用途原句：2026-08-19 至 2026-08-26 的受限实现范围由 第一批数据 Sprint 冻结。`WF-08/09` 已进入 `in_progress` 并有本地可验证路径，但对应 Gate 在完整机器与人工证据齐全前仍未通过。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L9` → `workflow/README.md:L14` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L91` → `workflow/README.md:L14` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L199` → `workflow/README.md:L14` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
12. **正文提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L18`，链接文字 `第一批数据 Sprint`。
   - 用途原句：本阶段已进入本地实现。第一批只承诺 1 个场景、1 个安全角色锚点、固定灯光、4 个静态相机候选（`near/far/high/side`）和确定性 Sequence；不做道具、移动相机、场景替换、天气或灯光编辑。冻结范围见 第一批数据 Sprint。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L18` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
13. **正文提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100`，链接文字 `第一批数据 Sprint`。
   - 用途原句：UE 资产边界见 `ADR-0007`，当前任务见 第一批数据 Sprint。本阶段实现并通过后进入 `WF-09`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
14. **正文提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L18`，链接文字 `Sprint`。
   - 用途原句：本阶段已有可断点续跑的本地 32-Look 代表矩阵执行器，以及符合当前契约的正式 640 节点配置图、8,320 条同域原子边、4,000 条编辑链、640 个 render job 和 15,000 回合双语 prompt；尚无正式 640 节点媒体执行器。第一批冻结目标为服务器完整渲染 640 个 Happy-only 唯一节点；节点只渲染一次，链和文本回合只引用媒体。正式节点使用 `near/far/high/side` 四台相机，并分为 female/male 两个各 320 节点的兼容域。历史本地 3…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L18` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
15. **正文提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L102`，链接文字 `Sprint`。
   - 用途原句：外部输出职责见 `EXTERNAL_DIRECTORIES.md`，当前实施顺序见 Sprint。本地 32 例只称为代表矩阵验收；只有 GT、sidecar、正式节点图、服务器媒体、链和引用检查全部通过 `GATE-09`，才代表一份数据集包完成。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L102` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
16. **正文提及**：`planning/README.md:L12`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：- `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`：当前唯一活动计划；冻结第一批 640 节点、两个兼容域和精确 4,000 条多轮编辑链的范围、预算、日门禁和降级顺序。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L12` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
17. **元数据提及**：`planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：> 上游：`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 与 v4 动作注册表
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L169` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L13` → `planning/FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md:L8` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
18. **正文提及**：`planning/ROADMAP.md:L16`，链接文字 `FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`。
   - 用途原句：`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L184` → `planning/ROADMAP.md:L16` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/ROADMAP.md:L16` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L271` → `planning/ROADMAP.md:L16` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`

### `ROADMAP.md`

- 定位：`planning/ROADMAP.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`13` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L184`，链接文字 `ROADMAP.md`。
   - 用途原句：开发阶段使用 `RM-*`，生产生命周期使用 `WF-*`；两者不得混用。当前开发顺序见 `ROADMAP.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L184` → `planning/ROADMAP.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L230`，链接文字 `ROADMAP.md`。
   - 用途原句：`README.md` 解释规划边界；`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md` 是当前唯一活动计划；`ROADMAP.md` 只保存 Sprint 之后未完成的 `RM-*`；`BACKLOG.md` 保存未承诺候选项。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/ROADMAP.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L271`，链接文字 `ROADMAP.md`。
   - 用途原句：- Sprint 之后开发什么：`ROADMAP.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L271` → `planning/ROADMAP.md`
4. **索引表提及**：`README.md:L25`，链接文字 `Roadmap`。
   - 用途原句：| 查下一阶段开发 | Roadmap |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L25` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L25` → `planning/ROADMAP.md`
5. **索引表提及**：`CURRENT_STATUS.md:L110`，链接文字 `Roadmap`。
   - 用途原句：| 后续而非本周工作 | Roadmap / Backlog |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L110` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L110` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L110` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L110` → `planning/ROADMAP.md`
6. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L130`，链接文字 `ROADMAP.md`。
   - 用途原句：通道分类和现有资产见 `ANIMATION_AND_MORPH_PIPELINE.md`，包级整理实现与证据见 `IMPLEMENTATION_INDEX.md` 的‘动画源发现与生产池开发’，Sprint 之后的动画池扩展见 `ROADMAP.md` 的 `RM-09R`。服装和变体边界见 `MODULAR_CHARACTER_RUNTIME.md`。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 `WF-08`，但其 Gate 通过前仍为 `planned`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L130` → `planning/ROADMAP.md`
7. **正文提及**：`cc_details/OUTFIT_PIPELINE.md:L587`，链接文字 `ROADMAP.md`。
   - 用途原句：当前状态与执行顺序分别见 `CURRENT_STATUS.md` 和 `ROADMAP.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L179` → `cc_details/OUTFIT_PIPELINE.md:L587` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L210` → `cc_details/OUTFIT_PIPELINE.md:L587` → `planning/ROADMAP.md`
8. **正文提及**：`cc_ue_transfer/README.md:L16`，链接文字 `ROADMAP.md`。
   - 用途原句：正式批量导出、LOD/贴图优化和十体型回归尚未实现，状态见 `ROADMAP.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L218` → `cc_ue_transfer/README.md:L16` → `planning/ROADMAP.md`
9. **元数据提及**：`planning/README.md:L9`，链接文字 `ROADMAP.md`。
   - 用途原句：> 下游：活动 Sprint、`ROADMAP.md`、`BACKLOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L9` → `planning/ROADMAP.md`
10. **正文提及**：`planning/README.md:L14`，链接文字 `ROADMAP.md`。
   - 用途原句：- `ROADMAP.md`：Sprint 之后仍未完成、已接受且已排序的 `RM-*` 开发工作。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/README.md:L14` → `planning/ROADMAP.md`
11. **正文提及**：`reference/IMPLEMENTATION_INDEX.md:L236`，链接文字 `ROADMAP.md`。
   - 用途原句：包级分类与静态文件名提示都不能替代逐条动作的 CC 播放、时长、循环、Root Motion、面部通道、隐藏依赖和动态质量门禁。剩余扩展见 `ROADMAP.md` 的 `RM-09R`，运行时组合规则见 `WF-07`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L236` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L236` → `planning/ROADMAP.md`
12. **正文提及**：`history/MILESTONE_LOG.md:L13`，链接文字 `../planning/ROADMAP.md`。
   - 用途原句：本文件只追加已经发生且有证据的事件。当前能力以 `../CURRENT_STATUS.md` 为准，未来工作以 `../planning/ROADMAP.md` 为准。修正旧条目时追加一条更正，不静默改写历史。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `history/MILESTONE_LOG.md:L13` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/MILESTONE_LOG.md:L13` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L274` → `history/MILESTONE_LOG.md:L13` → `planning/ROADMAP.md`
13. **索引表提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123`，链接文字 `ROADMAP.md`。
   - 用途原句：| 当前 Roadmap | `ROADMAP.md` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L123` → `planning/ROADMAP.md`

## decisions

### `README.md`

- 定位：`decisions/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`17` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L234`，链接文字 `README.md`。
   - 用途原句：`README.md` 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；`ADR-0011` 记录生命周期/Gate 架构；`ADR-0012` 记录用户对资产、安装包和许可/来源判断的独立权威边界；`ADR-0013` 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线；`ADR-0014` 记录配置图兼容域、双链策略与全量/稀疏节点生产决定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L273`，链接文字 `decisions/README.md`。
   - 用途原句：- 为什么采用当前规则：`decisions/README.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md`
3. **索引表提及**：`README.md:L29`，链接文字 `ADR`。
   - 用途原句：| 查历史决定或旧原文 | ADR / History |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L29` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L29` → `decisions/README.md`
4. **元数据提及**：`decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L16` → `decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L16` → `decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
5. **元数据提及**：`decisions/ADR-0002-FACE-IDENTITY-V3.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L17` → `decisions/ADR-0002-FACE-IDENTITY-V3.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L17` → `decisions/ADR-0002-FACE-IDENTITY-V3.md:L7` → `decisions/README.md` **[回链，不继续递归]**
6. **元数据提及**：`decisions/ADR-0003-AGE-VARIANTS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L18` → `decisions/ADR-0003-AGE-VARIANTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L18` → `decisions/ADR-0003-AGE-VARIANTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
7. **元数据提及**：`decisions/ADR-0004-APPEARANCE-POOLS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L19` → `decisions/ADR-0004-APPEARANCE-POOLS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L19` → `decisions/ADR-0004-APPEARANCE-POOLS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
8. **元数据提及**：`decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L20` → `decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L20` → `decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
9. **元数据提及**：`decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L21` → `decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L21` → `decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md:L7` → `decisions/README.md` **[回链，不继续递归]**
10. **元数据提及**：`decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L22` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L22` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L153` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md:L7` → `decisions/README.md`
11. **元数据提及**：`decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L23` → `decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L23` → `decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md:L7` → `decisions/README.md` **[回链，不继续递归]**
12. **元数据提及**：`decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L24` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L24` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md:L7` → `decisions/README.md` **[回链，不继续递归]**
13. **元数据提及**：`decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L25` → `decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md:L7` → `decisions/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L25` → `decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md:L7` → `decisions/README.md` **[回链，不继续递归]**
14. **元数据提及**：`decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md:L7` → `decisions/README.md`
15. **元数据提及**：`decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L34` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md:L7` → `decisions/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md:L7` → `decisions/README.md`
16. **元数据提及**：`decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md:L7` → `decisions/README.md`
17. **元数据提及**：`decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md:L7` → `decisions/README.md`

### `ADR-0001-BODYFIT-SOURCE-PROJECTS.md`

- 定位：`decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L16`，链接文字 `ADR-0001-BODYFIT-SOURCE-PROJECTS.md`。
   - 用途原句：| `ADR-0001-BODYFIT-SOURCE-PROJECTS.md` | Accepted | BodyFit 使用 hash 锁定源项目 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L16` → `decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L16` → `decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md`

### `ADR-0002-FACE-IDENTITY-V3.md`

- 定位：`decisions/ADR-0002-FACE-IDENTITY-V3.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L17`，链接文字 `ADR-0002-FACE-IDENTITY-V3.md`。
   - 用途原句：| `ADR-0002-FACE-IDENTITY-V3.md` | Accepted | 完整 seed + Facial Profile + 安全局部 Morph |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L17` → `decisions/ADR-0002-FACE-IDENTITY-V3.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L17` → `decisions/ADR-0002-FACE-IDENTITY-V3.md`

### `ADR-0003-AGE-VARIANTS.md`

- 定位：`decisions/ADR-0003-AGE-VARIANTS.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L18`，链接文字 `ADR-0003-AGE-VARIANTS.md`。
   - 用途原句：| `ADR-0003-AGE-VARIANTS.md` | Accepted | 年龄是可选面部变体，身体老化延后 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L18` → `decisions/ADR-0003-AGE-VARIANTS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L18` → `decisions/ADR-0003-AGE-VARIANTS.md`

### `ADR-0004-APPEARANCE-POOLS.md`

- 定位：`decisions/ADR-0004-APPEARANCE-POOLS.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L19`，链接文字 `ADR-0004-APPEARANCE-POOLS.md`。
   - 用途原句：| `ADR-0004-APPEARANCE-POOLS.md` | Accepted | 外观只从审核池选择，眼球只换材质 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L19` → `decisions/ADR-0004-APPEARANCE-POOLS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L19` → `decisions/ADR-0004-APPEARANCE-POOLS.md`

### `ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`

- 定位：`decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L20`，链接文字 `ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`。
   - 用途原句：| `ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md` | Accepted | 共享色素抽样，每角色三套已适配发型 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L20` → `decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L20` → `decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`

### `ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`

- 定位：`decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L21`，链接文字 `ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`。
   - 用途原句：| `ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md` | Accepted | 服装按 BodyFit × Look 管理 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L21` → `decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L21` → `decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`

### `ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`

- 定位：`decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`workflow/WF-05-UE-IMPORT-REFERENCE.md:L153`，链接文字 `ADR-0007`。
   - 用途原句：Vendor/DataMake 与追溯规则见 `ASSET_TRACEABILITY.md` 和 `ADR-0007`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L129` → `workflow/WF-05-UE-IMPORT-REFERENCE.md:L153` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`
2. **正文提及**：`workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100`，链接文字 `ADR-0007`。
   - 用途原句：UE 资产边界见 `ADR-0007`，当前任务见 第一批数据 Sprint。本阶段实现并通过后进入 `WF-09`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `workflow/WF-08-SCENE-CAMERA-SEQUENCE.md:L100` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`
3. **索引表提及**：`decisions/README.md:L22`，链接文字 `ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`。
   - 用途原句：| `ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md` | Accepted | Vendor 不动，DataMake 统一入口，模块化组件运行 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L22` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L22` → `decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`

### `ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`

- 定位：`decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L23`，链接文字 `ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`。
   - 用途原句：| `ADR-0008-BODY-FACE-ANIMATION-LAYERS.md` | Accepted | 按通道和复用政策分层动画 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L23` → `decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L23` → `decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`

### `ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`

- 定位：`decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **元数据提及**：`bridge_details/BRIDGE_OPERATIONS.md:L8`，链接文字 `ADR-0009`。
   - 用途原句：> 上游：`ADR-0009`、代码与 `bridge_config.json`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L111` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L180` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L214` → `bridge_details/BRIDGE_OPERATIONS.md:L8` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
2. **索引表提及**：`decisions/README.md:L24`，链接文字 `ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`。
   - 用途原句：| `ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md` | Accepted | Bridge 是受控离线文件队列，不执行任意代码 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L24` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L24` → `decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`

### `ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`

- 定位：`decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`1` 次。

1. **索引表提及**：`decisions/README.md:L25`，链接文字 `ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`。
   - 用途原句：| `ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md` | Accepted | 单一当前入口、技术子文档、不可变历史归档 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L25` → `decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L25` → `decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`

### `ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`

- 定位：`decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L234`，链接文字 `ADR-0011`。
   - 用途原句：`README.md` 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；`ADR-0011` 记录生命周期/Gate 架构；`ADR-0012` 记录用户对资产、安装包和许可/来源判断的独立权威边界；`ADR-0013` 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线；`ADR-0014` 记录配置图兼容域、双链策略与全量/稀疏节点生产决定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`
2. **元数据提及**：`DOCUMENTATION_RULES.md:L8`，链接文字 `ADR-0011`。
   - 用途原句：> 上游：`ADR-0011`、`ADR-0012`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`
3. **索引表提及**：`decisions/README.md:L26`，链接文字 `ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`。
   - 用途原句：| `ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md` | Accepted | 生产生命周期、Workflow、Gate 和单一命令来源 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L26` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L26` → `decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`

### `ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`

- 定位：`decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`5` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L34`，链接文字 `ADR-0012`。
   - 用途原句：**项目级最高操作边界之一**：用户独立负责资产、插件、安装包、输入数据及其许可、来源和对外发布边界。Agent 将用户提供的本地输入视为已获准用于本项目，不依据文件名、README、来源声明或授权措辞评价、拒绝或阻塞技术任务；只判断兼容性、完整性、稳定性、安全性、资源消耗和可复现性。详细决定见 `ADR-0012`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L34` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L234`，链接文字 `ADR-0012`。
   - 用途原句：`README.md` 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；`ADR-0011` 记录生命周期/Gate 架构；`ADR-0012` 记录用户对资产、安装包和许可/来源判断的独立权威边界；`ADR-0013` 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线；`ADR-0014` 记录配置图兼容域、双链策略与全量/稀疏节点生产决定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
3. **元数据提及**：`DOCUMENTATION_RULES.md:L8`，链接文字 `ADR-0012`。
   - 用途原句：> 上游：`ADR-0011`、`ADR-0012`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md:L8` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
4. **正文提及**：`DOCUMENTATION_RULES.md:L17`，链接文字 `ADR-0012`。
   - 用途原句：- 该职责边界适用于 CC、UE、第三方 DCC、素材、模型、动画、插件和数据来源。长期理由见 `ADR-0012`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md:L17` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md:L17` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md:L17` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
5. **索引表提及**：`decisions/README.md:L27`，链接文字 `ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`。
   - 用途原句：| `ADR-0012-USER-OWNED-ASSET-AUTHORITY.md` | Accepted | 用户负责资产、安装包和许可/来源判断；Agent 只做技术评估 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L27` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L27` → `decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`

### `ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`

- 定位：`decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`4` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L234`，链接文字 `ADR-0013`。
   - 用途原句：`README.md` 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；`ADR-0011` 记录生命周期/Gate 架构；`ADR-0012` 记录用户对资产、安装包和许可/来源判断的独立权威边界；`ADR-0013` 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线；`ADR-0014` 记录配置图兼容域、双链策略与全量/稀疏节点生产决定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
2. **正文提及**：`cc_details/FACE_IDENTITY_AND_AGE.md:L115`，链接文字 `ADR-0013`。
   - 用途原句：`F_HS_001/002`、`M_HS_001/002` 状态为 `candidate_cc5_hd_rm05b_visual_accepted`；`F_HS_003..005`、`M_HS_003..005` 为机器通过、原照片已映射、等待人工视觉验收的候选。`headshot_project_seed_then_bodyfit_v1` 已在 F02/M02 上取得机器与用户 Pilot 通过；本轮只完成十原型候选池闭环和暂存，不做 10/20 比较，也不进入当前生产 seed 池。扩容、`RM-06` 配方…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L105` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L176` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L207` → `cc_details/FACE_IDENTITY_AND_AGE.md:L115` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
3. **正文提及**：`cc_details/HEADSHOT_PIPELINE.md:L190`，链接文字 `ADR-0013`。
   - 用途原句：规范决定见 `ADR-0013`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L177` → `cc_details/HEADSHOT_PIPELINE.md:L190` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L208` → `cc_details/HEADSHOT_PIPELINE.md:L190` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
4. **索引表提及**：`decisions/README.md:L28`，链接文字 `ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`。
   - 用途原句：| `ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md` | Accepted | Headshot 身份用项目几何原型包保存，并采用 project-seed 装配路线 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L28` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L28` → `decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`

### `ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`

- 定位：`decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L234`，链接文字 `ADR-0014`。
   - 用途原句：`README.md` 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；`ADR-0011` 记录生命周期/Gate 架构；`ADR-0012` 记录用户对资产、安装包和许可/来源判断的独立权威边界；`ADR-0013` 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线；`ADR-0014` 记录配置图兼容域、双链策略与全量/稀疏节点生产决定。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
2. **正文提及**：`planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141`，链接文字 `ADR-0014`。
   - 用途原句：完整契约见 `MULTI_ROUND_CHAIN_SAMPLING_V1.md`，架构理由见 `ADR-0014`。本轮冻结：
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L147` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L270` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L282` → `planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md:L141` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
3. **索引表提及**：`decisions/README.md:L29`，链接文字 `ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`。
   - 用途原句：| `ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md` | Accepted | 男女按兼容域分别连通；采用 progressive_shortest/freeform_walk 双策略和全量/稀疏节点生产模式 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L234` → `decisions/README.md:L29` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L273` → `decisions/README.md:L29` → `decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`

## reference

### `README.md`

- 定位：`reference/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`4` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L238`，链接文字 `README.md`。
   - 用途原句：`README.md` 是参考索引；`IMPLEMENTATION_INDEX.md` 按 `WF-*` 定位代码/JSON/UE 资产；`EXTERNAL_DIRECTORIES.md` 定义本机路径和所有权；`GLOSSARY.md` 定义术语与 ID；`DOCUMENT_LINK_TRACE.md` 逐文件列出从 Master 出发的行号级提及链与回链。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md`
2. **元数据提及**：`reference/EXTERNAL_DIRECTORIES.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/EXTERNAL_DIRECTORIES.md:L7` → `reference/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L265` → `reference/EXTERNAL_DIRECTORIES.md:L7` → `reference/README.md`
3. **元数据提及**：`reference/GLOSSARY.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/GLOSSARY.md:L7` → `reference/README.md`
4. **元数据提及**：`reference/IMPLEMENTATION_INDEX.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md:L7` → `reference/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md:L7` → `reference/README.md`

### `DOCUMENT_LINK_TRACE.md`

- 定位：`reference/DOCUMENT_LINK_TRACE.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`4` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L238`，链接文字 `DOCUMENT_LINK_TRACE.md`。
   - 用途原句：`README.md` 是参考索引；`IMPLEMENTATION_INDEX.md` 按 `WF-*` 定位代码/JSON/UE 资产；`EXTERNAL_DIRECTORIES.md` 定义本机路径和所有权；`GLOSSARY.md` 定义术语与 ID；`DOCUMENT_LINK_TRACE.md` 逐文件列出从 Master 出发的行号级提及链与回链。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/DOCUMENT_LINK_TRACE.md`
2. **索引表提及**：`README.md:L23`，链接文字 `Document Link Trace`。
   - 用途原句：| 审查全部文档的递归提及路径 | Document Link Trace |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L23` → `reference/DOCUMENT_LINK_TRACE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L23` → `reference/DOCUMENT_LINK_TRACE.md`
3. **正文提及**：`DOCUMENTATION_RULES.md:L148`，链接文字 `reference/DOCUMENT_LINK_TRACE.md`。
   - 用途原句：行号级递归导航由 `reference/DOCUMENT_LINK_TRACE.md` 保存。修改现行 Markdown 的链接或行数后，先重新生成，再执行上述审计：
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L32` → `DOCUMENTATION_RULES.md:L148` → `reference/DOCUMENT_LINK_TRACE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L195` → `DOCUMENTATION_RULES.md:L148` → `reference/DOCUMENT_LINK_TRACE.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L292` → `DOCUMENTATION_RULES.md:L148` → `reference/DOCUMENT_LINK_TRACE.md`
4. **索引表提及**：`reference/README.md:L17`，链接文字 `DOCUMENT_LINK_TRACE.md`。
   - 用途原句：| `DOCUMENT_LINK_TRACE.md` | 每份现行文档在何处、因何被提及，以及从 Master 到它的行号级路径 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md:L17` → `reference/DOCUMENT_LINK_TRACE.md`

### `EXTERNAL_DIRECTORIES.md`

- 定位：`reference/EXTERNAL_DIRECTORIES.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`6` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L238`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：`README.md` 是参考索引；`IMPLEMENTATION_INDEX.md` 按 `WF-*` 定位代码/JSON/UE 资产；`EXTERNAL_DIRECTORIES.md` 定义本机路径和所有权；`GLOSSARY.md` 定义术语与 ID；`DOCUMENT_LINK_TRACE.md` 逐文件列出从 Master 出发的行号级提及链与回链。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/EXTERNAL_DIRECTORIES.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L265`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：代码、机器 JSON 和 artifacts 不存入 `full_process`。完整职责、Bridge 队列、Vendor/DataMake 和输出规则见 `EXTERNAL_DIRECTORIES.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L265` → `reference/EXTERNAL_DIRECTORIES.md`
3. **正文提及**：`workflow/WF-00-SESSION-PREFLIGHT.md:L66`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：Bridge 组件、安全边界和安装方法见 `BRIDGE_OPERATIONS.md`，外部路径见 `EXTERNAL_DIRECTORIES.md`。通过后进入 `WF-01`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L28` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `reference/EXTERNAL_DIRECTORIES.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L99` → `workflow/WF-00-SESSION-PREFLIGHT.md:L66` → `reference/EXTERNAL_DIRECTORIES.md`
4. **正文提及**：`workflow/WF-04-CC-EXPORT-BUNDLE.md:L75`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：追溯 schema 见 `ASSET_TRACEABILITY.md`，外部目录职责见 `EXTERNAL_DIRECTORIES.md`。通过后关闭或保留 CC 由资源情况决定，并进入 `WF-05`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L123` → `workflow/WF-04-CC-EXPORT-BUNDLE.md:L75` → `reference/EXTERNAL_DIRECTORIES.md`
5. **正文提及**：`workflow/WF-09-RENDER-DATASET-PACKAGE.md:L102`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：外部输出职责见 `EXTERNAL_DIRECTORIES.md`，当前实施顺序见 Sprint。本地 32 例只称为代表矩阵验收；只有 GT、sidecar、正式节点图、服务器媒体、链和引用检查全部通过 `GATE-09`，才代表一份数据集包完成。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L153` → `workflow/WF-09-RENDER-DATASET-PACKAGE.md:L102` → `reference/EXTERNAL_DIRECTORIES.md`
6. **索引表提及**：`reference/README.md:L15`，链接文字 `EXTERNAL_DIRECTORIES.md`。
   - 用途原句：| `EXTERNAL_DIRECTORIES.md` | CC、素材库、脚本、Bridge、输出、导出和 UE 工程在哪里，由谁维护 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md:L15` → `reference/EXTERNAL_DIRECTORIES.md`

### `GLOSSARY.md`

- 定位：`reference/GLOSSARY.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`2` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L238`，链接文字 `GLOSSARY.md`。
   - 用途原句：`README.md` 是参考索引；`IMPLEMENTATION_INDEX.md` 按 `WF-*` 定位代码/JSON/UE 资产；`EXTERNAL_DIRECTORIES.md` 定义本机路径和所有权；`GLOSSARY.md` 定义术语与 ID；`DOCUMENT_LINK_TRACE.md` 逐文件列出从 Master 出发的行号级提及链与回链。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/GLOSSARY.md`
2. **索引表提及**：`reference/README.md:L16`，链接文字 `GLOSSARY.md`。
   - 用途原句：| `GLOSSARY.md` | BodyFit、Manifest、Workflow、Gate、Validation、Look、Leader Pose 等术语是什么 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md:L16` → `reference/GLOSSARY.md`

### `IMPLEMENTATION_INDEX.md`

- 定位：`reference/IMPLEMENTATION_INDEX.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`7` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L238`，链接文字 `IMPLEMENTATION_INDEX.md`。
   - 用途原句：`README.md` 是参考索引；`IMPLEMENTATION_INDEX.md` 按 `WF-*` 定位代码/JSON/UE 资产；`EXTERNAL_DIRECTORIES.md` 定义本机路径和所有权；`GLOSSARY.md` 定义术语与 ID；`DOCUMENT_LINK_TRACE.md` 逐文件列出从 Master 出发的行号级提及链与回链。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/IMPLEMENTATION_INDEX.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L285`，链接文字 `IMPLEMENTATION_INDEX.md`。
   - 用途原句：6. 用 `IMPLEMENTATION_INDEX.md` 核对准确脚本、JSON、UE 资产和证据路径。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L285` → `reference/IMPLEMENTATION_INDEX.md`
3. **索引表提及**：`README.md:L22`，链接文字 `Implementation Index`。
   - 用途原句：| 查代码/JSON/UE 资产 | Implementation Index |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L22` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L22` → `reference/IMPLEMENTATION_INDEX.md`
4. **索引表提及**：`CURRENT_STATUS.md:L108`，链接文字 `Implementation Index`。
   - 用途原句：| 当前代码/JSON/UE 资产 | Implementation Index |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L108` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L108` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L108` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L108` → `reference/IMPLEMENTATION_INDEX.md`
5. **正文提及**：`workflow/WF-07-ANIMATION-AND-PROPS.md:L130`，链接文字 `IMPLEMENTATION_INDEX.md`。
   - 用途原句：通道分类和现有资产见 `ANIMATION_AND_MORPH_PIPELINE.md`，包级整理实现与证据见 `IMPLEMENTATION_INDEX.md` 的‘动画源发现与生产池开发’，Sprint 之后的动画池扩展见 `ROADMAP.md` 的 `RM-09R`。服装和变体边界见 `MODULAR_CHARACTER_RUNTIME.md`。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 `WF-08`，但其 Gate 通过前仍为 `planned`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L141` → `workflow/WF-07-ANIMATION-AND-PROPS.md:L130` → `reference/IMPLEMENTATION_INDEX.md`
6. **正文提及**：`ue_details/MODULAR_CHARACTER_RUNTIME.md:L44`，链接文字 `../reference/IMPLEMENTATION_INDEX.md`。
   - 用途原句：当前没有参数化的十体型 Blueprint 构建器，也没有独立的 v002 通用结构验证器。实现文件的完整定位见 `../reference/IMPLEMENTATION_INDEX.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L135` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L44` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L181` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L44` → `reference/IMPLEMENTATION_INDEX.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L222` → `ue_details/MODULAR_CHARACTER_RUNTIME.md:L44` → `reference/IMPLEMENTATION_INDEX.md`
7. **索引表提及**：`reference/README.md:L14`，链接文字 `IMPLEMENTATION_INDEX.md`。
   - 用途原句：| `IMPLEMENTATION_INDEX.md` | 每个 `WF-*` 实际使用哪些 Python、JSON、UE 资产和证据 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L238` → `reference/README.md:L14` → `reference/IMPLEMENTATION_INDEX.md`

## history

### `README.md`

- 定位：`history/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`4` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L242`，链接文字 `README.md`。
   - 用途原句：`README.md` 解释历史边界；`MILESTONE_LOG.md` 只追加完成事件；`reports/README.md` 索引日期化周报与阶段汇报。`legacy_2026-08-06/` 保存第一次重组前旧文档；`pre_lifecycle_restructure_2026-08-06/` 保存生命周期重构前 37 份原文；`pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` 保存本次数据链契约改写前的 Schema/Sampling…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md`
2. **索引表提及**：`README.md:L29`，链接文字 `History`。
   - 用途原句：| 查历史决定或旧原文 | ADR / History |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L29` → `history/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L29` → `history/README.md`
3. **元数据提及**：`history/reports/README.md:L7`，链接文字 `../README.md`。
   - 用途原句：> 上级入口：`../README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L7` → `history/README.md`
4. **元数据提及**：`history/MILESTONE_LOG.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `history/MILESTONE_LOG.md:L7` → `history/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/MILESTONE_LOG.md:L7` → `history/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L274` → `history/MILESTONE_LOG.md:L7` → `history/README.md`

### `README.md`

- 定位：`history/reports/README.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`3` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L242`，链接文字 `reports/README.md`。
   - 用途原句：`README.md` 解释历史边界；`MILESTONE_LOG.md` 只追加完成事件；`reports/README.md` 索引日期化周报与阶段汇报。`legacy_2026-08-06/` 保存第一次重组前旧文档；`pre_lifecycle_restructure_2026-08-06/` 保存生命周期重构前 37 份原文；`pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` 保存本次数据链契约改写前的 Schema/Sampling…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md`
2. **索引表提及**：`history/README.md:L15`，链接文字 `reports/README.md`。
   - 用途原句：| `reports/README.md` | 日期化周报和阶段汇报索引；只作汇报快照，不定义当前流程 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L15` → `history/reports/README.md`
3. **元数据提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7`，链接文字 `README.md`。
   - 用途原句：> 上级入口：`README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md` **[回链，不继续递归]**
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L7` → `history/reports/README.md`

### `MILESTONE_LOG.md`

- 定位：`history/MILESTONE_LOG.md`；从 Master 的最短层级为 `1`；状态：**可达**。
- 直接入站提及：`10` 次。

1. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L58`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：当前唯一活动计划是 第一批多轮编辑数据 Sprint：使用 F02/M02、8 个身份、同性各 4 套服装、32 个烘焙 Look、10 个生产动作（每个角色使用同性 5 个）、固定 Happy 表情、1 个场景和 `near/far/high/side` 四台生产相机，在服务器完整渲染 640 个唯一节点，并生成精确 4,000 条 3–5 轮编辑链及 15,000 回合双语 prompt。节点按 female/male 分成两个各 320 节点的连通兼容域；链按 `progressive_shortest/f…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `history/MILESTONE_LOG.md`
2. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L242`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：`README.md` 解释历史边界；`MILESTONE_LOG.md` 只追加完成事件；`reports/README.md` 索引日期化周报与阶段汇报。`legacy_2026-08-06/` 保存第一次重组前旧文档；`pre_lifecycle_restructure_2026-08-06/` 保存生命周期重构前 37 份原文；`pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` 保存本次数据链契约改写前的 Schema/Sampling…
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/MILESTONE_LOG.md`
3. **正文提及**：`CHARACTER_FACTORY_MASTER_SPEC.md:L274`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：- 已经发生过什么：`MILESTONE_LOG.md`。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L274` → `history/MILESTONE_LOG.md`
4. **元数据提及**：`CURRENT_STATUS.md:L11`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：> 更新方式：覆盖更新；完成事件只追加到 `MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L11` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L11` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L11` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L11` → `history/MILESTONE_LOG.md`
5. **索引表提及**：`CURRENT_STATUS.md:L111`，链接文字 `Milestone`。
   - 用途原句：| 已完成过程与证据 | Milestone / 周报 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/MILESTONE_LOG.md`
6. **正文提及**：`planning/ROADMAP.md:L12`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：已完成工作不在本文件复述，统一见 `MILESTONE_LOG.md` 和日期化周报。被放弃的方法不保留在活动 Roadmap；仍有长期解释价值的约束才保留在 ADR 或技术规范中。
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L184` → `planning/ROADMAP.md:L12` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L230` → `planning/ROADMAP.md:L12` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L271` → `planning/ROADMAP.md:L12` → `history/MILESTONE_LOG.md`
7. **索引表提及**：`history/README.md:L14`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：| `MILESTONE_LOG.md` | 只追加的完成事件、范围和证据入口 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L14` → `history/MILESTONE_LOG.md`
8. **元数据提及**：`history/reports/README.md:L8`，链接文字 `../MILESTONE_LOG.md`。
   - 用途原句：> 上游：`../MILESTONE_LOG.md` 与生成当日的现行状态/机器证据
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L8` → `history/MILESTONE_LOG.md`
9. **元数据提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8`，链接文字 `../MILESTONE_LOG.md`。
   - 用途原句：> 上游：`../MILESTONE_LOG.md`、`../../CURRENT_STATUS.md` 与本周机器报告
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L8` → `history/MILESTONE_LOG.md`
10. **索引表提及**：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122`，链接文字 `MILESTONE_LOG.md`。
   - 用途原句：| 本周完成事件 | `MILESTONE_LOG.md` |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md:L122` → `history/MILESTONE_LOG.md`

### `WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`

- 定位：`history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`；从 Master 的最短层级为 `2`；状态：**可达**。
- 直接入站提及：`4` 次。

1. **索引表提及**：`README.md:L28`，链接文字 `2026-08-13 至 2026-08-19 周报`。
   - 用途原句：| 查看本周汇报材料 | 2026-08-13 至 2026-08-19 周报 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L7` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L192` → `README.md:L28` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
2. **元数据提及**：`CURRENT_STATUS.md:L8`，链接文字 `2026-08-19 周报`。
   - 用途原句：> 上游：机器配置、验证报告、人工验收与 2026-08-19 周报
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L8` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
3. **索引表提及**：`CURRENT_STATUS.md:L111`，链接文字 `周报`。
   - 用途原句：| 已完成过程与证据 | Milestone / 周报 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L58` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L194` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L269` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L281` → `CURRENT_STATUS.md:L111` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`
4. **索引表提及**：`history/reports/README.md:L14`，链接文字 `WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`。
   - 用途原句：| `WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md` | 服装规则与门禁、P0 动画池、穿衣角色 CC→UE Pilot | 2026-08-19 项目汇报 |
    - `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/reports/README.md:L14` → `history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`

## 历史快照（Manifest 追溯）

归档正文不是现行规范，不参与当前链接图；以下链条通过 `history/README.md` 和 Manifest 的路径行定位。

### `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md`

- Manifest 入口：`CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md`
- 归档正文：`6` 份。

1.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L11` → `history/legacy_2026-08-06/README.md`
2.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L12` → `history/legacy_2026-08-06/STATUS.md`
3.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L13` → `history/legacy_2026-08-06/CHARACTER_FACTORY_MASTER_SPEC.md`
4.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L14` → `history/legacy_2026-08-06/FACIAL_GENERATION.md`
5.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L15` → `history/legacy_2026-08-06/FACIAL_GENERATION_NEXT_ITERATION_PLAN_2026-07-31.md`
6.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L16` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md` → `history/legacy_2026-08-06/ARCHIVE_MANIFEST.md:L16` → `history/legacy_2026-08-06/CHARACTER_REALISM_IMPROVEMENT_BACKLOG_2026-08-05.md`

### `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md`

- Manifest 入口：`CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md`
- Manifest 入口：`CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L18` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md`
- 归档正文：`2` 份。

1.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md:L14` → `history/pre_chain_contract_rewrite_2026-08-24/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md`
1.2. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L18` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md:L14` → `history/pre_chain_contract_rewrite_2026-08-24/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md`
2.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md:L15` → `history/pre_chain_contract_rewrite_2026-08-24/schema/CONFIG_GRAPH_SCHEMA_V1.md`
2.2. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L18` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md` → `history/pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md:L15` → `history/pre_chain_contract_rewrite_2026-08-24/schema/CONFIG_GRAPH_SCHEMA_V1.md`

### `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md`

- Manifest 入口：`CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md`
- 归档正文：`37` 份。

1.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L14` → `history/pre_lifecycle_restructure_2026-08-06/bridge_details/BRIDGE_OPERATIONS.md`
2.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L15` → `history/pre_lifecycle_restructure_2026-08-06/bridge_details/README.md`
3.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L16` → `history/pre_lifecycle_restructure_2026-08-06/cc_details/APPEARANCE_PIPELINE.md`
4.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/cc_details/BODYFIT_PIPELINE.md`
5.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L18` → `history/pre_lifecycle_restructure_2026-08-06/cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`
6.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L19` → `history/pre_lifecycle_restructure_2026-08-06/cc_details/FACE_IDENTITY_AND_AGE.md`
7.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L20` → `history/pre_lifecycle_restructure_2026-08-06/cc_details/README.md`
8.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L21` → `history/pre_lifecycle_restructure_2026-08-06/cc_ue_transfer/ASSET_TRACEABILITY.md`
9.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L22` → `history/pre_lifecycle_restructure_2026-08-06/cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`
10.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L23` → `history/pre_lifecycle_restructure_2026-08-06/cc_ue_transfer/README.md`
11.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L24` → `history/pre_lifecycle_restructure_2026-08-06/CHARACTER_FACTORY_MASTER_SPEC.md`
12.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L25` → `history/pre_lifecycle_restructure_2026-08-06/CURRENT_STATUS.md`
13.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L26` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md`
14.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L27` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0002-FACE-IDENTITY-V3.md`
15.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L28` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0003-AGE-VARIANTS.md`
16.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L29` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0004-APPEARANCE-POOLS.md`
17.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L30` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`
18.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L31` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`
19.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L32` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`
20.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L33` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`
21.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L34` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`
22.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L35` → `history/pre_lifecycle_restructure_2026-08-06/decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`
23.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L36` → `history/pre_lifecycle_restructure_2026-08-06/decisions/README.md`
24.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L37` → `history/pre_lifecycle_restructure_2026-08-06/DOCUMENTATION_RULES.md`
25.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L38` → `history/pre_lifecycle_restructure_2026-08-06/planning/BACKLOG.md`
26.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L39` → `history/pre_lifecycle_restructure_2026-08-06/planning/README.md`
27.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L40` → `history/pre_lifecycle_restructure_2026-08-06/planning/ROADMAP.md`
28.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L41` → `history/pre_lifecycle_restructure_2026-08-06/README.md`
29.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L42` → `history/pre_lifecycle_restructure_2026-08-06/reference/EXTERNAL_DIRECTORIES.md`
30.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L43` → `history/pre_lifecycle_restructure_2026-08-06/reference/GLOSSARY.md`
31.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L44` → `history/pre_lifecycle_restructure_2026-08-06/reference/IMPLEMENTATION_INDEX.md`
32.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L45` → `history/pre_lifecycle_restructure_2026-08-06/reference/README.md`
33.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L46` → `history/pre_lifecycle_restructure_2026-08-06/ue_details/ANIMATION_AND_MORPH_PIPELINE.md`
34.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L47` → `history/pre_lifecycle_restructure_2026-08-06/ue_details/MODULAR_CHARACTER_RUNTIME.md`
35.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L48` → `history/pre_lifecycle_restructure_2026-08-06/ue_details/README.md`
36.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L49` → `history/pre_lifecycle_restructure_2026-08-06/validation/README.md`
37.1. `CHARACTER_FACTORY_MASTER_SPEC.md:L242` → `history/README.md:L17` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md` → `history/pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md:L50` → `history/pre_lifecycle_restructure_2026-08-06/validation/VALIDATION_AND_RECOVERY.md`

## 生成统计

- 展开的提及链：`818` 条。
- 其中回链：`83` 条。
- 历史 Manifest：`3` 份。
- Manifest 登记的归档正文：`45` 份。

重新生成后必须运行文档审计器；两者退出码均为 0 才能提交文档结构变更。
