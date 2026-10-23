# 第二轮原始证据：哪些结论改变了方案

核查日期2026-10-21。只采作者论文、作者页/官方repo；未运行外部模型、未下载权重。主报告中的本地数值来自真实graph/session的离线投影，不来自这些论文。以下不提出模型架构建议，也不据此宣称新颖性。

| 来源 | 读到的原始位置与日期范围 | 本任务采用的证据 | 明确不能外推 |
| --- | --- | --- | --- |
| [Kiwi-Edit: Versatile Video Editing via Instruction and Reference Guidance](https://arxiv.org/html/2603.02175v1)，arXiv:2603.02175v1，2026-03-02；[官方repo](https://github.com/showlab/Kiwi-Edit) | 全文§3.1–3.3、官方数据格式 | RefVIE从现有视频对构造参考四元组；背景参考来自目标首帧去前景；基准区分subject/background参考 | 不是分支多轮基准；不证明同视角plate不会产生捷径；未复现其得分 |
| [RCEdit-500K: Reference Completion for Image-Conditioned Image Editing，低清全文](https://carpedkm.github.io/RCEdit-500K/RCEdit_paper_lowres.pdf)；[作者页](https://carpedkm.github.io/RCEdit-500K/) | 作者页标ECCV2026；首投日期未核验。全文§3.1–3.2、§4.4、附录B.1/B.2 | 按类型从现有text-edit对补参考；对style/alter用不同内容承载属性；弱指令提高对视觉条件的依赖；明确检查near-duplicate以防复制目标 | 论文主动排除单参考不适合的motion类别；不是视频动作或历史引用已解决的证据；不将图像收益量移用于本项目 |
| [ImgEdit: A Unified Image Editing Dataset and Benchmark](https://arxiv.org/html/2505.20275v1)，arXiv:2505.20275v1，2025-05-26 | 全文§3.1 Multi-Turn、§4.1 Multi-Turn Suite、相关附录 | 已有内容记忆、内容理解、版本回退的任务定义；“undo/从原图继续”不是新的交互概念 | 不等于保留弃支reference并按轴选择性复制的视频任务；其少量多轮基准不能替代本数据验证 |
| [Edit-R2: Context-Aware Reinforcement Learning for Multi-Turn Image Editing](https://arxiv.org/html/2606.05950v1)，2026-06-04 | 全文§3，附录E.1–E.3 | MICE-Bench把跨轮指代和早期约束当单独能力；非平凡约束避免任务被天然对象属性满足 | 本项目不采用其训练/架构；不能把显式版本号选择写成隐含意图理解；图像对象池不能直接证明视频可见性 |
| [Reenact Anything: Semantic Video Motion Transfer Using Motion-Textual Inversion](https://studios.disneyresearch.com/2025/07/16/reenact-anything-semantic-video-motion-transfer-using-motion-textual-inversion/)；[作者arXiv摘要](https://arxiv.org/abs/2408.00458) | 原摘要2024-08-01，作者SIGGRAPH2025页面2025-07-16；已读作者摘要/页面，全文PDF因工具体积上限未完整读，不冒称全文阅读 | 语义动作迁移不要求reference与目标空间对齐，可作为canonical示范的任务先例 | 不证明逐帧时序控制或源视频多轮原子编辑；不把论文的目标图动画化当成我们的源视频动作替换 |
| [Multi-turn Consistent Image Editing](https://arxiv.org/html/2505.04320v1)，2025-05-07；[ICCV2025官方入口](https://openaccess.thecvf.com/content/ICCV2025/html/Zhou_Multi-turn_Consistent_Image_Editing_ICCV_2025_paper.html) | 已读§4动机、§6.2–6.3评估 | 连续图像编辑的误差累积与单轮编辑质量不同，支持分开报告逐轮退化 | 没有视频reference分支协议；不从其实现反推本项目数据schema |

RCEdit和Kiwi-Edit的共同启发是“已有优质编辑对→补齐reference”可独立于“先建reference库→采样编辑”成立。两者都要求来源与输入角色可追踪；对本项目尚需对照验证，并不意味着允许把近乎完整GT当通用示例而不说明。

已核验但未作为主结论：OrionEdit作者页/官方repo确有多reference与source角色区分；其全文CVF入口工具返回403，故不引用不可见的具体实验。CompBench全文已读任务与逐轮背景保持段，但其大部分内容不是本轮reference历史预算的直接证据，未用来堆相关工作。

不采第三方Kiwi-Edit商业站、聚合leaderboard或博客结论。RefVIE-Bench的一手出处已锁定为ShowLab官方论文和仓库。未把发布日期未核准的MTEdit/ACEdit新检索项纳入本轮证据。
