# 六条实际编辑链示例

这些是本轮真实节点和边，不是虚构案例；尚无视频。V0是初始视频，每轮新增一个历史位置，回访时可指向已经存在的节点。完整配置见同目录REVIEW_EXAMPLES.json。

## train / 多属性直链 / session_000032

- 第1次：使用V0，修改服装：male.mercenery/default → male.summer/default（whole_outfit，单件明细见JSON），得到V1。
- 第2次：使用V1，修改发型：HAIR_HB1_11 → HAIR_HB1_05，得到V2。
- 第3次：使用V2，修改动作：ACT_M06_CHEER_HANDS_STEP_DANCE → MOTION_CAND_001，得到V3。
- 第4次：使用V3，修改发型：HAIR_HB1_05 → HAIR_HB1_11，得到V4。

## train / 使用中间历史版本的分叉 / session_000026

- 第1次：使用V0，修改动作：ACT_F05_TIE_SHOES → ACT_F01_SEXY_DANCE，得到V1。
- 第2次：使用V1，修改镜头：high_full → side_upper，得到V2。
- 第3次：使用V2，修改动作：ACT_F01_SEXY_DANCE → ACT_F05_TIE_SHOES，得到V3。
- 第4次：使用V1，修改镜头：high_full → front_three_quarter_upper，得到V4。

## train / 自然回访示例 / session_000006

- 第1次：使用V0，修改服装：female.jumpsuits_accessories/default → female.jumpsuits_accessories/default（single_piece，单件明细见JSON），得到V1。
- 第2次：使用V0，修改动作：MOTION_CAND_003 → MOTION_CAND_030，得到V2。
- 第3次：使用V2，修改动作：MOTION_CAND_030 → MOTION_CAND_003，得到V3。

## test / 多属性直链 / session_000057

- 第1次：使用V0，修改人物身份：CFD40_LF_004 → CFD40_BF_004，得到V1。
- 第2次：使用V1，修改人物身份：CFD40_BF_004 → CFD40_BF_003，得到V2。
- 第3次：使用V2，修改发色：silver_white → blue，得到V3。
- 第4次：使用V3，修改发型：HAIR_HB2_04 → HAIR_HB2_17，得到V4。

## test / 使用中间历史版本的分叉 / session_000035

- 第1次：使用V0，修改镜头：dolly_out_front → dolly_out_back，得到V1。
- 第2次：使用V1，修改服装：male.casual_01_04/default → male.white_tie/default（whole_outfit，单件明细见JSON），得到V2。
- 第3次：使用V2，修改场景点位：site_7ed6554b09 → site_05dac27bc7，得到V3。
- 第4次：使用V1，修改发型：HAIR_HB1_01 → HAIR_HB3_05，得到V4。

## test / 自然回访示例 / session_000001

- 第1次：使用V0，修改服装：female.elise/default → female.pretty_dresses/skirts（whole_outfit，单件明细见JSON），得到V1。
- 第2次：使用V1，修改服装：female.pretty_dresses/skirts → female.elise/default（whole_outfit，单件明细见JSON），得到V2。
- 第3次：使用V2，修改服装：female.elise/default → female.streetwear_collection/full_body（whole_outfit，单件明细见JSON），得到V3。
