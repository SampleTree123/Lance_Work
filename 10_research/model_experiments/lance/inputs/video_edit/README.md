# Lance video_edit 自测输入

本目录放 Lance `video_edit` 快速测试的本地输入。这里的内容服务于能力验证，不是正式数据集。

## 目录

| 路径 | 用途 | Git 状态 |
|------|------|----------|
| `videos/` | 原始测试视频，如 `.mp4` | 忽略 |
| `prompts/` | 单轮或多轮 prompt 文本 | 默认忽略；`example_*.txt` 和 curated batch prompt 作为模板保留 |

## 单轮 prompt

把一个 prompt 写进文本文件，文件可以只有一行：

```text
Change the car's color to red and change the background to a snowy road.
```

## 多轮 prompt

多轮编辑用“每个非空行一轮”的文本文件：

```text
Change the car's color to red.
Add snow to the road while keeping the car motion unchanged.
Remove the snow and make the road look dry again.
```

运行脚本时，第一轮输入原始视频，后续每轮自动输入上一轮生成的视频。

## 脚本

使用：

```bash
10_research/model_experiments/lance/scripts/run_video_edit.sh \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/example.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/example_multiturn.txt \
  --name my_test
```

输出会写入：

```text
10_research/model_experiments/lance/outputs/video_edit/my_test/
```
