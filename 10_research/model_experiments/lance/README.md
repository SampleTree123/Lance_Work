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
- 已新增 contextual 多轮 config 工具：`scripts/contextual_video_edit.py`。v1 把所有历史视频都作为 VAE source，turn1/turn2 视觉质量失败；复查后确认这种结构会让多个 `ref_source` 对一个 `noise target`，破坏 Lance edit 的 source-target 对齐。当前已改为 v2 role-aware 路径：历史视频 `history_vit` 只进 VIT，最新视频 `direct_source` 作为唯一 clean VAE source；turn2/turn3 已在 H200 上生成成功。v2 turn2 明显优于 v1 all-source，但 turn3 小目标项圈编辑仍有属性绑定失败。记录见 [`reports/contextual_video_edit_smoke.md`](./reports/contextual_video_edit_smoke.md)。
- 已接入并测试 full-conversation multi-turn chat A 方案原型：参考 `Jayce-Ping/Lance@8b002b5`，新增 Lance 内部 `multiturn/` engine 和 DataMake 入口 `scripts/run_multiturn_chat.sh`。该方案保留历史 user/assistant turns，而不是把历史 prompt 拼进最新 prompt；实现上仍保留我们的 v2 原则：历史视觉只作为 VIT 语义上下文，最新视觉才作为唯一 clean VAE direct source。2026-07-08 在 job `102622` 上完成三轮 GPU smoke：代码路径跑通，但同样例视觉保持差于 contextual v2 current-only，记录见 [`reports/full_conversation_multiturn_chat_smoke.md`](./reports/full_conversation_multiturn_chat_smoke.md)。

## 使用入口

### 连续单轮基线

```bash
10_research/model_experiments/lance/scripts/run_video_edit.sh \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/example.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/example_chained_single_turn.txt \
  --name my_test
```

当前 `--prompts-file` 只是把上一轮输出视频重新输入给下一次独立 `video_edit` 调用。后续多轮一致性测试应改用 contextual config，并先跑小规模 GPU smoke。

如果从登录节点提交到已存在的 SLURM allocation：

```bash
10_research/model_experiments/lance/scripts/run_video_edit.sh \
  --job-id <JOB_ID> \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/example.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/example_chained_single_turn.txt \
  --name my_test
```

### Contextual 多轮 config

生成第 2 轮 contextual config，其中 `history-video` 是第 1 轮已生成结果。默认 `--prompt-style current-only` 只写当前轮编辑指令，不复述历史编辑内容；当前测试中这比长上下文 prompt 更少干扰局部属性绑定：

```bash
10_research/model_experiments/lance/scripts/contextual_video_edit.py build \
  --source-video 10_research/model_experiments/lance/inputs/video_edit/videos/1.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/01_snow_couple_dog_multiedit.txt \
  --history-video 10_research/model_experiments/lance/outputs/video_edit/batch8_01_snow_couple_dog/turn_01/000001.mp4 \
  --turn 2 \
  --prompt-style current-only \
  --output 10_research/model_experiments/lance/logs/generated_configs/contextual/my_turn02.json
```

默认 v2 config 会写成 `text -> video(history_vit) -> video(direct_source)`。这是为了匹配 Lance 内部模板：它会把首个 text block 旋转到视频之后，同时用最后一个 JSON 元素的 dtype 生成正确的 `input video` system prompt。更重要的是，历史视频只作为 VIT 语义参考，最新视频才是唯一 clean VAE source。

如果需要复现旧 v1 行为，可显式使用：

```bash
--history-role-mode all-source
```

该模式会把所有历史视频都作为 VAE source，当前仅作为对照，不再作为推荐路径。

检查 Lance 数据层打包结构时，优先用 synthetic media 模式跳过真实 MP4 解码：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/contextual_video_edit.py inspect \
  --config 10_research/model_experiments/lance/logs/generated_configs/contextual/my_turn02.json \
  --pack \
  --synthetic-media \
  --frames 25 \
  --height 360 \
  --width 360 \
  --resolution video_360p
