# Lance batch8 video_edit 连续单轮测试记录

> 日期：2026-07-03。
> 目的：用公开视频快速覆盖不同编辑领域，确认 Lance `video_edit` 单轮调用路径和连续单轮脚本可运行。这里不评价 Lance 真多轮编辑能力。

## 环境与路径

| 项 | 当前值 |
|----|--------|
| Lance 代码 | `10_research/model_experiments/lance/lance/`，commit `9717d91` |
| Lance 权重 | `10_research/model_experiments/lance/models/Lance/`，约 18GB |
| HF cache | `/scratch/prj0000000275/jcy/.cache/huggingface` |
| 环境 | `xks_lance` |
| GPU | H200；原始批量测试使用 SLURM job `94398`，clean retry 使用 H64Y574 上的 SLURM job `94644` |
| 脚本 | `10_research/model_experiments/lance/scripts/run_video_edit.sh` |
| 输出 | `10_research/model_experiments/lance/outputs/video_edit/`，忽略不进 Git |

本轮参数：

```text
task: video_edit
steps: 12
frames: 50
seed: 42
resolution: video_480p
single-turn calls per video: 3
```

这轮测试把上一轮生成视频重新作为下一轮输入，因此是“连续多次单轮编辑”，不是模型内部保留上下文的真多轮编辑。用户初步查看认为主体修改和背景修改问题都较多；当前只把它作为单轮/连续单轮运行记录，不继续整理完整失败模式。

## 方法限制

- `run_video_edit.sh --prompts-file` 每一行 prompt 都会启动一次独立 `video_edit` 调用。
- 第 2、3 次调用的输入是上一轮输出视频，不包含前序 prompt、原始视频或显式对话上下文。
- 因此 batch8 只能说明单轮推理和输出回灌流程跑通，不能说明 Lance 的真实多轮编辑能力。
- 之后如要讨论多轮一致性，应使用 `scripts/contextual_video_edit.py` 生成包含历史输入/输出的 Lance config，再重新测试。

## 输入类型与结果

| 输入 | 类型/领域 | 连续三次单轮 prompt 目标 | 运行结果 |
|------|-----------|------------------|------|
| `1.mp4` | 雪地双人 + 狗，户外人物/动物 | 男外套变红；加暖色夕阳光；给黑狗加蓝项圈 | 生成完成 |
| `2.mp4` | 单人全身街拍走路 | 牛仔服变白色运动服；加黑墨镜；街道变雨后湿地 | 生成完成 |
| `3.mp4` | 人物近景肖像 | 黑上衣变深蓝；灰背景变暖米色；加圆框眼镜 | 生成完成 |
| `4.mp4` | 手持手机 + 纸杯，道具编辑 | 红纸杯变蓝；手机壳变白；背景变暖色夜间咖啡馆光照 | 生成完成 |
| `5.mp4` | 夜店舞者/帽子/墨镜/强光照 | 黑帽变白；紫色灯光变绿色；墨镜变透明眼镜 | 生成完成 |
| `6.mp4` | 双人街景，多主体 | 女外套变红；男外套变深蓝；广场变雪景 | 原始视频损坏；clean retry 生成完成 |
| `7.mp4` | 车辆/街道 | 黑车变红；路面变雨后湿地；加傍晚光照 | 原始视频损坏；clean retry 生成完成 |
| `8.mp4` | 黑狗街道，动物主体 | 加红项圈；路面变草地；加轻微降雪 | 生成完成 |

完成目录：

```text
batch8_01_snow_couple_dog/
batch8_02_walking_woman_street/
batch8_03_closeup_portrait/
batch8_04_phone_cup/
batch8_05_party_dancer/
batch8_06_two_people_street_clean_retry/
batch8_07_black_car_street_clean_retry/
batch8_08_black_dog_street/
```

历史中断目录，保留用于排查，不作为最终 batch8 结果：

```text
batch8_06_two_people_street_clean/turn_01/
```

## 输入文件问题

`6.mp4` 和 `7.mp4` 原始文件在 Decord 读帧时触发 H.264 NAL 错误，不应视为 Lance 模型失败。已用 OpenCV 生成 clean 输入：

```text
10_research/model_experiments/lance/inputs/video_edit/videos/6_clean_480p.mp4
10_research/model_experiments/lance/inputs/video_edit/videos/7_clean_480p.mp4
```

clean 版已通过 Decord 抽帧验证。`6_clean_480p.mp4` 曾在旧目录完成第 1 轮，补跑第 2 轮时 `94398` allocation 被 SLURM 终止；2026-07-03 已在 H64Y574 的 `94644` allocation 上重新完整跑完 `6_clean_480p.mp4` 和 `7_clean_480p.mp4` 的三次连续单轮编辑。

clean retry 输出目录：

```text
batch8_06_two_people_street_clean_retry/
batch8_07_black_car_street_clean_retry/
```

## 单轮覆盖价值

本轮已经覆盖了单轮输入类型和 prompt 类型：

- 人物身份/动作保持：单人走路、舞者、近景肖像。
- 局部外观编辑：衣服、帽子、墨镜、眼镜、头发/配饰类需求。
- 道具编辑：纸杯、手机、狗项圈。
- 背景/光照编辑：雪地、雨后湿地、夕阳、夜店灯光、咖啡馆光照。
- 多主体输入：双人街景 clean retry 已生成。
- 非人物主体：狗和车均已生成。

## 后续动作

1. 暂不继续整理这批输出的详细失败模式；用户初步观察已经足够说明原模型在主体和背景编辑上问题较多。
2. `scripts/contextual_video_edit.py` 已实现 config 生成和 synthetic media pack 检查。结构验证显示 `C0 + e1 + C1 + e2` 会形成 2 个 VIT 条件块、2 个 VAE 条件块和 1 个 target VAE block。
3. 首个 contextual v0 GPU smoke 已完成，见 [`contextual_video_edit_smoke.md`](./contextual_video_edit_smoke.md)。代码复查后 v1 已修正 prompt/config 顺序；后续质量判断前应先重跑 v1，如测 turn3 还应先预处理输入视频以控制帧数和尺寸。
