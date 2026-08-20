# 可视化结果门户运行规范

> 文档角色：`visual_review_operations`
> 状态：`current`
> 适用阶段：`WF-01..WF-09` 中所有产生视觉证据的任务
> 权威范围：结果分支格式、门户登记、页面启动和审查状态维护
> 上级入口：[`README.md`](./README.md)
> 上游：各 Workflow 产生的截图、联系表、结果 JSON 和 [`VISUAL_ACCEPTANCE.md`](./VISUAL_ACCEPTANCE.md)
> 下游：人工审查、`VIS-*` 结论和对应 Exit Gate
> 最近核验：2026-08-17

## 1. 目的与边界

`Lance Visual Review` 把每次视觉实验保存为独立结果分支，并在一个主页中按日期、任务和状态检索。结果页支持分组/视角切换、总览放大、任意两个方案的 A/B 对比、参数矩阵和原始产物跳转。

门户是视觉证据的导航和审查界面，不替代验证定义，也不自行判定 Gate 通过：

- `VISUAL_ACCEPTANCE.md` 定义应该观察什么和接受标准。
- 本文定义如何把观察材料登记、展示和保留。
- 人工结论仍需写入 run 的 `status/decision`，并同步到对应验证或 Gate 证据。

## 2. 在生命周期中的位置

从 2026-08-09 起，新产生的可视化审查结果按以下顺序处理：

```text
Workflow 或维护实验生成原始截图/联系表
  -> 机器验证确认文件完整且图片可读取
  -> 创建独立 run.json
  -> 登记到门户 registry.json
  -> 用户在网页中进行总览和 A/B 审查
  -> 更新该 run 的 status 与 decision
  -> 对应 VIS-* / Gate 引用该结果分支和原始报告
```

只有纯机器验证且完全没有视觉产物时可以不登记。门户中出现记录不代表 `VIS-*` 已通过；`pending_review` 和 `iteration_needed` 都不能晋级 Gate。

## 3. 路径与所有权

```text
PORTAL_ROOT = D:\UE\Lance_Work\00_engine\visualization_portal
PORTAL_URL  = http://127.0.0.1:8765/00_engine/visualization_portal/
RUN_ROOT    = %PORTAL_ROOT%\runs\<run-id>\run.json
REGISTRY    = %PORTAL_ROOT%\data\registry.json
ARTIFACTS   = D:\UE\Lance_Work\00_engine\outputs\...
```

门户只保存页面源码、轻量 run 元数据和索引。原始 PNG、JSON、日志和联系表继续留在 `00_engine\outputs` 的唯一 run 目录中；`run.json` 使用 `/00_engine/outputs/...` URL 引用，不复制大图。

## 4. 结果分支契约

每个 `run.json` 至少包含：

| 字段 | 含义 |
| --- | --- |
| `id` | 小写字母、数字和连字符组成的稳定运行 ID；建议以日期开头 |
| `title/task/created_at` | 人类标题、任务域和 ISO-8601 时间 |
| `status` | 当前人工审查状态 |
| `summary` | 本轮做了什么，不写超出证据的结论 |
| `thumbnail` | 主页预览图 URL |
| `groups` | 性别、角色、场景等一级分组；每组含总览、比较图和 cases |
| `groups.*.cases.*.images` | 同一方案各视角的原图 URL |
| `groups.*.cases.*.parameters` | 该方案的受控参数，用于网页参数表 |
| `decision` | 人工审查后写入的结论与下一动作 |
| `artifacts` | manifest、验证结果、README 等原始证据链接 |

当前状态语义：

| 状态 | 含义 |
| --- | --- |
| `pending_review` | 机器产物就绪，等待人工审查 |
| `iteration_needed` | 已审查，结果稳定但需要调整范围或重做 |
| `approved` / `complete` | 本轮目标在明确范围内通过 |
| `failed` / `blocked` | 产物错误或存在阻塞，不能作为接受证据 |

“分支”是独立结果记录，不是 Git branch。历史 run 不因后续实验而覆盖。

## 5. 新增结果的准确步骤

1. 先完成对应 `VAL-*` 或任务级文件完整性检查。
2. 在 `runs/<run-id>/run.json` 写入本轮元数据和产物 URL。
3. 执行登记：

```powershell
cd D:\UE\Lance_Work\00_engine\visualization_portal
python tools\register_run.py runs\<run-id>\run.json
```

如同一 run 只是在人工审查后更新状态和结论，保留 ID 并执行：

```powershell
python tools\register_run.py runs\<run-id>\run.json --replace
```

4. 运行测试并检查所有本地 URL：

```powershell
python -m unittest discover -s tests -v
```

5. 打开门户，至少检查主页记录、所有分组、全部视角、一个 A/B 组合和窄屏布局。
6. 将门户 run ID 与原始 artifact 路径写入相应 `VIS-*` 或阶段证据。

