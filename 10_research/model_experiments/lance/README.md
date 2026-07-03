# lance —— Lance 外部模型验证

> 父层：[`../README.md`](../README.md) → [`../../README.md`](../../README.md)。

本目录收拢 Lance 相关的代码、权重、输入、输出、脚本和报告。这里不是训练代码仓库；Lance 在 DataMake 中先作为外部单轮调用基线和运行验证对象。

## 目录

| 路径 | 内容 | Git 状态 |
|------|------|----------|
| `README.md` | 本层说明 | 提交 |
| `validation_plan.md` | Lance 下载、环境、验证计划和执行状态 | 提交 |
| `reports/` | 稳定实验记录和结果摘要 | 提交 |
| `scripts/` | Lance 快速验证脚本 | 提交 |
| `inputs/video_edit/` | `video_edit` 自测输入和 prompt 模板 | 部分提交 |
| `lance/` | 上游 Lance 代码仓库 | 忽略 |
| `models/` | Lance 权重目录 | 忽略 |
| `outputs/` | 生成视频、图片、json 结果 | 忽略 |
| `logs/` | 运行日志和自动生成 config | 忽略 |

## 当前状态

- Lance 代码位于 `lance/`，当前验证过的 commit 是 `9717d91`。
- 视频分支权重位于 `models/Lance/`，约 18GB。
- 代码仓库内 `downloads -> ../models/Lance`，因此官方脚本仍可使用 `downloads/Lance_3B_Video`。
- 当前只下载视频分支，没有下载 `Lance_3B/` 图片分支和 HF demo assets。
- Batch8 多领域连续单轮测试记录见 [`reports/video_edit_batch8_report.md`](./reports/video_edit_batch8_report.md)。这不是 Lance 真多轮编辑验证。

## 使用入口

```bash
10_research/model_experiments/lance/scripts/run_video_edit.sh \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/example.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/example_chained_single_turn.txt \
  --name my_test
```

当前 `--prompts-file` 只是把上一轮输出视频重新输入给下一次独立 `video_edit` 调用。后续需要先实现 Lance 真多轮编辑逻辑，再重新做多轮一致性测试。

如果从登录节点提交到已存在的 SLURM allocation：

```bash
10_research/model_experiments/lance/scripts/run_video_edit.sh \
  --job-id <JOB_ID> \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/example.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/example_chained_single_turn.txt \
  --name my_test
```
