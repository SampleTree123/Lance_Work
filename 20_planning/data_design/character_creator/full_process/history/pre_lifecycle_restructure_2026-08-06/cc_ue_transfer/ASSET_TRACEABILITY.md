# CC→UE 资产追溯规范

> 文档角色：`technical_reference`
> 状态：`validated_pilot`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 追溯链

```text
BodyFit .ccProject + face recipe + appearance IDs
  -> compiled character manifest
  -> normalized .ccProject + CC validation result
  -> versioned FBX/JSON/textures bundle
  -> UE Vendor import assets
  -> DataMake derived Blueprint/animations/config
  -> validation reports and rendered evidence
```

每层必须能够回指上一层，不能仅依靠 UE 资产显示名或截图猜测来源。

## 2. 导出 manifest 最小字段

```json
{
  "export_id": "cc_m02_average_ue58_v001",
  "character_id": "CCSHOW_M02_AVERAGE_001",
  "bodyfit_id": "M02_Average",
  "face_recipe_id": "MFACEV3_0006",
  "source_project": {"path": "...", "sha256": "..."},
  "character_manifest": {"path": "...", "sha256": "..."},
  "fbx": {"path": "...", "sha256": "..."},
  "json": {"path": "...", "sha256": "..."},
  "target": {"engine": "UE 5.8", "auto_setup": "2.03"}
}
```

未来正式批量导出时把 schema 固化为机器 JSON；当前 M02 仍为 Pilot，不能伪造缺失字段。

## 3. M02 当前映射

| 层 | 当前路径 |
| --- | --- |
| CC bundle | `D:\UE\exports\character_creator\pilot_m02_ue58_v001` |
| Full reference mesh | `/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/CC_M02_Average_Pilot_UE58` |
| Skeleton | `/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/CC_M02_Average_Pilot_UE58_Skeleton` |
| Split module root | `/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot` |
| DataMake Blueprint | `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` |
| Current disk AnimBP | `/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003` |
| UE project index | `D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` |
| Evidence root | `D:\UE\Lance_Work\00_engine\outputs\unreal_character_import` |

`dm_asset_index.json` 当前仍登记 AnimBP v002。只有 UE 在线核对 v003 后才能更新索引；文档先记录该同步债务。

## 4. 命名与版本

- Vendor：`/Game/Vendor/Reallusion/CC5/<Domain>/<BodyFit>/...`
- DataMake：`/Game/DataMake/<Domain>/CC5/...`
- 版本使用 `_v001`、`_v002`，不覆盖已验证资产。
- FullReference、Modules、Animations 和 Derived Blueprint 分开。
- 来源资产不移动；替代版本通过 manifest/ADR 标记，不使用重定向器掩盖来源变化。

## 5. 验证证据

UE 构建/验证 JSON 保存在：

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\
```

输出不是长期权威配置。通过结论要同步到 `CURRENT_STATUS.md` 和 Milestone Log，UE 对象路径同步到 `dm_asset_index.json`；后者必须在线核验后修改。

