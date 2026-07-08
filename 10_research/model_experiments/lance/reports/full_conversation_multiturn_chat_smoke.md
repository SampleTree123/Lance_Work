# Lance full-conversation multi-turn chat smoke 测试记录

> 日期：2026-07-08。
> 目的：验证 Lance full-conversation A 方案是否能在一次模型加载中保留历史 user/assistant turns，并把上一轮生成视频作为 assistant visual 回写后继续下一轮 `edit_video`。

## 结论

- 代码路径已在 H200 上跑通：三轮 `edit_video` 都成功生成，`transcript.json` 记录了完整历史对话。
- 这不是连续单轮回灌脚本。turn1 后，engine 将 `turn00.mp4` 作为 assistant video 加入历史；turn2 后同理加入 `turn01.mp4`；turn3 再基于完整历史和最新 direct source 生成。
- 初次 `steps=12` 结果视觉质量很差：turn1 成功把人物衣服改红，但同行女性基本消失，狗从黑狗漂移成白色大狗；turn2 能加入暖金夕阳；turn3 没有形成清晰蓝色狗项圈。后续代码检查发现旧的 `contextual_role_v2_current_only_full_01` 使用 `steps=30`，因此 `steps=12` 只能作为链路 smoke，不能作为质量结论。
- 复跑 `steps=30` 后，A 方案明显改善：turn1 保住双人主体并改红衣服；turn2 加入夕阳；turn3 大体保持双人和夕阳，但狗颜色仍漂移，蓝色项圈仍不明显。
- 当前没有发现“多个 clean VAE source”“上一轮输出未回写”“target latent 取错”等明确代码错误。更合理的结论是：full-conversation A 的代码路径成立，但结果对步数敏感，且 `assistant video -> user text` 的对话格式仍可能弱于 contextual v2 的手工 edit 样本格式。
- 当前推荐仍是：v2 role-aware contextual config + `current-only` prompt + 必要的少量保持约束。full-conversation A 可以继续作为研究分支，用于测试混合任务对话或换更短、更清晰的视频。

## 环境与参数

| 项 | 值 |
|----|----|
| SLURM job | `102622` |
| 节点/GPU | `8FS9B74`，1 GPU |
| Lance 环境 | `xks_lance` |
| 权重 | `downloads/Lance_3B_Video` |
| 入口脚本 | `scripts/run_multiturn_chat.sh` |
| run name | `full_conversation_a_job102622_01` |
| steps | 12；复测 30 |
| cfg | 4.0 |
| seed | 42 |
| requested frames | 50 |
| requested resolution | `video_360p` |
| requested height/width | 360 / 360 |

## 命令

```bash
10_research/model_experiments/lance/scripts/run_multiturn_chat.sh \
  --job-id 102622 \
  --video 10_research/model_experiments/lance/inputs/video_edit/videos/1.mp4 \
  --prompts-file 10_research/model_experiments/lance/inputs/video_edit/prompts/01_snow_couple_dog_multiedit.txt \
  --name full_conversation_a_job102622_01 \
  --steps 12 \
  --resolution video_360p \
  --height 360 \
  --width 360
```

## 输入 prompt

```text
Change the man's jacket to bright red while keeping the woman, dog, and walking motion unchanged.
Add warm golden sunset lighting to the snowy forest scene while preserving the snow and subjects.
Add a bright blue collar to the black dog while keeping both people unchanged.
```

## 输出

