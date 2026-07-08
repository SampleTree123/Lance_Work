# asset ledger schema —— 资产台账字段

> 父层：[`./README.md`](./README.md) → [`../README.md`](../README.md) → [`../../README.md`](../../README.md)。
> 本文件定义资产进入 DataMake 前必须记录的字段。实际台账可用 `asset_ledger.csv`、`asset_ledger.yaml` 或数据库导出，但字段语义以本文为准。

## 目的

资产台账不是素材文件夹清单，而是每个资产的来源、许可证、用途状态、容量和存储位置的可审计记录。

没有台账记录的资产只能作为临时草稿，不得进入训练/发布候选数据。

## 资产状态

| 状态 | 含义 | 允许用途 |
|------|------|----------|
| `candidate` | 候选资产，尚未完成来源、许可证或技术验证 | 本地/服务器短期试看，不能进入训练/发布候选 |
| `prototype-only` | 明确只能用于内部管线测试或视觉原型 | 测导入、测脚本、测动画绑定、测渲染流程 |
| `cleared` | 来源、许可证、训练权、再分发权和 NoAI 状态已确认 | 在授权范围内进入数据生成 |
| `rejected` | 技术或合规原因不使用 | 保留记录，避免重复引入 |
| `archived` | 当前批次不用，但冷存储保留 | 未来可按台账恢复 |

## 字段定义

| 字段 | 必填 | 示例 | 说明 |
|------|------|------|------|
| `asset_id` | 是 | `char_0001`, `motion_walk_0007`, `scene_city_0002` | 稳定唯一 ID，不随文件名变化 |
| `asset_type` | 是 | `character`, `motion`, `scene`, `prop`, `accessory`, `material`, `audio` | 资产类型 |
| `display_name` | 是 | `Business Woman A` | 人类可读名称 |
| `source_kind` | 是 | `marketplace`, `public_dataset`, `self_made`, `generated`, `unknown` | 来源类别 |
| `source_name` | 是 | `Fab`, `Mixamo`, `internal` | 来源平台或包名 |
| `source_url_or_package` | 是 | `https://...` 或包名 | 可追溯来源；离线包写包名和来源记录路径 |
| `provenance_date` | 是 | `2026-07-08` | 取证日期；外部事实必须带日期 |
| `license_name` | 是 | `CC-BY-4.0`, `Marketplace EULA`, `unknown` | 许可证名称 |
| `license_evidence` | 是 | `docs/licenses/char_0001_20260708.pdf` | 许可证截图、网页存档或说明的路径/引用 |
| `noai_status` | 是 | `allows_training`, `noai`, `unknown` | 是否带 NoAI/禁止训练限制 |
| `training_allowed` | 是 | `yes`, `no`, `unknown` | 是否允许用于训练数据 |
| `redistribution_allowed` | 是 | `yes`, `no`, `unknown` | 是否允许再分发资产或衍生数据 |
| `commercial_allowed` | 是 | `yes`, `no`, `unknown` | 是否允许商业用途；即使本项目暂不商业化也要记录 |
| `status` | 是 | `candidate`, `prototype-only`, `cleared` | 资产状态 |
| `raw_size_gb` | 是 | `1.8` | 原始下载/压缩/解包资产大致大小 |
| `imported_size_gb` | 否 | `3.2` | 导入 UE 后大小；未知可留空 |
| `storage_local` | 是 | `absent`, `present`, `planned` | 本地预览层是否保留 |
| `storage_server` | 是 | `absent`, `present`, `planned` | DataMake 服务器工作层是否保留 |
| `cold_archive` | 是 | `absent`, `present`, `planned` | 长期素材/冷存储是否保留 |
| `local_path_hint` | 否 | `D:/DataMakeAssets/...` | 本地路径提示；不要写凭据 |
| `server_path_hint` | 否 | `00_engine/assets/prototype/...` | 服务器工作副本路径 |
| `cold_path_hint` | 否 | `TBD` | 冷存储路径；可迁移，不写死进生产脚本 |
| `hash_sha256` | 否 | `...` | 原包或 manifest hash；正式归档建议必填 |
| `ue_import_status` | 是 | `not_imported`, `imported`, `failed` | UE 导入状态 |
| `technical_notes` | 否 | `skeleton=UE5 Manny compatible` | 骨骼、材质、贴图、动作绑定等技术说明 |
| `dataset_role` | 是 | `mvp`, `batch-candidate`, `excluded` | 当前项目中的用途 |
| `review_owner` | 否 | `stuchengyou` | 谁做过人工确认 |
| `last_review_date` | 否 | `2026-07-08` | 最近一次复查日期 |
| `notes` | 否 | `prototype only until license confirmed` | 其他说明 |

## 最小 CSV 表头

```csv
asset_id,asset_type,display_name,source_kind,source_name,source_url_or_package,provenance_date,license_name,license_evidence,noai_status,training_allowed,redistribution_allowed,commercial_allowed,status,raw_size_gb,imported_size_gb,storage_local,storage_server,cold_archive,local_path_hint,server_path_hint,cold_path_hint,hash_sha256,ue_import_status,technical_notes,dataset_role,review_owner,last_review_date,notes
```

## 路径与存储规则

服务器工作副本路径按状态区分：

```text
00_engine/assets/raw/          # 当前批次原始包暂存，不长期归档
00_engine/assets/prototype/    # prototype-only 工作副本
00_engine/assets/marketplace/  # marketplace/商店来源工作副本
00_engine/assets/released/     # cleared 且允许进入发布/训练候选的工作副本
```

这些目录默认不进 Git。Git 只提交台账、schema、下载说明、hash manifest 和必要的许可证记录摘要。

## 准入流程

1. 先登记 `candidate`，记录来源、日期、预估大小和许可证未知项。
2. 下载或复制到本地/服务器工作副本区，补 `raw_size_gb` 和路径提示。
3. 做 UE 导入或动作绑定 smoke，更新 `ue_import_status` 和技术说明。
4. 合规不完整但可用于内部测试的，标记 `prototype-only`。
5. 来源、许可证、训练权、再分发权和 NoAI 状态都确认后，才可标记 `cleared`。
6. 进入批量生产前，必须确认 `storage_server=present`，并为可复现实验准备 `cold_archive=present` 或 `planned`。

## Agent 备忘

- 不要把缺少许可证结论的资产写成 `cleared`。
- `prototype-only` 可以服务管线测试，但不能混入训练/发布候选。
- 大文件路径可以写相对路径或路径提示；不要把凭据、下载 token 或一次性签名 URL 写进台账。
- 正式规模生产前，必须先确定冷存储层位置，并为已用资产补齐 `hash_sha256`。