页面不需要为新任务改代码；只有新数据形状无法表达时才升级 schema 和前端，并保留旧 schema 兼容。

## 6. 启动与恢复

启动：

```powershell
& "D:\UE\Lance_Work\00_engine\visualization_portal\start_portal.ps1"
```

启动器先使用 `Invoke-WebRequest -UseBasicParsing` 检查健康状态；已有健康服务时直接复用，否则只终止门户自己记录的旧 PID，并以隐藏、脱离当前终端的进程启动 `serve.py`。不要用旧 Windows PowerShell 的默认 IE 解析模式判断服务是否可用，它可能在已经收到 HTTP 内容时仍抛出解析错误。

浏览器显示“无法读取结果索引”时，首先确认通过 HTTP URL 而不是双击 `index.html` 打开；然后检查 `data/registry.json` 是否为合法 JSON。某张图片失败时运行注册/资产校验，修正 URL，不移动原始 artifact 来迁就网页。

端口被占用时可选择其他端口，URL 路径部分保持不变。服务只监听 `127.0.0.1`，不对局域网或互联网发布。

## 7. 已登记 Headshot 结果

### 7.1 初始组合范围

```text
run id: 2026-08-09-headshot-skull-profile-review-v1
任务: Headshot 头型 Morph 初始范围审查
内容: 2 个性别、12 个方案、36 张 1536x1536 源图、7 个受控 Morph
状态: iteration_needed
结论: 几何稳定，但初始组合差异偏小；下一轮扩大单轴扫描范围
```

该记录由 `tools/build_headshot_skull_run.py` 从原始 `review_20260809_v1/index.json` 重建，是后续结果分支的参考实现。

### 7.2 扩大范围单轴扫描

```text
run id: 2026-08-09-headshot-skull-axis-sweep-v2
任务: Headshot 头型 Morph 扩大范围单轴扫描
内容: 2 个性别、30 个案例、90 张 1536x1536 源图、7 个单独扫描轴
状态: approved
结论: 6 个轴沿用扫描范围；Skull Back Depth 收紧为 [-0.50, +0.50]
```

该记录由 `tools/build_headshot_skull_axis_run.py` 从 `headshot_skull_axis_sweep_v2/review_20260809_v1/index.json` 重建。原始范围清单为 `cc_headshot_skull_axis_sweep_v2.json`；女性和男性 Bridge 结果分别保存在同名 artifact 根下的 `female_20260809_v1` 与 `male_20260809_v1`。

人工批准后的唯一机器区间源为 `cc_headshot_skull_safe_ranges_v1.json`：

| 轴 | 批准区间 |
| --- | --- |
| `Head Width` | `[-0.65, +0.65]` |
| `Head Depth` | `[-0.60, +0.60]` |
| `Skull Height` | `[-0.65, +0.65]` |
| `Skull Width` | `[-0.65, +0.65]` |
| `Skull Depth` | `[-0.60, +0.60]` |
| `Skull Back Depth` | `[-0.50, +0.50]` |
| `Skull Peak` | `[-0.55, +0.55]` |

这些区间只证明单轴端点可接受。任意多个轴同时接近极值尚无视觉证据，不能据此直接批准整个七维笛卡尔积。

### 7.3 多轴候选与规范头型动态

```text
run id: 2026-08-09-headshot-skull-composition-candidates-v1
状态: approved
内容: 2 个性别、9 个候选、54 张源图；用户选出 H00..H03

run id: 2026-08-09-headshot-skull-profile-dynamic-gate-v1
机器状态: 8/8 passed
用户状态: accepted（权威记录为 cc_headshot_skull_profile_validation_v1.json）
内容: H00..H03 的男女 CC5 HD 动态门禁
```

### 7.4 Project-seed + BodyFit Pilot

```text
run id: 2026-08-10-headshot-project-seed-bodyfit-pilot-v1
状态: approved
内容: F_HS_002/F02 与 M_HS_002/M02 两个完整装配、动态和重载案例
```

该记录证明 `headshot_project_seed_then_bodyfit_v1` 在两个平均体型上的最小闭环，不证明十体型或全部身份原型已经接入生产。

### 7.5 十原型身份池

```text
run id: 2026-08-10-headshot-identity-pool-10-v2
状态: pending_review
内容: 5 女 + 5 男；原照片身份匹配、中性、3/4、闭眼、三级 Smile、Jaw Open
机器状态: 10/10 passed
来源状态: 10/10 mapped
视觉状态: 原 4 人 passed；新增 6 人 pending_user_review
生产启用: 0
```

重建命令：

```powershell
python "$LANCE_ROOT\00_engine\scripts\character_creator\cc_make_headshot_identity_pool_review_sheets_v1.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\build_headshot_identity_pool_run.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\register_run.py" `
  "$LANCE_ROOT\00_engine\visualization_portal\runs\2026-08-10-headshot-identity-pool-10-v2\run.json" `
  --replace
```

