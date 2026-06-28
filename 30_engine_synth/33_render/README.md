# 33_render —— 渲染与自动化 / 流水线打通（Level 2）★当前主线

> ↑ 父层：[`../README.md`](../README.md)（引擎合成）→ [`../../README.md`](../../README.md)（总览）。
> 本层放 **UE5.8 目标环境下的自动化脚本、渲染配置、GT 导出、sidecar**。当前唯一目标：**把整条流水线打通（MVP 最小闭环）**。版权暂缓仅限内部原型；所有临时资产必须标为 `prototype-only`，不得进入发布/训练数据。

---

## 📂 内容说明（规划，随实现补充）

| 文件 | 职责 | 状态 |
|------|------|------|
| `README.md` | 本文件：MVP 闭环定义、脚本架构、对齐 checklist、样本 schema v0 | ✅ |
| `cluster_deploy_and_mvp.md` | **集群部署 + MVP 启动计划**（命令级：装 UE5.8 无 root / 无头渲染 native vs Apptainer / SLURM job-array / Win↔集群同步） | ✅ 调研稿 |
| `../../05_research/unreal_harness_survey.md` | UE 官方 automation / MCP / harness 调研结论 | ✅ 参考 |
| `render_pair.py` | 主入口：给定 (base_config, edit) 渲一对前后视频 + GT + sidecar | 待写 |
| `factors.py` | 每个因子的"读/改"接口（统一签名，便于扩到 E1–E11） | 待写 |
| `passes.py` | 配置 GT passes + 多层 EXR 输出 | 待写 |
| `sidecar.py` | 写样本 JSON（= 统一样本 schema） | 待写 |
| `walk.py` | （MVP 之后）随机游走批量生成"节点+边"，端点复用 | 待写 |

---

## 1. "打通"的定义（MVP 验收标准）

**一个脚本能自动产出 1 对像素级对齐的前后编辑配对 + GT + sidecar**，且未改动区域逐像素差 ≈ 0。跑通这一条，整条数据范式（配置图/对齐/自动指令/GT）就验证了。

## 2. MVP 最简场景

- 1 角色（绑 UE5 Manny/Quinn 骨架）+ 1 个 **in-place 循环动作**（避 root-motion 批量导出 bug）。
- 1 环境 + 1 固定相机 + 1 光照。
- **第一类编辑建议 E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情**。这些编辑不依赖换装/重定向，最适合先验证渲染、GT 和 sidecar。
- 原型资产用最省力的组合即可，但必须记录来源并标 `prototype-only`；进入发布/训练数据前必须替换为合规资产。

## 3. 闭环步骤

1. 加载关卡 + Sequencer，固定**帧率 / 起始帧 / 时长**。
2. 配置 MoviePipeline：**AA=None + 空间采样≥8**（去 TAA/TSR 抖动）；启用 Additional Render Passes（WorldDepth、MotionVectors）；**多层 EXR** 输出；设足够 **warm-up 帧**让 Lumen 收敛一致。
3. 渲染配置 **C** → `video_in` + GT passes。
4. Python **只改一个因子**（如光照参数 / 换 Wardrobe Item / 换 Animation），其余一切不动（同种子/时间轴/相机/console vars）。
5. 渲染 **C'** → `video_out` + GT passes。
6. 写 **sidecar JSON**：改动因子、前后参数、自动指令、各文件路径、相机内外参。
7. **对齐 sanity check**：未改动区域逐像素差应 ≈ 0（E8 光照例外——光照改动是全局的，改用"几何/深度通道一致"来校验）。

## 4. 脚本架构（建议）

```
render_pair(base_config, edit) ->
  set_scene(base_config)          # factors.py: 摆好角色/服装/动作/场景/相机/光照
  render(C)  -> video_in, gt_in   # passes.py + MoviePipeline
  apply_edit(edit)                # factors.py: 只动一个因子
  render(C') -> video_out, gt_out
  write_sidecar(...)              # sidecar.py
```

- **factors.py 统一接口**（为 E1–E11 预留）：`set_light / swap_outfit / swap_anim / swap_identity / swap_env / toggle_prop / toggle_accessory / set_camera / set_expression`，每个都成对提供 `read_*`（记录前后值）与 `apply_*`。
- 无头批渲：`UnrealEditor-Cmd Proj.uproject Map -game -RenderOffscreen -unattended -log -stdout ...`。

## 5. 确定性 / 对齐 checklist

- [ ] AA=None，仅空间采样（≥8）
- [ ] 固定 帧率 / 起始帧 / 时长 / 相机 / console vars
- [ ] warm-up 帧足够（Lumen / 时序效果收敛一致）
- [ ] 动作用 in-place 循环（无 root motion 导出）
- [ ] 道具增删用 visibility toggle（`SetActorHiddenInGame` / Sequencer Visibility track），不 spawn/destroy
- [ ] 未改动区域逐像素差 sanity check（E8 光照改用深度/几何一致性校验）

## 6. 统一样本 schema v0（草案，稳定后升级到 `00_planning/schema/`）

```json
{
  "pair_id": "w001_s03_E8",
  "walk_id": "w001", "step": 3,
  "factor_changed": "E8_light",
  "instruction": "把光照改成日落",
  "video_in":  "out/w001/s02.mp4",
  "video_out": "out/w001/s03.mp4",
  "gt_in":  {"depth": "...", "motion": "...", "seg": "..."},
  "gt_out": {"depth": "...", "motion": "...", "seg": "..."},
  "camera": {"intrinsics": {}, "extrinsics": {}},
  "fps": 24, "frames": 96,
  "config_in":  {"identity": "...", "outfit": "...", "anim": "...", "env": "...", "light": "noon", "...": "..."},
  "config_out": {"...": "...", "light": "sunset"},
  "assets": [{"id": "...", "license": "prototype-only"}]
}
```

> 关键：`video_out` 作为下一条边的 `video_in` 文件被直接复用（**端点复用**），多轮链由 `walk.py` 在图上取子路径得到。

---

## Agent 备忘（33_render）

- **当前主线就是这里**：把第 1 节的 MVP 跑通 = 项目当前最高优先。
- **动手写脚本前先确认**：① UE5.8 是否已安装并能跑 Python/MoviePipeline；② 当前先要操作指南还是直接脚本；③ 第一对采用 E8/E5/E6/E11 哪个最小编辑。
- **写脚本时落地要点**（来自 `../pipeline_research_memo.md`）：MRG 优先验证，必要时退回 MRQ；GT 走多层 EXR（depth/motion vectors=光流）；相机内外参 + 每-actor 标签需自写 sidecar；Object IDs/Cryptomatte 实验性、仅编辑器。
- **harness 策略**（来自 `../../05_research/unreal_harness_survey.md`）：生产侧自建薄 harness，底层用 UE Python + Automation Test Framework + MRQ/MRG；Unreal MCP/agent 工具只作编辑器辅助。
- **版权**：原型资产可先服务内部管线验证，但必须标 `prototype-only`；进入发布集的资产再回 `../../90_meta/` 收口。
- MVP 之后：写 `walk.py` 做随机游走批量，验证端点复用与多轮链抽取。
