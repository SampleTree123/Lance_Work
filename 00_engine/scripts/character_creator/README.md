# Character Creator 脚本与机器配置

本目录保存当前 Character Creator 角色工厂的系统 Python 生成器、CC/RLPy 执行器和机器 JSON。它不是人类流程总入口。

当前文档：

- 总规范：[`CHARACTER_FACTORY_MASTER_SPEC.md`](../../../20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md)
- 逐步实现索引：[`IMPLEMENTATION_INDEX.md`](../../../20_planning/data_design/character_creator/full_process/reference/IMPLEMENTATION_INDEX.md)
- CC 装配 Runbook：[`CHARACTER_ASSEMBLY_RUNBOOK.md`](../../../20_planning/data_design/character_creator/full_process/cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md)
- 验证与恢复：[`VALIDATION_AND_RECOVERY.md`](../../../20_planning/data_design/character_creator/full_process/validation/VALIDATION_AND_RECOVERY.md)

运行边界：

- 生成器、编译器、汇总器和联系表可以在系统 Python 中运行。
- 导入 `RLPy` 的文件只能由 Character Creator 内 Python 或 Bridge 插件加载。
- `runtime_staging/<run_id>` 是按需生成的 Bridge 输入暂存区，不应提交 Git。
- 精确配置以当前 registry 和 library JSON 为准；历史 probe 文件不得作为默认入口。
