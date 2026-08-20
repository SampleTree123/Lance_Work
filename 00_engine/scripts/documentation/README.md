# 文档校验工具

本目录维护 Character Factory 文档树的只读结构检查和引用追踪工具。

## 命令

```powershell
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python 00_engine/scripts/documentation/generate_character_factory_link_trace.py
python -m pytest 00_engine/scripts/documentation/tests -q
```

- `check_character_factory_docs.py`：检查 metadata、文档 ID、工作流固定章节、链接、归档清单和可达性。
- `generate_character_factory_link_trace.py`：从主规范生成递归引用路径，更新文档树追踪结果。

提交前检查器必须为 `0 errors / 0 warnings`。生成引用追踪会修改文档时，应检查 diff 后再提交，不能把生成动作当作只读校验。

权威文档入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](../../../20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md)。
