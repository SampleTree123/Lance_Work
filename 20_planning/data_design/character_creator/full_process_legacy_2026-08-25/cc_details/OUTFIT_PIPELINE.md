# Character Creator 服装 Look 技术规范

> 文档角色：`cc_outfit_domain_spec`
> 状态：`active_development`
> 适用阶段：`WF-01..WF-07`
> 权威范围：服装源包、服装资产、Look、替换组、十体型兼容和 CC→UE 服装边界
> 上级入口：[`README.md`](./README.md)
> 上游：用户提供的本地服装源、十个 BodyFit 与机器源包索引
> 下游：CC Look Pilot、十体型兼容矩阵、UE `SetOutfitLook`
> 最近核验：2026-08-17

## 1. 目的与使用时机

本文定义服装从“本地下载包”进入“可在角色工厂使用的批准 Look”的完整技术路线。新增服装来源、挑选 Pilot、设计层级、判断能否拆换、扩展到十体型或导入 UE 时先读本文。

当前已完成 **源发现、机器分类、按性别最新 50% 的日期重组、人工精选、六槽位物理规范、全部 41 个服装族 JSON、鞋规则合并、极端 BodyFit 静态门禁，以及同性重体型动作压力诊断门禁**。当前规则为 37 个 `slot_groups` family 和 4 个 `locked_bundle` family，共 53 个逻辑组。静态门禁 v3 已发布 159/159 案例、53/53 个完整 Look、795/795 图；动作压力 gate v3 已完成 53/53 Look、583/583 图，inventory 匹配 53/53，机器失败均为 0。用户抽查动态结果后报告未发现问题，门户已标为 `approved`；该结论不是逐 Look 全量签字。Redsoul 已通过受注册表和双哈希约束的字节完全相同扩展名调度别名完成正式复测。头发-头部服装兼容、全部十体型和 UE 切换仍未完成。因此：

- `source package` 不是批准服装；
- CC 能加载某件衣服不代表它可与任意上衣/外套组合；
- `female/male` 来源目录是用户初分标签，不是机器兼容结论；
- 门户中的 `pending_review` 记录不能作为生产 Look。

## 2. 当前源盘点结论

源目录：

```text
CLOTHING_SOURCE_ROOT = D:\BaiduNetdiskDownload\人物和服装
CLOTHING_FILTERED_ROOT = D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted
CLOTHING_FILTERED_V1_ROOT = D:\BaiduNetdiskDownload\人物和服装_2022plus_sorted
FEMALE_SOURCE_ROOT   = %CLOTHING_SOURCE_ROOT%\female
MALE_SOURCE_ROOT     = %CLOTHING_SOURCE_ROOT%\male
```

2026-08-11 `cc_clothing_source_inventory_20260811_v1` 的当前结果：

| 指标 | 数量 |
| --- | ---: |
| 物理源文件 | 1330 |
| 源数据体积 | 38.83 GiB |
| ZIP | 61，全部可读 |
| 散装目录包 | 187 |
| 机器源包 | 248 |
| 含服装源包 | 231 |
| 服装资产条目 | 2596 |
| `clothing_only` | 223 |
| `clothing_with_character` | 8 |
| `character_only` | 2 |
| `accessory_only` | 11 |
| 材质/道具等非服装目录 | 4 |
| 已复制预览 | 85，覆盖 57 个源包 |
| 精确重复 ZIP 组 | 1 |
| 内部资产清单重复组 | 10 |

`Pajamas & Nighties` 和 `阿拉伯头巾连衣裙` 当前只暴露角色/项目资产，不能按独立服装处理。帽子、眼镜、饰品、MaterialPlus 和 Prop 目录保留为支持资产，但不计入服装候选。

至少 10 组内容跨 `female/male` 重复，包括运动服、职业装、Ancient Rome、末日幸存者、潮牌服装等。后续先建立一个规范 `source_family_id`，再根据实际 CC 适配记录 `target_sex`；禁止因目录位置重复计数。

源盘点器还执行载荷门禁：`.ccCloth/.ccShoes/.ccGloves` 小于 `64 KiB` 时保留来源记录，但标记为 `suspected_placeholder`，只含此类文件的包不能进入 CC Pilot。该规则来自 `All Star` 的真实失败：五个所谓服装文件均只有约 `6-7 KiB` 且全部无法加载；正常候选通常为数 MiB 至数十 MiB。

### 2.1 固定 2022 日期门禁历史结果

2026-08-11 对源目录执行包级日期门禁。ZIP 以完整压缩包为单位；散装内容以一个产品根目录为单位。日期只读取 CC 资产本体，不使用预览图、说明文件或 ZIP 下载时间。只要包内有一个有效 CC 资产时间早于 `2022-01-01`，整个包进入 `_outdated`。

ZIP 成员时间是压缩包记录的最后修改时间，散装资产使用文件最后修改时间，二者都不是作者制作日期的绝对证明。ZIP 默认 `1980` 日期、无日期及明显由 2026-08-07 下载/解压操作重写的散装时间进入 `_date_unknown`，不得自动视为新资产。

| 结果 | 包数 | 处理规则 |
| --- | ---: | --- |
| 物理包 | 140 | 61 ZIP + 79 个产品级散装目录 |
| 去重后逻辑包 | 131 | 同载荷包只保留一份 |
| 通过日期门禁 | 54 | 直接位于 `male/female/both`，进入第一人工审查队列 |
| 过时 | 55 | 位于 `_outdated`，默认不再使用 |
| 日期不明 | 22 | 位于 `_date_unknown`，需单独人工确认，不能自动批准 |
| 男女共有 | 9 | 全部早于 2022，因此位于 `both\_outdated` |

男女共有的九个逻辑包为：`12款帽子 多种颜色`、`Modern Glasses`、`服装1`、`服装Ancient Rome 4.0 Bundle`、`末日幸存者`、`潮牌服装`、`狂徒`、`职业装`、`运动服装`。它们只保留一份，不在男女目录重复计数。

复制使用独立目标根，原始 `%CLOTHING_SOURCE_ROOT%` 未移动、未删除。完整 SHA-256 验证通过：131 个逻辑包、1309 个载荷文件、`36,213,453,075` 字节，错误为 0。

