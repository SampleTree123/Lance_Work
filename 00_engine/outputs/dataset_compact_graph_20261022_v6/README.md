# 第六轮当前入口

先看[中文结果简报](REPORT.md)，机器可读入口为[CURRENT_CANDIDATE.json](CURRENT_CANDIDATE.json)。当前推荐`selected_seed1`：训练3752个节点、12000条链；测试800个节点、2400条链。

- `selected_seed1/train`、`selected_seed1/test`：本轮选定的节点、边和链条；还没有渲染成视频。
- `selected_seed2`、`selected_seed3`：相同图和配置的稳定性复核，不是额外数据，不能与第一组混合。
- `FINAL_SELECTION.json`：训练图N、测试图T及原始采样来源。每组`ASSEMBLY.json`绑定原始文件与副本。
- `RULES.json`：当前规则和实际实现；保留历史理想边际分布的说明不等于承诺全联合空间均匀。
- `INPUTS_AND_METHODS.json`：精确重采样参数、输入和代码指纹；测试实际种子为命令所给基数加1。
- `DELIVERY_MANIFEST.json`、`delivery_verification.json`：选定文件与独立检查的绑定。
- `ITERATIONS.md`：未采用实验和取舍。其他`graph_*`、`candidate_*`目录不是当前推荐入口。

重采样应在本目录使用`INPUTS_AND_METHODS.json`中的命令，并指定新的输出目录，避免覆盖实验。最终训练使用`graph_n/train`，测试使用`graph_t/test`；不要直接使用构图脚本默认输出的训练图替代N。构图依赖与快照也已记录，旧版本及未选试验保留。

本轮在用户允许的5小时上限内提前收敛。全套参数需要继续讨论的是渲染分辨率、帧率、片长及参考素材生成；这里没有把离线通过写成渲染完成或用户最终验收。
