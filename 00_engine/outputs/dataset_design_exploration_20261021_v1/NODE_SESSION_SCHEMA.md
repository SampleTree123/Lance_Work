# 节点、编辑边、会话与参考：字段草案

2026-10-21。探索版，不替换历史V1 schema；不是已经接通的正式数据编译器。

## 1. 四种对象分开

**节点**描述完整视频状态，**边**描述从某节点只改一个属性后得到哪个节点，**会话**描述用户按什么时间顺序做编辑和选历史版本，**参考**描述用于说明目标属性的图或视频。

下面是建议字段。运行机器路径只放内部清单，对外发布用可迁移的相对URI。

```json
{
  "node": {
    "node_id": "content_hash_of_resolved_state_and_render_version",
    "split": "train",
    "family_id": "compatible_seed_family",
    "state": {
      "identity_id": "CFD40_AF_001",
      "wardrobe": {
        "family_id": "family",
        "group_id": "group",
        "slots": {"upper": "upper_a", "lower": "lower_a", "shoes": "shoe_a"}
      },
      "hair_id": "hair_a",
      "hair_color_id": "black",
      "expression_id": "none",
      "motion_id": "motion_a",
      "camera_policy_id": "front_full",
      "site_id": "site_a",
      "aspect": "landscape"
    },
    "resolved_render": {
      "asset_snapshot_id": "snapshot",
      "scene_snapshot_id": "saved_map_and_site_snapshot",
      "body_clock_id": "motion_timing_profile",
      "face_clock_id": "face_timing_profile",
      "camera_trajectory_id": "resolved_trajectory",
      "environment_profile_id": "scene_owned_exposure_and_lights",
      "render_profile_id": "resolution_fps_duration_AA_seed_and_versions"
    },
    "media": {"uri": null, "sha256": null, "status": "not_rendered"}
  },
  "edge": {
    "edge_id": "edge_hash",
    "source_node_id": "node_a",
    "target_node_id": "node_b",
    "edit_axis": "wardrobe.upper",
    "old_value": "upper_a",
    "new_value": "upper_b",
    "compatibility_rule_id": "same_group_single_slot_v1",
    "derived_changes": ["cloth_geometry", "cast_shadow", "occlusion"]
  }
}
```

示例中的槽位名和资产ID只是解释字段关系，不可直接提交UE。正式编译使用当前`choice.slot_choices`、共享鞋和可选部件接口，不新建平行装配规则。

语义状态相同但资产或渲染配置版本不同，不能强行复用旧文件。反过来，只有命名／目录不同而实际状态相同，也不应虚增节点数。状态哈希与成片文件哈希都保留，分别解决配置去重和媒体完整性。

## 2. 单属性与派生结果

每条边仅允许一个被用户请求的语义轴变化，不把渲染器派生变化算成第二条编辑：

- 换动作导致衣服运动和身体投影变化。
- 换衣服导致其轮廓、遮挡和阴影变化。
- 换环境允许采用目标场景自己的光照与用户已调曝光。
- 换镜头预设允许同时改变该预设内的景别和运动路径。
- 身份是否包含体型必须先确定；不能数据一部分只换脸，另一部分悄悄连体型一起换。

派生变化应由固定规则算出来，不能在渲染时随意额外采样。隐含换鞋、为适配套装自动清掉头发等独立内容变化，不当作普通换上衣边；可以避开这类搭配，或以后单独定义任务。

“原色”是资产原生颜色，未必是跨发型统一色值。因此保持`hair_color_id=original`换发型时，视觉颜色可能一起变化。建议发型编辑使用明确的黑／金等颜色，使发型形状和颜色更易分离；原色仍可作为主视频外观或颜色边目标，单独记录其资产依赖。此项需小样确认，不应直接宣称原色的跨发型边已经满足视觉单属性。

## 3. 会话存出现位置，不能只存视频列表

