# 本次离线构图目录接口

`normalize_catalog.py` 与 `catalog.json` 读取当前正式目录和用户已保存点位；没有操作 UE、修改源目录或做渲染。导出使用当前双人面板采用的轻量目录读取方法，未重新验证所有大型资产哈希。

实际候选：女 20 人、20 发型、12 来源服装家族/17 合法组；男 20 人、13 发型、25 家族/28 合法组。保留全部合法组和 4 个锁定衣柜，仅排除已退休 Rugged。镜头 21、动作 25、当前主场景用户点位 21；1428 条排除含横竖两方向。`MOTION_CAND_007` 已按正式选择策略移除。

## 机器接口

- `load_catalog()`：读取本轮快照。`sexes[sex]` 下有 `identities/hairs/families/shared_shoes/presets` 列表；顶层有 `actions/cameras/sites/exclusions/hair_colors/aspects`。
- `sample_choice(sex, rng, family_id=None, group_id=None, hair_id=None)`：按 family→group→合法衣物→合法鞋顺序随机，返回正式 choice。
- `validate_choice(sex, choice)`：复用正式合约；返回含 `normalized_choice/canonical_choice/assignments/selected_family_asset_ids/shared_shoe_id/hair_deny` 的 resolution。
- `single_piece_neighbors(sex, choice)`：返回 `[{"choice":choice,"slot":slot}, ...]`。同 family/group，仅一个核心槽变化；鞋、配饰、头发固定；锁定衣柜返回空列表。
- `sample_whole_change(sex, choice, rng, require_upper_change=False)`：返回另一 family 的合法 choice，核心衣物实际资产必须变化；可要求上半衣物变化。
- `wardrobe_key(sex, choice)`：排序后的实际衣物＋鞋 assetID 元组；忽略 family/group/hair 标签。
- `resolved_asset_ids/core_asset_ids/upper_asset_ids(sex, choice)`：返回实际选中资产 ID 列表。上半按 shirts/coats/full_body 判断，未宣称像素可见性。

Choice 的字段为 `family_id/group_id/slot_choices/optional_asset_ids/shared_shoe_id/hair_id`。主状态将 hair 独立存放时，验证前注入 `hair_id`；缺省 None 只是未注入头发，不代表本轮增加无发候选。

同一 hairID 合法出现在男、女两池；保留各自真实 fit。正式合约允许无发与无衣物，但本轮候选没有加入这两类。

## 鞋和锁定衣柜

`group.shoe_rules` 明确原生鞋、共享鞋、赤脚条件；`shared_options` 受“未选原生鞋”条件约束。4 个女装组必须选 9 双共享鞋之一，不能赤脚；13 个女装组允许赤脚或共享鞋。男装 25 组要求原生鞋，共享鞋不可叠加；另 3 组允许在没有原生鞋时选共享鞋或赤脚。实际状态仍以 `validate_choice` 为准。

4 个锁定衣柜是 `female.elise/female.misaki/male.redsoul/male.cyberpunk_locked`。它们的 `lock_presets` 是能直接验证的完整 choice，`lock_required_asset_ids` 保存整套必须资产，没有人为拆出可换槽。女装锁定套装按正式政策允许选共享鞋/赤脚，男装两套固定保留原生鞋。

## 点位与路径

`sites[].id` 是真实 `site_*` ID，`label` 是用户保存名称，`scene_label` 是当前主场景名称，`source` 含原保存文件路径及哈希。只取当前主地图上的用户 `site_*` 点；历史 `primary_*`、试点和已退休地图不纳入候选。人工排除复用 `pair_review_site_intent_v1.saved_intent`，显式空快照有权清空历史排除，不盲目合并。

人物路径来自当前 40 人修订交接；衣物/头发/鞋路径来自现用 formal active pointer，并应用已验收粉色外套修正映射。原 assetID 保留。

验证结果见 `catalog_verification.json`：45 组、704 个组×发型抽样状态、2655 条单件边、704 条跨家族整套边、260 个鞋状态、4 个锁定预设通过；4 个强制鞋组拒绝赤脚。890 个直接可选对象路径都存在于本机。没有穷举衣物笛卡尔积，没有新增视觉验收。
