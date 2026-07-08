# 文件系统与资产存储约定（当前 DataMake 工作区）

> 父层：[`./README.md`](./README.md) → [`../README.md`](../README.md) → [`../../README.md`](../../README.md)。
> 本文件是当前服务器上“东西放哪、怎么用”的权威约定。

## 一、当前结论（2026-07-08）

管理员已确认：**不能使用 `/local`**。当前阶段的 UE 安装、DDC、MVP 工程、Lance 等外部模型验证权重/cache 和少量输出都放在当前项目目录下：

```text
/scratch/prj0000000275/jcy/xks/DataMake
```

当前策略不是“所有东西都同步到一处”，而是三层：

| 层级 | 位置 | 角色 | 保留内容 | 不保留内容 |
|------|------|------|----------|------------|
| 本地交互预览层 | 用户本地 Windows / Laptop 4080 / 约 400G 可用 | 人工查看、调 UE 工程、少量资产组合验证 | UE 编辑器、少量精选角色/动作/场景、当前正在看的测试输出 | 完整资产库、完整生成数据集、长期缓存、批量中间帧 |
| 服务器生产工作层 | 当前 DataMake `/scratch` 目录 | 脚本化 UE、MCP/offscreen/MRQ smoke、当前批次生产 | UE 5.8、MVP 工程、当前批次资产、DDC、少量输出、外部模型验证权重 | 多版本 UE、历史批次全量输出、未筛选资产全集、长期冷归档 |
| 长期素材/冷存储层 | 待确认：实验室共享盘、专门 scratch 目录、对象存储、外接盘或 DVC/git-annex/rclone 后端 | 放完整资产包、历史版本、可复现实验输入、长期结果归档 | 原始资产包、下载凭据记录之外的非敏感元数据、可发布数据归档、hash manifest | Git 仓库正文、凭据、临时缓存 |

本地 400G 可以支撑交互预览和 MVP 子集，但不应作为完整素材库。服务器当前空间可以继续推进 MVP 和小批量验证；如果进入 100+ 角色、多动作、多场景和正式视频生成，必须先确定长期素材/冷存储层。

当前文件系统实测（2026-07-08，UE zip 已下载且 UE 5.8 已解压）：

```text
Filesystem: /scratch
Size:       2.8T
Used:       2.0T
Avail:      826G
Use%:       71%
```

这对 **单个 UE5.8 Installed Build + DDC + MVP 小规模渲染 + Lance 单模型验证** 比较宽裕，也足够启动第一批资产筛选和小批量 smoke；但仍然不应直接承诺正式规模资产全集和完整输出归档。UE zip 解压和验证后仍应删除或迁走下载包。正式大规模数据生产不在这个布局里直接展开，MVP 通过后另行规划。

## 二、容量边界

以下只是容量判断，不是硬上限。每次实际引入资产前，以资产台账记录的真实大小为准。

| 类型 | 常见规模 | 策略 |
|------|----------|------|
| UE 5.8 Installed Build | 已实测约 73G | 服务器保留一个主版本；本地按需安装；zip 解压确认后删除 |
| UE zip / 安装包 | 已实测约 38G | 只作临时下载包，不长期留在 DataMake |
| DDC / shader cache | 数十 GB 到上百 GB | 服务器保留当前工程 cache；可清理但会换时间成本 |
| 高质量场景 | 数 GB 到数十 GB | 只把当前 MVP/批次需要的场景放进服务器工作层 |
| 角色资产 | 数百 MB 到数 GB，复杂角色更大 | 本地只留精选预览子集；服务器只留当前批次 |
| 动作包 | 数十 MB 到数 GB | 可比角色更容易扩量，但仍需台账和筛选 |
| 渲染输出 | 取决于分辨率、时长、编码和中间帧 | 长期只保留最终视频、sidecar、manifest；中间帧默认可删除 |
| 外部模型权重 | 数 GB 到数十 GB | 明确模型范围后下载；避免 demo assets 和重复 cache |

本项目不把“资产全集同步到本地”作为目标。更合理的本地子集规模是：

```text
1-2 个场景
5-10 个角色
20-50 个动作
少量测试输出
```

服务器工作层的第一阶段目标是支持 MVP 和小批量 smoke，不直接承诺正式规模生产。正式规模启动前必须重新评估：资产总量、DDC 上限、输出编码策略、冷存储目标、清理脚本和恢复流程。

## 三、目录布局