该版本保留在 `%CLOTHING_FILTERED_V1_ROOT%` 作为可回退历史结果，不再是当前人工审查入口。

### 2.2 当前 newest-50 日期策略

由于固定 2022 截止只留下 5 个女性已知日期包，当前政策改为按 `female`、`male`、`both` 分组，以包内最早 CC 资产时间降序排列，各自保留最新约 50%。日期不明包不参与百分位排名，继续放在 `_date_unknown`；排名落入较旧半区的包放在 `_older_half`。

| 分组 | 有可靠日期 | 当前主队列 | 较旧半区 | 日期不明 | 边界时间 |
| --- | ---: | ---: | ---: | ---: | --- |
| female | 39 | 20 | 19 | 21 | `2021-03-28 09:22:32` |
| male | 61 | 31 | 30 | 1 | `2022-08-18 11:16:12` |
| both | 9 | 5 | 4 | 0 | `2021-03-10 18:17:32` |
| 合计 | 109 | 56 | 53 | 22 | 分组计算 |

`both` 当前主队列包含：`12款帽子 多种颜色`、`Modern Glasses`、`服装Ancient Rome 4.0 Bundle`、`末日幸存者`、`狂徒`。当前权威根为 `%CLOTHING_FILTERED_ROOT%`。最终全量 SHA-256 验证仍为 131 个逻辑包、1309 个载荷文件、`36,213,453,075` 字节、0 错误。

### 2.3 人工精选与物理目录规范终态

2026-08-12 用户完成 newest-50 结果的逐项去留与人工整理。物理规范执行时 male/female 主体库包含 13 个女性服装族、28 个男性服装族，共 349 个可穿戴资产；随后用户继续删除未批准或无兼容关系的资产，2026-08-13 当前实际为 332 个。`both` 的鞋于 2026-08-14 完成第一轮规范，其余帽子、眼镜和饰品仍延后处理。

普通服装族只使用实际需要的六个主体槽位目录：`Coats`、`Shirts`、`Pants`、`Skirts`、`Full-body`、`Shoes`。物理规范时有 21 个帽子、首饰、围巾、手套、腰带等组件放在 `_Accessories-Pending`；用户清理后当前剩 13 个，现已全部在 family JSON 中确认为家族专用配饰。普通 `Full-body` 直属文件各自代表一个单件候选；`Elise`、`Misaki`、赛博朋克套装的多文件锁定整体分别位于 `Full-body/Locked-Bundle`，每族只有一个锁定整体。

物理规范共移动 288 个文件：19 个 Coats、75 个 Shirts、70 个 Pants、6 个 Skirts、26 个普通 Full-body、19 个 Locked-Bundle 组件、52 个 Shoes 和 21 个待处理配件。移动前后逐文件 SHA-256 一致；执行后的幂等 dry-run 为 0 个待移动文件，结构违规和空目录均为 0。操作证据位于：

```text
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\clothing_structure_normalization\run_20260812_v1
```

日期阶段发布的根目录 CSV、`COPY_MAP.json` 与说明文件是历史筛选证据，不再是人工精选终态清单；正式 `outfit_library.json` 建立后必须替代它们作为权威入口。

### 2.4 全部服装族 JSON

2026-08-13 用户完成剩余复杂家族的组装关系确认，并删除无法建立合理兼容关系的资产。2026-08-14 进一步澄清：除真正不可拆的多文件整体外，同一服装族内不保留基于名称推断的固定编号搭配；`Shirts`、`Pants`、`Shoes` 等各自形成槽位池，`Full-body` 也作为单件池，每次从当前逻辑组的各必需池中选一件。原有 24 个 `explicit_looks` family 已迁移为 `slot_groups`。

当前 41 个 male/female family 全部生成 `outfit_family.json`，覆盖 332 个可穿戴资产：37 个使用 `slot_groups`、4 个使用 `locked_bundle`，共 53 个逻辑组；生产规则中 `explicit_looks=0`。当前 deferred 数为 0，13 个家族专用配饰全部登记；独立验证结果为 `41/41`、0 错误。Cheer Leader 是“同一 family 内仍需固定子组”的已验证例外：不同编号的上衣与裤子在 CC 中会互相替换，因此必须使用 `matched_01/02/03` 三个组，不允许跨编号抽取。

复杂家族的已确认组装边界如下。每次先选择一行对应的组，再在该行槽位池内抽取；不允许跨行拼接：

| Family | 已确认组装规则 |
| --- | --- |
| `潮牌服装` | `Full-body` 单件；或 `Pants+Shirts`；或 `Pants` 分别与 `CasualJacket/WarriorCloak/Windbreaker` 三类之一组合；或 `Skirts+Shirts`。`Shirts` 与三个 Coats 子类互斥 |
| `非洲女性休闲装` | `Full-body` 单件；或任意 Pants + `anita 5/6 shirt`；或任意 Pants + `anita 3/4 bra` + 任意 Coat |
| `海滩内衣Bikini & Ruana` | Pants 与 Shirts 必选并可自由组合；Coats 可选且最多一件 |
| `连衣裙` | 任意 Full-body + Shoes；或 Shirts + Skirts + Shoes；三个家族配饰均为可独立开关的可选项 |
| `漂亮裙子` | Shirts 与 Shoes 必选；下装在 Pants/Skirts 两组中二选一；组内自由组合 |
| `Jiving` | Pants + Shirts，均必选且组内自由组合 |
| `Lift & Haul`、`Oahu`、`Streetstyle` | Pants + Shirts + Shoes，均必选且组内自由组合 |
| `redsoul` | 六个组件构成一个不可拆的 `locked_bundle` |
| `White Tie` | Coats + Pants + Shirts + Shoes + Waist Coat 全部必选，主体槽组内自由组合 |
| `男士服装+帽子` | `Full-body+Shoes`；或 `Pants+Shirts+Shoes` 且 Coats 可选；帽子由未来 `both` 规则处理 |

