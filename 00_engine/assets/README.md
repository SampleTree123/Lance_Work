# assets —— 引擎资产入口

> 父层：[`../README.md`](../README.md)。

本目录记录会进入 UE 合成画面的角色、服装、动作、场景、道具和配饰。当前阶段尚未引入正式资产；原型资产可以用于内部管线验证，但必须明确标记 `prototype-only`。

## 内容说明

| 文件/路径 | 内容 | Git 策略 |
|-----------|------|----------|
| `README.md` | 本层说明 | 提交 |
| `asset_ledger_schema.md` | 资产台账字段、状态和准入流程 | 提交 |
| `asset_ledger.csv` / `asset_ledger.yaml` | 未来实际资产台账 | 提交 |
| `raw/` | 当前批次原始资产包暂存 | 忽略 |
| `prototype/` | 只用于内部测试的原型资产 | 忽略 |
| `marketplace/` | 商店/Marketplace 来源资产工作副本 | 忽略 |
| `released/` | 已确认可用于发布/训练候选的数据资产工作副本 | 忽略 |

## 存储定位

资产不默认完整同步到本地，也不默认永久保存在服务器工作目录。

- 本地只放小规模预览子集，用于人工看效果和调 UE。
- 服务器只放当前批次生产需要的工作副本。
- 完整资产包、历史版本和可复现实验输入应进入长期素材/冷存储层；该位置尚未确定，正式规模生产前必须补齐。

完整策略见 [`../../20_planning/implementation/storage.md`](../../20_planning/implementation/storage.md)。

本地 UE 整理资产、打包上传服务器和 Git/素材分离规则见 [`../../20_planning/implementation/local_asset_workflow.md`](../../20_planning/implementation/local_asset_workflow.md)。

## 约定

- 原始资产包、大型贴图、压缩包、下载缓存不进 Git。
- 每个可能进入训练/发布数据的资产必须记录来源、许可证、NoAI 状态、训练权、再分发权和取证日期。
- 实际引入第一批资产时，先按 [`asset_ledger_schema.md`](./asset_ledger_schema.md) 创建台账，再下载或导入资产。
- 许可证策略见 [`../../20_planning/compliance/licensing_compliance.md`](../../20_planning/compliance/licensing_compliance.md)。
- 资产形态与数据设计的关系见 [`../../20_planning/data_design/README.md`](../../20_planning/data_design/README.md)。
- 本地导入 UE 的 `Content/` 二进制资产不进 Git；服务器需要时通过资产包、`rsync`、压缩包或后续冷存储同步工具传输。

## Agent 备忘

- 不要把 `prototype-only` 资产误写成可训练或可发布。
- 不要建议把完整素材库同步到用户本地；本地只保留当前预览子集。
- 真正引入资产时先建台账，再写下载/转换步骤。
- 用户准备推送远程 Git 前，确认没有 `.uasset`、`.umap`、视频、压缩包或模型权重进入 tracked files。
