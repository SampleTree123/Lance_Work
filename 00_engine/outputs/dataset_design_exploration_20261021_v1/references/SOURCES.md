# 参考素材设计：原始来源与阅读记录

核查日期：2026-10-21。仅使用论文作者提交的全文、官方会议入口和作者仓库。全文确已打开并读下列任务/数据/评估/限制段；未运行其代码，未下载其训练数据，未复现效果。本文无模型架构建议。8项选择重在直接支持参考素材、动作条件、历史与输入公平性，不是全面相关工作检索。

引用契约：`S1`等是本目录内部证据ID；对外引用使用直接论文链接，不引用搜索摘要。**论文报告**只限其任务和实验；**项目建议**只在REFERENCE_DESIGN中提出；**未验证**表示本机资产/UE管线尚未测。不能将论文能力、作者主张和本项目验收混写。论文标题/版本按实际读到的页面，勿从搜索标题反推版本。

| ID | 一手来源、版本与日期 | 实际阅读位置 | 本目录支持的具体claim | 不能据此推断 |
| --- | --- | --- | --- | --- |
| S1 | [Video-As-Prompt: Unified Semantic Control for Video Generation，arXiv:2510.20888v1，2025-10-23](https://arxiv.org/html/2510.20888v1)；[ICLR 2026官方入口](https://proceedings.iclr.cc/paper_files/paper/2026/hash/ba8d1b46292c5e82cbfb3b3dc3b968af-Abstract-Conference.html)；[作者repo](https://github.com/bytedance/Video-As-Prompt) | §2.2、§3.2、§4.4/图7；repo使用说明 | 视频可承载动作/相机等语义；论文区分不要求像素对应的语义条件与对齐结构条件，报告未见语义示例 | 不证明本项目RGB动作clip有逐帧精确控制；不证明多轮继承或分支；参考视频提示不等同目标视频首帧输入 |
| S2 | [VACE: All-in-One Video Creation and Editing，arXiv:2503.07598v1，2025-03-10](https://arxiv.org/html/2503.07598v1)；[ICCV 2025官方paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Jiang_VACE_All-in-One_Video_Creation_and_Editing_ICCV_2025_paper.pdf)；[官方repo](https://github.com/ali-vilab/VACE) | §3.1–3.2；Appendix C.1 | R2V、V2V、masked V2V及任务组合有明确输入角色；作者承认身份保持和组合输入控制的限制 | 不能说任意reference都能稳定复制指定属性，更不能当现用模型已验证 |
| S3 | [Animate Anyone: Consistent and Controllable Image-to-Video Synthesis for Character Animation，arXiv:2311.17117v1，2023-11-28](https://arxiv.org/html/2311.17117v1) | §1任务定义、§5 Limitations | 人物图与期望姿态序列分工；作者指出单视图下未见部位生成的不适定性和手部难点 | 不保证参考正脸可唯一规定背部；姿态条件结果不能当RGB视频条件结果 |
| S4 | [Improving Diffusion Models for Authentic Virtual Try-on in the Wild（IDM-VTON），arXiv:2403.05139v1，2024-03-08](https://arxiv.org/html/2403.05139v1) | §1、实验中Detailed Caption效果/图7 | 人物图和衣服图的任务分工；细图案保留与详细衣服文字有实验支持 | 不能外推四视角、多个服装slot或多轮视频；不支持换整套衣服算单属性 |
| S5 | [MagicBrush: A Manually Annotated Dataset for Instruction-Guided Image Editing，arXiv:2306.10012v3](https://arxiv.org/html/2306.10012v3)，首投2023-06-16；[作者evaluation代码](https://github.com/OSU-NLP-Group/MagicBrush/blob/main/evaluation/image_eval.py) | §3.1、§4.2–4.3、表2/3 | 数据有多轮图像编辑；作者逐轮回灌评估并观察误差累积；mask提供与否分开评估 | 不能据此说支持历史source指代、视频或弃支；其末轮评估不足以覆盖本项目每轮原子性 |
| S6 | [I²Edit: Towards Multi-turn Interactive Image Editing via Dialogue，arXiv:2303.11108v1，2023-03-20](https://arxiv.org/html/2303.11108v1) | §3.1–3.3，Edit Requirement Tracking | 数据逐轮记录用户属性需求，输入使用从开始到当前的完整对话历史 | arXiv摘要检索可能显示CHATEDIT旧/异名；本记录按实际全文I²Edit标注；不把其原图重编辑方案移植为本任务架构 |
| S7 | [WBench: A Comprehensive Multi-turn Benchmark for Interactive Video World Model Evaluation，arXiv:2605.25874v1，2026-05-25](https://arxiv.org/html/2605.25874v1)；[官方repo](https://github.com/meituan-longcat/WBench) | §1、§3–4、Appendix C.5.3 | 交互视频中分开评估设定遵循、交互遵循与一致性；同一导航任务可提供多种对齐控制表述并分轨比较 | 属世界继续演化，不能冒充同一时间窗口编辑；往返导航一致性不等于视频回退分支正确性 |
| S8 | [MotionCoach: Constructing Multimodal Guidance for Video Professional Motion Editing，arXiv:2610.12963v1，2026-10-09预印本](https://arxiv.org/html/2610.12963v1) | §3.2、§4.3及表3、Appendix A.1 | 动作参考clip需清楚完整，提示应包含技术/时序与保留约束；论文输入消融报告clip+grounded文字互补 | 不证明本项目全轴多轮编辑；其多轮是工具获取指导过程；尚未复现，不能移用论文数值作本数据收益 |

研究迁移只作以下三个假设：模型能够接收约定的RGB图/视频；UE能独立控制参考carrier和目标属性；参考资产有清楚的家族与兼容性登记。这三项在本次研究中均未执行验证。

本次检索未确认与“同一主视频、2–5原子编辑、一次回到历史节点、弃支完整保留、图/视频参考混合、source由模型判断”全部一致的公开基准。该句仅描述本次8项阅读范围，不是文献不存在或新颖性的证明。

未纳入：AnyV2V虽定位并打开摘要/官方repo，但在8项限额内优先完整阅读动作与历史相关来源；搜索中的MTEdit arXiv:2610.23751日期与本次截止日未可靠核准，不作为设计证据；非作者转载、博客与搜索摘要不作为证据。