`Rugged & Trendy Collection` 男女各有一个扩展名为 `.ccShoes`、语义上却是完整服装的资产。两者均保留原文件和扩展名，移动到 `Full-body`，并在 JSON 中写入 `slot=full_body` 与 `semantic_slot_override=true`；不能为了名称整齐修改 Reallusion 资产扩展名。

权威实现与证据：

```text
Schema:
D:\UE\Lance_Work\00_engine\scripts\character_creator\outfit_family_v1.schema.json

确认/延后规则：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_outfit_confirmed_rules_v1.json

生成器：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_build_confirmed_outfit_family_json_v1.py

独立验证器：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_validate_outfit_family_library_v1.py

证据：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_family_rules\run_20260812_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_family_rules\run_20260812_v2_family_accessories
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_family_rules\run_20260813_v3_all_confirmed
```

### 2.5 共享鞋池第一轮规范

2026-08-14 对以下活动根执行了可回滚迁移：

```text
D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted\both\shoes
```

迁移前该根含 60 个物理 `.ccShoes`。脚本同时对照全部 `outfit_family.json` 的鞋声明，找回此前未移动进 `both/shoes` 的 2 双男鞋；随后只按 SHA-256 合并 4 份完全相同的冗余副本，不删除任何仅外观相似但二进制不同的鞋。最终结果为 58 双唯一鞋：女性 17 双、男性 41 双。

活动目录只保留 `Female`、`Male` 和 `shoe_inventory.json`，不再设置 Unisex。男女分别独立连续编号为 `F001-F017` 和 `M001-M041`；每个资产路径固定为 `Sex/Style/ID_Name.ccShoes`。当前样式分类是人工审查前的初稿：女性 `Formal 10 / Heels 7`，男性 `Boots 10 / Casual 16 / Formal 3 / Sandals 4 / Sport 6 / Traditional 2`。

权威实现、清单和审计证据：

```text
脚本：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_organize_shared_shoes_v1.py

活动清单：
D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted\both\shoes\shoe_inventory.json

执行报告与迁移前完整备份：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v1
```

这是第一轮迁移的历史状态。当时有 2 双家族原配鞋被错误地从 family 目录移入审计备份；该问题已在 2.7 节修复。共享池副本与 family 原配鞋此后严格分离，不能再用共享池成员资格推断原配鞋是否可用。

### 2.6 第一轮用户筛选后重编号

2026-08-14 用户完成鞋的视觉去留和类别调整。筛选删除 6 双男鞋后，使用 `cc_finalize_curated_shoes_v1.py` 对全部保留资产重新编号、修正目录/文件名类别，并生成 schema 2 权威清单。当前共 52 双唯一鞋：女性 17、男性 35。

```text
Female/Flats    F001-F001   1
Female/Heels    F002-F017  16
Male/Boots      M001-M007   7
Male/Casual     M008-M019  12
Male/Formal     M020-M025   6
Male/Sandals    M026-M029   4
Male/Sport      M030-M035   6
```

当前文件严格使用 `Sex/Category/ID_Category_Family_Name.ccShoes`，52 个 ID 连续且唯一，文件名类别与目录一致，文件哈希与筛选前来源逐一匹配。清单中的 `removed_from_previous_inventory` 记录了 6 个用户删除项；`rename_map`、执行报告及重编号前完整备份位于执行证据目录。

```text
脚本：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_finalize_curated_shoes_v1.py

权威清单：
D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted\both\shoes\shoe_inventory.json

dry-run：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v2_curated_reindex_dry_run

执行、映射和备份：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v2_curated_reindex
```

该 schema 2 清单是第二轮跨性别副本加入前的历史版本。当前权威状态见 2.7 节。

### 2.7 男女副本与家族原配池分离

用户确认以下业务边界：

- 套装自己的 `Shoes` 目录是该家族的原配鞋池；存在多个原配鞋时，可在该目录登记的候选中选择；
- `both/shoes` 是独立共享池，主要为没有原配鞋的套装提供候选；每个缺鞋套装可以拥有多个允许的共享鞋 ID，不限制为一双；
- 从共享池删除某双鞋，只表示它不能跨套装复用，不会删除或禁用其家族原配版本；
- 同一几何可分别作为男性和女性共享资产登记，但同一性别池内不得出现重复哈希。

2026-08-14 用户从男性池复制 8 双适合女性使用的鞋。规范后 schema 3 清单包含 60 个性别资产和 52 套唯一几何：

```text
Female/Boots      F001-F002   2
Female/Flats      F003-F005   3
Female/Heels      F006-F021  16
Female/Sandals    F022-F025   4
Male/Boots        M001-M007   7
Male/Casual       M008-M019  12
Male/Formal       M020-M025   6
Male/Sandals      M026-M029   4
Male/Sport        M030-M035   6
```

8 个女性资产通过 `copied_from` 指向对应男性 ID，物理文件分别保留，但哈希相同。早期误移的 `male.redsoul` 和 `male.cyberpunk_locked` 原配鞋已从审计备份复制回各自 `Shoes` 目录；完整服装族验证重新得到 `41/41`、0 错误，覆盖 51 双 family JSON 原配鞋。

```text
脚本：
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_integrate_cross_sex_shoes_v1.py

权威 schema 3 清单：
D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted\both\shoes\shoe_inventory.json

dry-run：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v3_cross_sex_dry_run

执行、备份和 family 验证：
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v3_cross_sex
```

下一数据步骤不是替换 family JSON 的原配鞋路径，而是只为没有原配鞋的 family 增加 `allowed_shared_shoe_ids` 与默认选择；最终字段名应在共享分配 schema 确定后统一写入。

待填写草稿已生成：

```text
D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted\both\shared_shoe_assignment_draft.json
```

草稿只包含 `native_shoe_asset_count=0` 的 15 个 family：女性 11、男性 4；另外 26 个有原配鞋的 family 被排除。每项由用户填写 `shoe_resolution`、`allowed_shared_shoe_ids`、可选的 `default_shared_shoe_id`、`allow_barefoot` 和备注。`allow_barefoot` 与 `shared_pool` 独立：它为 true 时，生成器可在鞋池和赤脚之间选择；只有必须始终赤脚时才使用 `barefoot_only`。Elise、Misaki 及男女 Rugged & Trendy 标记为 `review_before_assignment`；Bikini 与 Pyjamas 带有 `barefoot_may_be_valid` 提示。生成器默认拒绝覆盖已存在草稿，避免清除用户输入。

