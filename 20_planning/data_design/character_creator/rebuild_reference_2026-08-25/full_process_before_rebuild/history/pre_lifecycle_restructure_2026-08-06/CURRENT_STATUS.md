# Character Creator 角色工厂当前状态

> 文档角色：`current_status_snapshot`
> 当前日期：2026-08-06
> 上级入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 更新方式：覆盖更新；已完成事件追加到 [`history/MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)

## 1. 当前结论

| 子系统 | 状态 | 当前结论 |
| --- | --- | --- |
| 成人 BodyFit | `production` | 10 个 hash 锁定 `.ccProject`；精确 Morph 只用于漂移审计 |
| Face V3 | `production` | 20 seed、17 个生产主原型；策略审计 51 个控制，当前 200 条配方实际使用 28 个安全局部 Morph |
| 面部组件池 | `production` | 21 皮肤、12 眼球材质、13 眉毛、9 睫毛、2 牙齿、5 胡须、58 发型 |
| 面部材质质量档案 | `production` | `cc_face_material_quality_v1`，状态 `production_approved` |
| 十体型展示 | `manual_verified` | 10 个完整角色已由用户视觉验收；展示 JSON 内部仍标 `pending-visual-review`，待后续配置同步 |
| CC Bridge | `validated_pilot` | 文件队列、心跳和 4 个受控命令可用；本轮未在线重验 |
| CC 完整角色装配 | `validated_pilot` | `validate-bodies` 可执行兼容 manifest；尚未提供语义明确的 `assemble-character` 命令 |
| CC→UE M02 | `validated_pilot` | FBX/JSON、Auto Setup 2.03、材质、Morph 与比例验证成功 |
| UE 模块化 M02 | `validated_pilot` | 20 个网格、19 个 follower、Morph 广播和材质分配通过 |
| UE 动画分层 | `validated_pilot` | v003 身体动画与 5 个面部状态矩阵 `10/10` |
| UE Elder Morph | `validated_pilot` | `AgeAlpha=0/0.5/1.0` 连续变化；批量化前仍需拓扑门禁 |
| 服装 Look 十体型 | `planned` | 采购资产已有，兼容矩阵和十体型导出尚未完成 |
| 每角色三发型 | `planned` | 策略已接受，正式资产导出与 UE 切换未完成 |
| 场景与批量渲染 | `planned` | 不属于当前角色工厂已完成能力 |

## 2. 十个 BodyFit

| ID | 性别 | 身高 cm | Head Scale UI | Neck Height UI |
| --- | --- | ---: | ---: | ---: |
| `M01_Lean` | male | 173.42 | -10 | -20 |
| `M02_Average` | male | 181.28 | 0 | 0 |
| `M03_Athletic` | male | 187.74 | 10 | -20 |
| `M04_Heavy` | male | 187.93 | 30 | 0 |
| `M05_Short_Average` | male | 159.89 | 0 | 0 |
| `F01_Lean` | female | 158.38 | -20 | -40 |
| `F02_Average` | female | 172.71 | 10 | 0 |
| `F03_Athletic` | female | 173.16 | 10 | 0 |
| `F04_Heavy` | female | 174.85 | 30 | 0 |
| `F05_Short_Average` | female | 152.53 | -10 | 0 |

权威配置为 `cc_body_preset_library_v2.json` 和 `cc_head_bodyfit_scale_decisions_v1.json`；身高证据为 `bodyfit_height_matrix_current_20260803_01/bodyfit_height_matrix.json`。

## 3. 当前关键版本

| 项目 | 当前值 |
| --- | --- |
| BodyFit library | `adult_body_fits_v2` |
| Face seed library | `adult_face_seeds_v1` |
| Face recipes | schema 3，`200` 条，文件状态 `quality-review-only` |
| Facial registry | `cc5_adult_facial_production_registry_v1` |
| Material profile | `cc_face_material_quality_v1` / `production_approved` |
| Animation registry | `cc5_unreal_animation_channels_v1` |
| UE project | `D:\UE\projects\datatry_02` / UE 5.8 |
| UE Auto Setup | Reallusion All-in-One 2.03 |
| UE animation controller | 磁盘存在 v003；`dm_asset_index.json` 仍登记 v002，待 UE 在线同步 |

## 4. 当前操作约束

- CC 使用学校离线许可证；Agent 不自动重启 CC。
- CC private memory 达到 24 GB 时停止长批次并由用户决定重启。
- Undo 警告守卫只允许精确匹配已知对话框；其他弹窗必须停止等待人工处理。
- Bridge、UE Python Remote Execution 或 Unreal MCP 的配置存在都不代表对应通道在线，必须分别做实时健康检查。
- 外观 API 成功不等于视觉通过；完整角色必须执行静态和动态门禁。
- M05/F05 不自动继承原 8 BodyFit 的所有历史眼球、牙齿和外观矩阵结论。

## 5. 当前同步债务

1. `cc_character_showcase_10_20260803_v1.json` 仍保留视觉审核待定状态，与用户已验收事实不一致；本轮文档重组不修改 JSON。
2. `D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` 仍指向动画控制器 v002，磁盘实际 Pilot 已到 v003；必须在 UE 与 MCP 在线时核对后更新。
3. Bridge 命令名 `validate-bodies` 实际也承担兼容角色 manifest 执行，语义不清；完整角色专用命令仍在 Roadmap。
4. 十体型尚未全部完成 CC→UE 批量导出和运行时验证。
5. Bridge `apply-face` 仍要求旧 `target_face_morphs` schema，不能直接接收当前 `primary_face_seed_id + local_morphs + Facial Profile` 的 Face V3 配方。
6. `cc_face_recipes_v3_200.json` 的文件元数据仍为 `quality-review-only`，而当前人工规范已将其作为生产 Face V3 基线；后续允许修改 JSON 时应统一状态并保留版本迁移记录。
7. `ue_validate_m02_modular_blueprint.py` 仍硬编码 `BP_DM_M02_ModularPilot_v001`；当前 v002 的结构只由 broadcaster 验证和 v003 PIE 矩阵部分覆盖，尚无独立参数化结构验证器。
8. v003 hybrid-face 和 Elder Morph 两个 UE wrapper 使用固定输出目录并覆盖同名 Pilot 报告；参数化 `run_id/output_dir` 前，重跑需先人工归档旧证据。

## 6. 当前下一步

阶段 5B：离线 Headshot 4 人 smoke。先验证生成、保存、重载、Facial Profile、弹窗和脚本可达性，再决定 10/20 高质量原型比较。详细验收见 [`planning/ROADMAP.md`](./planning/ROADMAP.md)。
