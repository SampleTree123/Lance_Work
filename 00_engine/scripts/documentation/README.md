# 文档维护工具

本目录维护 Character Factory 文档树、脚本生命周期和输出保留清单。详细契约分别见 [文档体系审计](../../../20_planning/data_design/character_creator/full_process/technical/validation/DOCUMENTATION_VALIDATION.md)、[脚本生命周期与所有权](../../../20_planning/data_design/character_creator/full_process/technical/implementation/SCRIPT_LIFECYCLE.md) 和 [输出盘点与保留](../../../20_planning/data_design/character_creator/full_process/technical/output/INVENTORY_AND_RETENTION.md)。

## 工具

- `build_script_lifecycle_catalog.py`：生成 `00_engine/scripts/SCRIPT_CATALOG.json`。
- `build_output_inventory.py`：按 `RETENTION_POLICY.json` 生成 `OUTPUT_INVENTORY.json`，不删除文件。
- `check_character_factory_docs.py`：检查元数据、链接、Master 可达性、目录索引、十阶段 Workflow、当前计划/状态、脚本 owner 和输出保留规则。
- `generate_character_factory_link_trace.py`：旧体系兼容工具；只在专项诊断时使用，不把逐行追踪结果提交为活跃人工文档。

## 标准命令

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/documentation/tests -q
```

重建暂存树可通过 `--doc-root` 和 `--root` 显式指定。正常运行不传参数，始终审计 `full_process/` 当前树。
