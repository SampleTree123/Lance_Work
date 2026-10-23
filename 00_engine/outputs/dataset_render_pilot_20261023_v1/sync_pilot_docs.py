"""Bounded documentation sync for the local v11 rendering pilot."""
import copy
import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
DOC = ROOT / '20_planning/data_design/character_creator/full_process'
PREP = ROOT / '00_engine/outputs/dataset_return_control_20261022_v11/render_preparation'
RUNREL = RUN.relative_to(ROOT).as_posix()

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p, d): p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def link(src, target): return os.path.relpath(target, src.parent).replace('\\','/')
def section(p, title, body):
    s=p.read_text(encoding='utf-8'); marker='\n## '+title+'\n'
    if marker in s: s=s[:s.index(marker)]
    p.write_text(s.rstrip()+marker+'\n'+body.rstrip()+'\n', encoding='utf-8')

profile=read(PREP/'VIDEO_PROFILE.json')
profile.update(status='local_main_pilot_tested_reference_presentation_and_server_pending', render_started=True,
               formal_production_render_started=False, last_updated='2026-10-23')
profile['pending']=['user_sample_quality_review','reference_presentation_and_motion_carrier',
                    'full_reference_manifest_execution','server_exact_build_plugins_and_resource_profile',
                    'local_render_and_server_sample_comparison']
profile['output_format'].update(color_conversion_policy='opaque RGB/RGBA PNG -> discard alpha -> full-range RGB to BT.709 limited-range yuv420p; libx264 CRF16 medium',
    remaining_encoder_details='implemented and all 12 clips fully decoded; compression quality awaits user review',
    actual_local_png_channels='RGBA, fully opaque in sampled frames despite write_alpha=False',
    local_color_spotcheck=RUNREL+'/COLOR_SPOTCHECK.json')
profile['motion_timing']['render_integration_status']='main_12_clips_use_baked_production10_rate1_start0; dedicated_motion_reference_not_rendered'
profile['render_quality'].update(anti_aliasing_policy='explicit TSR (r.AntiAliasingMethod=4), screen percentage100, dynamic resolution disabled',
    resolved_cvars={'r.AntiAliasingMethod':4,'r.ScreenPercentage':100,'r.DynamicRes.OperationMode':0,
        'r.DynamicGlobalIlluminationMethod':1,'r.ReflectionMethod':1,'r.Shadow.Virtual.Enable':1,
        **{'sg.'+n+'Quality':3 for n in ['ViewDistance','AntiAliasing','Shadow','GlobalIllumination','Reflection','PostProcess','Texture','Effects','Foliage']}},
    resolved_settings_evidence='Main pilot actual project readback; explicit renderer baseline also exercised in later reference renders')
profile['local_pilot']={'run_root':RUNREL,'main_clips':12,'reference_image_prototypes':6,
    'resume_test_passed':True,'user_visual_acceptance':False,'linux_tested':False}
write(PREP/'VIDEO_PROFILE.json',profile)
machine=read(PREP/'MACHINE_LOCAL.json')
machine.update(status='local_12_clip_pilot_completed',output_root=RUN.as_posix(),
    output_root_note='Pilot only; use a separate new run root on the server',
    sampled_gpu={'name':'NVIDIA GeForce RTX 4080 Laptop GPU','total_mib':12282,'peak_used_mib':10734,
                 'samples':180,'duration_minutes':6.4,'evidence':RUNREL+'/gpu_telemetry.csv'})
write(PREP/'MACHINE_LOCAL.json',machine)
server=read(PREP/'MACHINE_SERVER.template.json')
server['version_note']='User will install Epic Linux UE5.8.1; actual server Build.version not read in this task'
server['gpu_assignment']='Use UE Vulkan -graphicsadapter=N after confirming visible adapter list; CUDA_VISIBLE_DEVICES alone is not a Vulkan selector'
write(PREP/'MACHINE_SERVER.template.json',server)

statepath=DOC/'project_management/status/PROJECT_STATE.json'
state=read(statepath); before=copy.deepcopy(state); b=state['dataset_design_branch_20261021']
b.update(status='configuration_accepted_local_12_clip_pilot_completed_server_pending', shared_UE_modified=True,
    formal_render_started=False, next_action='审查本地样片与参考图原型，确定参考载体；同步Linux UE5.8.1与工程，先做同任务服务器对照小样，再决定并发与批渲。')