```

Contextual v1 smoke 已用 turn1/turn2 跑通，但抽帧检查显示主体和场景保持失败。注意：Lance edit 路径会按输入视频 transform 后的条件张量覆盖目标帧数和尺寸；后续若要控制 token/显存，应先预处理输入视频，而不是只依赖 `--NUM_FRAMES` 和 `--VIDEO_HEIGHT/--VIDEO_WIDTH`。

当前 v2 synthetic pack 检查结果：

```text
role sequence: text -> video(history_vit) -> video(direct_source)
attn_modes: causal, full, full, full_noise, causal, causal, noise, causal
vit_condition_blocks=2
vae_condition_blocks=1
target_vae_blocks=1
ref_source=3390
noise=3390
source_target_alignment=PASS
```

当前 v2 GPU 结果摘要：

- `outputs/video_edit/contextual_role_v2_01/turn_02/000001.mp4`：相比 v1 turn2 明显减少场景重绘，能在 turn1 结果上叠加暖金色夕阳。
- `outputs/video_edit/contextual_role_v2_01/turn_03/000001.mp4`：小目标“蓝色狗项圈”编辑失败，蓝色错误绑定到人物外套。
- `outputs/video_edit/contextual_role_v2_01/turn_03_current_only_collar_simple/000001.mp4`：只写当前项圈指令时，蓝色能更稳定落到狗脖子附近，但红外套会漂移成棕/灰。
- `outputs/video_edit/contextual_role_v2_01/turn_03_current_only_collar_keep_red/000001.mp4`：只写当前项圈指令和必要保持约束时，红外套和夕阳保持最好，但蓝项圈不明显。
- `outputs/video_edit/contextual_role_v2_01_single_turn_collar_from_turn2/turn_01/000001.mp4`：同类项圈 prompt 的直接单轮对照基本保住红外套，说明多历史上下文会增加局部属性绑定干扰。
- `outputs/video_edit/contextual_role_v2_current_only_full_01/`：从原视频重新完整跑 current-only 三轮。turn1 保住双人主体并改红外套，turn2 加入夕阳且主体稳定，turn3 保住红外套和夕阳并把蓝色加到前景狗附近，但仍不是精确小项圈。

当前 prompt 策略：

- 默认用 `current-only`：只描述当前编辑。
- 若当前编辑容易破坏已接受属性，在当前 prompt 里写少量保持约束，例如“keep the red jacket unchanged”。
- 不默认使用 `natural`/`structured` 复述历史编辑；当前测试中这会把旧对象和颜色描述重新引入，反而干扰第三轮局部编辑。
- 完整三轮验证后，当前默认组合是：v2 role-aware 视频结构 + `current-only` 文本 + 当前 prompt 内少量保持约束。

### Full-Conversation 多轮 chat 原型

该入口用于测试 A 方案：历史文本保留为独立的历史 turn，历史输出以 assistant visual 形式回写到 conversation。它比 `contextual_video_edit.py` 更接近真正的多轮对话推理，并且可以混合不同任务，例如：

```text
user understand(video) -> assistant text
user edit_video(text) -> assistant video
user understand(text) -> assistant text
user edit_video(text) -> assistant video
```

从初始视频和 prompt 文件快速构建三轮 `edit_video` conversation 并运行：

```bash
10_research/model_experiments/lance/scripts/run_multiturn_chat.sh \
  --job-id <JOB_ID> \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/1.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/01_snow_couple_dog_multiedit.txt \
  --name full_conversation_a_01 \
  --steps 12 \
  --resolution video_360p \
  --height 360 \
  --width 360
```

也可以直接手写 conversation JSON，然后运行：

```bash
10_research/model_experiments/lance/scripts/run_multiturn_chat.sh \
  --job-id <JOB_ID> \
  --conversation path/to/conversation.json \
  --name mixed_task_conversation_01
```

当前实现边界：

- 文本上下文采用 full conversation：前几轮 prompt 是历史 user turns，不被拼接进最新 prompt 字符串。
- 视觉上下文采用 role-aware：旧图/视频只进 VIT，最新图/视频进 VIT + VAE direct source。
- `edit_video` 第二轮以后可以只写当前轮文本，因为 engine 会把上一轮生成视频作为 assistant visual 自动追加回上下文。
- 2026-07-08 已完成 GPU smoke；该入口可继续用于混合任务 conversation 研究，但当前默认多轮视频编辑验证仍使用 `contextual_video_edit.py` 的 v2 role-aware + `current-only`。
