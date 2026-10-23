# DataMake Lance 实验与后续探索登记（2026-09-04）

> 状态：`active`；第一部分保留历史受控消融，第二部分登记后续探索。2026-10-11 的现存run状态由[进度快照](datamake_progress_20261011.md)维护，不以旧Stage5/Stage6记录推断当前运行态。  
> 最近更新：2026-10-11  
> 完整 rollout 参照：`../configs/datamake_dialogue_online_rollout_lora_r64_v2.json`（历史文件已于2026-09-11清理）  
> 快速历史候选：[`../configs/datamake_dialogue_one_step_x0_lora_r64_v3.json`](../configs/datamake_dialogue_one_step_x0_lora_r64_v3.json)  
> 目的：把当前可归因消融和中长期训练方向放在同一权威入口；记录方向不等于代码已实现、训练已授权或质量已通过。文件名为兼容已有链接继续保留。

## 第一部分：受控消融（执行状态逐项登记）

### 1.1 Stage4/5历史来源与基座消融的共同控制项

本节只约束Stage4/5消融；新Stage6采用§1.6的Stage2配方，不能混用。除被测变量外，实验固定同一 3,600/200/200 chain split、同一 prompt、seed 集、VAE 480 / ViT 448、LoRA r64/alpha64/dropout0、condition dropout0、`LR=1e-4`、目标视频等权 loss、无区域加权、4 GPU 与相同目标 optimizer-step 预算。最终 evaluation 统一30-step；训练历史依所属实验固定，当前基座 A/B 均用 v3 单步 `pred_x0`，不能暗中改回30-step rollout。先比较 optimization 健康度与真正自回灌的 held-out 固定链；训练 MSE 不能单独决定胜负。

建议共同记录：每轮指令完成度、身份/服装/动作/相机保持、跨轮漂移、失败率、人工成对偏好、逐轮自动相似度、总 MSE/分轮 MSE、梯度范数、step time、rollout time 与峰值显存。

### 1.2 核心消融

| ID | 优先级 | 只改变的变量 | A | B | 主要回答 | 状态 |
|---|---|---|---|---|---|---|
| `ABL-LORA-BASE-01` | P0 | LoRA 挂接基座 | 官方 Lance 预训练权重 + fresh LoRA | 第二阶段 `0003669` 全参权重 + fresh LoRA | 已学会的 DataMake 编辑能力是否有利于当前快速历史训练 | A/B均停止，恢复点800/350；B最后完成393但只保存到350，未做匹配步数视觉比较，见 [运行报告](./datamake_stage2base_lora_preparation_20260905.md) |
| `ABL-LORA-UND-01` | P0 | 理解侧LoRA是否训练 | S6-1：理解+生成adapter | S6-2：仅生成adapter | 在Stage2 GT前缀配方下，理解适配的作用 | 800续跑已提交，同条件各六个视觉输出和媒体检查完成；质量待用户验收，见§1.6 |
| `ABL-ROLLOUT-CFG-01` | P0 | 训练期 rollout CFG | 每条链固定 `1.0` | 每条链从 `{1,2,4}` 确定性采一个值并整链保持 | 是否需要覆盖不同条件强度下的历史分布；CFG 只改变 rollout 历史，不改变原生 flow loss 定义 | queued |
| `ABL-HISTORY-01` | P0 | 历史来源 | rendered GT teacher-forced | 当前模型在线 full rollout，ViT 与最新 VAE source 全替换 | 检验 online history 是否改善真正多轮自回灌；由于 generated parent 与 rendered target 不共轨，收益不能只解释为 exposure-gap 修复 | queued，先实现 online 臂 |
| `ABL-HISTORY-02` | P1 | rollout 替换范围 | online full rollout | 只替换更早 ViT 历史，最新 ViT/VAE source 保持 GT parent | 区分“历史语义噪声”与“生成 source 和 GT target 不同轨迹”两类影响 | queued |
| `ABL-HISTORY-FAST-01` | P0 | 模型历史构造 | 30-step online full rollout | 从同一次训练 forward 计算 `pred_x0=z_t-t*pred_velocity`，detach/VAE decode 后回灌 | 快速 noisy-GT proxy 能否在约一半训练时间内保留或改善标准 30-step held-out 多轮质量 | B 工程 Gate passed；官方基座 Job `123628` 已停止、恢复点800；step400 视觉一般，后续质量待评估 |

Stage 4 首个实现选择 `ABL-LORA-BASE-01/A`、`ABL-ROLLOUT-CFG-01/A` 与 `ABL-HISTORY-01/B`：官方基座、固定 CFG1、online full rollout。由于 30-step 历史成为主要训练瓶颈，Stage 5 保持其他变量不变，转而优先验证 `ABL-HISTORY-FAST-01/B`；其正式 Job `122959` 已启动并通过首个 step50 checkpoint Gate。Teacher-forced 仍按用户决定稍后实现；它是解释模型历史收益的必要对照，但不是当前 Stage 5 工程 Gate 的前置。