```json
{
  "session_id": "structural_session_hash",
  "split": "train",
  "root_node_id": "n0",
  "occurrences": [
    {"occurrence_id": 0, "node_id": "n0"},
    {"occurrence_id": 1, "node_id": "n1"},
    {"occurrence_id": 2, "node_id": "n2"},
    {"occurrence_id": 3, "node_id": "n3"},
    {"occurrence_id": 4, "node_id": "n4"}
  ],
  "turns": [
    {"turn": 1, "source_occurrence": 0, "target_occurrence": 1, "edge_id": "e01"},
    {"turn": 2, "source_occurrence": 1, "target_occurrence": 2, "edge_id": "e12"},
    {"turn": 3, "source_occurrence": 1, "target_occurrence": 3, "edge_id": "e13"},
    {"turn": 4, "source_occurrence": 3, "target_occurrence": 4, "edge_id": "e34"}
  ],
  "structure": {"edit_count": 4, "nonlatest_source_count": 1}
}
```

结构去重键应包括初始节点、每轮父出现位置及原子边／目标节点，**不包括措辞或改写编号**。不同参考输入策略是同一结构的条件变体，另标variant，不能因此增加“不同编辑链”的数目。

上例第3轮分叉后，第4轮继续用最新结果。若第4轮又选第2轮结果，即发生第二次切换历史源，违反当前最多一次规则。

## 4. 公开输入与答案分别保存

```json
{
  "public_turn": {
    "turn": 3,
    "instruction": "回到换好蓝色上衣的那个版本，只把动作改成参考视频中的挥手。",
    "reference_ids": ["ref_motion_wave"],
    "history_available_through_occurrence": 2
  },
  "private_supervision": {
    "source_occurrence": 1,
    "source_node_id": "n1",
    "target_node_id": "n3",
    "changed_axis": "motion",
    "new_value": "wave_asset",
    "incorrect_latest_source_target_would_differ": true
  }
}
```

历史视频在公开输入里仍有稳定的可引用序号；这里隐藏的是“本轮到底选哪一条”的答案字段，不是删去历史身份。当前用户文字、公开参考及过往已经给出的参考正常可见，未来回合参考不提前给出。

允许文字明确说“回到第一轮结果”，也可以说“用还没有染金发的那个版本”。建议两类都留，避免所有分支仅靠固定口令触发。对不明确的“用之前那个”，不要随机贴一个正确源标签；可以补充描述或作为需澄清的独立任务。

若历史出现过两次相同状态，则按显式轮次指代评来源定位，按等价状态评编辑结果，分别报告。主结构实验先不重复状态，减少这种歧义，但不把它永久从任务定义里删掉。

## 5. 参考素材字段

```json
{
  "reference_id": "opaque_reference_id",
  "role": "target_attribute",
  "media_type": "video",
  "edit_axis": "motion",
  "conditioning_strength": "matched_camera_timing_aligned",
  "public_label": "动作视频A",
  "first_visible_turn": 3,
  "carrier_profile_id": "neutral_carrier",
  "view_policy": "source_camera_on_independent_carrier",
  "timing_profile_id": "same_motion_time_mapping",
  "split_policy": "seen_target_value_canonical_reference",
  "ignore_axes": ["identity", "wardrobe", "scene"],
  "media": {"uri": null, "sha256": null},
  "private_provenance": {
    "target_attribute_asset_id": "wave_asset",
    "generated_from_target_video": false
  }
}
```

属性资产ID、载体规则和GT等内部字段供数据检查，不自动拼入模型输入。参考当然要透露目标动作／衣服长什么样，这是其用途；需要避免的是把包含整个人物、服装、场景和动作答案的完整目标视频换个名字当“参考”。

## 6. 少量但关键的离线检查

生成时直接检查以下规则即可，不必扩成繁琐审核流程：

1. 父出现位置已在历史中，且每条会话最多一次非最新源。
2. 目标等于所选源只应用一个编辑后的状态；父子在允许的适配域。
3. 分叉的错误最新源结果与正确结果可区分；优先有分叉后继续编辑。
4. 主视频去重、训练测试隔离、场景／参考的划分政策一致。
5. 目标衣物可编辑且可见；主链不主要靠循环／同一颜色来回变化填数。

结构检查能在渲染前完成；“看上去能否辨认、参考是否足够”留给少量完整样例。图的离线成功不替代媒体可读性，也不需要为此把全部资产重新审查一遍。
