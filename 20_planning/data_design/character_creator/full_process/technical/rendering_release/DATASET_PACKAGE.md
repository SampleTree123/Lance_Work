# 数据集封装与发布

> 文档 ID：`TECH-RELEASE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-90`
> 实现所有权：媒体、Sidecar、GT、文本、QA、哈希与交付 Manifest
> 验证所有权：`VAL-RELEASE-01`
> 输出契约：`OUT-WF90-DATASET-RELEASE`
> 最近核验：2026-08-31

## 1. 交付结构

```text
delivery/<batch_id>/<release_id>/dataset_v1/
  videos/
    1.mp4
    2.mp4
    ...
  chains.json
  chains_simple.json
  manifest.json
```

渲染层仍使用 `media/nodes/<node_id>/video.mp4`；只有交付层把本次发布涉及的唯一节点按 `node_id` 字典序映射为从 1 开始的数字文件名。视频不按链复制，多条链通过数字路径复用同一文件；`manifest.json` 保存数字路径、内部 `node_id`、配置和媒体哈希的完整映射。长期决定见 [ADR-0017](../../project_management/decisions/ADR-0017-SEQUENTIAL-DELIVERY-VIDEO-NAMES.md)。

## 2. `chains.json`

每条记录保存 Chain 策略、语义事实、按位置排列的视频序列和完整 Turn。每个 Turn 至少包含：

- `video_in`、双语 `prompt`、双语 `standalone_prompt`、`video_out`；
- Chain/Turn/Edge/Node 内部 ID 和唯一变化轴；
- 身份编辑的可见人物描述 Grounding；
- 原子性、语言完整性和内部 ID 文本泄漏检查结果。

`chains.jsonl.instructions` 只是图构建时的技术占位文本，不能进入交付包。封装器必须从正式 `dialogs.jsonl`/`turns.jsonl` 合并模型文本。

### 2.1 `chains_simple.json`

训练简化版与完整链一一对应，按完整 `chains.json` 的确定性顺序增加 `chain_index: 1..4000`，同时保留 Hash `chain_id` 用于追溯。每条记录只包含：

- `chain_index`、`chain_id`、`turns`；
- 每轮 `input_video`、双语 `instruction` 和 `output_video`。

数组顺序表示编辑轮次，不重复保存 `round`。验证器必须证明每条简化链都能从同位置完整链无损投影得到，不允许两份文本独立演化。

## 3. `manifest.json`

Manifest 至少记录：Dataset/Batch/Package Scope、输入图与 Prompt 哈希、Render Run、编号规则、视频编号到 Node 的映射、Node 配置与哈希、Look/Render Profile、媒体规格/SHA-256、源 Sidecar 哈希、完整/简化链哈希、链/Turn 数量和全部封装检查。

GT 只来自确定性配置和 UE 实际绑定，不从视频理解模型反推。机器感知结果可作为 QA 辅助，但不能替代配置真值。

## 4. 生成命令

完整发布默认读取全部 4,000 条链；只有图/Prompt 哈希对齐、15,000 个 Turn 有效且所有 640 个唯一节点均有 accepted 媒体时才会成功：

```bash
python 00_engine/scripts/dataset/build_first_batch_delivery_v1.py \
  --graph-dir 00_engine/outputs/first_batch_dataset/graph_20260824_v1 \
  --prompt-dir 00_engine/outputs/first_batch_dataset/graph_20260824_v1/text_first_batch_20260824_v2 \
  --render-run-root 00_engine/outputs/unreal_render/<full_run_id> \
  --output-dir 00_engine/outputs/delivery/<release_id>/dataset_v1 \
  --dataset-id dataset_v1 \
  --package-scope full_first_batch
```

`--chain-id` 可重复传入，只用于构建明确标为 `sample` 的局部审查包。`--materialization-mode hardlink` 在同一文件系统复用视频字节，失败时回退复制；交付到另一存储时使用 `copy`。即使全量封装成功，脚本也只写为 `package_candidate_pending_release_qa`；只有 `VAL-RELEASE-01` 可以把版本晋升为正式发布。

另一台机器只取得 `dataset_v1` 后，使用不依赖图、Prompt 源或 Render Run Root 的验证器：

```bash
python 00_engine/scripts/dataset/verify_first_batch_delivery_v1.py \
  --dataset-root /path/to/dataset_v1 \
  --output-report /path/to/evidence/package_verification.json \
  --ffprobe-bin /path/to/ffprobe \
  --workers 8
```

报告必须写在不可变交付目录之外。验证器重算 `chains.json`、`chains_simple.json` 和全部视频 SHA-256，逐个探测编码、分辨率、帧率、帧数与时长，并检查 4,000 条链、15,000 个 Turn、双语文本、原子标志、前后视频连续性、简化链编号/投影、视频编号解析及内部 ID 文本泄漏。

## 5. 发布 Gate