在 `DataMake/` 下使用以下固定布局：

| 路径 | 用途 | Git 状态 |
|------|------|----------|
| `00_engine/unreal/UE_5.8/` | UE5.8 Linux 解压后的引擎目录 | 忽略 |
| `00_engine/unreal/downloads/` | UE zip / 临时下载包；解压确认后尽快删除 | 忽略 |
| `00_engine/runtime/` | 用户态补库目录；当前包含解包后的 `libgbm1` | 忽略 |
| `00_engine/cache/ddc/` | UE DDC / shader cache | 忽略 |
| `00_engine/cache/tmp/` | UE 临时目录 / staging | 忽略 |
| `00_engine/cache/ue_home/` | 只给 UE 进程使用的项目内 `HOME`，避免写真实 home | 忽略 |
| `00_engine/assets/` | 资产台账、来源说明、prototype-only/release 状态 | 台账和文档提交；原始资产忽略 |
| `00_engine/assets/raw/` | 当前工作批次原始资产包的服务器暂存区 | 忽略 |
| `00_engine/assets/prototype/` | 只用于内部管线测试的原型资产 | 忽略 |
| `00_engine/assets/marketplace/` | Marketplace/商店来源资产的工作副本 | 忽略 |
| `00_engine/assets/released/` | 已确认可用于发布/训练的数据资产工作副本 | 忽略 |
| `00_engine/projects/` | MVP UE 工程；初期可先不进 Git，稳定后只提交源码/配置 | 部分忽略 |
| `00_engine/outputs/mvp/` | MVP 少量验证输出 | 忽略 |
| `00_engine/logs/` | UE 安装、启动、渲染日志 | 忽略；摘要可进文档 |
| `10_research/model_experiments/lance/lance/` | Lance 上游代码仓库 | 忽略 |
| `10_research/model_experiments/lance/models/` | Lance 权重 | 忽略 |
| `10_research/model_experiments/lance/inputs/` | Lance 自测输入、prompt 和 clean 输入副本 | 部分提交 |
| `10_research/model_experiments/lance/outputs/` | Lance 能力验证输出 | 忽略 |
| `10_research/model_experiments/lance/logs/` | Lance 运行日志和自动生成 config | 忽略；摘要可进文档 |

