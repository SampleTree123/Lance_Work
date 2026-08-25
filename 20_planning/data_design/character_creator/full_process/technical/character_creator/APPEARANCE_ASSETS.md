# 面部外观与毛发资产

> 文档 ID：`TECH-CC-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：Appearance Catalog、Compatibility Registry、Pigmentation Policy 和视觉门禁
> 验证所有权：`VAL-MATRIX-01`（外观资产子项）、`VAL-CC-01`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-25

## 1. 能力与边界

外观资产包括皮肤、眼球材质、牙齿、眉毛、睫毛、头发和胡须。可以替换不等于任意组合自然；性别偏好、皮肤色素、毛发颜色、眼口几何和服装冲突必须由 Registry/Policy 控制。

## 2. 机器入口

| 文件 | 作用 | 状态 |
| --- | --- | --- |
| `cc_appearance_asset_catalog_v1.json` | 资产 ID、路径和类型 | `production` |
| `cc_appearance_compatibility_v1.json` | 性别/部件兼容结果 | `validated_pilot` |
| `cc_appearance_domain_policy_v1.json` | 皮肤与毛发色素域 | `validated_pilot` |
| `cc_facial_hair_asset_catalog_v1.json` | 胡须候选 | `validated_pilot` |
| `cc_scalp_hair_asset_catalog_v1.json` | 头发候选与性别偏好 | `validated_pilot` |
| `cc_eyelash_compatibility_batch_v1.json` | 睫毛兼容输入 | `validated_pilot` |

生成器包括 `cc_build_appearance_asset_catalog.py`、`cc_build_appearance_compatibility_registry.py` 及各部件批次/汇总工具。运行时统一由 `cc_validate_body_reconstruction.py` 执行受控配置。

## 3. 当前已验证池

当前历史证据覆盖 21 套皮肤、12 套眼球材质、13 套眉毛、9 套睫毛、2 套牙齿、5 套胡须和 58 个发型候选。数字只表示已盘点/验证边界，具体生产启用由批次矩阵决定。

眼球资产主要改变材质，但仍需检查极端视线、闭眼和眼皮遮挡。牙齿需要张嘴和微笑检查。睫毛和眉毛可以跨多种脸型，但必须保留资产应用时产生的支持状态。

## 4. 色素策略

角色先根据皮肤/身份选择自然色素档案，再从档案抽取统一毛发颜色，应用到头发、眉毛和胡须。自然模式不从全局颜色池无条件采样；染发和罕见模式必须显式标记，不能伪装成自然分布。

## 5. 头发和胡须

- 发型有 `male_default`、`female_default` 和可选跨性别呈现标签。
- 第一批使用烘焙 Look，不在 UE 中任意替换头发。
- 长发、兜帽、头巾和高领服装存在相交风险；批次 Matrix 必须登记组合。
- 胡须可以作为有/无变体研究，但网格适配仍需按头面验证。

## 6. 应用顺序

```text
Identity/BodyFit
  -> Skin
  -> Eye/Teeth
  -> Brows/Eyelashes
  -> Hair/Beard
  -> Pigmentation/material settings
  -> static and dynamic acceptance
```

不得为了替换一个部件把所有未关注 Morph 清零。应用后检查中性、眨眼、闭眼、微笑、张嘴和材质接缝。

## 7. 输出与保留

Catalog、Compatibility 和 Policy 为 `authoritative` 或 `retained_evidence`；批次截图由视觉决定引用后为 `retained_evidence`，重复轴扫描可降为 `superseded`。准确视觉入口见 [视觉审查](../validation/VISUAL_REVIEW.md)。

本能力拥有以下历史输出根及启动诊断：

```text
%OUTPUT_ROOT%/character_creator_content_acquisition/
%OUTPUT_ROOT%/character_creator_content_migration/
%OUTPUT_ROOT%/eyebrow_runner_boot.stdout.log
%OUTPUT_ROOT%/eyebrow_runner_boot.stderr.log
```

它们用于内容采购/迁移审计和早期眉毛 Runner 诊断；当前未评为 `superseded/disposable` 的项继续受保护。

## 8. 失败与恢复

资产应用失败、眼口偏移或材质异常时，从干净规范项目重新加载 Identity/BodyFit，再只重放已登记的外观步骤；不得通过清零未知 Morph、覆盖源资产或连续点击未知弹窗修补。单一资产失败时隔离该资产并保留失败组合与截图，其他已通过资产可以继续；修复后生成新 Compatibility 结果，不原地改写已接受证据。
