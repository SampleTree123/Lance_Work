# 00_engine —— 引擎合成工作区

> 父层：[`../README.md`](../README.md)。

本目录放 Unreal Engine 合成数据相关内容：引擎安装、资产策略、自动化脚本、UE 工程、缓存和少量验证输出。当前目标不是大规模生产，而是先跑通一个可复现 MVP。

## 目录说明

| 路径 | 内容 | Git 策略 |
|------|------|----------|
| `unreal/` | UE 5.8 安装/部署说明、历史技术调研、集群 MVP 计划 | 文档提交；实际引擎目录忽略 |
| `assets/` | 资产来源、台账、prototype-only 标记和合规约束 | 台账提交；原始资产包忽略 |
| `scripts/` | UE Python / MRQ / MRG 薄 harness，当前 MVP 主入口 | 脚本和文档提交 |
| `projects/` | UE MVP 工程 | 初期只提交必要源码/配置；生成目录忽略 |
| `outputs/` | 少量 smoke test、MVP 输出和对齐检查结果 | 输出文件忽略，摘要回写文档 |
| `cache/` | DDC、临时目录、shader cache | 忽略 |

## 当前主线

- 引擎目标：UE 5.8。
- 渲染策略：官方 UE Python + Automation Test Framework + MRQ/MRG 自建薄 harness。
- MVP 入口：[`scripts/README.md`](./scripts/README.md)。
- 部署计划：[`unreal/cluster_deploy_and_mvp.md`](./unreal/cluster_deploy_and_mvp.md)。
- 存储路径：[`../20_planning/implementation/storage.md`](../20_planning/implementation/storage.md)。

## Agent 备忘

- 不把 UE 安装、DDC、工程生成目录、渲染输出或原始资产包提交进 Git。
- 原型资产必须标 `prototype-only`；可发布资产必须走 [`../20_planning/compliance/`](../20_planning/compliance/README.md) 的台账。
- 第一对样例优先 E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情。