b['media_profile']={'path':'render_preparation/VIDEO_PROFILE.json',**{k:v for k,v in profile.items() if k not in ['basis','scope']}}
b['render_preparation'].update(parameterized_executor_status='implemented_local_12_clips_and_resume_tested',
    local_pilot_completed=True,server_upload_started=False,server_exact_engine_version='not_read_user_will_sync_5.8.1',
    local_pilot={'root':RUNREL,'main_clips':12,'reference_image_prototypes':6,'report':RUNREL+'/PILOT_REPORT.json',
        'review':RUNREL+'/REVIEW.md','resume_passed':True,'portable_bootstrap_windows_tested':True,
        'server_tested':False,'quality_accepted_by_user':False,'dedicated_motion_reference_rendered':False},
    ue_modification_scope='Owned capture maps/sequences/reference stages only; user source maps/sites/exposure not saved or changed')
write(statepath,state)
assert {k:v for k,v in before.items() if k!='dataset_design_branch_20261021'}=={k:v for k,v in state.items() if k!='dataset_design_branch_20261021'}

statuspath=DOC/'project_management/status/PROJECT_STATUS.md'
s=statuspath.read_text(encoding='utf-8'); start=s.index('## 渲染准备：'); end=s.index('## 当前数据集分支：',start)
runlink=link(statuspath,RUN/'HANDOFF.md')
s=s[:start]+f'''## 渲染准备：本地执行器与代表小样已完成（2026-10-23）

已完成12条当前v11节点主视频和6张参考图原型；统一10秒、30fps、横1920×1080／竖1080×1920、H.264 CRF16。沿用当前40人正式槽位、已完成的production10动作和关卡保存曝光，实际渲染与编码均成功；中断驱动后继续编码而不重复渲染的实测通过。具体结果与审查入口见[本地交接]({runlink})。这次是代表小样，尚未获得用户媒体质量确认，未启动全量生产、上传或服务器渲染。

主视频队列、参数化渲染／编码、续跑、场景排序、分片、路径迁移适配和上传清单均已实现。下一步审查样片与参考布置，待用户同步Linux UE5.8.1后用同任务作服务器对照，再确定实际并行与批渲安排。动作参考专用载体／背景仍待定；本次未渲染专用动作参考视频。源场景、点位、曝光及已采用数据图保持。

下列第十一轮及更早段落描述各次离线阶段的历史范围；其中“未操作UE／未渲染”不代表当前本地小样状态。R17和唯一current父计划继续，其他分支不变。

'''+s[end:]
s=s.replace('> 最近更新：2026-10-22（视频规格及全部参考图尺寸已确认）','> 最近更新：2026-10-23（本地渲染小样、续跑及迁移准备）')
statuspath.write_text(s,encoding='utf-8')

