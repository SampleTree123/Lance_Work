# 2026-07-29 Facial Profile 与闭眼穿模记录

> 结案状态：已解决。24 个完整角色均通过主 Facial Profile、真实眼球材质、15 姿态、中性 clip 保留和最终眼位恢复门禁。本文第 1 至 6 节保留事故发生时的诊断记录，最终结论见第 7 节。

## 1. 现象

首个 24 角色完整装配 pilot `CCINT_M01_YOUNG` 在真实皮肤和白色眼球材质下执行双眼闭合时，眼球从眼皮前方穿出。

问题图：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  character_integration_v1_20260729_03/chunk_01/
    CCINT_M01_YOUNG/face_blink_bilateral_front.png
```

中性状态的眼球位置可接受；异常由闭眼表情暴露。

## 2. 已排除项

### 2.1 不是睫毛资产

在不把睫毛作为变量的隔离案例中仍能复现。灰色检查材质曾让眼球和面部颜色相同，导致旧人工审核遗漏。

### 2.2 不是单一眼部局部 Morph

旧配方 `MFACEV3_0017` 含 `Eye Scale`。随后冻结全部 7 个眼部局部 Morph，并以原随机种子重建 200 条配方：

```text
regions:
  brow
  cheek
  ear
  forehead
  jaw
  nose

eye local Morph count = 0
mouth local Morph count = 0
```

新 pilot 仍复现闭眼穿出。

### 2.3 仅替换 Actor Parts 支撑不足

组装器已把 BodyFit 中活动的 `CC_Base_Eye`、`CC_Base_Teeth` 支撑替换为主 seed 的目标支撑，并证明：

```text
face_support_matches_primary_after_preset = true
BodyFit unchanged = true
Junction unchanged = true
```

产物：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  character_integration_v1_20260729_04/chunk_01/
```

闭眼图仍失败，说明静态 Shaping Morph 和 Actor Parts 向量不能完整表示表情状态。

## 3. 根因方向

`HD Aaron.ccAvatarPreset` 是 Head Morph 内容；完整 Aaron 角色还包含：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Actor\Facial Profile\
  Custom Profile\CC5 HD\HD Aaron.ccFacialProfile
```

Facial Profile 保存表情滑块、骨骼、Morph 和 corrective 的映射。当前最可能的根因是：

```text
Aaron 静态 Head Morph
+ BodyFit/Neutral 的 Facial Profile
= 静态脸正确，但闭眼 corrective 与眼球/眼睑关系错误
```

该判断仍需运行时验证，不能提前写成最终根因。

## 4. API 负面结果

以下调用不能用于当前 `.ccFacialProfile` 自动化：

```python
avatar.GetFacialProfileComponent().LoadProfile(path)
```

诊断作业：

```text
job:
  integration-aaron-facial-profile-diag-20260729-03

input:
  00_engine/scripts/character_creator/
    cc_integration_aaron_facial_profile_diagnostic_v1.json
```

该调用持续超过 45 分钟未返回，CC 内存约 `15.86 GiB`，进程仍存在，但桥接线程被同步调用占用。Agent 未关闭或重启 CC。

`.rlWrinkle` 动态皱纹曾通过同一 component API 加载；该正向结果不能外推到 `.ccFacialProfile`。

## 5. 当前候选修复

组装器已实现但尚未完成 CC 复验：

```text
select avatar
  -> RLPy.RFileIO.LoadFile(.ccFacialProfile)
  -> verify same avatar identity
  -> verify all static body/junction/face/other Shaping Morphs unchanged
  -> verify Eye AvatarPart and eye-bone structure unchanged
  -> verify Eyeball Move unchanged
