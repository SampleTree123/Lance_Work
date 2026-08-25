# 数据集封装与发布

> 文档 ID：`TECH-RELEASE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-90`
> 实现所有权：媒体、Sidecar、GT、文本、QA、哈希与交付 Manifest
> 验证所有权：`VAL-RELEASE-01`
> 输出契约：`OUT-WF90-DATASET-RELEASE`
> 最近核验：2026-08-25

## 1. 交付结构

```text
delivery/<batch_id>/
  manifest/
  graph/
  text/
  media/nodes/<node_id>/
  metadata/
  qa/
  checksums/
```

视频不按链复制；链和 Turn 通过 `node_id`/相对 URI 复用唯一权威媒体。

## 2. 节点 Sidecar

每个节点至少记录：Node 配置与哈希、Look/Action/Expression/Camera/Scene/Render Profile、UE/插件/项目 revision、帧率/帧数/分辨率/时长、视频编码/字节数/SHA-256、渲染 attempt、QA 状态和报告引用。

GT 只来自确定性配置和 UE 实际绑定，不从视频理解模型反推。机器感知结果可作为 QA 辅助，但不能替代配置真值。

## 3. 发布 Gate

- 640/640 节点拥有唯一 accepted 视频、Sidecar 和匹配哈希；
- 图的两个兼容域、8,320 边、4,000 链和五个事实标签仍通过；
- 15,000 Turn 全部解析到 accepted 输入/输出媒体；
- 跨域、悬空、no-op、完整重复链、内部 ID 文本泄漏和哈希冲突均为 0；
- 至少 2% 节点完成分层视觉抽样，覆盖两性、所有动作和四相机；
- Delivery Manifest 和 checksums 可在另一台机器独立验证。

## 4. 发布与不可变性

发布后任何媒体、Prompt、图或 Sidecar 改变都创建新发布版本。旧发布不得原地覆盖。交付包、最终 Manifest、checksums 和发布报告为 `authoritative`；抽样联系表为 `retained_evidence`；编码临时文件为 `disposable`。

## 5. 当前缺口

第一批结构图和 Prompt 已通过，本地代表媒体已验证；正式 640 节点媒体、统一 Sidecar/GT、媒体 Manifest、服务器重试和最终 Delivery 构建尚未完成。因此当前批次状态不能标记为 released。

## 6. 失败与恢复

封装或校验失败时保留当前发布候选及报告，不修改已接受节点媒体。先按 Manifest 定位缺失 URI、哈希冲突、Sidecar/GT 缺口或文本引用错误，再从对应 `WF-70/WF-80` 权威输入重建受影响层。任何媒体、图或文本内容变化都创建新发布版本；仅重新生成 checksums/索引且内容哈希未变时，仍需记录新的打包 attempt。
