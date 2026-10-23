# 可选单张参考图：问题回答、实现与验证

日期：2026-10-11。Technical owner：[训练接入](../training_integration.md)。本次实现保留直链编辑，增加每轮可选的一张静态参考图片，第一版只用现有 ViT。没有实现分支编辑、多视角、动作视频参考或参考图 VAE 通路；没有提交正式训练。

## 1. 对三个问题的回答

### 可以同时容纳有参考图和没有参考图吗？

可以，同一个模型、同一个训练入口、同一个 batch 的样本可以混用。没有参考图的轮次继续使用原视频＋文字，例如相机视角变化；有参考图的轮次在原条件旁边增加图片，例如更换衣服。没有图片时不补空白图片、不插参考标记，也不额外消耗随机数。现有无图输入的数值行为作为回归约束保留。

第一版按“每轮最多一张”理解：一条链第一轮可以给服装图，第二轮只用文字调整相机。之后的上下文仍保留第一轮所属的参考图，解释历史编辑的来源；它不会被自动当成第二轮新的参考任务。历史中可以有此前不同轮次各自的一张图，本次当前指令始终最多一张，不支持当前轮同时提供多视角图片。

这需要训练时同时保留无图样本和有图样本；输入接口支持可选，并不自动保证新训练后纯文本能力完全不退化。未来效果验证应包含无图相机编辑回归。

### 第一版用 ViT，不用参考图 VAE，对吗？以后加 VAE 会很难吗？

对。原视频和目标视频原本的 VAE 仍然使用，新增参考图只进入 ViT。模型看到的是：源视频提供需要保留的内容，图片提供指定属性，文字说明从图片中借用什么。图中其他人物、姿态和背景不应自动迁移。

以后增加参考图 VAE 并不意味着要重新训练一个 VAE，也不一定要重写 Transformer。可以复用冻结 VAE 和已有 latent 投影，但需要把它明确标记为“参考条件”，保持 clean timestep、无目标 loss，并处理位置、mask、源/参考选择和 CFG。

工程复杂度会增加，训练资源也通常增加，因为主干要处理更多条件 token；但不能在未测量时承诺增加百分之多少。以448×448方图作示意，当前 ViT 的时间patch为1、空间merge后约256个token；按空间压缩16、latent patch1的 VAE 网格则约784个token。实际尺寸受各自bucket、对齐与单图编码实现影响，这不是新增VAE通路的实测benchmark。主干需要读取两类条件后，attention及激活成本也随之变化。

更难的部分是让模型正确使用这些细节：参考服装图的空间位置通常不对应源视频中的衣服位置，而且参考图可能包含另一张脸和背景。VAE提供更多细节，不保证模型只复制需要的细节，甚至可能加重无关内容迁移。

因此先检查ViT版能否跟随参考图的颜色、款式和轮廓。若这些有效但纹理/徽标总是丢失，再增加细节通路，能更清楚判断收益来自哪里。

### 本次是否坚持只用一张图？

是。每轮字段只能是一个图片路径或null，多图列表会报错。图片用于外观参考；单张图无法唯一指定完整运动，也不能证明未展示的服装背面是什么样。动作视频和多视角不在本次实现范围。

## 2. 实现的输入合同

训练parquet仍是一行一个目标前缀，增加可选列 `reference_images`，与 `prompts` 一一对应：

```json
{
  "sample_id": "example-r2",
  "chain_id": "example",
  "target_round": 2,
  "context_length": 2,
  "prompts": ["Use the shirt in the reference image.", "Move the camera to the left."],
  "video_paths": ["videos/source.mp4", "videos/after_shirt.mp4", "videos/after_camera.mp4"],
  "reference_images": ["references/shirt.png", null]
}
```

这是字段示意，不是完整CoinVE行；混合数据原来的origin、crop、采样身份等字段继续保留。图片路径支持绝对路径，或相对于该Dataset YAML的 `media_root`。缺省该列、整列值null、与prompts等长的全null列表在模型输入上等价。误用推理字段 `reference_image` 会显式拒绝。

推理conversation在每个user turn上使用单数 `reference_image`，它不放入普通content视觉列表：

```json
{
  "turns": [
    {
      "role": "user",
      "action": "edit_video",
      "reference_image": "/absolute/path/shirt.png",
      "content": [
        {"type": "video", "value": "/absolute/path/source.mp4"},
        {"type": "text", "value": "Use the shirt in the reference image; keep the person, motion and background."}
      ]
    },
    {
      "role": "user",
      "action": "edit_video",
      "content": [{"type": "text", "value": "Move the camera to the left."}]
    }
  ]
}
```

后续轮次继续复用原来的历史回填方式。手写JSON建议使用绝对路径；相对推理路径沿用现有运行CWD语义，不会自动相对于conversation文件。构建器 [build_multiturn_conversation.py](../scripts/build_multiturn_conversation.py) 新增可重复的 `--reference-image`，逐轮对应prompt；`-`代表该轮无图。原 `--conversation` 推理入口可继续使用。