### 1.3 次级消融

| ID | 优先级 | 候选值 | 触发条件 | 状态 |
|---|---|---|---|---|
| `ABL-LORA-RANK-01` | P2 | r32 / r64 / r128，alpha 与 rank 同值 | r64 已稳定但容量或过拟合迹象不明确 | queued |
| `ABL-LORA-SCOPE-01` | P2 | 仅 252 个 generation experts / experts + 4 generation I/O | 需要确认 I/O adapter 的边际收益 | queued |
| `ABL-ACCUM-01` | P2 | accumulation 1 / 2 | 实测显存或吞吐表明累计 2 有明显代价 | queued |
| `ABL-TEXT-DROPOUT-01` | P2 | text dropout 0 / 0.1 | 条件齐全训练已能生成，但 CFG 泛化或指令鲁棒性不足 | queued |
| `ABL-REGION-01` | P3 | 无区域权重 / 基于 rendered parent-target 的可靠 mask | 仅 teacher-forced 或能取得对齐 parent 时 | blocked for online-full |
| `ABL-ROLLOUT-STEPS-01` | P3 | 15 / 30 | 30-step 在线生成成本成为主要瓶颈，且 15-step 历史质量可接受 | queued |

### 1.4 Stage4/5历史来源与基座消融的归因规则

1. 每个比较只改变表中变量；初始化、数据顺序、训练预算和评测链必须记录到各自 Run Manifest。
2. 固定 CFG 与 mixed CFG 对照中，一条链的所有轮次使用同一 CFG，避免链内分布不断跳变。
3. teacher-forced 与 online 的每个 target 都保持相同 rendered GT；不得同时开启 R5 过采样或区域损失。
4. `ABL-LORA-BASE-01/B` 的“从第二阶段开始”指以 `outputs/model_bases/datamake_dialogue_stage2_step3669/model.safetensors` 作为冻结基座并挂接 fresh LoRA，不加载官方基座上的 adapter。该 base-only artifact 不含旧 optimizer，不用于恢复第二阶段全参训练。
5. online-full 的 generated direct source 与 GT target 不一定是精确原子父子；在没有可靠 mask 前，`ABL-REGION-01` 不得用于该臂。
6. 中间 checkpoint 可用于早停判断，但最终比较必须使用同一 completed step 或明确按相同 target-video exposure 对齐。
7. `pred_x0` 臂复用 rendered GT 加噪得到的 `z_t`，不得称为完整 model rollout；最终质量比较必须让两个训练臂都执行相同 30-step held-out 自回灌推理。

每次启动消融前应复制冻结 profile、赋予独立 W&B Run ID，并把本表的对应状态改为 `running`；只有 held-out 输出和 Run Manifest 完整后才能改为 `completed`。

### 1.5 当前基座对照的冻结决定（2026-09-05）

