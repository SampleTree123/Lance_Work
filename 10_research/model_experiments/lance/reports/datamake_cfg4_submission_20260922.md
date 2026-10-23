# GT1650 CFG 四卡推理任务（2026-09-22）

状态更新（2026-10-11核对）：作业145517已于2026-09-23 03:11:51完成，COMPLETED/0:0，五组共140视频、95个conversation，rank清单和媒体审计齐全。[结果页面](../outputs/multiturn_chat/mixed_cfg_gt1650_job145517/index.html)；[当前进度与质量边界](datamake_progress_20261011.md)。用户观察text CFG编辑更明显、ViT CFG更偏保持源视频，尚未完成逐例最终排名。运行完成不等于已证明所有CFG分支与独立参考实现数值等价。

入口：`jobs/datamake_cfg4_gt1650.sbatch`；实现：`scripts/run_datamake_cfg4.py`、`scripts/build_datamake_cfg4_review.py`。Technical owner：`../training_integration.md`。

复用20260911混合validation套件：3/4/5轮合成链，各含GT历史和自回填模式，加4个真实单轮复合指令。五组(text,vit)：(1,1)、(3,1)、(5,1)、(1,3)、(1,5)，总计140视频。单节点4H200、4独立进程，不进行DDP同步，不拆开自回填链。输出位于`outputs/multiturn_chat/mixed_cfg_gt1650_job<jobid>/`，完成后生成index.html和media_audit.json。

GT1650推理快照已复制到共享scratch的`outputs/optimization_diagnostics/cfg_gt1650_shared_snapshot`，无optimizer，不是可续训checkpoint。推理不依赖跨节点/tmp。

KV-cache视觉CFG修正：条件分支任一scale>1即可激活；修复提前引用text ids/grid；无文本无ViT分支保留源VAE，RoPE grid与条件筛选同步；MoT上下文局部索引使用当前slice起点。无cache视觉CFG旧接口不支持此实验，明确报错。后续GPU生成与媒体检查已经完成，语义效果及严格参考数值对照分别记录，不因能运行而自动验收。

提交：从仓库根执行`sbatch 10_research/model_experiments/lance/jobs/datamake_cfg4_gt1650.sbatch`。沿用既有account/partition/qos设置，调度端是否接受需提交时确认。