用户分配已于 2026-08-14 完成并规范化。当前 15 个 family 中，13 个为 `shared_pool`，男女 Rugged & Trendy 两个为 `integrated_footwear`；共有 116 个鞋引用和 43 个唯一共享鞋 ID，全部存在、性别匹配且实体文件可读。Bikini 与 Pyjamas 的 `allow_barefoot=true` 表示可在共享鞋池和赤脚之间随机，不表示必须赤脚。当前所有 `look_overrides` 均为空，因此每个 family 的共享池适用于其全部 Look。

两个容易误解的字段：

- `semantic_footwear_assets` 是机器扫描证据，不是共享鞋候选池。它记录扩展名或语义像鞋、但被 family 归入 `full_body` 等其他槽位的资产，用于发现服装本身已经包含脚部/鞋的情况。当前只有男女 Rugged & Trendy 各一项，因此选择 `integrated_footwear`，避免再叠加共享鞋。
- `look_overrides` 是 family 级共享池的例外表。只有同一 family 内某个特定 Look 不能使用完整共享池时才填写更窄的候选池；空数组表示不设置例外。其正式子结构应在首次出现真实例外时连同验证器一起冻结，当前不要为普通 family 填写。

本轮仅完成静态分配。下一个门禁仍是把登记过的实际 `Look × Shoe` 组合加载进 CC，检查穿模、脚底接地、动作形变和服装层级，并把通过组合写入兼容性记录。

## 3. 数据模型

| 对象 | 定义 | 能否直接生产使用 |
| --- | --- | --- |
| Source package | 一个 ZIP 或包含 CC 资产的散装目录 | 否，只是来源边界 |
| Source family | 同一产品在多个目录、槽位或男女根中的逻辑集合 | 否，先去重和归并 |
| Garment asset | 一份 `.ccCloth/.ccShoes/.ccGloves` 几何资产 | 否，需槽位和适配验证 |
| Material variant | 同一几何的颜色/纹理变化 | 只能附属于已批准几何 |
| Outfit Look | 一套明确槽位、层级、互斥、隐藏和动作约束的完整搭配 | 通过门禁后可以 |
| Swap group | 在同一已批准 Look 中可替换的等价资产集合 | 只允许登记组合 |
| BodyFit variant | 为某个 BodyFit 保存/导出的该 Look 网格集合 | 只对该 BodyFit 有效 |
| Compatibility record | `BodyFit × Look × motion/profile` 的通过、拒绝和证据 | UE 运行时唯一许可来源 |

### 3.1 `outfit_family.json` 组装模式

| 模式 | 含义 | 使用边界 |
| --- | --- | --- |
| `explicit_looks` | 列出一套或多套确定的完整穿法，每套显式引用全部必需资产 | 仅在用户或作者资料明确要求固定搭配时使用；当前活动库为 0 |
| `slot_groups` | 在一个已确认子组内，为每个必需/可选槽位列出允许抽取的资产池 | 只有用户已确认组内任意替换安全时使用；不是跨 family 笛卡尔积 |
| `locked_bundle` | 多个资产共同构成一个不可拆的整体 | 细碎组件必须全部加载，不能作为普通单件替换 |

Schema 仍保留 `explicit_looks` 以兼容未来确有作者锁定搭配的资产，但当前活动库没有使用该模式。当前普通服装一律在所属 `slot_group` 内按槽位抽取；这不是跨 family 混穿。`Full-body` 池的语义是“一次选一件完整服装”，不会把池内多件同时装配。

每个 confirmed JSON 必须满足以下不变量：

- family 目录中的每个可穿戴资产恰好被组装规则覆盖，不能漏登记；
- `rules_exhaustive=true`，且 `allow_cross_family_components=false`；
- `Full-body` 与 `Coats/Shirts/Pants/Skirts` 互斥，`Pants` 与 `Skirts` 互斥；
- 每个资产记录相对路径、语义槽、原扩展名、字节数和 SHA-256；
- deferred family 不得存在 `outfit_family.json`；
- JSON 成功生成只证明“规则被明确记录”，不等于完成 CC 几何与动作门禁。

`_Accessories-Pending` 仍是物理暂存目录，不是第七个主体服装槽。某个组件经用户确认只能服务于当前服装族后，JSON 将其登记为 `slot=family_accessory`、`component_scope=family_local`，并强制 `family_accessories_cross_family=false`。`required_assets` 中的配饰必须加载；`optional_assets` 使用 `independent_subset` 语义，表示每项可独立开关，允许全不选、任选一项或全部选择。有依赖关系的配饰禁止用该简化语义，必须枚举为独立 Look。

Look 至少登记：

```text
look_id
source_family_ids
target_sex_profile
slot_assets
layer_order
required_assets
mutual_exclusions
body_hide_mask
material_variant_ids
supported_bodyfit_ids
motion_risk_tags
status
evidence
```

## 4. 源包机器分类

索引器按 ZIP 内部成员或散装文件的真实扩展名分类，不信任文件夹名和压缩包名：

| `content_class` | 判定 |
| --- | --- |
| `clothing_only` | 有服装/鞋/手套，没有角色项目 |
| `clothing_with_character` | 同时有服装和 `.ccAvatar/.ccProject` 等角色资产 |
| `character_only` | 只有角色/项目，没有独立服装 |
| `accessory_only` | 只有 `.ccAcc/.iAcc` 等附件 |
| `mixed_nonclothing` | 材质、道具、毛发或其他支持内容，无独立服装 |

机器还给出槽位、风格和 `look_policy_hint`。它们只用于缩小人工检查范围：

| 提示 | 第一轮策略 |
| --- | --- |
| `locked_look_first` | 保留作者整套搭配；历史、制服、末日、盔甲和复杂 Full-body 默认采用 |
| `constrained_modular_candidate` | 可研究上/下/外套/鞋的受限替换，不做任意笛卡尔积 |
| `swap_group_candidate` | 单槽资产可进入等价替换组，但仍需轮廓、层级和动作门禁 |
| `manual_classification_required` | 路径不足以判断槽位，必须在 CC 中人工分类 |