用户确认在不改变 A 的情况下准备 B，由用户手动提交。B 保持同一 chain 顺序、single-forward `pred_x0`、生成侧 r64 LoRA、accumulation2、1800-step horizon、warmup20/cosine和checkpoint50/keep4；只替换基座与 Run 身份。B 从自己的 step0 开始，不继承 A adapter 或任何旧 optimizer。先看 B step50～100，再按相同 step400/900 比较；必须同时对照未加新 adapter 的 Stage 2 起点。不得因 B 高于 A 就忽略 B 相对起点是否退化，也不把两个基座不同的既往训练成本当成等预算比较。准确提交/恢复命令由 [训练接入 §6.10](../training_integration.md#610-stage-2-基座对照的手动启动与续跑) 拥有。

### 1.6 Stage6：Stage2配方的理解侧LoRA对照（2026-09-07）

用户要求以Stage2为基础使用LoRA，并只对比理解参数冻结；后续明确统一覆盖累计步数、学习率、训练预算与共同基座。两份[配置及实现边界](./datamake_stage6_stage2_lora_preparation_20260907.md)将实验命名为S6-1/S6-2，避免与旧基座A/B混淆。

共同项：GT历史的dialogue前缀、Stage2 R5×3、区域加权、LR3e-4→3e-5、warmup101/cosine、3000 optimizer steps、4卡每卡micro batch1/accumulation8/effective batch32、r64/alpha64/dropout0、condition dropout0、无EMA、Stage2数据顺序与预处理；checkpoint100/keep4/final-save（restart1从头训练；2026-09-08用户更新保留数），使用adapter-only与完整恢复状态。两组均冻结基座、ViT/VAE、embedding/lm_head，均不截断理解激活；唯一语义差异是理解侧adapter可训练性。

共同基座已确认为官方Lance预训练权重，双方fresh LoRA/optimizer；不从Stage2或旧adapter续跑。3000更新共96,000次目标样本暴露，约6.54次R5×3有效训练集遍历；不再沿用最初单epoch预算。按Stage2的microbatch区域加权loss平均累计8次，不额外改变损失定义。生成adapter初始化和后续噪声RNG应保持对齐；最终需按相同步数/样本暴露、同一30-step推理比较，并保留未加adapter的共同起点。

本条运行时和非零adapter四卡恢复Gate已通过；两臂均有800完整checkpoint，用户已提交800续训，保持原3000预算和同一restart1身份。此次[同条件800步视觉检查](./datamake_stage6_step800_visual_sanity_20260909.md)比较同一步数、相同官方基座与输入配方，不能用训练MSE或少量样例接受泛化质量。实际运行状态由[恢复记录](./datamake_stage6_checkpoint_rescue_20260907.md)维护；手动SAVE_AND_STOP GPU退出仍未执行。

## 第二部分：下一探索方向

下表按2026-10-11用户决定更新：先实现可选单张ViT参考图，再根据效果讨论分支编辑。参考图代码与工程验证已完成，其余方向仍仅记录设计；工程通过不等于正式训练已授权或学习后质量通过。

| ID | 优先级 | 方向 | 主要问题 | 当前建议 | 状态 |
|---|---|---|---|---|---|
| `EXP-REFIMG-01` | P0 | 当前轮可选单张参考图片 | 文本不易精确表达外观，同时保留无图编辑 | ViT-only已实现，[实现与验证](datamake_optional_reference_image_20261011.md)；VAE候选暂缓 | engineering_passed_quality_pending |
| `EXP-BRANCH-01` | P1 | 从任意历史节点继续编辑 | 用户可能引用第二轮、若干轮前或具有某种属性的历史视频，而不是最新视频 | 外部 parent resolver 先确定节点；选中父节点是唯一 VAE direct source | design_recorded |
| `EXP-HISTORY-VAE-01` | P2 | 压缩历史 VAE memory | 历史 ViT 可能丢失服装、脸部等低层细节 | 保持一个完整 direct source；旧历史只作压缩/检索 memory | design_recorded |

### 2.1 `EXP-REFIMG-01`：目标参考图片条件

**2026-10-11覆盖决定**：[ADR-0018](../../../../20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0018-OPTIONAL-SINGLE-VIT-REFERENCE.md)接受每轮可选单张ViT图片，明确暂不实现参考VAE、多视角与动作视频。输入合同和当前验证以[新报告](datamake_optional_reference_image_20261011.md)为准，质量归当前计划L11。以下ViT+VAE及三组比较是9月原始候选，不是本次已冻结或待自动执行的任务。

目标是把当前的文本视频编辑扩展为“文本 + 目标外观参考图”的视频编辑。参考图必须在推理时也可取得，例如 UE 服装资产独立渲染图、不同视角的身份照或独立配饰图；不得直接截取与监督目标同构图的真值帧作为仅训练期答案。

建议 packed sequence 的角色关系为：

```text
ancestor/history video -> ViT
selected/latest parent -> ViT + full clean VAE direct source
reference image        -> ViT + optional clean VAE appearance reference
target video           -> noisy VAE target, MSE only here
```

参考图片不得复用 `ref_source` 身份，应新增 `ref_appearance_image`，并可进一步细分 `ref_garment_image`、`ref_identity_image`。ViT 提供对象/身份/类别语义，VAE 提供颜色、纹理、材质和局部外观；参考图本身不计算生成损失。第一组质量比较冻结为：

1. 当前 text-only baseline；
2. text + reference ViT；
3. text + reference ViT + reference VAE。

当前最长五轮 pack 已接近 65,536 token 上限；参考图接入前必须重新审计每轮 token、峰值显存与 step time。若新增 reference adapter 或 role embedding，它们必须显式列入 trainable/checkpoint topology；只复用冻结 ViT/VAE 时，当前 generation LoRA 可作为首个适配候选，但不能预先宣称足以学会细节引用。

### 2.2 `EXP-BRANCH-01`：任意历史父节点与编辑图

线性链需要升级为带显式父节点的编辑图：

```text
v0 -> v1 -> v2 -> v3
       `----> b1 -> b2
```

每个新节点至少记录：

```json
{
  "conversation_id": "conv_001",
  "node_id": "b1",
  "created_order": 5,
  "parent_node_id": "v1",
  "ancestor_node_ids": ["v0", "v1"],
  "available_node_ids": ["v0", "v1", "v2", "v3"],
  "reference_expression": "从人物还穿黄色衣服且没有帽子的时候继续",
  "edit_prompt": "把动作改成坐下",
  "parent_video_path": "v1.mp4",
  "target_video_path": "b1.mp4"
}
```

首选系统结构是两阶段而非让生成模型在多个 VAE 中软选择：

```text
raw user prompt -> external parent resolver -> parent_node_id + normalized edit prompt
selected parent -> sole full VAE direct source -> Lance editor -> new branch node
```

resolver 依次使用显式点击/节点 ID、相对轮次规则、编辑日志与 UE 结构化状态、caption/ViT/VLM 检索；唯一高置信候选可执行，多个近似候选必须询问用户。只有用户显式选择节点才能给出确定性保证，自由自然语言解析必须记录置信度和歧义拒绝率。

数据构建必须从被选父节点的 UE 状态真正派生并重渲染 target，不能只改 prompt 后沿用原线性链目标。同一根图的主链和全部分支必须进入同一 train/validation/test split。resolver 数据单独保存 `history_nodes + raw query + gold_parent_node_id + ambiguity`，并包含相对、绝对、属性、事件、复合表达及 hard negatives。

父节点解析器可以检索所有已创建节点；Lance 编辑器默认只接收被选父节点的祖先路径 ViT、被选父节点 ViT 和唯一完整 VAE。无关 sibling branch 不按全局生成顺序送入编辑器。在线 rollout 需要把单一 `latest_generated_video` 改为按 `node_id` 索引的 generated-node map，并按图的拓扑顺序生成。

### 2.3 `EXP-HISTORY-VAE-01`：压缩历史 VAE memory

所有旧视频同时作为完整 VAE source 会产生状态冲突、复制/平均歧义和 token 爆炸，因此不作为候选。无论采用何种 memory，选中父节点必须继续保持唯一 `direct_source_vae`，其他历史只能使用独立的 `history_vae_memory` 角色。

候选压缩方式按实现复杂度递增：

1. 只为旧历史编码少量关键帧；
2. 只编码当轮发生改变的服装、脸部或配饰区域；
3. 对严格对齐的相邻节点保存 VAE latent 差分；
4. 用 resampler/adapter 把每个历史视频压缩为固定 128～512 个 memory tokens；
5. 根据当前引用只检索一个相关旧节点，而不是总是输入全部历史。

多段 VAE 不得沿时间维拼成一个伪长视频；每个节点必须保留独立 sequence split、node/parent/role 标记和 attention 边界。该方向只有在参考图与分支父节点实验表明 ViT/当前 direct source 确实无法保存所需细节后才进入实现。

### 2.4 图结构下的 ViT 与 latent 排列规则

全局 `created_order` 只用于界面历史、相对时间解析和拓扑调度，不再决定 Lance 输入继承顺序。生成某个分支节点时使用被选父节点的祖先路径：

```text
[root history ViT]
[ancestor history ViT]
[selected parent ViT]
[selected parent full VAE direct source]
[optional current reference image ViT/VAE]
[current edit text]
[target noisy VAE]
```

父节点 resolver 可查看整棵历史图，编辑器不应默认吞入无关支线。短链可以保留完整祖先 ViT；链或分支增长后再检索“根节点 + 最近祖先 + 明确引用节点”，并以 token audit 决定窗口，而不是无界增加 `max_tokens`。

### 2.5 建议推进顺序与共同评估

1. 先完成当前 Stage 5 v3 的标准 30-step held-out 多轮质量评估，形成可比较 baseline。
2. 优先实现 `EXP-REFIMG-01` 的最小数据/pack smoke，再执行 text-only、ViT-only reference、ViT+VAE reference 三臂质量比较。
3. 实现 `EXP-BRANCH-01` 的图 schema、确定性轮次 resolver 和单一父节点 VAE 路由；语义/VLM resolver 在此基础上增加。
4. 最后根据前两项失败模式决定是否实现 `EXP-HISTORY-VAE-01`，避免在没有证据时引入多 VAE 与新 adapter 复杂度。

参考图评估记录衣服/面部细节、姿态/背景泄漏和指令完成度；分支评估将 parent exact-match、候选 recall、歧义拒绝与“给定正确 parent 后”的视频编辑质量分开报告；history memory 评估必须同时报告增量质量、token、峰值显存和 wall time。三个方向可以最终组合，但第一轮实验不得同时改变，以保留归因能力。

2026-09-09用户另行授权[PEFT/DDP 性能优化](./datamake_ddp_peft_optimization_20260909.md)：保留 Stage6 两臂语义，独立后端、Run 与完整状态迁移。实现和 CPU 检查已完成，四卡 Gate 待执行；原任务/恢复合同不改动，质量 Gate 不因此关闭。
