# Lance_Work / DataMake

用于构建可追溯的 Unreal Engine 多轮视频编辑数据集。系统把 Character Creator 角色、Unreal 场景与表演资产、确定性配置图、原子编辑链、文本指令和节点媒体连接为可复现的生产流水线；当前不负责模型训练。

新会话先读 [`HANDOFF.md`](./HANDOFF.md)。角色工厂与数据生产的唯一主入口是 [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md)，当前事实与唯一下一步见 [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)。

## 数据模型

一个节点由全部受控因素唯一确定：

```text
C = {identity, body_fit, outfit, action, expression, scene, camera, lighting}
render(C) -> media(node_id)
```

一条原子边只改变一个允许编辑轴。多轮样本沿图中的连续原子边构成，上一轮的真实输出节点直接成为下一轮输入，不重新渲染伪造端点。

配置图、兼容域、链策略与文本 Schema 分别由：

- [`CONFIG_GRAPH_SCHEMA_V1.md`](./20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md)
- [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)
- [`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](./20_planning/data_design/schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)

定义。当前批次的精确数量和冻结资产不在本页重复维护。

## 执行入口

| 目标 | 入口 |
| --- | --- |
| 理解完整生产流程 | [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md) |
| 查看当前状态、计划和下一步 | [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md) |
| 定位十个生产阶段 | [`workflow/README.md`](./20_planning/data_design/character_creator/full_process/workflow/README.md) |
| 查找准确脚本、命令和输出 | [`technical/README.md`](./20_planning/data_design/character_creator/full_process/technical/README.md) |
| 查看代码目录 | [`00_engine/scripts/README.md`](./00_engine/scripts/README.md) |
| 服务器预检 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](./20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |

不要从旧计划、历史截图或名字相近的脚本推断当前生产方式。先由 Workflow 定位 Technical，再执行 Technical 声明的代码和 Registry。

## 仓库结构

```text
Lance_Work/
├── .codex/         # 可迁移的项目 Skill 权威源
├── 00_engine/      # CC/UE/数据图实现、Bridge、审查工具和运行输出
├── 10_research/    # 外部模型与工具研究，不阻塞当前数据生产
├── 20_planning/    # 数据契约、完整生产文档、计划、状态与历史
├── README.md       # GitHub 总入口
├── HANDOFF.md      # 新会话接手入口
└── AGENTS.md       # 协作和仓库维护规则
```

## 资产与输出边界

Git 保存代码、Markdown、JSON、Manifest、哈希和适合版本控制的证据。CC 二进制资产、UE `Content/`、`.uasset/.umap`、DDC 和批量媒体通过独立资产包或本地/服务器工作层管理，但必须由 Registry、Technical 文档和 Batch Manifest 追溯。

`00_engine/outputs/` 不是天然可删除的缓存。保留策略与当前盘点见：

```text
00_engine/outputs/RETENTION_POLICY.json
00_engine/outputs/OUTPUT_INVENTORY.json
```

## 快速校验

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/documentation/tests 00_engine/scripts/dataset/tests 00_engine/scripts/unreal/tests -q
```


## 数据集设计决定入口

2026-10-21：新阶段节点/边/链与参考素材的已确认规则见[试构建契约](./20_planning/data_design/character_creator/full_process/technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)。执行状态仍由PROJECT_STATUS拥有，旧探索不自动成为正式渲染规格。

同日补充：用户接受每个视频只安排部分合法编辑目标，以整个数据集的多样性为前提；不再要求每个源视频具备全目录目标。具体边界见上述契约“最新确认”节，旧试构建保留为历史实验。

2026-10-21第四轮反馈：用户明确以单项属性值覆盖为主，接受每个人物的服装/发型等搭配范围缩小；不要求恢复旧版跨属性搭配数量。服装条件比例另行澄清，详见上述试构建契约。

2026-10-22：用户已授权第五轮离线平衡构图，训练要求实际使用节点与编辑目标全单项值覆盖，测试不强求所有具体值、保持七轴充分样本并尽量广覆盖；保留服装条件50/50并加入有向边复用上限与全历史权重衰减。规则入口仍为[试构建契约](./20_planning/data_design/character_creator/full_process/technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)最新修订；第五轮离线候选及同图三sampling seed检查已完成，是否采用待用户审查；初始镜头分布仍受图影响，旧实验保留，未启动渲染。
