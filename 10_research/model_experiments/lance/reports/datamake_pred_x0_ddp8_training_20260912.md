# 八卡混合数据 detached pred_x0 历史训练

> 日期：2026-09-12。所有者：[训练接入](../training_integration.md)。用户要求只改变现有八卡训练的历史视频来源，生成历史不参与跨轮反向传播。新实验尚未提交。

## 配方与实现

主配置：[pred_x0 八卡配置](../configs/datamake_coinve_mixed_ddp8_lora64_both_pred_x0_no_region_v1.json)。对照为 [GT 历史八卡配置](../configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json)。加载器逐字段验证：data/model/optimization/lora/freeze/initialization/run数值语义、distributed、checkpoint及DDP性能选项与对照一致；仅history和独立run/W&B/入口元数据不同。

保留官方基座新建LoRA、508模块双分支r64、全基座冻结、batch1×8×累计4/global32、3000步、原LR与warmup、区域loss加权关闭、off10检查点、VAE retain、minimal padding、每50步保存/最近4份。不是从GT实验1150步接着训练。训练/验证/test划分、混合比例、R5×3和prefix消费顺序完全沿用。

对目标第k轮的每条UE prefix：

1. 保留初始v0和全部编辑prompt；从当前模型在线重建v1到v(k−1)。每轮输入该轮GT加噪目标，调用已有Lance训练forward暴露的flow中间值，复用`predict_clean_latent_patches()`计算`pred_x0=z_t−t*v_theta`。
2. 用官方VAE解码器将pred_x0变成CPU FP16 CTHW视频，截断至[-1,1]，通过已有内存视频adapter进入后续ViT历史及最近VAE source。无MP4编解码或原视频复制。
3. 历史生成forward、VAE decode全程`torch.no_grad()`，视频显式detach。目标第k轮仅执行一次正常带梯度forward/backward，loss只监督GT vk。历史生成轮不另算训练loss，不增加target权重。
4. 生成历史使用由rank/prefix微步/轮次确定的独立RNG，退出恢复Python/NumPy/CPU/CUDA RNG。最终目标采用原数据预处理seed；模型噪声流不会被额外历史forward消耗。
5. UE R1与全部CoinVE单轮记录直接走原Dataset和原loss。CoinVE共同5秒窗口不变。

“detach历史”切断的是上一轮生成图。当前轮理解/生成LoRA仍从正常监督损失反传，包括对历史视频的当前轮理解特征；没有额外detach理解分支。

为了保持原来随机prefix顺序，每条prefix都重新生成自己的历史，不改为chain采样、不跨optimizer步缓存旧模型输出。因此需要平均约1.325次额外无梯度历史forward/混合prefix，另有VAE解码与重新编码开销；不宣称免费获得在线历史，也不把GT加噪的一步pred_x0等同于纯噪声30步推理。

## 代码和保存恢复边界

- [新launcher](../scripts/run_datamake_pred_x0_ddp_training.py)：严格比较对照配方，复用原eight-rank启动Gate、run锁和训练启动器。
- `lance/train/datamake_pred_x0_ddp_train.py`：进程内替换数据/历史准备hook，复用原DDP主循环、模型初始化、官方PEFT、监督loss、no_sync、优化器和完整checkpoint-v6。
- `lance/train/datamake_pred_x0_prefix.py`：保留原indexed schedule；worker预读压缩媒体，主进程使用现有内存row adapter打包。生成轮调用裸模型，避免不同rank历史长度引发DDP forward collective错序；最终监督仍通过DDP。
- [0024 patch](../patches/legacy/0024-detached-pred-x0-prefix-ddp.patch)：持久化新增clone文件，原22份对照合同源码未改；新合同另绑定5份使用到的新增/历史代码，共27份。不能混用两个实验的resume状态。
- [CPU回归](../tests/test_datamake_pred_x0_ddp.py)及[双进程测试](../tests/pred_x0_ddp_distributed_check.py)覆盖关键新边界。八卡真实NCCL与完整连续3步/2步保存恢复1步验证由新作业启动Gate执行。

## 验证状态

