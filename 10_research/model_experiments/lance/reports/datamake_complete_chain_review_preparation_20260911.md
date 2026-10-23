# 混合训练后的完整编辑链推理准备

后续已执行：[step600完整推理结果](./datamake_mixed_step600_inference_20260911.md)。原预览页面已填入28段输出；以下准备态描述保留为执行前记录。

2026-09-11，按用户要求准备新的完整链展示。状态：CPU 输入、回填语义及页面结构验证通过，真值预览已生成；尚未运行这套 GPU 推理，没有新模型结果或视觉质量结论。实现与输出所有者为 [training_integration.md](../training_integration.md)。

## 展示和样例

每条链占一个卡片，上半部分为「真值回填」，下半部分为「自回填」，两部分有分隔线。每部分仅两行：推理结果、真值视频。两行以相同列宽依次展示 Source、Prompt、R1、Prompt、R2……；真值行不重复长指令。窄屏横向滚动，不把每轮拆成独立行。可同时从头播放或暂停该部分两行视频；这是播放控制，不是不同帧率视频的逐帧同步器。

固定清单：[datamake_mixed_complete_chain_review_20260911.json](../configs/datamake_mixed_complete_chain_review_20260911.json)。

| 完整链 | 轮数 | 编辑顺序 |
| --- | --- | --- |
| `c_575347cc8db313eb` | 3 | 身份 → 动作 → 机位 |
| `c_3071d965660823b5` | 4 | 动作 → 机位 → 服装 → 身份 |
| `c_e98974f1c66a9300` | 5 | 动作 → 服装 → 身份 → 机位 → 服装 |

从当前混合索引的 UE validation 链最大前缀选择，不截短长链充当短链。按 seed20260911，在减少样例间端点重用后优先覆盖不同编辑轴。已遍历现有推理目录中的84份JSON，排除以前展示的 `c_7669cabae1467386`、`c_c6282282709e3a10`，并核实新 chain_id 不在当前训练分片中。三条新链共15个不同真值端点；这不意味着端点视频在训练中从未出现，原数据按链划分且允许端点复用。CoinVE只有单轮 source/target，不拼接成虚构多轮真值链。

UE部分两种回填方式共生成24段视频：真值回填12个独立前缀会话，各生成最后一轮；自回填3个完整会话，共生成12轮。前者每次使用完整GT历史，当前目标GT只写在评估映射中，不进入推理会话；后者只提供初始source和所有用户指令，所有历史输出由现有引擎生成并追加。

## 实现与运行

- [prepare_datamake_chain_review.py](../scripts/prepare_datamake_chain_review.py)：CPU选链，冻结原始parquet、媒体、历史展示证据哈希和采样参数；输入媒体只引用。
- [run_datamake_lora_visual_sanity.py](../scripts/run_datamake_lora_visual_sanity.py)：新增可选`--suite`和`--dry-run`。继续使用现有`MultiTurnChatEngine`、官方采样路径和PEFT推理加载器。修正旧入口只接受合成Dataset键的问题，现在可识别混合Dataset，并验证训练YAML哈希。省略suite仍为历史六视频套件。
- [build_datamake_chain_review.py](../scripts/build_datamake_chain_review.py)：验证轮次/prompt/GT/回填映射完整一致，输出四行链网页及全帧媒体检查；准备页显式标记尚未推理，生成位置使用占位，不拿GT充当推理结果。
- [test_datamake_chain_review.py](../tests/test_datamake_chain_review.py)：回填隔离、完整链选择、输出缺失/映射错误、四行布局和混合预处理检查。

新suite明确固定30 diffusion steps、CFG1、shift3.5、global seed42、noise seed42、KV cache。空间变换与帧采样从所选checkpoint的训练YAML读取；UE原视频仍采样为57帧。旧runner未显式设置noise seed，其配置类默认值是2025；历史报告笼统写“noise seed42”不能代替实际运行manifest，本次显式绑定为42。

后续在独立的已分配GPU上运行，`LANCE_CHECKPOINT`设为届时仍存在的完整checkpoint绝对路径，`LANCE_EVAL_RUN`使用新的输出目录：

```bash
LANCE_PYTHON=/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python
LANCE_ROOT=/scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance

"$LANCE_PYTHON" "$LANCE_ROOT/scripts/run_datamake_lora_visual_sanity.py" \
  --checkpoint "${LANCE_CHECKPOINT:?请设置完整checkpoint目录}" \
  --suite "$LANCE_ROOT/configs/datamake_mixed_complete_chain_review_20260911.json" \
  --output-dir "${LANCE_EVAL_RUN:?请设置新的推理输出目录}"

"$LANCE_PYTHON" "$LANCE_ROOT/scripts/build_datamake_chain_review.py" \
  --run-dir "$LANCE_EVAL_RUN"
```

runner启动时把adapter权重、LoRA配置和训练合同校验后固定到本次Run的`inference_adapter/`，避免训练keep4轮换删除原checkpoint后无法追溯。它不复制optimizer，也不是可恢复训练的checkpoint。正式推理仍执行加载后逐tensor核对。