```

绑定策略：

```text
M01_Aaron  -> HD Aaron.ccFacialProfile
F01_Ariana -> HD Ariana.ccFacialProfile
other male seeds   -> HD Neutral M.ccFacialProfile (candidate)
other female seeds -> HD Neutral F.ccFacialProfile (candidate)
```

如果旧代头型使用 Neutral profile 失败，必须为该 seed 绑定完整源角色内嵌 profile 或独立保存的验证 profile，不允许用 `Eyeball Move` 补丁。

机器可读绑定已经完成：

```text
cc_face_recipes_v3_200.json:
  200/200 recipes contain source_facial_profile

cc_character_integration_manifest_v1.json:
  24/24 presets contain source_facial_profile
  recipe/manifest mismatch = 0

required fields:
  application_mode
  path
  sha256
  policy_binding
```

生成器、manifest 编译器和 CC 验证器都会与 `cc_face_seed_library_v1.json` 的策略交叉核对。代码还会强制 `.ccFacialProfile` 与 `.rlWrinkle` 分走不同加载接口，历史错误诊断不能再次进入 component API。当前完整测试为 `106/106` 通过；这只证明离线实现与清单一致，不能替代 CC 中的眨眼视觉复验。

## 6. 下一次复验

CC 由用户按离线许可要求重新启动后：

1. 只提交 `CCINT_M01_YOUNG`。
2. 检查 profile 内容加载是否正常返回，未知弹窗立即失败。
3. 检查中性、双眼闭合、左右单眼闭合、四向视线、眯眼和睁大。
4. 检查微笑和张嘴，避免 profile 修复眼睛后破坏口腔。
5. 使用真实皮肤、巩膜和虹膜材质，不使用全灰遮挡验收。
6. Aaron 通过后，覆盖 17 个主 seed。
7. 主 seed 通过后，再覆盖 8 个 BodyFit 和 24 个完整角色。

提交前必须确认 `state/heartbeat.json` 满足：

```text
instance_id != f724639a3a26474cbc43d232871176d1
state = idle
busy = false
queue_depth = 0
```

首例固定命令：

```powershell
python 00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies `
  --library-file 00_engine/scripts/character_creator/cc_character_integration_manifest_v1.json `
  --output-dir 00_engine/outputs/character_creator_bridge/artifacts/character_integration_profile_fix_20260729_01/chunk_01 `
  --preset-id CCINT_M01_YOUNG `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id character-integration-profile-fix-20260729-01 `
  --no-wait
```

该命令只提交一个角色。只有精确 Undo Manager 警告可自动关闭；任何其他弹窗、内存达到 `24 GiB`、heartbeat 停止更新或结果缺少 profile 阶段证据时立即停止。

当时的停止条件是：验收前不得继续批量生成，也不得把旧 `25/25` 视觉结论恢复为生产通过。

## 7. 最终解决结果

运行时验证确认 `.ccFacialProfile` 必须和 Head Preset、眼球/牙齿支撑一起作为主面部原型加载。加入该步骤后，真实皮肤和白色眼球材质下的闭眼、单眼闭合、四向视线、眯眼、睁大、微笑和张嘴门禁均可通过。

后续又发现姿态测试清理和 CC 求值缓存两个独立问题：

- 旧清理逻辑可能误删项目原有中性 expression clip；现只删除本轮追加的临时 clip，并强制最终 clip 数量等于基线。
- 角色从临时检测机位恢复后，CC 偶尔保留单眼旧世界变换；现强制触发 Morph 更新与时间求值，最多重试 4 次，并比较最终眼位。

最终证据：

```text
24/24 case success
24/24 structural pass
15 poses per case
360 pose images
24/24 neutral eye integrity
24/24 post-validation eye restoration
1 baseline expression clip preserved per case
121/121 local tests
```

正式汇总：

```text
00_engine/scripts/character_creator/
  cc_character_integration_automation_summary_v1.json

00_engine/outputs/character_creator_bridge/artifacts/
  character_integration_24_fixed_20260729_01/
    character_integration_final_summary.json
```

状态仍为 `automation-complete-visual-review-pending`：自动结构门禁完成，代表性截图已抽查，但全部动态图的人工逐张签核尚未宣称完成。
