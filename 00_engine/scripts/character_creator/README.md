# Character Creator 实现目录

本目录保存 CC 系统 Python 生成器、RLPy Payload、Registry、审查配置和测试。人类流程从 [CC 技术索引](../../../20_planning/data_design/character_creator/full_process/technical/character_creator/README.md) 进入。

## 运行边界

- 普通生成器、编译器、汇总器和 Registry 审计可由系统 Python 运行。
- 导入 `RLPy` 的脚本只能由 Character Creator 内置 Python 或受控 Bridge 执行。
- `runtime_staging/<run_id>` 是 Bridge 临时输入，不进入 Git 或长期证据。
- 源 CC 项目与资产库默认只读；规范项目、导出 Bundle 和证据写入对应 Technical 规定的目标。
- 名字包含 `probe/pilot/review` 的脚本不能仅凭存在升级为生产入口。

## 选择入口

- BodyFit、Identity、Headshot 与年龄：[BODYFIT_IDENTITY_AGE.md](../../../20_planning/data_design/character_creator/full_process/technical/character_creator/BODYFIT_IDENTITY_AGE.md)
- 皮肤、眼睛、眉毛、睫毛、牙齿、胡须与头发：[APPEARANCE_ASSETS.md](../../../20_planning/data_design/character_creator/full_process/technical/character_creator/APPEARANCE_ASSETS.md)
- 服装与鞋池：[OUTFIT_SYSTEM.md](../../../20_planning/data_design/character_creator/full_process/technical/character_creator/OUTFIT_SYSTEM.md)
- 角色组装、验收和 Bundle：[ASSEMBLY_AND_ACCEPTANCE.md](../../../20_planning/data_design/character_creator/full_process/technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md)
- Bridge 操作：[CC_BRIDGE_OPERATIONS.md](../../../20_planning/data_design/character_creator/full_process/technical/bridge/CC_BRIDGE_OPERATIONS.md)

完整脚本生命周期和 owner 由 `../SCRIPT_CATALOG.json` 提供；当前批次精确矩阵由 Batch Status 和 Registry 提供，不在本页复制。