- 640/640 节点拥有唯一 accepted 视频、Sidecar 和匹配哈希；
- 图的两个兼容域、8,320 边、4,000 链和五个事实标签仍通过；
- 15,000 Turn 全部解析到 accepted 输入/输出媒体；
- 跨域、悬空、no-op、完整重复链、内部 ID 文本泄漏和哈希冲突均为 0；
- 至少 2% 节点完成分层视觉抽样，覆盖两性、所有动作和四相机；
- Delivery Manifest 和 checksums 可在另一台机器独立验证；
- 视频名从 `1.mp4` 连续编号且无缺口，Manifest 映射与 `chains.json` 引用一致；
- `chains_simple.json` 的 `chain_index` 从 1 连续到 4,000，且每条记录与完整链逐轮一致；
- 15,000 个 Turn 使用正式 Prompt 层，不得使用图中的内部 ID 占位指令。

## 6. 发布与不可变性

发布后任何媒体、Prompt、图或 Sidecar 改变都创建新发布版本。旧发布不得原地覆盖。交付包、最终 Manifest、checksums 和发布报告为 `authoritative`；抽样联系表为 `retained_evidence`；编码临时文件为 `disposable`。

## 7. 当前能力与缺口

`build_first_batch_delivery_v1.py` 已从 `first_batch_server_production_20260829_v004` 构建新版 `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/`：640 个顺序编号视频、4,000 条完整链、4,000 条简化链和 15,000 个双语 Turn。`chains_simple.json` 的 `chain_index` 连续为 1..4000。Manifest 的媒体记录、Sidecar accepted 状态、GT 图、Prompt 图、双语文本、路径解析、完整/简化链一致性、编号连续性与源哈希检查全部通过；640 个视频与上一候选及 Run Root 字节相同。

本机发布 QA 又对 13 个视频执行 2.03125% 分层视觉抽样，覆盖两性、10 个动作和四相机；帧 0/75/149 的联系表未发现 T-pose、黑帧、白块、错误构图或首帧姿态跳变。用户已于 2026-08-30 确认三张联系表没有问题。新版候选的视频有序哈希列表与该签字候选完全相同，因此视觉结论可继承；新版报告位于 `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/release_evidence/release_qa/release_qa_report_candidate_20260830_v002.json`。

`verify_first_batch_delivery_v1.py` 先在生产服务器对新版候选执行 package-only 全量验证。2026-08-30 清理原始 Run Root、旧 Delivery、staging 与缓存后，又从当前候选重新读取并验证 640 个视频、4,000 条完整链、4,000 条简化链和 15,000 个 Turn，全部通过；报告为 `release_evidence/release_qa/package_verification_post_cleanup_20260830.json`。这证明交付包不再依赖源视频硬链接或 Render Run Root。

2026-08-31，独立节点 `JDS9B74/job118880/testqueue` 使用 ffprobe 8.0.1 和同一验证器完成候选态全包验证，报告 `package_verification_independent_jds9b74_20260831.json` 的 SHA-256 为 `b268012a005cd4c42c33f28a906de782d67cce12de8364e7aa5769d8fe74d4e1`。随后只把 Manifest 的 `status` 晋升为 `released`，并再次完成全包复验；发布态报告 `package_verification_released_independent_jds9b74_20260831.json` 的 SHA-256 为 `8fb9328f262329d555dcf35be8e97795c9e8dee497a1091cd91ddb5019595a73`。前后 `chains.json`、`chains_simple.json` 和有序视频哈希表分别保持 `f28b0872...0c2d`、`afd07d31...ec2d`、`68bec5d6...f51e` 不变。发布决定见 `release_decision_20260831.json`。

正式 `chains.json` 还与工作区根目录的用户样例逐层比对：样例中的 Chain、`video_sequence` 和 Turn 字段全部保留；正式版只新增顶层 `dataset_id` 和身份 Turn 的 `grounding`，并按 ADR-0017 把哈希视频名替换为 Manifest 可追溯的 `videos/1.mp4...640.mp4`。因此正式格式是用户样例的兼容超集。

早期封装样例、未版本化 `delivery/dataset_v1` 和原始 `first_batch_server_production_20260829_v004` 已按用户批准的 2026-08-30 清理决定删除。最终运行的输入锁、profile、结果、媒体 Manifest、控制器 checkpoint、QA 报告和用户抽检图已迁入当前候选根的 `release_evidence/`；替代映射见 `project_management/history/reports/FIRST_BATCH_STORAGE_CLEANUP_20260830.json`。

第一批结构图、Prompt、正式 640 节点媒体、完整 Delivery、本机 QA、用户视觉签字、清理后自包含验证和独立节点发布复验均已完成。Manifest 状态为 `released`，`VAL-RELEASE-01/GATE-90` 已关闭；下游可以据此冻结 Lance 训练 split 与正式配置，但不得原地改动发布包。

## 8. 失败与恢复

封装或校验失败时保留当前发布候选及报告，不修改已接受节点媒体。先按 Manifest 定位缺失 URI、哈希冲突、Sidecar/GT 缺口或文本引用错误，再从对应 `WF-70/WF-80` 权威输入重建受影响层。任何媒体、图或文本内容变化都创建新发布版本；仅重新生成 checksums/索引且内容哈希未变时，仍需记录新的打包 attempt。