## 5. 可复现源盘点

运行环境是系统 Python，不需要打开 CC：

```powershell
$root = 'D:\UE\Lance_Work'
$ccScriptRoot = "$root\00_engine\scripts\character_creator"
$portalRoot = "$root\00_engine\visualization_portal"

python "$ccScriptRoot\cc_inventory_clothing_sources_v1.py"
python "$ccScriptRoot\cc_make_clothing_source_inventory_review_v1.py"
python "$portalRoot\tools\build_clothing_source_inventory_run.py"
python "$portalRoot\tools\register_run.py" `
  "$portalRoot\runs\2026-08-11-cc-clothing-source-inventory-v1\run.json" `
  --replace

# 当前 newest-50 策略先 dry-run；只有建立全新目标目录时才执行 --execute。
python "$ccScriptRoot\cc_reorganize_clothing_by_date_v1.py" --policy newest-half-per-sex
python "$ccScriptRoot\cc_reorganize_clothing_by_date_v1.py" --policy newest-half-per-sex --execute
python "$ccScriptRoot\cc_validate_clothing_date_reorganization_v1.py" --profile newest50-v2
python "$ccScriptRoot\cc_build_clothing_review_queue_v1.py" --profile newest50-v2 --publish

# 首批 family JSON：先 dry-run，再显式执行；现有文件只有确认要重建时才加 --replace。
$outfitRoot = 'D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted'
$rulesEvidence = "$root\00_engine\outputs\character_creator_bridge\artifacts\outfit_family_rules\run_20260813_v3_all_confirmed"
python "$ccScriptRoot\cc_build_confirmed_outfit_family_json_v1.py" `
  --root "$outfitRoot" `
  --report "$rulesEvidence\dry_run_report.json"
python "$ccScriptRoot\cc_build_confirmed_outfit_family_json_v1.py" `
  --root "$outfitRoot" `
  --report "$rulesEvidence\execution_report.json" `
  --execute --replace
python "$ccScriptRoot\cc_validate_outfit_family_library_v1.py" `
  --root "$outfitRoot" `
  --report "$rulesEvidence\validation_report.json"
```

权威产物：

```text
机器目录:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\clothing_source_inventory\inventory_20260811_v1\inventory.json

审查索引:
...\inventory_20260811_v1\review\index.json

网页 run:
D:\UE\Lance_Work\00_engine\visualization_portal\runs\2026-08-11-cc-clothing-source-inventory-v1\run.json

网页入口:
http://127.0.0.1:8765/00_engine/visualization_portal/

日期重组清单:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\clothing_date_reorganization\reorg_20260811_v2_newest50\manifest.json

人工审查 CSV:
...\reorg_20260811_v2_newest50\packages.csv

可填写人工队列:
...\reorg_20260811_v2_newest50\human_review\clothing_human_review_queue_20260811_v2_newest50.csv

