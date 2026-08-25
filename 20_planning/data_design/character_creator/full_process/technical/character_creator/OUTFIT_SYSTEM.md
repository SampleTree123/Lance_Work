# 服装 Family、槽位组与兼容性

> 文档 ID：`TECH-CC-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：Outfit Family JSON、共享鞋池、静态兼容门禁和动作压力门禁
> 验证所有权：`VAL-MATRIX-01`（服装兼容子项）、`VAL-CC-02`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-25

## 1. 能力与边界

服装以 Family 为兼容边界。除人工明确合并或 Registry 允许的组合外，不跨 Family 随意替换单件。第一批在 UE 中使用烘焙 FullReference Look，不依赖运行时单件换装。

## 2. 输入、规范目录和槽位

Family 内服装目录只使用：

```text
Coats/
Shirts/
Pants/
Skirts/
Full-body/
Shoes/
_Accessories-Pending/
outfit_family.json
```

`Full-body` 的单个资产可以是独立整套，也可以是由多个锁定组件构成的 Bundle；JSON 的组类型消除歧义。

## 3. Family JSON 模型

- `slot_group`：定义必选/可选槽位及每个槽位的候选池；兼容项可自由组合。
- `locked_bundle`：一组资产必须整体应用，不能拆分。
- `local_accessories`：只适用于当前 Family 的配件，不进入全局 Both 池。
- 鞋：Family 有原配鞋时只使用自己的 `Shoes/`；没有原配鞋时通过共享 `shoe_ids` 解析到全局鞋 Registry；`barefoot_allowed` 不等于必须赤脚。

## 4. 机器入口

| 文件/工具 | 作用 |
| --- | --- |
| `outfit_family_v1.schema.json` | Family JSON Schema |
| `cc_validate_outfit_family_library_v1.py` | 全库结构与引用验证 |
| `cc_build_confirmed_outfit_family_json_v1.py` | 从已确认规则生成 Family JSON |
| `cc_merge_shared_shoe_assignments_into_outfit_rules_v1.py` | 合并鞋池分配 |
| `cc_organize_shared_shoes_v1.py` / `cc_finalize_curated_shoes_v1.py` | 鞋池去重、分类、重编号 |
| `cc_build_outfit_compatibility_gate_v1.py` | 三体型静态门禁计划 |
| `cc_build_outfit_motion_stress_gate_v1.py` | 重体型动作压力门禁计划 |
| `cc_validate_body_reconstruction.py` | CC 内实际装配、动作和截图 |

## 5. 当前验证边界

现有精选库包含 41 个 Family 和 53 个逻辑组。静态极端体型门禁为 159/159，动作压力门禁为 53/53，用户已抽查并接受；这不代表未来新增体型、动作或跨 Family 组合自动兼容。

## 6. 组装顺序与弹窗

1. 重载规范角色项目并清除源服装/源局部配件。
2. 按内到外顺序应用 Pants/Skirts、Shirts、Coats、Full-body、Shoes 和本地配件。
3. 对旧代服装的 Apply Cloth Options 只能使用 Family 已验证策略；未知情况停止。
4. 验证 Inventory Signature，防止资产被隐式替换或驱逐。

## 7. 验证

- 静态：前、后、左右和三分之四视角，覆盖 slim/heavy/short 极端体型。
- 动态：至少 Walk 与 Full Body Calibration 的归一化时间采样。
- 人工：腋下、腰腹、胯部、裙摆、鞋脚、头发/兜帽和多层服装。
- UE：导入后用生产 Skeleton 和动作再次检查，CC 通过不能替代 UE 验收。

## 8. 输出与保留

Family JSON、Schema、鞋 Registry 和最终审查索引为 `authoritative`。完整静态/动态 Gate 和用户决定为 `retained_evidence`。日期重组备份、旧恢复分片和被取代联系表在映射确认后可标为 `superseded`。
