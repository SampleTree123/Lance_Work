# model_experiments —— 外部模型能力验证

> 父层：[`../README.md`](../README.md) → [`../../README.md`](../../README.md)。

本目录放 Lance、BAGEL、后续开放模型的验证计划、实验协议和结果记录。它不是上游模型训练代码主仓；用户于 2026-08-29 明确扩展了 Lance 微调接入范围，因此允许在模型子目录维护 DataMake 数据适配器、可追踪 patch、训练配置和小规模 smoke。

## 内容说明

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md` | 本层索引和实验记录规则 | 当前 |
| `lance/` | Lance 外部模型验证工作区：代码、模型、输入、输出、脚本和报告 | Stage 5 单步 `pred_x0` 历史四卡 Gate 已通过 |

## 目录边界

- 本层提交“计划、协议、结果摘要、失败案例索引”，以及服务 DataMake 数据接入的轻量适配代码、测试和 patch。
- 按模型/项目分层管理。当前 Lance 全部收拢在 `lance/` 下。
- Lance 上游代码放 `lance/lance/`，权重放 `lance/models/`，输入放 `lance/inputs/`，输出放 `lance/outputs/`。
- 原始视频、clean 输入副本、模型权重、日志和生成输出默认不进 Git；稳定实验协议、脚本和报告进入 Git。
- 大文件不进 Git；如果后续需要可复现归档，再讨论 DVC/Git LFS/对象存储。

## 统一实验记录格式

每次模型验证至少记录：

- 模型名、版本/commit、权重来源、下载日期。
- 环境：节点、GPU、driver、CUDA、Python、PyTorch、关键依赖版本。
- 输入样例：视频路径、prompt、随机种子、分辨率、帧数。
- 输出路径：生成结果、日志、失败截图/片段。
- 主观结论：指令遵循、身份保持、运动稳定、时序一致性、是否可多轮。
- 对 DataMake 的反推：哪个编辑类型需要优先合成数据。

## Agent 备忘

- Lance 是当前唯一已进入实测的外部模型。
- Lance 多轮训练适配已完成两轮四卡全参训练。第二阶段 Job `120425` 已完成 3,669 steps；局部编辑质量提升但真正自回灌仍有累积漂移。Stage 4 的 generation-only r64 LoRA、一行一链、30-step online full rollout 与 checkpoint-v5 已通过四卡 exact-resume；为缩短训练时间，Stage 5 只把历史构造换成复用训练 forward 的单步 `pred_x0`，连续/恢复 exact-resume 已通过并相对 full rollout 提速 1.91×。Stage5 A/B 已按用户要求暂停，等待修改；tiny 与 Stage1 结果退役，保留 Stage2 与当前 LoRA，见 [`lance/training_integration.md`](./lance/training_integration.md)。
- Lance 视频分支权重和 `xks_lance` 环境已建立；后续不要重复下载 `Lance_3B/` 图片分支，除非明确要测图片任务。
- 真实视频输入、clean 输入副本、生成输出和日志默认忽略；稳定结论写入报告。
- 训练接入只服务本项目多轮数据，不扩展成通用训练或完整 benchmark 平台。