完整复制校验:
...\reorg_20260811_v2_newest50\validation.json
```

索引器只读源目录；不解压服装本体，只把每包最多 4 张、单张不超过 20 MiB 的预览复制到 artifacts。无预览不等于拒绝，表示必须进入 CC 视觉检查。

## 6. 首批 Pilot 来源与手工载入门禁

下表是日期重组前的首轮 Pilot 证据，用于保留加载、弹窗和穿模经验，不再等价于当前候选清单。后续候选以 `%CLOTHING_FILTERED_ROOT%` 的 56 个主队列包为主，22 个 `_date_unknown` 包只在时间来源得到解释后进入审查；`_older_half` 默认不进入本轮。

| 来源族 | 规范源包 ID | 目标 Look | 2026-08-11 手工载入结论 |
| --- | --- | --- | --- |
| Male Casual 01 | `m-l-casual-01-23f24204b9` | `M08-CASUAL-01` | M02 可加载；Jacket 需 `Conform > Increase Size = 1` |
| Male Casual 02 | `m-l-casual-02-24646486c2` | `M08-CASUAL-02` | M02 可加载；仍需记录具体放大部件和值 |
| Silver Screen 1920s | `m-z-package-90a5da7627` | `M08-1920-01` | M02 组件可加载；选择 `Keep Cloth Shape`；帽子尚待补测 |
| Female Summer | `f-z-4-173be654c8` | `F08-SUMMER-01` | F02 静态通过，无弹窗和可见穿模 |
| African Female Casual | `f-z-package-c2f9c4afcc` | `F08-AFRICAN-04` | F02 静态通过，无弹窗和可见穿模 |
| Jumpsuit & Accessories | `f-z-jumpsuits-accessories-c4bd7258b1` | `F08-JUMPSUIT-02` | F02 连体服、项链和戒指静态通过 |
| Professional Outfits | `f-z-package-3b3097475f` | 男 `PO_01/03/04/06`；女 `PO_08/09/10/12` | 八个作者项目均可打开，但尚未把服装拆出后应用到 M02/F02；PO_06 作者胖体项目自身有明显穿模 |
| Modern Sportswear | `f-z-package-5d6ca29a6c` | `M08-SPORT-01`、`F08-SPORT-01` | 文件可加载；当前男女自由组装均未批准，必须重组后复测 |

`All Star`（`m-l-all-star-91aad9b180`）已拒绝：五个 Wearable 文件只有 `6-7 KiB` 且全部加载失败，属于占位/索引壳文件。

### 6.1 目标十六套 Look

男性：`Casual 01`、`Casual 02`、1920s、西装 `PO_01`、军装 `PO_03`、消防 `PO_04`、施工 `PO_06`、一套重组后的男性运动装。

女性：`Top1 + Shorts1`、`Anita 4`、`Jumpsuit_Burberry_2`、`PO_08`、`PO_09`、`PO_10`、`PO_12`、一套重组后的女性运动装。

这些名称当前仍是 Pilot 标识。作者 `.ccProject` 只能用于确认原搭配；直接加载项目会替换角色身体，不能作为 `BodyFit × Look` 兼容证据。必须先枚举项目中的服装组件，再在 M02/F02 上重新组装。

### 6.2 旧代服装弹窗规则

`Apply Cloth Options` 表示资产来自不同 CC 代际，不表示文件损坏：

- 结构化或宽松外层，如 Jacket、Suit、Coat，先选 `Keep Cloth Shape`，再使用 Conform 修正间距；
- 紧身 Shirt、Pants、Shorts、Socks、Tights 和 Shoes，先选 `Fit Body Shape`；
- 任一选项仍穿模时，不通过当前 Look；必须删减层级、换作者搭配或拒绝该资产；
- 批量生产前必须把批准结果转换并保存为 CC5 Custom 资产，完成保存/重载验证，不能依赖运行时人工处理弹窗。

当前男性运动探索混用了 Jacket A、Pants E、Shoes B，且 Jacket 与 Pull D 严重穿模，不是作者 Look。下一次改测无外套、同后缀的 B 或 C 组。女性运动探索中的 `W_Towel` 与 Shirt/上身层级风险高；下一次先去掉 Towel，再逐件加入 Shirt、Short、Socks、Shoes。

本轮逐项证据：

```text
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\clothing_pilot_validation\manual_load_gate_20260811_v1\result.json
```

## 7. 服装实施顺序

### 7.1 A：源发现

状态 `complete`。运行第 5 节命令，确认全部 ZIP 可读、包 ID 唯一、来源存在，并保留重复组。

### 7.2 B：人工源包筛选

状态 `complete_for_garments`。newest-50 日期门禁、跨性别去重和用户人工去留已完成；当前人工精选结果为 13 个女性服装族和 28 个男性服装族。`both` 只作为共享组件来源保留，延后到配件阶段处理。历史八来源 Pilot 只保留经验，`All Star` 因缺失真实载荷继续拒绝。

### 7.3 C：选择性解压与 CC 可见性

状态 `complete_for_family_rules`。male/female 资产已经解压、人工去留并按六个主体槽位规范；复杂整体与家族专用配件没有被错误拆分。统一 Schema 已建立，41 个 family JSON 覆盖当前全部 332 个可穿戴资产并独立验证通过。当前为 37 个 `slot_groups` family、4 个 `locked_bundle` family，共 53 个逻辑组。Cheer Leader 三个同编号匹配组已替代原错误自由池。`both/shoes` 的清单和缺鞋 family 分配已完成，其他共享配件仍待后续规范。

### 7.4 D：代表组合与极端体型静态门禁

当前不是从作者项目直接继承服装，也不做槽位池笛卡尔积。`cc_build_outfit_compatibility_gate_v1.py` 对 53 个逻辑组各做一次确定性抽样，然后分别应用到同性的瘦、胖、矮三个已验收完整角色：女性 `F01/F04/F05`，男性 `M01/M04/M05`。`slot_groups` 的装配顺序固定为 `full_body → pants/skirts → shirts → coats → family_accessory → shoes`；`locked_bundle` 必须逐项保留 family JSON 中人工确认的 `required_assets` 顺序，不得套用通用槽位重排。每个案例先重载来源角色项目、清除原服装、动作和源项目配饰，同时保留身份、面部和 `GetHairs` 毛发。每次加载前必须 `ClearSelectObjects` 并只选择 Avatar；若后加载资产移除任何先前已应用的必选对象，案例立即失败。清除源配饰仅适用于当前不测试共享配件的服装门禁，不代表最终角色装配永远禁用配饰。

每个案例捕获 `front/front_three_quarter/left_profile/rear/right_profile` 五图。机器通过只证明来源哈希、项目重载、逐资产应用、scene inventory 变化、毛发保留、构图和图片写入成功；穿模、层级和美术合理性必须由用户在门户中审查。

CC5 的公开 `RFileIO.LoadFile` 会根据文件名扩展名选择内部加载分支。Redsoul 的 `SHSV_S02MA_gloves.ccGloves` 内容有效，但 `.ccGloves` 分支返回状态码 1；相同字节使用 `.ccCloth` 文件名时可正常装配。生产流程不得改写来源资产，也不得任意改扩展名：只允许 `compatibility_alias_registry.json` 登记的 `extension_dispatch_alias_only` 别名。生成器每次构建都会重新计算来源与别名的大小和 SHA-256，要求二者完全相同；未注册 `.ccGloves`、哈希漂移或策略不匹配会直接失败。该机制只改变加载器调度路径，不改变几何、蒙皮、材质或元数据。

权威文件：

```text
完整门禁:
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_outfit_compatibility_gate_20260816_v3.json

加载兼容别名注册表:
D:\UE\Lance_Work\00_engine\assets\character_creator\outfit_compatibility_aliases\compatibility_alias_registry.json

首批检查点:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260815_execution_v1\validation_result.json

首个重启分块检查点:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260815_chunks_v1\chunk_01\validation_result.json

最终复核计划:
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_outfit_compatibility_resume_plan_20260816_v6.json

最终恢复执行分片:
D:\UE\Lance_Work\00_engine\scripts\character_creator\outfit_compatibility_chunks_20260816_r14\chunk_01.json ... chunk_06.json

最终恢复执行输出根:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260816_chunks_v14

Cheer Leader 修正规则与正式结果:
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_outfit_cheer_leader_correction_20260815_v1.json
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260815_cheer_leader_fix_v1\validation_result.json

F01 修复计划:
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_outfit_f01_correction_plan_20260815_v1.json

F01 Smoke 与已取消的修复分片:
D:\UE\Lance_Work\00_engine\scripts\character_creator\outfit_f01_correction_20260815_v1\smoke.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\outfit_f01_correction_20260815_v1\chunk_01.json ... chunk_04.json

F01 修复输出根:
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260815_f01_fix_v1

