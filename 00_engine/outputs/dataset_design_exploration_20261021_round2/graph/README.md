# 第二轮图结构研究入口

先读 [RESEARCH_REPORT.md](RESEARCH_REPORT.md)，机器汇总见 [SUMMARY.json](SUMMARY.json)，各路线状态见 [ROUTE_STATUS.json](ROUTE_STATUS.json)。所有数字均为真实catalog约束的离线拓扑，不是UE媒体或资产全量验收。

稳定候选文件保持不变：

- `motif_a7_f5_n3000_s20261021_train_uq1_ab3_graph.json` / `_sessions.jsonl`
- `motif_a7_f5_n3000_s20261021_test_uq1_ab3_graph.json` / `_sessions.jsonl`

两分区分别2500/500唯一视频state、12k/3k会话；全部根、中间、输出都在预算内，全部被引用。会话的`node_indices`引用同分区graph.nodes；`parent_occurrence_indices_gt`引用会话的时间位置，可回到非最新版本。不要把父指针当成相邻node index。

这对图只是有取舍的局部任务候选：小family限制身份替换范围。追加身份扩展另存为`bridge_p5_*`和`bridge_p10_*`，详情及实际使用覆盖见`bridge_metrics.json`、`bridge_context_analysis.json`，没有覆盖稳定文件。

新采样研究也单独交付：

- `sampling_{train,test}_candidate_pool.jsonl`：共享、去重、strict有效的候选会话池。
- `sampling_<policy>_<split>_1x_indices.json`：从同分区候选池选取的12k或3k行号。
- `sampling_study_metrics.json`：0.5×/1×/2×预算下四策略比较。
- `sampling_study_verification.json`：64642条候选与全部索引配额的定向复算。
- `bridge_verification.json`：四个追加候选、30k会话的定向检查。

索引策略是对同一有限池的比较，不能把不同策略的同一会话计为额外独立样本。`joint_reserved_swap`保留显式交换顺序探针；是否使用任何替代采样或身份扩展仍是研究选择，不自动替换稳定15k。

代码入口是`experiments.py`、`sampling_study.py`、`bridge_families.py`。输入JSON已固定在本目录，实验只用Python标准库。`quality_kernel_round1.py`是本轮私有复制并扩展的内核，不是原生产脚本，不应单独当作生产入口运行。
