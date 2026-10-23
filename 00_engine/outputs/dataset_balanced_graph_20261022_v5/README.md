# 本轮编辑链候选

先读 [结果报告](REPORT.md)。本目录只有配置和编辑链，没有生成视频。

- 主候选：[candidate_c_seed1](candidate_c_seed1/)，训练4670节点/12000链，测试768节点/2400链。
- `candidate_c_seed2`、`candidate_c_seed3` 是同图的其他采样种子，用于稳定性检查，**不要与主候选合并为额外训练数据**。
- 每个候选的 `train/`、`test/` 均包含 `nodes.json`（完整配置）、`edges.json`（合法有向边）、`sessions.jsonl`（每行一个多轮交互）、`metrics.json`（构造/采样参数与统计）。
- 每个候选的 `audit.json` 是对保存文件的独立复核，`source_position` 是交互历史中的位置，分叉必须按它选择源视频。
- [GOAL.md](GOAL.md)、[RULES.json](RULES.json) 保存用户批准的目标与规则；[CURRENT_CANDIDATE.json](CURRENT_CANDIDATE.json) 是主候选指针。
- [comparison.json](comparison.json)、[sampling_stability.json](sampling_stability.json) 分别保存v4 rotated对照与三个采样种子的结果。
- [INPUTS_AND_METHODS.json](INPUTS_AND_METHODS.json)、[DELIVERY_MANIFEST.json](DELIVERY_MANIFEST.json) 保存输入/代码版本和交付文件哈希，`code_snapshot/` 是取证副本。
- `candidate_a*`、`candidate_b_seed*` 是方法迭代证据；`candidate_b/` 是最终采样使用的固定图，不是最终链清单。

当前为待用户审查采用的离线候选，未冻结渲染计划、未进行视觉验收，不代表模型性能已验证。测试集无需全属性值覆盖，具体范围和初始镜头分布的局限见报告。
