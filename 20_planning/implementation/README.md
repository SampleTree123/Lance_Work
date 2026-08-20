# implementation —— 实施环境与风险

> 父层：[`../README.md`](../README.md) → [`../../README.md`](../../README.md)。

本目录放项目运行层面的事实：存储、服务器环境、风险登记和执行前检查。它不定义数据样本本身。

## 内容说明

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md` | 本层索引和维护规则 | 当前 |
| `storage.md` | 当前 DataMake 工作区、三层资产存储策略、缓存/权重/输出路径 | 当前权威 |
| `local_asset_workflow.md` | 本地 UE 整理资产、上传服务器工作副本、Git/素材分离规则 | 当前 |
| `environment.md` | UE 版本、本机/服务器分工、远程 UI、配套软件、工程同步 | 历史调研稿 |
| `risks.md` | 可行性与风险登记、go 判定、服务器自检记录 | 当前风险表 |
| [`FIRST_BATCH_SERVER_RUNBOOK.md`](./FIRST_BATCH_SERVER_RUNBOOK.md) | 第一批数据的 Linux/UE 5.8 同步、预检、10 节点基准、批量渲染与重试边界 | 当前计划 |
| [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](./FIRST_BATCH_SERVER_PREFLIGHT.sh) | 第一批数据服务器的可执行预检；采集 Linux/NVIDIA/Vulkan/UE 5.8 证据，并在项目已上传时执行插件检查和两次离屏启动 smoke | 当前可执行入口 |

## 当前服务器同步状态（2026-08-20）

- GitHub `main` 已包含当前代码、文档、JSON 配置、manifest 与轻量证据。
- CC/UE 二进制资产、正式 UE `Content/` 和项目工作副本不通过 Git 分发，仍需按资产 manifest 独立上传。
- 资产包未上传时，可先运行 `FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only`。
- 项目上传后必须继续执行项目插件/大小写路径检查、两次离屏 smoke 和 10 节点基准；环境预检通过不等于生产门禁通过。

## 维护规则

- 这里记录“在哪里运行、东西放哪、有什么风险”，不要把具体数据 schema 写在这里。
- 服务器、驱动、UE 版本、许可证、集群策略等外部事实必须带日期；执行前重新核实。
- 存储策略以 [`storage.md`](./storage.md) 为准。管理员已确认不能使用 `/local`。
- 当前本地机器只作为交互预览层；服务器 DataMake 是生产工作层；长期素材/冷存储层尚未确定，正式规模生产前必须补齐。
- 本地找素材、导入 UE、打包给服务器的流程以 [`local_asset_workflow.md`](./local_asset_workflow.md) 为准。

## Agent 备忘

- 当前 DataMake 工作区已是本地 Git 仓库，分支 `main`。
- 大文件、模型权重、UE、缓存和输出不进 Git。
- 资产进入项目前先看 [`../../00_engine/assets/asset_ledger_schema.md`](../../00_engine/assets/asset_ledger_schema.md)，没有台账记录的资产不得进入训练/发布候选。
- 本地 clone 后阅读项目进度，优先看 `HANDOFF.md`、顶层 `README.md`、`local_asset_workflow.md` 和资产台账 schema。
- 每次安装 UE、下载模型或跑大输出前，先检查 `storage.md` 和 `git status --short`。