technical=DOC/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
section(technical,'2026-10-23：v11本地参数化渲染与迁移准备',f'''
本Technical拥有`{RUNREL}/`（本地pilot，非正式生产）及以下现用实现：

- `00_engine/scripts/dataset/render_plan_v11.py`：当前候选→7203主任务及12代表任务；不修改节点、边、链、参考需求。
- `00_engine/scripts/unreal/ue_dataset_render_v11.py`：正式40人槽位、production10、世界相机、关卡曝光、MRQ；只保存独立capture副本。睫毛从审查临时actor转为可保存的正式跟随actor，保证PIE仍存在。
- `00_engine/scripts/unreal/run_dataset_render_v11.py`：连接已有UE、串行队列、错误回执、续跑与分片。未知运行状态停止队列；不无限重试。
- `00_engine/scripts/dataset/encode_render_v11.py`：300帧→MP4、完整解码与输入／成片签名；接受UE实际不透明RGBA并丢弃alpha后进行BT.709有限范围转换。
- `00_engine/scripts/dataset/schedule_render_v11.py`：场景→点位→性别→人物→服装→发型→发色→动作→镜头→画幅；整场景分片。只排序，不改内容。
- `00_engine/scripts/unreal/dataset_runtime_paths_v11.py`：私有导入图内重定位Windows绝对路径及JSON读取值，不改原文件；`--portable-runtime`。Windows实机状态查询通过，Linux未测。
- `00_engine/scripts/unreal/ue_dataset_reference_pilot_v11.py`：6张独立参考原型；背景严格取对应主片sequence首帧相机后移除人物，身份／头发／单件另建中性布光场。
- `00_engine/scripts/dataset/build_render_transfer_manifest_v11.py`、`report_render_pilot_v11.py`：只读传输清单及耗时／媒体报告。

运行命令由[OPERATIONS]({link(technical,RUN/'OPERATIONS.md')})拥有；结果由[PILOT_REPORT]({link(technical,RUN/'PILOT_REPORT.md')})拥有；本地审查从[REVIEW]({link(technical,RUN/'REVIEW.md')})进入。运行目录内`run_reference_pilots.py`、`sync_pilot_docs.py`仅为本次有界执行辅助，生命周期prototype，不作通用全量入口。

实际输出与限制：12主片全解码通过，11条另有PIE可见网格／睫毛leader核对，首条未采集该快照；6参考图成功但布置未获用户确认。专用动作参考未拍。测试断开外部driver于192帧、UE继续到300，下次直接编码成功。代表图片观察不替代逐视频人工审查。

固定1×1采样、TSR、100%屏幕比例、关闭动态分辨率和运动模糊、120／32预热、画质组3、流送10240MiB本机预算、CRF16 medium。保留用户曝光和原相机；不强制全部纹理驻留。预算属于机器参数。量化设置与界限见VIDEO_PROFILE；相同设置不保证Linux逐像素相等。

排序将场景切换2181→20、人物947→332、服装4134→1174，代价是便宜属性切换增加。样片仍逐任务复制／加载capture地图，中位约9秒，尚未实现完全常驻世界的单次队列；编码4–6秒，当前串行，不声明已有编码流水重叠。冷启动／首次着色器未独立测量，阶段差异不能当严格单轴基准。

迁移保留完整Content与读取依赖，排除本地缓存和历史媒体。Linux UE5.8.1、插件、实际GPU与画面待现场核对；不把Windows路径适配通过写成服务器可运行。原始PNG当前保留供审查，正式批次确认媒体可用后按VIDEO_PROFILE策略清理，不在本次删除。仅运行本次直接相关测试，不开展全树重建／审计。
''')
plan=DOC/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
section(plan,'R17 本地渲染交付更新（2026-10-23）',f'''本轮授权范围已完成：参数化主任务渲染、12真实节点小样、编码／续跑实测、性能分阶段记录、排序与分片、迁移清单，以及6参考图原型。证据入口为[本地交接]({link(plan,RUN/'HANDOFF.md')})。参考正式布置、专用动作参考、服务器5.8.1现场对照与全量生产仍待后续；本地小样不等于生产质量验收。R17继续in_progress，本父计划保持唯一current，其他需求及分支不修改。''')
serverdoc=DOC/'technical/rendering_release/SERVER_EXECUTION.md'
section(serverdoc,'2026-10-23 v11数据集本地准备交接',f'''当前v11使用新的参数化入口，本地12真实节点完成，未连接服务器或上传。运行命令及分片见[OPERATIONS]({link(serverdoc,RUN/'OPERATIONS.md')})；路径、Linux UE5.8.1与RLPlugin范围见[PORTABILITY]({link(serverdoc,RUN/'PORTABILITY.md')})；传输文件清单见[TRANSFER_PLAN]({link(serverdoc,RUN/'TRANSFER_PLAN.md')})。先把工程／脚本／数据配置迁移到独立服务器运行根，再做同任务小样；不要复制本机资源profile后绕过机器名检查，不要把历史服务器运行结论替代本批验证。多GPU按独立UE进程与整场景清单分配，显式确认Vulkan设备；本次未决定服务器并发数。''')
registry=DOC/'registry/README.md'
section(registry,'v11本地渲染入口反查（2026-10-23）',f'''`{RUNREL}/main_jobs.json`、`pilot_jobs.json`、`jobs/*/prepared.json`、`jobs/*/media_receipt.json`、`render_receipts/`及`TRANSFER_PLAN.json`由[数据集探索Technical]({link(registry,technical)})拥有，范围为当前v11本地pilot与迁移准备。候选权威仍为dataset_return_control_20261022_v11/selected_candidate；这些执行输出不替换候选、不证明服务器或正式生产验收。''')
execution=PREP/'RENDER_EXECUTION_PLAN.md'
section(execution,'2026-10-23 执行进度更新',f'''上文“待实现”是制定计划时的状态。现在主任务执行器、续跑、编码、场景排序、整场景分片和路径适配已完成；12真实主片与6参考图原型已输出，详见[本地交接]({link(execution,RUN/'HANDOFF.md')})。实际调度优先场景／人物／服装，画幅在便宜属性之后，不再优先按画幅拆场景。保留每条capture副本，暂未重叠编码流水。独立动作参考制作及最终参考展示待确定；服务器现场版本、插件与小样对照仍待完成，未实际上传／批渲。''')

