# PLAN-2026-08 文档体系 V2 重构

> 文档 ID：`PLAN-2026-08-DOCUMENTATION-V2`
> 文档类型：`completed_plan`
> 生命周期：`completed`
> 影响阶段：`global`
> 完成日期：2026-08-25
> 最近核验：2026-08-25

## 目标与结果

把主题堆叠式旧文档重建为可从 Master 沿生产逻辑定位到 Workflow、Technical、Validation、Status、Plan、ADR 和 History 的长期体系；同时明确外挂代码/输出归属、保留等级和维护方法。

## 完成项

- 完整审计文档、代码、输出和语义漂移；
- 建立 WF-00/10/.../90 长期流程和双层状态；
- 为 CC、Bridge、Transfer、UE、Dataset、Rendering、Validation 建立可执行技术文档；
- 建立路径/术语/Registry 反向索引；
- 建立 ADR-0015、统一输出契约和项目文档维护 Skill；
- 更新文档检查器并通过自动/人工导航审计；
- 重构前完整树保存在哈希快照中。
- 已确认完全被取代的早期机械重组暂存目录已清理；旧活跃树和原始哈希快照继续保留。

## 验收证据

- 活跃入口：`20_planning/data_design/character_creator/full_process/README.md`；98/98 活跃文档可从 Master 到达。
- 自动审计：`00_engine/scripts/documentation/check_character_factory_docs.py`，切换后无 error/warning。
- 脚本目录：`00_engine/scripts/SCRIPT_CATALOG.json`，Character Factory 两个实现根内 384 个脚本均有生命周期和 Technical owner。
- 输出目录：`00_engine/outputs/OUTPUT_INVENTORY.json` 与 `RETENTION_POLICY.json`；100 个作用域已盘点，未分类项默认受保护。
- 历史保护：`rebuild_reference_2026-08-25/SNAPSHOT_MANIFEST.json` 的 110 个文件和 Legacy 副本均通过 SHA-256 复核。
- 自动测试：Documentation/Dataset/Unreal 57 项、可视化门户 23 项、Bridge 1 项、可在系统 Python 运行的 CC 测试 193 项通过。
- 维护入口：`%DOC_SKILL_SOURCE%/SKILL.md` 是 Git 权威源，`%DOC_SKILL_ROOT%/SKILL.md` 是当前工作区安装副本；两者哈希一致并通过 Skill 结构验证。

三个只能在 CC 内部 PySide2/RLPy 环境收集的测试不计入系统 Python 通过数；这属于明确的运行环境边界，不被记录为实现失败。历史输出未在本计划中批量删除；100 个作用域均已有 Technical owner，91 个 `unclassified` 作用域已进入 Backlog，待逐项确认保留等级和替代关系。

## 未纳入范围与后续演进

本关闭记录对应 V2 首次切换时的 98 文档、100 输出作用域和当时测试结果。随后进行的 Workflow/Validation/Output/Technical/Status 等独立契约加固属于后续维护，不回写上述历史计数；当前数量、审计结果和唯一下一步必须以活动 Status、Catalog 和 Inventory 为准。