推荐环境变量：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
export UE_RUNTIME_LIB_DIR="$DATAMAKE_ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu"
export HF_HOME="/scratch/prj0000000275/jcy/.cache/huggingface"
```

> Linux 下 DDC 变量使用 `UE_LocalDataCachePath`（下划线），不要用 Windows 风格的 `UE-LocalDataCachePath`。
> 日常 UE 命令直接使用 `00_engine/scripts/run_ue_cmd.sh`，脚本会设置上述 UE 变量和 `LD_LIBRARY_PATH`。

## 四、本地/服务器/冷存储同步规则

### 本地交互预览层

- 本地只保存“正在看的小切片”，不追求完整资产覆盖。
- 本地工程和服务器工程必须能通过 Git 中的脚本、配置和台账重新建立关系；不要靠手工复制后的隐含状态。
- 本地导入资产时，先在台账中登记 `asset_id`、来源、许可证、用途状态和存放层级，再决定是否同步服务器。
- 本地输出只用于人工挑选和调参；稳定结论回写文档，样例文件按需传到服务器或冷存储。

### 服务器生产工作层

- 服务器只放当前批次需要的资产工作副本和必要 cache。
- 批量渲染默认保留最终压缩视频、sidecar metadata、manifest、日志摘要；中间帧、临时工程副本和重复导入包默认可清理。
- `00_engine/assets/raw/`、`prototype/`、`marketplace/`、`released/` 是工作副本区，不是长期归档区。
- 正式生产前必须为每个资产在台账中标记 `storage_server=present` 和 `cold_archive=present/planned`。

### 长期素材/冷存储层

- 当前尚未指定具体位置；在正式规模生产前必须由用户确认。
- 冷存储保存资产原包、hash manifest、许可证取证材料、可复现实验输入和最终发布候选数据。
- 冷存储路径不写死到脚本核心逻辑中；脚本读取台账或 manifest，允许后续迁移。
- Git 只提交台账、manifest、schema、下载说明和 hash，不提交资产本体。

## 五、资产台账与准入

资产进入项目的核心准入状态分三种：

| 状态 | 含义 | 可做什么 | 不能做什么 |
|------|------|----------|------------|
| `candidate` | 候选资产，尚未完成来源/许可证/大小核查 | 本地或服务器短期试看 | 进入正式训练/发布数据 |
| `prototype-only` | 只允许内部管线测试或视觉原型 | 测脚本、测导入、测动画绑定 | 混入可发布数据、作为训练数据发布 |
| `cleared` | 来源、许可证、训练权、再分发权、NoAI 状态已确认 | 可进入对应授权范围内的数据生成 | 超出授权范围使用 |

台账 schema 见 [`../../00_engine/assets/asset_ledger_schema.md`](../../00_engine/assets/asset_ledger_schema.md)。实际引入第一批资产时，再创建并提交 `00_engine/assets/asset_ledger.csv` 或等价的 YAML/JSON manifest。

最小准入字段：

```text
asset_id, type, source_url_or_package, license, noai_status,
training_allowed, redistribution_allowed, provenance_date,
raw_size_gb, imported_size_gb, status,
storage_local, storage_server, cold_archive,
notes
```

没有台账记录的资产只能视为临时草稿，不能进入训练/发布候选。

## 六、为什么这样放

- 当前 `/scratch` 是 WekaFS/网络盘，小文件 I/O 可能慢，但管理员限制下这是可用方案。
- 服务器空间足够当前 MVP 和 Lance 这类单模型验证；要避免同时保留多个 UE 版本、大量 zip、海量 EXR、多个大模型权重和正式数据集。
- 用户本地 400G 不适合承载完整素材库，但适合做图形化预览和小子集组合验证。
- UE 相关内容集中在 `00_engine/`，研究和模型验证集中在 `10_research/`，讨论/计划集中在 `20_planning/`。
- DDC 路径固定在 `00_engine/cache/ddc/`，避免每次换路径导致重复 shader/cache 构建。
- 所有大文件和缓存目录都由 `.gitignore` 排除，避免本地 Git 仓库被大文件污染。
- Lance 当前采用用户已配置的 scratch 全局 HF cache：`/scratch/prj0000000275/jcy/.cache/huggingface`；可运行权重目录放在 `10_research/model_experiments/lance/models/Lance/`，避免重复下载和默认写入小 home。

## 七、使用纪律

1. UE zip 解压成功并在 GPU 节点确认可运行后，删除或转移 `00_engine/unreal/downloads/` 里的 zip。即使当前可用空间约 826G，也不要长期保留下载包。
2. MVP 输出控制在几十 GB 量级；不要直接开高分辨率、多通道、大规模 job-array。
3. 大型资产下载前先登记候选台账；没有许可证结论时标记 `candidate` 或 `prototype-only`。
4. 外部模型下载前先明确范围；不要整仓库拉 demo assets，优先用 allowlist 下载权重和配置。
5. `00_engine/outputs/`、`00_engine/cache/`、`10_research/model_experiments/*/outputs/`、`10_research/model_experiments/*/logs/` 不作为长期归档。
6. 重要脚本、配置、文档应进入 Git；引擎、缓存、输出、模型权重和资产大包不进 Git。
7. 每次大渲染、模型下载或资产导入前先检查空间：

```bash
df -h /scratch/prj0000000275/jcy/xks/DataMake
du -sh 00_engine 00_engine/assets 10_research/model_experiments 20_planning 2>/dev/null
```

## 八、历史方案（已废弃）

2026-06-19 的三层方案曾计划：

- `/local/$USER` 放 engine/DDC/render scratch；
- `/scratch` 放大成品；
- `/home` 放工程源/备份。

该方案已被 2026-06-28 的管理员限制取代：**当前不能使用 `/local`**。旧方案只作为历史背景保留，不再作为执行方案。

## Agent 备忘

- 当前权威结论：**所有当前阶段工作都在 DataMake 目录下完成**。
- 网络盘小文件慢是已知风险，不再反复争论；MVP 和单模型验证阶段通过控制规模接受该风险。
- 本地 400G 只作为交互预览层；不要建议把完整资产库同步到本地。
- 服务器 DataMake 是生产工作层，不是长期冷归档层。
- 长期素材/冷存储位置尚未确定；正式规模生产前必须补齐。
- Hugging Face / model cache 必须显式指向 scratch 上的可用路径。当前 Lance 使用 `/scratch/prj0000000275/jcy/.cache/huggingface`；不要落回默认小 home。
- 如果后续进入正式大规模生产，必须重新讨论存储，不能沿用本 MVP 布局直接扩量。
