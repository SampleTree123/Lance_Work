# Lance 上游更新与公开 LoRA 实现核查

> 后续状态：本报告记录迁移前的上游调查。同日已完成[源码迁移](datamake_source_migration_20261022.md)，当前本地官方基线为4baeee0；下面的9717d91指调查时的旧目录。

核查日期：2026-10-22，Asia/Singapore。Technical owner：[训练接入](../training_integration.md)。范围：GitHub/Hugging Face公开接口、网页搜索、候选项目文档和源码；未升级环境、拉取覆盖工作树、安装第三方项目、下载新权重或执行GPU实验。

## 1. 官方上游比当前本地基线多一个提交

本地 `lance/` 的origin为 `https://github.com/bytedance/Lance.git`，HEAD为 `9717d9160ed16fedfdad5ce39ccbc6c9d69695e0`，2026-06-17发布fine-tuning代码。HEAD只说明基线，工作树含本地patch，不能称为未经修改的官方运行环境。

GitHub公开API本日返回main为 `4baeee086648996f6ab12e673cbe461b0b149997`，提交时间2026-07-14，标题 `feat: fix security warnings (#46)`。compare接口确认相对本地基线ahead_by=1、behind_by=0。当前只列main分支，没有tag/release。仓库updated_at为10月并不等于10月有模型代码提交，应以commit记录为准。[官方提交](https://github.com/bytedance/Lance/commit/4baeee086648996f6ab12e673cbe461b0b149997)、[比较差异](https://github.com/bytedance/Lance/compare/9717d9160ed16fedfdad5ce39ccbc6c9d69695e0...4baeee086648996f6ab12e673cbe461b0b149997)。

八个变更文件为README中英版、历史changelog、Gradio helpers/settings、caption_rewrite.py、inference_lance.py、lance_gradio.py。内容主要是提示词改写服务改用环境变量、Gradio浏览器可见文件目录及默认监听等；inference_lance.py仅修改改写服务的配置提示。没有修改train/、modeling/、data/训练核心，没有新增LoRA、模型结构或参考媒体能力。

Hugging Face官方模型仓库本日API返回revision `7395315758865e6f56ab87ad06a88c7ac172f056`，lastModified为2026-05-28T06:25:28Z；本次未发现更晚的官方权重仓库更新。本轮没有逐字节比较本地大权重，因此不将此结果说成本地权重哈希已核验。[官方模型仓库](https://huggingface.co/bytedance-research/Lance)。

## 2. 官方训练有SFT，但没有找到LoRA接入

核对当前main的训练指南、unified_train.py、train_utils.py、generation/understand启动脚本和仓库树：

- 官方提供理解、生成、混合任务三种SFT入口，使用FSDP与组件冻结开关。
- 训练主干及脚本中未发现PEFT/LoRA注入、rank/alpha配置和adapter保存加载闭环；仓库树也没有LoRA/PEFT专用文件。不能把“发布fine-tuning代码”理解为“官方发布LoRA训练器”。
- [Issue #9](https://github.com/bytedance/Lance/issues/9)询问量化和加速LoRA，作者2026-05-21回复当时暂无相关计划，欢迎社区贡献。这是历史答复，当前实现结论另由本次源码检查支持。
- [PR #43](https://github.com/bytedance/Lance/pull/43)和[PR #44](https://github.com/bytedance/Lance/pull/44)本日仍未合并，主题为低RAM/多GPU推理加载和低显存T2I relay，不是LoRA训练。

官方入口：[训练指南](https://github.com/bytedance/Lance/blob/4baeee086648996f6ab12e673cbe461b0b149997/train.md)。我们当前DataMake PEFT/DDP与分支LoRA仍属于本地适配，本轮未找到官方替代入口。

## 3. 第三方实现分类

| 项目 | 可核实范围 | 与本任务关系 |
| --- | --- | --- |
| [vLLM-Omni Lance recipe](https://github.com/vllm-project/vllm-omni/blob/main/recipes/ByteDance/Lance.md) | 图像/视频理解、生成和编辑的推理/服务接入 | 可作为后续推理性能研究对象；不是训练框架，不代表其实现与官方在所有任务逐数值一致 |
| [benjiyaya/ComfyUI-Lance](https://github.com/benjiyaya/ComfyUI-Lance) | ComfyUI推理节点及相关加载选项 | 便于交互测试，未核实到Lance LoRA训练入口 |
| [Reza2kn/lance-quant](https://github.com/Reza2kn/lance-quant) | AWQ INT4/NVFP4量化工具与推理集成 | 量化不等于LoRA训练；本轮未运行或验收其质量/速度 |
| [X-GenGroup/Flow-Factory](https://github.com/X-GenGroup/Flow-Factory) | 官方支持表与models目录有BAGEL、Wan等 | 当前没有Lance适配；此前借鉴BAGEL实现不等于能够直接训练Lance |
| [Jayce-Ping/Lance 多轮分支](https://github.com/Jayce-Ping/Lance/tree/feat/multiturn-multimodal-chat) | 相对其main一个inference-only提交，新增multiturn模块和入口 | 多轮推理参考，不是新LoRA训练版本；与本地已有多轮接入要分别核对来源，不能据仓库名推断独立新能力 |
| [liaoyiqiao/Lance profiler分支](https://github.com/liaoyiqiao/Lance/tree/feat/arena-profile-v1-oc11) | 相对main十个提交，arena评分/训练剖析与marker协议 | 训练性能记录方向，不是LoRA接入；未运行其代码 |

额外排除：[GRNEdit](https://github.com/Foxerity/GRNEdit)确实有Stage-LoRA，但Lance仅出现在它的比较表中，并非Lance的LoRA实现。搜索中的LanceDB存储格式、X-LANCE语音项目、同名2023论文也不属于当前模型。

## 4. 检索覆盖与不确定性

使用 `bytedance/Lance LoRA`、`Lance_3B_Video lora`、`Lance PEFT`、`Lance finetune` 等网络与GitHub仓库搜索；读取官方PR、Issue9和公开fork列表。本日fork接口返回96条（仓库统计字段与列表可能短暂不一致，不把动态fork数量当作结论）。针对具有额外推送迹象的liaoyiqiao、laj52、Jayce-Ping、johbau、byhwhite五个fork核对默认分支、分支列表和目录；对相关feature分支进一步查看compare。

没有逐个审查所有fork的所有分支或私有仓库，也没有全网完备索引。准确结论是：**本次公开检索未找到可以核实为Lance专用、具有训练入口的现成LoRA版本**，不是证明不存在。README提到LoRA、目录含其他模型adapter或讨论希望训练LoRA均不足以判定支持。

## 5. 对准备进行的小实验的建议

可先以官方Lance_3B_Video权重、不加载DataMake adapter作为基座基线，不需要等待新版LoRA训练库。若目标是官方能力，应使用独立固定commit的官方代码副本，或明确列出必要输入适配，避免把本地多轮/参考图/CFG改动混称原生官方能力。

第一组先测官方支持的单视频理解、基础编辑；多候选指代、多图/视频混合参考与toolcall属于待验证的输入协议与泛化能力，不能因底层接受交错序列就认定已具备目标任务能力。若比较后端性能，应另列vLLM-Omni组，固定权重、精度、帧数、尺寸、CFG、seed与去噪步数；不以第三方README的显存或速度承诺替代本地测试。

本轮只完成核查与记录，没有创建新实验、启动训练/推理或迁移当前工作树。
