# Lance batch8 video_edit 多轮测试记录

> 日期：2026-07-03。
> 目的：用公开视频快速覆盖不同编辑领域，评估 Lance `video_edit` 的多轮链式编辑能力，并为 DataMake/UE 合成数据设计收集失败模式。

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
turns per video: 3
```

这是一轮广泛筛查，不是最终质量评估。表现有价值的样例后续可用 `30 steps / 50 frames` 复跑。

## 输入类型与结果

| 输入 | 类型/领域 | 三轮 prompt 目标 | 结果 |
|------|-----------|------------------|------|
| `1.mp4` | 雪地双人 + 狗，户外人物/动物 | 男外套变红；加暖色夕阳光；给黑狗加蓝项圈 | 完成 |
| `2.mp4` | 单人全身街拍走路 | 牛仔服变白色运动服；加黑墨镜；街道变雨后湿地 | 完成 |
| `3.mp4` | 人物近景肖像 | 黑上衣变深蓝；灰背景变暖米色；加圆框眼镜 | 完成 |
| `4.mp4` | 手持手机 + 纸杯，道具编辑 | 红纸杯变蓝；手机壳变白；背景变暖色夜间咖啡馆光照 | 完成 |
| `5.mp4` | 夜店舞者/帽子/墨镜/强光照 | 黑帽变白；紫色灯光变绿色；墨镜变透明眼镜 | 完成 |
| `6.mp4` | 双人街景，多主体 | 女外套变红；男外套变深蓝；广场变雪景 | 原始视频损坏；clean retry 已完成三轮 |
| `7.mp4` | 车辆/街道 | 黑车变红；路面变雨后湿地；加傍晚光照 | 原始视频损坏；clean retry 已完成三轮 |
| `8.mp4` | 黑狗街道，动物主体 | 加红项圈；路面变草地；加轻微降雪 | 完成 |

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

clean 版已通过 Decord 抽帧验证。`6_clean_480p.mp4` 曾在旧目录完成第 1 轮，补跑第 2 轮时 `94398` allocation 被 SLURM 终止；2026-07-03 已在 H64Y574 的 `94644` allocation 上重新完整跑完 `6_clean_480p.mp4` 和 `7_clean_480p.mp4` 的三轮链式编辑。

clean retry 输出目录：

```text
batch8_06_two_people_street_clean_retry/
batch8_07_black_car_street_clean_retry/
```

## 覆盖价值

本轮已经覆盖：

- 人物身份/动作保持：单人走路、舞者、近景肖像。
- 局部外观编辑：衣服、帽子、墨镜、眼镜、头发/配饰类需求。
- 道具编辑：纸杯、手机、狗项圈。
- 背景/光照编辑：雪地、雨后湿地、夕阳、夜店灯光、咖啡馆光照。
- 多主体误编辑风险：双人街景 clean retry 已完成，待人工检查局部编辑是否串扰。
- 非人物主体：狗和车均已完成，待人工检查车辆颜色、路面和光照编辑是否稳定。

## 后续动作

1. 人工查看已完成输出，按以下字段记录失败模式：

```text
instruction_following
identity_preservation
motion_preservation
background_consistency
locality_of_edit
temporal_stability
quality_degradation_across_turns
```

2. 把常见失败模式回写到 UE 数据设计优先级，尤其关注可确定性合成的编辑：配饰/道具显隐、局部颜色、光照/天气、多主体目标选择。
