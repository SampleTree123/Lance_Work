# 双画幅离线配置入口

当前推荐入口是`selected_candidate/`；`CURRENT_CANDIDATE.json`记录唯一选择。先读`REPORT.md`了解实际视频数量、镜头分布及未冻结的媒体参数。

- `selected_candidate/train`与`test`：实际画幅节点、同画幅边、原结构链及逐节点`render_requests.json`。
- `selected_assignment`：每条原链对应横/竖屏的固定分配；`SOURCES.json`记录候选来源及条件细化策略。
- `selected_candidate/reference_manifest.json`与`reference_summary.json`：从实际步骤重新生成的参考需求；所有媒体仍未渲染。
- `audit_agent/audit_selected.json`：原链完整保留、画幅与正式合法性、跨集合内容隔离和相机模板引用的独立核验。
- `reference_binding_check.json`：逐步骤核对动作/背景参考是否匹配目标画幅；不代替实际画面检查。
- `partition_agent/`：不同成本与分布的整链分配试验。
- `resample_agent/`：更便宜但重新引入换衣分布偏差的重采样试验；不是默认交付。

正式生产前仍需冻结分辨率、帧率、时长及参考拍摄实施。请求中的production10相机参数只指向已有横竖屏轨迹模板，不代表直接采用其10秒/30fps预设，不是已验证的点位世界轨迹。

`materialize.py`负责原链画幅投影，`assemble_selection.py`固定当前来源并重算参考，`check_references.py`核对引用，`report_selection.py`生成交付报告和文件清单。新实验请另建输出目录，勿覆盖既有候选。
