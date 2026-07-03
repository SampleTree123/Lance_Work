# 文件系统使用约定（当前单目录方案）

> 父层：[`./README.md`](./README.md) → [`../README.md`](../README.md) → [`../../README.md`](../../README.md)。
> 本文件是当前服务器上“东西放哪、怎么用”的权威约定。

## 一、当前结论（2026-07-01）

管理员已确认：**不能使用 `/local`**。当前阶段的 UE 安装、DDC、MVP 工程、Lance 等外部模型验证权重/cache 和少量输出都放在当前项目目录下：

```text
/scratch/prj0000000275/jcy/xks/DataMake
```

当前文件系统实测（2026-07-01）：

```text
Filesystem: /scratch
Size:       2.8T
Used:       2.0T
Avail:      766G
Use%:       73%
```

这对 **UE5.8 安装 + DDC + MVP 小规模渲染 + Lance 单模型验证** 足够。正式大规模数据生产不在这个布局里直接展开，MVP 通过后另行规划。

## 二、目录布局

在 `DataMake/` 下使用以下固定布局：

| 路径 | 用途 | Git 状态 |
|------|------|----------|
| `00_engine/unreal/UE_5.8/` | UE5.8 Linux 解压后的引擎目录 | 忽略 |
| `00_engine/unreal/downloads/` | UE zip / 临时下载包；解压确认后尽快删除 | 忽略 |
| `00_engine/cache/ddc/` | UE DDC / shader cache | 忽略 |
| `00_engine/cache/tmp/` | UE 临时目录 / staging | 忽略 |
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
export HF_HOME="/scratch/prj0000000275/jcy/.cache/huggingface"
```

> Linux 下 DDC 变量使用 `UE_LocalDataCachePath`（下划线），不要用 Windows 风格的 `UE-LocalDataCachePath`。

## 三、为什么这样放

- 当前 `/scratch` 是 WekaFS/网络盘，小文件 I/O 可能慢，但管理员限制下这是可用方案。
- 766G 可用空间足够当前 MVP 和 Lance 这类单模型验证；要避免同时保留多个 UE 版本、大量 zip、海量 EXR、多个大模型权重和正式数据集。
- UE 相关内容集中在 `00_engine/`，研究和模型验证集中在 `10_research/`，讨论/计划集中在 `20_planning/`。
- DDC 路径固定在 `00_engine/cache/ddc/`，避免每次换路径导致重复 shader/cache 构建。
- 所有大文件和缓存目录都由 `.gitignore` 排除，避免本地 Git 仓库被大文件污染。
- Lance 当前采用用户已配置的 scratch 全局 HF cache：`/scratch/prj0000000275/jcy/.cache/huggingface`；可运行权重目录放在 `10_research/model_experiments/lance/models/Lance/`，避免重复下载和默认写入小 home。

## 四、使用纪律

1. UE zip 解压成功并确认可运行后，删除或转移 `00_engine/unreal/downloads/` 里的 zip。
2. MVP 输出控制在几十 GB 量级；不要直接开高分辨率、多通道、大规模 job-array。
3. 外部模型下载前先明确范围；不要整仓库拉 demo assets，优先用 allowlist 下载权重和配置。
4. `00_engine/outputs/`、`00_engine/cache/`、`10_research/model_experiments/*/outputs/`、`10_research/model_experiments/*/logs/` 不作为长期归档。
5. 重要脚本、配置、文档应进入 Git；引擎、缓存、输出、模型权重和资产大包不进 Git。
6. 每次大渲染或模型下载前先检查空间：

```bash
df -h /scratch/prj0000000275/jcy/xks/DataMake
du -sh 00_engine 10_research/model_experiments 20_planning 2>/dev/null
```

## 五、历史方案（已废弃）

2026-06-19 的三层方案曾计划：

- `/local/$USER` 放 engine/DDC/render scratch；
- `/scratch` 放大成品；
- `/home` 放工程源/备份。

该方案已被 2026-06-28 的管理员限制取代：**当前不能使用 `/local`**。旧方案只作为历史背景保留，不再作为执行方案。

## Agent 备忘

- 当前权威结论：**所有当前阶段工作都在 DataMake 目录下完成**。
- 网络盘小文件慢是已知风险，不再反复争论；MVP 和单模型验证阶段通过控制规模接受该风险。
- Hugging Face / model cache 必须显式指向 scratch 上的可用路径。当前 Lance 使用 `/scratch/prj0000000275/jcy/.cache/huggingface`；不要落回默认小 home。
- 如果后续进入正式大规模生产，必须重新讨论存储，不能沿用本 MVP 布局直接扩量。