# User-facing gallery and links.
jobs=read(RUN/'pilot_jobs.json')['jobs']; refs=read(RUN/'reference_pilot_jobs.json')['jobs']
md=['# 本地样片审查入口','', '12条主片均为10秒、30fps；6张参考图是展示原型。此页只审查媒体，不更改已采用的数据图。', '',
    '[交付说明](HANDOFF.md) · [耗时报告](PILOT_REPORT.md) · [浏览器视频画廊](REVIEW.html)', '',
    '![主视频中间帧](CONTACT_SHEET.jpg)', '', '## 主视频','', '|节点|场景／方向|人物、动作、镜头|成片|','|---|---|---|---|']
cards=[]
for j in jobs:
    jid=j['job_id']; st=j['state']; title=f"{j['node_id']} · {j['site']['name']} · {st['aspect']}"
    details=f"{st['identity']} / {st['action']} / {st['camera']}"
    md.append(f"|{j['node_id']}|{j['site']['name']}／{st['aspect']}|{details}|[播放](jobs/{jid}/video.mp4)|")
    cards.append(f'<article><h3>{html.escape(title)}</h3><video controls preload="metadata" poster="jobs/{jid}/frames/frame_0150.png" src="jobs/{jid}/video.mp4"></video><p>{html.escape(details)}</p></article>')
md += ['', '## 参考图原型', '', '![参考图预览](REFERENCE_CONTACT_SHEET.jpg)', '', '中性布光与T姿态仅为这轮展示方案；服装图无人体，发型参考采用黑色。动作参考专用视频尚未制作。', '']
for j in refs: md.append(f"- [{j['job_id']}](jobs/{j['job_id']}/frames/frame_0000.png)")
(RUN/'REVIEW.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
refcards=''.join(f'<article><h3>{html.escape(j["job_id"])}</h3><a href="jobs/{j["job_id"]}/frames/frame_0000.png"><img loading="lazy" src="jobs/{j["job_id"]}/frames/frame_0000.png"></a></article>' for j in refs)
(RUN/'REVIEW.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>v11 本地样片</title><style>body{background:#141922;color:#e8edf4;font:16px system-ui;margin:28px}h1{font-size:28px}h3{font-size:16px}p{color:#bac6d8}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px}article{padding:16px;background:#202936;border-radius:10px;overflow:hidden}video,img{width:100%;height:420px;object-fit:contain;background:#080b10}a{color:#8dc5ff}article p{overflow-wrap:anywhere}h3{overflow-wrap:anywhere}</style><h1>v11 本地样片审查</h1><p>12条主视频 · 10秒 / 30fps / 1080P · 点击播放。参考图仍为原型。</p><main>'''+''.join(cards)+'</main><h2>参考图原型</h2><main>'+refcards+'</main></html>',encoding='utf-8')
write(RUN/'DOCUMENTATION_SYNC.json',{'scope':'dataset branch and affected owners only','other_project_state_branches_unchanged':True,
    'parent_plan_closed':False,'dataset_candidate_modified':False,'local_media_available':True,'server_verified':False,
    'full_tree_audit_run':False,'reason':'User/AGENTS delivery-first bounded validation policy'})
print('Synchronized local pilot profile, branch status, plan, technical ownership and gallery.')