累计网页 run:
D:\UE\Lance_Work\00_engine\visualization_portal\runs\2026-08-15-outfit-compatibility-gate-progress-v1\run.json
```

首个长批次完成 39/153 后，CC 私有内存由约 11 GiB 增至约 30.49 GiB。用户离线重启后，首个恢复分块完成 15/15、失败 0、Undo 0，内存约由 3.53 GiB 增至 16.29 GiB。原 v1 曾累计到 81/153，但人工网页检查发现 Cheer Leader `default` 缺裤：`Pants 02` 先成功加载，随后 `Shirt 01` 将其从 inventory 删除，而旧门禁只检查“本次存在变化”，因此产生机器假阳性。反序和选择重置探针排除了选中状态问题；三组作者同编号搭配均可共存。当前规则拆为 `matched_01/02/03`，v2 总量为 159 例；正式修复 9/9、45/45 图、必选件驱逐 0，修复完成时累计 87/159、29/53 个完整 Look、435 图。旧 `default` 三例由门户和恢复计划明确忽略。

随后 `r7/chunk_01` 完成 Jiving、Kilt、Lederhosen、Lift & Haul、Lincoln 五个 Look：15/15 案例、75/75 图、必选件驱逐 0、选择重置失败 0、Undo 0。累计状态为 102/159、34/53 个完整 Look、510 图。同一进程此前已跑 Cheer 修复，分片后期显存余量最低约 0.23 GiB；资源释放探针将其从任务结束后的约 0.69 GiB 恢复到 1.77 GiB，Private 从约 23.52 GiB 降到 22.29 GiB，但仍低于 2 GiB 显存软边界。后续禁止运行完整 159 例单作业，也不允许逐例重启；默认每个提交作业 1–2 个完整 Look / 3–6 例，单 CC 进程通常 6–12 例。每个完整 Look 后联合检查资源：Private 24/30 GiB 仅作为软/硬参考，同时要求可用物理内存不低于 8 GiB、commit 低于 75%/85%，显存余量以 2048/1024 MiB 为软/硬边界。命中软边界时先执行资源释放探针；只有全部资源恢复到软边界以上才继续，否则由用户决定是否离线重启。Agent 不得自行重启 CC。

用户随后复审从固定套装迁移出的 family：Cheer Leader 保持三个匹配组，其余 family 批准维持现有自由搭配。新 CC 进程执行 `r8/chunk_01-02`，完成 Mercenery、Mesh it Up、Oahu、Owen 四个 Look：12/12 案例、60/60 图、必选件驱逐 0、Undo 0。累计状态更新为 114/159、38/53 个完整 Look、570 图。12 例边界时 CC Private 13.54 GiB、可用物理内存约 12.0 GiB、commit 63.4%、显存余量约 5.59 GiB；随后在建议进程边界收口。剩余 45 例、15 个 Look 已生成 8 个 `r9` 小分片。

在同一进程执行一次资源释放探针后，Private 降至 12.28 GiB、显存余量回升到约 6.5 GiB，随后安全完成 `r9/chunk_01` 的 Pop Style 与 Pyjamas：6/6 案例、30/30 图、21 次资产应用、必选件驱逐 0、Undo 0。进程累计 18 个正式案例后，清理前 commit 达到 72.5%、显存余量约 2.8 GiB，因此停止继续提交并再次清除当前临时角色。该检查点累计为 120/159、40/53 个完整 Look、600 图；剩余 39 例、13 个 Look 曾生成 7 个 `r10` 小分片。

用户观察到系统内存释放后，`r10/chunk_01` 以一个 6 例小作业继续：Rugged & Trendy 在 M01/M04/M05 上 3/3 通过并生成 15/15 图；redsoul 三例都在 `SHSV_S02MA_gloves.ccGloves` 返回状态码 1，且 Undo 0，因此是资产装配失败而非弹窗阻塞。诊断发现 gate 生成器把所有资产按通用槽位重新排序，使 `locked_bundle` 从用户确认的 `suit → boots → gloves → harness → pockets → hood` 变成 `suit → gloves → pockets → hood → harness → boots`。生成器现仅对 `slot_groups` 排序，`locked_bundle.required_assets` 保留权威顺序；新增回归测试已通过。累计门户只吸收 Rugged & Trendy，更新为 123/159、41/53 个完整 Look、615 图。`r11` 恢复计划包含 36 例、12 个单 Look 分片，第一片只复测 redsoul。作业后清理将 Private 从约 20.23 降至 18.99 GiB、显存余量从约 0.75 提升至约 1.85 GiB，但 commit/显存仍未同时恢复到软边界，因此不得在当前进程继续提交。

用户离线重启后进一步探针排除了资产损坏、选择状态、Undo、加载顺序、`LoadObject` 和组件重存储：原 `.ccGloves` 在所有公开加载形式下均返回状态码 1，而字节完全相同的 `.ccCloth` 别名与控制资产共同通过 2/2、阻塞弹窗 0。生产别名及注册表位于 `00_engine/assets/character_creator/outfit_compatibility_aliases`；门禁生成器新增策略、来源/别名大小与 SHA-256 校验，并拒绝任何未登记 `.ccGloves`。`r12/chunk_01` 的 Redsoul 随后正式通过 3/3、15/15 图；同一进程继续完成 Streetscape、Streetstyle、Summer、Underbelly、Vacation 共 15/15、75/75 图。该历史检查点的累计门户为 141/159、47/53 个完整 Look、705 图，且五个新增总览均完成视觉抽查。18 个正式案例后空闲显存一度降至 914 MiB；释放探针只恢复到 2021 MiB，仍低于 2048 MiB 软边界，因此当时停在完整 Look 边界并生成 `r14` 的 6 个单 Look 恢复分片。

2026-08-16 的最终恢复执行完成 `r14/chunk_01..06`：White Tie、Workout、Wrinkled、1920s full-body、1920s separates 和 Cyberpunk 共 18/18 案例、90/90 图、必选件驱逐 0、阻塞弹窗 0。期间在完整 Look 边界执行资源释放探针，并在用户明确接受一次轻微软边界偏离后继续，未触及硬边界。最终复核计划 `cc_outfit_compatibility_resume_plan_20260816_v6.json` 合并 28 个检查点，确认 159/159 已完成、0 未完成、53/53 个 Look；累计门户发布 795 图和 53 张总览。最后六张总览已完成机器侧视觉抽查，人物居中、五视图齐全、未见明显缺装；这仍不替代 `VIS-CC-05` 的用户穿模与动作验收。

`cc_resource_release_probe_20260815_v1.json` 会删除当前一次性测试角色、清空 Qt `QPixmapCache` 并执行三轮 Python GC，不关闭 CC。第一次实测 Private `19.63→18.43 GiB`、显存可用 `1.37→2.44 GiB`；Hippasuta 后第二次实测 Private `21.29→19.99 GiB`、显存可用 `0.66→1.80 GiB`。RLPy 的 `RGlobal/RScene` 未暴露 cache/purge/release API，因此该探针只能释放活动场景引用，不能清空随独特服装持续增加的 CC 原生缓存。

累计图像检查发现全部 18 个已跑 `F01_Lean` 的 `right_profile` 固定位置存在离体黑色几何，而 F04/F05 同一区域没有该对象。它与 F01 源项目唯一 `GetAccessories` 对象 `Double Bubble Braids` 一致，不是服装资产本身。执行器已加入 `remove_source_accessories=true`。`female_dress_collection__shirt_with_skirt__F01_Lean` 单例 Smoke 已确认只移除该配饰、保留 3 个 `GetHairs`，新右侧图无离体物且 Undo 为 0；后续新增 F01 也未复现。用户决定保留既有 18 个 F01 图，不执行原拟 `5/5/5/3` 修复分片；修复计划和分片只作为已取消决策留档。旧 `v1/chunk_01` 清单继续保留实际执行时 `remove_source_accessories=false` 的历史语义，未完成案例只允许使用 `r5` 分片。

用户已审查累计 795 图并接受服装-身体和服装层级的静态结果。决定文件为 `cc_outfit_visual_review_20260816_v1.json`，其受审索引冻结为 `reviewed_index_20260816_v1.json`。已知头发与头巾、兜帽、高领或其他头部半包裹布料会相交；该问题不在当前快速贯通阶段擅自修改源资产，也不与服装-身体失败混为一类。后续通过 head-occupancy 分类、hat-safe/compact HairStyleSet、完整头部覆盖时隐藏头皮毛发，以及必要的专用变体处理。它不阻断首轮动作压力门禁，但阻断最终生产批准。

### 7.5 E：静态与动作门禁

每个 Look 至少检查：

- 正面、侧面、背面、近景接缝；
- T/A Pose、自然站立、举臂、交叉臂、深屈肘、跨步、坐姿或深屈髋；
- 腋下、肩、肘、腰、胯、膝、踝、鞋底和多层边界；
- 身体隐藏后是否缺肉，取消隐藏后是否穿透；
- 外套+上衣、裙/裤+上衣、袜/裤+鞋的层级压力；
- 动作回到中性后无残留变形。

结果只能是 `passed/rejected/conditional`，`conditional` 必须登记禁止动作或必需 hide mask。

### 7.6 F：十体型扩展

当前瘦/胖/矮门禁是廉价压力筛选，不替代最终十体型扩展。只有机器与人工静态通过的 Look 才进入动作压力测试，再扩展到全部十个 BodyFit。每个体型保存独立网格/项目和 `BodyFit × Look` 兼容记录；不能因为 CC 自动 conform 成功就自动继承通过状态。

### 7.7 G：CC→UE 与运行时

UE 中每个 Look 是一组独立 Skeletal Mesh Component 或等效模块，统一使用对应 BodyFit Skeleton 和 Leader Pose。`SetOutfitLook` 只接受兼容登记中的完整 Look ID；大件可独立切换，但不得让 Shirts/Coats 等槽位任意随机叠加。

## 8. 几何与材质计数规则

- 同一网格的十种颜色计为 `1 geometry + 10 material variants`，不计为十套服装。
- 轮廓、拓扑、层级或覆盖范围变化才建立新 geometry identity。
- 两个名称相同的 `.ccCloth` 不视为相同；需要来源哈希/清单和 CC 场景核对。
- 同一资产在男女目录重复时先归入一个 source family；只有实际适配结果不同才产生两条 compatibility record。
- 服装数量以已批准 Look 和有效 material variant 分别统计，不用源文件总数代替生产多样性。

## 9. 停止条件

- ZIP 损坏、密码未知或内部路径不可追溯；
- 加载服装触发未知弹窗或覆盖身份/BodyFit；
- Look 在平均体型已经有不可接受穿模；
- 层级只能靠不可复现的手工 Sculpt 修补；
- 十体型 conform 改变身份、身体比例或 Skeleton；
- 只看到正面静态图，没有动作压力证据；
- UE 资产无法回溯到 `BodyFit × Look × source package`。

## 10. 当前未完成

- `cc_outfit_motion_stress_gate_20260816_v3` 的 53 个同性重体型案例已机器完成并发布动作审查入口；每例包含静态参考、Walk 五帧和 Full Body Calibration 五帧；v3 复用冻结静态装配顺序、允许替换和最终 inventory 签名；
- 正式结果为 53/53 Look、583/583 图、机器失败 0、inventory 匹配 53/53；`cc_outfit_motion_stress_execution_state_20260816_v1.json` 状态为 `complete_user_spot_check_accepted`，无续跑分片。门户 `2026-08-16-outfit-motion-stress-gate-v1` 为 `approved`；
- 用户抽查动作压力结果并报告未发现问题；决定由 `cc_outfit_motion_visual_review_20260817_v1.json` 固化。没有记录抽查数量，因此不建立虚假的逐 Look `passed` 清单；诊断动作不得登记为生产动画池；
- 为头发与头巾、兜帽、高领建立 head-occupancy 与 HairStyleSet 兼容规则；在规则落地前该问题保持 `deferred_known_issue`；
- `both` 帽子、眼镜及其余配件的分类、迁移和兼容规则；
- 13 个已登记家族专用配饰的动作验证；
- 批准组件的 CC5 Custom 转换、保存/重载和真实 Look ID；
- 十体型兼容矩阵、Body hide mask 和导出网格；
- UE `SetOutfitLook`、材质变体和运行时验证。

当前状态与执行顺序分别见 [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) 和 [`ROADMAP.md`](../planning/ROADMAP.md)。
