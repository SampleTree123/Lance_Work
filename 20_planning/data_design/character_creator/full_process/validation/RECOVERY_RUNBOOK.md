# 角色工厂失败恢复 Runbook

> 文档角色：`recovery_runbook`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：失败停止条件、恢复到可重跑状态的步骤
> 上级入口：[`README.md`](./README.md)
> 上游：任一失败的 Workflow、Gate、`VAL-*` 或 `VIS-*`
> 下游：恢复后重新执行受影响阶段的进入 Gate
> 最近核验：2026-08-06

## 1. 通用原则

1. 失败时停止发送新命令，记录 run/job ID、最后成功步骤、弹窗/错误和应用状态。
2. 保留 request、Manifest、result、日志、截图和失败目录；不修改结果 JSON 伪造成功。
3. 不复用半完成场景、相同 job ID 或旧输出目录。
4. 恢复后从受影响阶段开头重跑，并重新通过其所有 Gate。

## REC-BRIDGE-01 Bridge 无响应或长时间 busy

1. 执行 `VAL-BRIDGE-01`，读取 heartbeat、active job、lease、processing 和日志。
2. heartbeat 过期时不重复提交；检查 CC 是否关闭或被弹窗阻塞。
3. CC 可操作时先关闭已识别弹窗，再重做健康检查。
4. 必须重启时先保留证据，由用户离线重启 CC。
5. 新 instance ID 出现且 `VAL-BRIDGE-01` 通过后，以新 job ID 重跑。

## REC-DIALOG-01 Undo 或未知模态弹窗

- 已知 Undo 警告：停止批次，允许精确守卫或人工点击 `OK`；记录 guard 审计。
- `Replace / Material Only`：只按资产登记策略处理；眼球用 Material Only，其他资产按已登记 Replace 策略。
- 未知弹窗：禁止自动点击，保存截图、标题、run ID 和最后动作，等待人工判断。
- 连续 Undo 警告：丢弃当前半完成角色，降低加载速度；必要时由用户重启 CC。

## REC-CC-01 CC 内存、关闭或保存异常

1. private memory 达到 24 GB 时停止长批次。
2. CC 关闭或崩溃后将当前作业记为失败/中断，不推断项目已保存。
3. 保存 Bridge 请求、结果、日志和已生成证据。
4. 用户离线重启后执行 `WF-00`。
5. 使用原 Manifest、新 run/job ID 和新输出目录从 `WF-02` 重跑。

## REC-MANIFEST-01 请求或编译失败

1. 保留原 request 和编译错误。
2. 判断是未知 ID、性别/组合拒绝、schema、路径还是注册表不一致。
3. 修改权威请求或注册表；禁止直接篡改编译后 Manifest。
4. 生成新 Manifest 版本并重新执行 `VAL-MANIFEST-01`。

## REC-XFER-01 导出或 UE 参考导入失败

1. 导出缺失 JSON/纹理时保留失败 Bundle，新建版本重导。
2. UE Skeleton、材质或 Morph 错误时保留完整参考资产和 Output Log，不在原目录覆盖修补。
3. 校正插件、导入选项或 Bundle 后导入新目标版本。
4. 从 `GATE-04` 或 `GATE-05` 完整重验。

## REC-UE-01 UE 崩溃、恢复包或自动化离线

1. 区分 `UE_UI`、`UE_REMOTE` 和 `UE_MCP` 失败通道。
2. UE 重启后只恢复明确属于本轮且未另存的包；不确定时跳过。
3. 打开工程，编译相关 Blueprint，核对脏包和引用。
4. Remote 报项目未发现时检查工程名、Remote Execution 设置和唯一节点；MCP 则检查插件、服务监听并刷新会话。
5. 先运行最小 smoke，再运行完整矩阵；任一通道离线时只能做文件检查，不能声称编辑器验证完成。

## REC-EVIDENCE-01 固定输出目录与证据覆盖风险

当前 v003 hybrid-face 与 Elder wrapper 使用固定目录。重跑前复制整个旧报告目录到带 run ID 的证据归档；若已覆盖且无副本，旧结论只能保留为历史说明，不能伪造旧 run 的哈希。

## 2. 恢复完成条件

恢复完成不是“应用重新打开”，而是：状态已知、无未知弹窗、输入未漂移、新输出路径已建立、相应进入 Gate 重新通过。之后从失败阶段开头继续。
