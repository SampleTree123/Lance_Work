# 40_model_validation —— 外部模型能力验证（Level 1）

> ↑ 父层：[`../README.md`](../README.md)（项目总览）。
> 本层放外部模型验证计划、实验协议和结果记录。这里不是训练代码仓库。

---

## 📂 内容说明

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md` | 本层索引和实验记录规则 | ✅ |
| `lance_validation_plan.md` | Lance 下载、环境、视频编辑验证计划 | ✅ 待执行 |

## 目录边界

- 本层提交“计划、协议、结果摘要、失败案例索引”。
- 模型代码放 `external/repos/`，权重放 `external/models/`，HF cache 放 `external/hf_cache/`。
- 输出视频、图片、json 结果放 `outputs/model_validation/`。
- 大文件不进 Git；如果后续需要可复现归档，再讨论 DVC/Git LFS/对象存储。

## 统一实验记录格式

每次模型验证至少记录：

- 模型名、版本/commit、权重来源、下载日期。
- 环境：节点、GPU、driver、CUDA、Python、PyTorch、关键依赖版本。
- 输入样例：视频路径、prompt、随机种子、分辨率、帧数。
- 输出路径：生成结果、日志、失败截图/片段。
- 主观结论：指令遵循、身份保持、运动稳定、时序一致性、是否可多轮。
- 对 DataMake 的反推：哪个编辑类型需要优先合成数据。

## Agent 备忘（40_model_validation）

- Lance 是当前唯一已进入验证计划的外部模型。
- 下载权重前先确认用户同意，因为即使只下视频分支也会产生约 20GB 级别权重和额外缓存。
- 这里的验证服务于数据方案设计，不要扩展成完整训练或评测平台。
