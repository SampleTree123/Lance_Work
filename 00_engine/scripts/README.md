# `00_engine/scripts` 实现代码入口

本目录保存 Character Creator、Unreal Engine、数据图和文档维护代码。它是实现目录，不是项目状态或生产顺序的权威入口。

开始执行前按以下路径定位：

```text
full_process/README.md
  -> workflow/WF-*.md
  -> technical/<domain>/*.md
  -> 本目录中的脚本/配置/测试
```

当前阶段、活动批次、冻结数量和唯一下一步只从 [`PROJECT_STATUS.md`](../../20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md) 获取。

## 子目录

| 路径 | 主要实现 | Technical 所有者 |
| --- | --- | --- |
| [`character_creator/`](./character_creator/README.md) | CC 角色、服装、动作、导出与视觉验证 | [CC 技术索引](../../20_planning/data_design/character_creator/full_process/technical/character_creator/README.md) |
| [`unreal/`](./unreal/README.md) | UE 导入、运行时、动画/表情、Sequence 和渲染 | [UE 技术索引](../../20_planning/data_design/character_creator/full_process/technical/unreal/README.md) |
| [`dataset/`](./dataset/README.md) | 配置图、原子边、链、Prompt 和作业清单 | [Dataset 技术索引](../../20_planning/data_design/character_creator/full_process/technical/dataset/README.md) |
| [`documentation/`](./documentation/README.md) | 文档目录、输出盘点与结构审计 | [文档验证](../../20_planning/data_design/character_creator/full_process/technical/validation/DOCUMENTATION_VALIDATION.md) |

根目录 shell 脚本提供 Linux/服务器侧 UE 环境和命令包装，其运行边界见 [服务器执行](../../20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md)。

## 脚本生命周期

全部 `.py/.ps1/.sh/.cmd` 的机器目录为：

```text
00_engine/scripts/SCRIPT_CATALOG.json
```

Catalog 记录路径、SHA-256、生命周期、活动批次标记和 Technical owner。`production` 才是当前正式实现；`validated_pilot` 只在登记范围内有效；`experimental` 不能作为生产入口。不要仅根据文件名或较新的时间戳选择脚本。

重新生成：

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
```

规则见 [脚本生命周期与所有权](../../20_planning/data_design/character_creator/full_process/technical/implementation/SCRIPT_LIFECYCLE.md)。

## 校验

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json

python -m pytest `
  00_engine/scripts/documentation/tests `
  00_engine/scripts/dataset/tests `
  00_engine/scripts/unreal/tests -q
```

需要 CC 内置 Python、PySide2、UE Editor/MCP、二进制资产或服务器环境的测试不能由普通系统 Python 替代。无法运行时记录准确边界，不把未执行写成通过。