示例只说明新字段，不擅自把历史GT配置改成自回填或反过来。当前只开放视频编辑上下文，其他action收到参考图会明确拒绝。

## 3. 模型如何接收图片

共享实现：[data/datamake_reference_image.py](../lance/data/datamake_reference_image.py)。

```text
图片文件 → PIL解码、EXIF方向处理、RGB
        → 现有官方vit_transform
        → 将同一静态帧复制为2帧，满足ViT temporal patch2
        → 一个时间格的ViT token（grid_t=1）
        → 普通文字角色说明＋现有video placeholder
        → Transformer UND条件，与目标GEN token做原有attention
```

复制两帧只是编码器输入形状要求，不是把单图变成有动作的视频。沿用video placeholder是为了复用当前统一video-grid位置游标，避免混用image/video placeholder时两套游标错配。

图片在所属user轮的源视觉条件之后、当前文字之前插入。训练与推理使用完全相同的角色说明，不新增词表，不新增随机且被冻结的embedding。

参考图不参与VAE编码、不成为最近源视频、不改变目标帧数/尺寸、不参与MSE或CE。ViT仍冻结；UND与GEN LoRA仍可通过目标视频loss获得梯度。源视频与目标视频原来的时序裁剪保持，CoinVE共同5秒窗不会误套到图片。

当前参考图与源视频ViT使用同一 `vit_cfg` 条件组，没有独立 `reference_cfg`。训练参考图遵守现有 `vit_cond_dropout_prob`；概率0时不增加随机数调用，概率1时移除图片及其角色标记。当前正式配方的三个条件dropout仍为0，没有擅自改变训练超参数。

## 4. 训练路径与复现合同

当前GT前缀Dataset和在线内存历史处理器都接入了共享图片helper。prefix pred_x0截取前缀时同步截取参考列表；整链v2检查同一链不同前缀的参考列表一致。生成历史仍detach，参考图不会成为生成历史或监督目标。

本次配套配置准备器首先支持GT历史参考训练，未提供整链参考训练的正式新profile；旧Stage4/Stage5 chain-record格式会明确拒绝非空参考图，避免旧结构悄悄丢字段。不要把底层在线处理器支持等同于全部历史启动器均已验收。

新增 [prepare_datamake_reference_training.py](../scripts/prepare_datamake_reference_training.py)：

- `audit`遍历全部parquet行和图片，检查单图schema、路径、可解码性与哈希；默认要求至少一个当前编辑轮实际带参考图。
- `prepare`接收完整新数据绑定，生成隔离的 `profile.json`、`recipe.json` 和 `reference_audit.json`，保持八卡/双分支LoRA/部分检查点/每50步keep4等既有参数。
- 新run/W&B身份必须独立；新profile的 `training_authorized=false`，该工具不提交作业。
- 正常launcher加载新profile时再次检查图片、parquet、YAML及符号链接解析绑定。图片内容或链接目标改变会使合同失效。

准备命令模板（先提供实际数据路径）：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
PYTHON=/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python

"$PYTHON" 10_research/model_experiments/lance/scripts/prepare_datamake_reference_training.py audit \
  --dataset-config /absolute/path/new_train/lance_dataset.yaml \
  --report /absolute/path/new_reference_audit.json

"$PYTHON" 10_research/model_experiments/lance/scripts/prepare_datamake_reference_training.py prepare \
  --base-profile 10_research/model_experiments/lance/configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json \
  --data-binding /absolute/path/new_data_binding.json \
  --run-name datamake_single_reference_vit_gt_v1 \
  --output-dir /absolute/path/new_reference_config