148项Lance CPU回归通过；双进程CPU/Gloo DDP检查通过：两rank交替R1/R5、累计4，额外历史均无梯度，最终梯度与显式全局参考完全相等。新入口从零dry-run和GT对照从最新1150完整恢复dry-run通过；补丁单独重放与工作源码字节一致，sbatch语法通过。

单H200（allocation133209）四更新/16prefix真实训练与审计通过：13条UE覆盖R1～R5，3条CoinVE单轮。23次历史生成forward全部no_grad，16次当前目标forward/backward带梯度。回填张量均为无grad_fn的CPU FP16；每次最终监督forward前CUDA RNG恢复一致。动态打包的GT目标像素、packed训练时间步、文本及索引与原GT Dataset相等；完整16条sample_id、target曝光、MSE/attention/padding token数及LR/scheduler与原单卡对照逐项一致。

| 更新 | loss | 时间/秒 | 峰值allocated/GiB | 历史生成轮数 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.247856 | 235.49 | 95.13 | 4 |
| 2 | 0.135124 | 193.82 | 118.01 | 7 |
| 3 | 0.098785 | 109.76 | 94.32 | 3 |
| 4 | 0.154174 | 231.94 | 116.87 | 9 |

所有loss/梯度有限，无OOM。非零学习率更新时两侧LoRA均变化，第三/四步分别494个理解、512个生成adapter张量更新；冻结基座始终无梯度，训练前后全部冻结参数内容SHA256相同。最高allocated118.01GiB、reserved120.08GiB。上述时间包含新增no_grad图首次编译、重复打包及审计，单卡实际batch4，不是八卡稳态吞吐测量，也不用于估计epoch时长。在线历史的额外forward/decode/re-encode开销确实存在。

短测采用原主循环的single-gpu-probe/smoke/benchmark-only；只增加审计hook，未保存可供八卡恢复的诊断checkpoint，也没有跑到第50步。checkpoint和八卡NCCL/完整恢复路径复用原实现，真实八rank Gate仍由用户提交的新作业执行。训练结束后仅更新最终profile的验证状态文字，数值配方与短测一致。GPU进程正常退出，显存归零；没有提交正式训练。初始交互终端继承单核绑定，本次短测进程树已限制在既有allocation的14核cpuset内展开，时间也包含该调整与审计开销。

机器证据：[GPU审计](../outputs/optimization_diagnostics/pred_x0_ddp8_single_gpu_20260912/gpu_audit.json)、[与GT对照比较](../outputs/optimization_diagnostics/pred_x0_ddp8_single_gpu_20260912/control_comparison.json)、[Gloo检查](../outputs/optimization_diagnostics/pred_x0_ddp8_single_gpu_20260912/gloo_audit.json)。另外132项核心回归（文档22/数据30/UE脚本80）通过；项目文档独立子系统及跨层审计通过，errors=0、warnings=0。


诊断输出所有权：`outputs/optimization_diagnostics/pred_x0_ddp8_single_gpu_20260912/`，由本报告和训练接入维护；probe/run脚本是本次allocation133209的复现证据，不是正式训练入口，保留日志/trace/检查报告，不自动清理。

## 启动与恢复

从工作区根目录首次提交：

```bash
RESUME_FROM=none DDP_MODE=train sbatch 10_research/model_experiments/lance/jobs/datamake_coinve_mixed_ddp8_lora64_both_pred_x0_no_region_v1.sbatch
```

作业先执行eight-rank连续/恢复Gate，通过后才进入正式训练和独立W&B run `dm-coinve-mix-ddp8-both-predx0-noreg-v1`。作业配置默认validate，必须显式`DDP_MODE=train`。训练输出为`outputs/training_runs/datamake_coinve_mixed_ddp8_lora64_both_pred_x0_no_region_v1/`。本实验之后若达到18小时上限，使用同一命令的`RESUME_FROM=latest`续跑自己的checkpoint；不读取GT对照checkpoint。

原GT对照job132170于2026-09-12 00:52:24达到18小时上限TIMEOUT；日志完成1186步，最近完整保存1150步。原22源码和profile保持不变，1150完整恢复dry-run通过，本次没有取消或重启它。L06/L08仍待真实推理视觉验收，WF90发布包和Stage5 B保留边界不变。
