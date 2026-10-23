# 原生面部表演自然持续五秒

> 文档 ID：`PLAN-2026-10-NATIVE-FACE-FIVE-SECOND`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50`
> 最近核验：2026-10-08（R01–R03限定技术交付完成，用户自然度pending）

## 目标与授权

用户已审查前一轮五种表情，认为整体正确；本次要求自然持续5秒。不能整体放慢眨眼、嘴部动作或只扩大眨眼间隔。允许寻找更长现成素材、自然延长现有表演和联网参考，先用少量试验判断效果。该新确认只覆盖用户实际看过的旧表情，不代表新五秒候选已获自然度接受。

前一计划保留完成历史，旧回执里的pending不倒写。旧五种表情审查库继续可用，新候选在技术与代表观察完成前不替换当前库。UE/CC实际修改由主agent串行完成；本任务不扩充身体动作、场景或改动服装/发色规则。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-NATIVE-FACE-FIVE-SECOND/R01` | 建立来源、节奏及五秒候选小样 | `WF-50` | 冻结旧审查库引用，登记新用户确认；明确可复现源片段/参数，保留眨眼与嘴部自然速度，不用全局慢放或仅拉大眨眼间隔凑时长 | `completed` | N2的user_feedback_20261008_v1.json、来源清单与任务；连续原片五秒rate=1，无loop/envelope或全局慢放 |
| `PLAN-2026-10-NATIVE-FACE-FIVE-SECOND/R02` | 验证五秒实际表演与身体组合 | `WF-50` | 代表候选实际持续5秒；曲线/面部骨与身体保护通过；检查首尾、眼口及连续播放节奏，精确记录观察范围和缺口 | `completed` | N2的compositions及男女body_probes成功；八组_capture_v2逐151点三曲线同time核验通过，review_media_validation_v1.json确认8段150帧/5.0秒；技术完成，用户自然度和浏览器交互播放未代签 |
| `PLAN-2026-10-NATIVE-FACE-FIVE-SECOND/R03` | 交付可比较候选并完成记录 | `WF-50` | 保留可恢复旧库、提供明确审查入口；技术结果与最终用户自然度评价独立记录；完成必要回归、目录与文档审计 | `completed` | technical_delivery_v1.json、八卡review.html及FFmpeg实解码；743通过＋宿主18恢复覆盖761项；两目录已重建、preclosure独立子系统/跨层审计通过，归档终验见documentation_final_audit_v2.json；用户自然度pending独立保留 |

## 实现与输出

- 技术所有者：[Animation §8](../../../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#8-五秒自然面部表演试验)。
- 当前落实：[WF-50 Status](../../status/workflows/WF-50.md)。
- N2=`%OUTPUT_ROOT%/unreal_character_import/native_face_five_second_20261008_v1/`，沿用`OUT-WF50-RUNTIME-ACCEPTANCE`，默认`unclassified`保护。
- 旧库、旧计划完成事实和来源资产不覆盖。候选的技术通过不能代签最终用户自然度接受；新五秒自然度仍pending。

## 完成条件与下一步

R01–R03已按原技术交付条件完成并移入History。用户自然度、情绪持续性和正式库晋升仍pending；旧库没有替换，未宣称全部旧情绪均已有自然五秒替代。当前进入显式idle，等待用户通过review.html或MP4评价，不自动扩展其他任务。打开请求仅queued，浏览器file协议被工具安全策略拒绝，交互播放未验证。

## 未纳入与后续范围

本次没有取得用户对新五秒候选的自然度、情绪标签或持续性接受，没有发布新正式表情库，也没有验证全部旧情绪、全40角色或所有身体动作组合。浏览器交互播放未验证，HTML打开请求仅queued。后续先由用户查看已交付候选，再按明确反馈决定调整或晋升；不自动启动身体动作/场景扩充或其他延期任务。