```

`new_data_binding.json`是完整profile的 `data` 对象，包含train/validation/test YAML、split/sampling manifest、各split计数与8个训练shard等绑定。工具重新计算相关文件哈希；它不创建新数据、不复制原视频、不自动为旧样本找参考图。图片内容与编辑目标语义是否匹配不属于这项技术审计。

现有正式混合训练集已全量检查：18276个前缀、7201条链、8个shard，参考图样本为0。所以代码已经接通，不等于手头已有可正式训练的参考图数据；普通模式会拒绝把旧数据包装成参考训练。`--allow-no-reference`只用于诊断。

模型参数形状没有因本功能改变，旧GT1150 adapter已实际用于本次推理检查。但代码哈希和输入合同发生变化，旧checkpoint不能绕过恢复检查被宣称可无损续训；既有run/profile/checkpoint没有被覆盖。

## 5. 独立对抗审查与测试

由独立agent审查主实现及配置，发现并修复：

| 问题 | 修复 |
| --- | --- |
| 图像可能被当成最新源视频 | 独立turn字段，不进入源视频选择集合 |
| 混合image/video RoPE游标错配 | 静态ViT块沿用统一video-grid |
| 图片误走CoinVE视频裁剪 | 共享独立静态图解码 |
| 参考图未遵守视觉dropout | 纳入现有概率，drop时不保留角色标记 |
| 旧chain-record入口静默丢图 | 显式拒绝不支持的参考字段 |
| 训练/推理字段名混用静默忽略 | 两侧对常见误用显式报错 |
| 审计只手动有效 | launcher接入并绑定验证工具代码哈希 |
| 审计字段残缺、symlink改指未失效 | 完整字段约束及读取路径解析绑定 |

新增CPU检查覆盖有/无图混合、多轮定位、无图输入及RNG精确回归、静态图帧复制、坏路径/多图/动画拒绝、CoinVE裁剪隔离、pred_x0截断、真实推理packing、输入修改后的launcher拒绝。参考图专项共31项；当前训练/推理路径相关18个测试模块共101项通过（包含专项，不应相加）。核心文档/数据/引擎回归22＋30＋80＝132项通过。日志保存在[本轮诊断目录](../outputs/optimization_diagnostics/reference_image_20261011/)。

额外的混合pack测试将一条无图和一条有图样本装入同一生产PackedDataset：各自8个MSE token，总计32个VAE token、3个ViT token，并使用生产attention mask函数确认两个sample之间双向不可见。这里替换了视频解码夹具，但packing、索引、角色和mask均使用实际代码。

完整Lance测试集报告执行179项、1 failure和9 errors（其中包含一个类初始化失败，不能简单相减计算通过数）：旧Stage2/online-rollout合同要求的 `config/config_factory.py` 哈希与当前工作树不符，本次未修改该文件，也没有更新旧冻结哈希来掩盖拒绝。失败会影响旧入口的直接复用；不影响上述当前路径专项通过的结论，但不能宣称整个仓库测试全绿。具体失败保留在 `lance_all_unittest.log`。

真实H200推理证据：[gpu_gt1150/evidence.json](../outputs/optimization_diagnostics/reference_image_20261011/gpu_gt1150/evidence.json)。使用GT fresh1150、人工64×64/9帧视频、两种参考色块，每例2个采样步；无图/红图/蓝图/text CFG3/ViT CFG3共5例通过，latent和解码均有限，输出统一9×64×64。固定seed换红蓝图使latent平均绝对差为0.426510，表明图像确实进入预测计算。

真实训练证据：[training_gpu_gt1150/evidence.json](../outputs/optimization_diagnostics/reference_image_20261011/training_gpu_gt1150/evidence.json)。复用正式Mixed Dataset、PackedDataset、VAE与Lance forward，在人工小视频上分别完成无图和有图的loss/backward，再执行一次内存AdamW更新：

| 检查 | 无参考图 | 有参考图 |
| --- | ---: | ---: |
| MSE | 0.068534 | 0.069820 |
| 目标损失token | 48 | 48 |
| VAE token | 96 | 96 |
| ViT token | 20 | 24 |
| 有限LoRA梯度张量 | 1016 | 1016 |
| 非零UND / GEN LoRA B梯度 | 247 / 256 | 247 / 256 |

1411个冻结主模型参数均无梯度，VAE也无梯度；一次更新确实改变LoRA抽检参数，三个冻结参数完整张量哈希不变。峰值显存约19.144GiB。两次forward的计时包含不同的首次编译开销，不用于比较吞吐。没有保存或覆盖模型权重。

忽略目录内的8个修改文件已归档为[0026补丁](../patches/legacy/0026-optional-single-reference-image.patch)，在本功能前的文件快照上通过 `git apply --check`、实际应用及逐文件字节比对：[重放收据](../outputs/optimization_diagnostics/reference_image_20261011/patch_replay.json)。验证范围是本次增量，不宣称所有历史补丁从干净上游重放完成。

项目状态、当前Plan的L11、Technical owner与ADR-0018已同步。Script Catalog及Output Inventory已重建；最终文档审计覆盖115份文档、663条本地链接，各独立子系统和跨层检查均通过，0 errors / 0 warnings：[审计收据](../outputs/optimization_diagnostics/reference_image_20261011/documentation_audit.json)。代码语法、补丁哈希一致性及本轮diff空白检查通过。

这不是服装迁移质量测试：旧adapter未经过参考图专项训练，小尺寸两步结果只证明通路。正式分辨率、多卡训练、完整恢复Gate和新训练后的视觉效果仍需在真实参考数据就绪后验证。

## 6. 下一步

提供真实参考图数据绑定后，先检查少量样例的“图片只描述指定属性”是否合理；再运行正式训练配置下的短测与恢复Gate，最后决定正式训练。评估至少包含：固定视频/文字换参考图、去掉参考图、参考一致性、非目标内容保持，以及纯文字相机编辑回归。分支编辑继续暂缓。