| 文件 | 说明 |
|------|------|
| `logs/generated_configs/full_conversation_a_job102622_01/conversation.json` | 初始 conversation |
| `outputs/multiturn_chat/full_conversation_a_job102622_01/turn00.mp4` | 第 1 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_01/turn01.mp4` | 第 2 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_01/turn02.mp4` | 第 3 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_01/transcript.json` | 运行后的完整对话历史 |
| `outputs/multiturn_chat/full_conversation_a_job102622_01/contact_sheet.jpg` | 源视频和三轮输出的抽帧检查图 |
| `outputs/multiturn_chat/full_conversation_a_job102622_steps30_01/turn00.mp4` | `steps=30` 第 1 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_steps30_01/turn01.mp4` | `steps=30` 第 2 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_steps30_01/turn02.mp4` | `steps=30` 第 3 轮输出 |
| `outputs/multiturn_chat/full_conversation_a_job102622_steps30_01/a30_vs_a12_v2_contact_sheet.jpg` | 12 步、30 步与 v2 current-only 对比抽帧图 |

文件级检查：

| 输出 | 分辨率 | 帧数 | FPS | 大小 |
|------|--------|------|-----|------|
| source | 1080x1920 | 380 | 25 | 约 9.0MB |
| turn00 | 352x624 | 69 | 12 | 约 1.1MB |
| turn01 | 352x624 | 69 | 12 | 约 613KB |
| turn02 | 352x624 | 69 | 12 | 约 688KB |

`steps=30` 复测输出：

| 输出 | 分辨率 | 帧数 | FPS | 大小 |
|------|--------|------|-----|------|
| turn00 | 352x624 | 69 | 12 | 约 975KB |
| turn01 | 352x624 | 69 | 12 | 约 720KB |
| turn02 | 352x624 | 69 | 12 | 约 845KB |

## Transcript 结构

运行后的 `transcript.json` 结构符合 A 方案：

```text
user:      [source video, turn1 text] action=edit_video
assistant: [turn00 video]
user:      [turn2 text] action=edit_video
assistant: [turn01 video]
user:      [turn3 text] action=edit_video
assistant: [turn02 video]
```

这说明历史 prompt 没有被拼进最后一轮 prompt 字符串，而是作为独立历史 turn 输入。历史视觉由 engine 按 role-aware 规则处理：旧 visual 作为 VIT 语义上下文，最新 visual 作为 direct source。

## 视觉检查

抽帧图：

```text
outputs/multiturn_chat/full_conversation_a_job102622_01/contact_sheet.jpg
outputs/multiturn_chat/full_conversation_a_job102622_steps30_01/a30_vs_a12_v2_contact_sheet.jpg
```

`steps=12` 观察：

- `turn00`：红衣服编辑生效，但女性主体丢失，黑狗漂移为白色大狗，构图也更像单人牵狗。
- `turn01`：暖金夕阳光生效，并基本继承 `turn00` 的单人/白狗状态。
- `turn02`：没有看到清晰蓝色项圈；主体保持大体稳定，但狗和人物仍是已经漂移后的状态。

`steps=30` 观察：

- `turn00`：红衣服编辑生效，双人主体保留明显好于 `steps=12`；狗仍有变浅/变白倾向。
- `turn01`：暖金夕阳光生效，双人和雪林构图基本保持。
- `turn02`：双人和夕阳大体保持，但蓝色项圈仍不清晰，狗颜色问题没有恢复。

解释：

- A 方案的上下文组织已经工作，但它没有修复 Lance 在该公开视频上的单轮主体保持问题。
- `steps=12` 会显著放大主体漂移，不能和旧 `steps=30` v2 current-only 直接比较。
- 历史文本作为独立 turns 被保留后，可能增加全局语义干扰；在 `steps=30` 同等设置下，它仍没有明显优于 v2 contextual current-only。
- 第 3 轮 prompt 仍提到“black dog”，但前两轮后狗已经变成白色，这会继续放大目标绑定困难。

## 下一步

1. 后续质量对比默认使用 `steps=30`；`steps=12` 只作为链路 smoke。
2. 当前默认路径保持为 `contextual_video_edit.py` 的 v2 role-aware + `current-only`。
3. A 方案如继续测试，应换更短、更稳定的源视频，并优先测大尺度或中尺度编辑，不要用“小项圈”作为首要判据。
4. 若要证明 A 方案的优势，应使用混合任务 conversation，例如 `understand(video) -> edit_video -> understand(text) -> edit_video`，而不是仅复制三轮纯编辑链。
