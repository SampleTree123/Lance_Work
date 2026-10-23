# Dataset 确定性生成工具

本目录保存配置源、节点/边/链、Prompt、Render Jobs 和审查包的确定性生成器。完整语义和执行顺序见 [Dataset 技术索引](../../../20_planning/data_design/character_creator/full_process/technical/dataset/README.md)。

## 主要阶段

1. `build_first_batch_graph_source_v1.py`：从已验收 Registry 生成冻结图源。
2. `build_first_batch_config_graph_v1.py`：生成并验证 assets、domains、nodes、atomic edges、chains 和 render jobs。
3. `build_first_batch_prompt_layer_v1.py`：在不修改图的前提下生成模型文本层。
4. `build_first_batch_chain_review_v1.py`：生成可读代表链与视觉 Smoke 候选。
5. `build_first_batch_delivery_v1.py`：在发布层把 accepted Node Media 映射为顺序编号，并生成完整 `chains.json` 与带 `chain_index=1..N` 的训练简化版 `chains_simple.json`。
6. `verify_first_batch_delivery_v1.py`：只依赖交付目录，独立复核顺序编号、视频哈希/媒体规格、完整/简化 Chain 文本和全部媒体引用。

准确参数、Schema、输出和当前限制见：

- [CONFIG_GRAPH_AND_CHAINS.md](../../../20_planning/data_design/character_creator/full_process/technical/dataset/CONFIG_GRAPH_AND_CHAINS.md)
- [PROMPT_LAYER.md](../../../20_planning/data_design/character_creator/full_process/technical/dataset/PROMPT_LAYER.md)
- [DATASET_PACKAGE.md](../../../20_planning/data_design/character_creator/full_process/technical/rendering_release/DATASET_PACKAGE.md)

## 规则

- 工具只冻结逻辑引用，不拥有 CC/UE 二进制资产。
- `chains.jsonl.instructions` 是内部审计字段，不是模型 Prompt 权威。
- 渲染层始终保留哈希 `node_id`；只有交付层通过 Manifest 映射为 `videos/1.mp4...`。
- 输出版本不可原地覆盖；输入 Registry 或 Schema 变化必须生成新版本并重新 Gate。
- 当前批次数量、兼容域和冻结值由 Batch Status 与图源 JSON 维护，不在本页复制。

完整脚本生命周期和 owner 由 `../SCRIPT_CATALOG.json` 提供。