输出继续归属`outputs/multiturn_chat/`研究验证范围。网页默认以符号链接引用原始GT媒体，不复制视频。需要复制到本地离线浏览时，对该Run重建网页并加`--copy-media`，只物化本页引用的GT；随后复制完整Run即可。现有准备页：[index.html](../outputs/multiturn_chat/mixed_complete_chain_preview_20260911/index.html)。其`manifest.json`和`media_audit.json`均标记`prepared`，不含生成结果。

## 检查证据与边界

- 新增6项CPU单测、原有10项推理与review单测全部通过。
- 文档技能要求的核心回归132项通过（documentation22、dataset30、unreal80）；目录清单重建及完整文档审计通过，114份文档/683条本地链接，各子系统和交叉检查均无错误或警告。
- 用混合训练完整step350 checkpoint执行`--suite ... --dry-run`通过：15会话、24预期生成视频；不创建推理Run、不加载模型。
- 准备页引用的15段GT全部全帧解码通过。HTML结构测试覆盖两部分各两行、生成占位、prompt转义、缺失结果拒绝、符号链接及便携复制。
- 实际准备页检查为12行（3个case各4行）、15个媒体符号链接，每段GT均成功解码150帧；页面JavaScript通过`node --check`，`git diff --check`通过。
- 当前环境没有浏览器/Playwright，未做浏览器截图或真人播放验收。新suite的GPU生成、长链显存和实际编辑质量仍待推理阶段检查。
- 对正在运行的混合训练合同复核，22份生产实现文件哈希未变。本次没有修改训练配置、提交GPU作业或调用训练停止/恢复操作。

同日训练状态核对：用户提交的132170已开始正式八卡训练，启动验证`passed-d8c49fc822cb2b96c77044b45c5190b286c2d9a411b09da4925bb2497e6fe13b.json`确认连续/恢复一致；本次准备期间日志推进至393步。此前文档的“八卡Gate待执行/未提交”属于启动前历史。本次准备不关闭L06/L08质量验收，WF-90已发布状态不变。


## 追加真实单轮样例（2026-09-11）

用户确认原有链式排布后，要求追加真实数据集的单轮例子，仍不执行推理。已在同一清单、同一预览页下方增加独立「真实数据 · CoinVE 单轮编辑」区域。原三条UE链及采样参数保持不变；每个真实例子只展示一次，明确区分Source、我们的模型输出占位、真值Target。完整复合指令仍是一轮，不拆成多轮或重复两种回填。

| 样例 | 编辑内容摘要 |
| --- | --- |
| `coinve-085619` | 去除眼镜、将城市背景换成公园 |
| `coinve-192680` | 蓝碗改红色、木台面换白色大理石 |
| `coinve-186523` | 蛋糕改乐高风格、托盘换深色石板 |
| `coinve-006415` | 添加领带、更换饮料杯、草地湖景换雪山 |

选自当前混合数据的195条CoinVE validation配对，按已有seed在编辑类型组合内固定选择，已核实未出现在训练分片或此前推理展示中。现在清单包含19个会话、28段预期生成视频（UE24＋CoinVE4）；模型输出仍全部为空。

新增[datamake_coinve_review_media.py](../scripts/datamake_coinve_review_media.py)复用训练的`crop_frame_indices()`：读取原始浮点FPS，对source/target使用冻结清单的共同绝对起点和5秒窗口，得到61帧。网页只编码8段小尺寸H.264采样预览，保存原视频哈希、FPS、实际帧号和窗口记录；不复制完整原始视频。预览代理只供观看，模型直接读取原始source的采样帧，避免将有损预览再送入模型。

独立runner以case范围的`paired_input()`覆盖原始视频解码，继续使用训练VAE/ViT空间变换。只有source允许进入这次单轮推理，target仅供页面对照；ViT末帧复制为62帧。退出或异常时恢复原解码方法，训练代码不变。

`prepare_datamake_chain_review.py --extend-suite SUITE`保留UE样例并追加真实样例。页面更新使用原命令加`--refresh-preview`，仅允许更新`prepared`页面，不覆盖生成结果。现有推理和生成后构建页面的命令不变，自动包含新增单轮输出。

追加验证：9项链/真实样例CPU单测通过。实际对`coinve-085619`用训练Dataset与新推理解码分别处理，VAE `[3,61,352,624]`、ViT `[3,62,336,588]`张量逐元素完全一致。未进行GPU生成；真实source/target本身的内容时序噪声仍遵守此前用户暂缓筛查的决定。

页面追加后检查通过：4张真实样例卡片、4个模型输出占位、8段61帧采样预览，整页共23个媒体引用均可完整解码。原10项推理/review回归通过，本轮相关单测合计19项；实际checkpoint入口dry-run确认19会话/28输出。生产训练22份源码哈希保持一致，JavaScript语法、diff检查、目录重建和114文档/683链接审计通过。原核心132项回归本会话已通过，本轮未重复运行无关核心测试。