新增六例的原照片已通过显式映射配置和 SHA-256 锁定。用户应先在 `source_identity_match` 视图核对上方原照片与下方生成中性正面，再审查其余动态；只有逐人接受后才能把对应 manifest 记为 `passed`。本 run 完成后只冻结暂存候选池，不触发生产迁移。

### 7.6 服装源包盘点

```text
run id: 2026-08-11-cc-clothing-source-inventory-v1
状态: pending_review
内容: female/male 两根、61 个 ZIP、187 个散装目录包、248 个源包卡片
机器状态: 61/61 ZIP 可读，包 ID 与来源检查通过
生产 Look: 0
```

该 run 用于查看包级预览、真实内容类型、槽位和初步 Look 政策，并接受、替换或延期首批 Pilot 源候选。它不展示 CC 穿模结果，不能替代 `VIS-CC-05`。

重建命令：

```powershell
python "$LANCE_ROOT\00_engine\scripts\character_creator\cc_inventory_clothing_sources_v1.py"
python "$LANCE_ROOT\00_engine\scripts\character_creator\cc_make_clothing_source_inventory_review_v1.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\build_clothing_source_inventory_run.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\register_run.py" `
  "$LANCE_ROOT\00_engine\visualization_portal\runs\2026-08-11-cc-clothing-source-inventory-v1\run.json" `
  --replace
```

### 7.7 P0 动画动态 Gate

```text
run id: 2026-08-17-cc-animation-p0-dynamic-gate-v1
状态: approved（视觉自然度）
内容: F02/M02 各 8 条动作；每条 5 个归一化时间点，共 16 条、80 张 1024×1024 原图
机器状态: 16/16 passed，失败 0
Root 分类: 7 moving_candidate，9 in_place_candidate
面部通道线索: 16 none_detected
隐藏 Prop 增量: 0
视觉接受: 16/16
生产批准: 0
```

该 run 当前合并正式明亮重采 `animation_p0_dynamic_gate\run_20260818_v8_lit_review` 与 `p0_009_city_walk_normal_m` 的首帧 Root 对齐恢复批 `animation_p0_lighting_scout\start_aligned_20260818_v1`。构建器按案例选取最新成功证据，并从平移前的 `RL_BoneRoot` 样本重算 Root 分类。统一使用 Lightroom 当前相机、源项目 yaw 和可见材质；动作首帧先对齐源项目 Root，后续临时截图跟随只维持人物居中，不改变位移证据。用户已完整检查 16 条并接受视觉自然度，决定文件为 `cc_p0_animation_visual_review_20260818_v1.json`。当前门户资源曾通过 99/99 HTTP 检查；切组详情视角错误修复后，首组与末组不同中间帧键也均返回 200。

重建命令：

```powershell
python "$LANCE_ROOT\00_engine\visualization_portal\tools\build_animation_p0_dynamic_gate_run.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\register_run.py" `
  "$LANCE_ROOT\00_engine\visualization_portal\runs\2026-08-17-cc-animation-p0-dynamic-gate-v1\run.json" `
  --replace
```

人工审查应逐条查看五个时间点，至少检查动作语义、脚滑、肢体自穿插、手部接触和角色是否完整入镜。当前用户已对 16 条完整集合报告无不自然现象，因此视觉门禁为 `approved`。这次结论没有逐条书面备注，也没有分配循环意图和复用策略；动作仍不得直接进入生产池。详情 A/B 组件必须在每次切换动作组或方案后，重新计算两方案共有的 `images` 帧键，禁止沿用首组帧键。

### 7.8 UE P0 FullReference 运行时矩阵

```text
run id: 2026-08-19-ue-p0-runtime-pilot-v1
状态: approved（P0 技术视觉门禁）
内容: F02/M02；4 个身体状态 × 4 个直接 Morph 面部状态
机器状态: 16/16 cases，24/24 images，errors 0
运行时契约: FullReference direct Morph；组件 Post Process 禁用
视觉接受: 双眼 Blink、单眼 Asymmetric Blink、Subtle Smile 通过
生产批准: 0
```

该 run 用于审查 Neutral 全身正面/侧面/头部、Natural Blink、Asymmetric Blink 和 Subtle Smile。它明确不验证 eye-bone gaze；模块 eye-bone + curve 混合仍查看 `m02_face_hybrid_review_v003`。本分支的 `approved` 只表示当前 F02/M02 FullReference P0 组合通过，不把其余 P0、三发型、道具或十体型推断为通过。

复跑与重新注册：

```powershell
python "$LANCE_ROOT\00_engine\scripts\unreal\run_p0_runtime_validation.py"
python "$LANCE_ROOT\00_engine\visualization_portal\tools\register_run.py" `
  "$LANCE_ROOT\00_engine\visualization_portal\runs\2026-08-19-ue-p0-runtime-pilot-v1\run.json" `
  --replace
```
