"""Record the bounded smoke evidence and update only current status owners."""
import json, hashlib
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parent
repo=root.parents[2]
docs=repo/'20_planning/data_design/character_creator/full_process'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=read(root/'render_receipts/readiness_budget10240_v1.json')
assert receipt['status']=='completed' and receipt['success']
frames=sorted((root/'renders/readiness_budget10240_v1/readiness_3frames').glob('*.png'))
assert [p.name for p in frames]==['frame_0000.png','frame_0001.png','frame_0002.png']
files=[]
for p in frames:
    with Image.open(p) as im:
        im.load()
        assert im.size==(1024,576)
        files.append({'path':str(p.relative_to(root)), 'size':list(im.size),
                      'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
gpu=read(root/'gpu_budget10240.json')
values=[list(map(int,r['memory_mib'].split(','))) for r in gpu if r['memory_mib']]
restored=read(root/'finish_probe.json')
assert all(restored[k] for k in ('source_map_unchanged','site_unchanged','preview_unchanged',
    'appearance_unchanged','post_process_volumes_unchanged'))
assert restored['pool_after']==7000
report={
    'schema':'render_readiness_bounded_validation_v1','updated_on':'2026-10-21',
    'status':'bounded_static_smoke_passed','formal_render_started':False,
    'receipt':'render_receipts/readiness_budget10240_v1.json','frames':files,
    'visual_review':{'observed_frames':[0,2],'finding':'Clothing plaid, facial and background detail restored relative to the same 1024x576 smoke with 7000 MB pool.',
                     'scope':'Static copied preview only, not acceptance of all characters, motion, eyelashes or formal look serialization.'},
    'warmup':{'engine_frames':120,'render_frames':32,'full_texture_residency_guaranteed':False},
    'pool':{'editor_mb':7000,'mrq_mb':10240,'restored_editor_mb':restored['pool_after'],
            'machine_bound':True,'all_scene_or_resolution_budget_verified':False},
    'gpu_observation':{'samples':len(values),'max_used_mib':max(v[1] for v in values),
        'min_free_mib':min(v[2] for v in values),'continuous_peak_measurement':False},
    'preservation':{k:restored[k] for k in ('source_map_unchanged','site_unchanged','preview_unchanged','appearance_unchanged','post_process_volumes_unchanged')},
    'tests':{'passed':83,'failed':1,
        'failure':'test_gallery_keeps_pending_cards_and_does_not_claim_all1260_visual_acceptance: older gallery Chinese wording assertion, unrelated to exposure/warmup; not changed.',
        'scope':['test_mrq_streaming_warmup_v1.py','test_primary_scene_samples_v1.py'],
        'separate_exposure_old_prepared_guard_tests_passed':2,'full_repository_tests_run':False},
    'environment_note':'First PIE run prompted for existing BP_TestPlayer compile error; continued this bounded smoke. Three later runs completed without another prompt. Blueprint itself not repaired.',
}
write(root/'media_validation.json',report)

next_action='渲染规划由用户已建立的分支会话继续；原会话曝光继承和本机纹理预热接入已完成限定验证，后续按用户反馈维护UE资产、场景与面板。尚未确认首批参数或启动正式批量渲染。'
status='exposure_and_texture_warmup_bounded_verified_planning_in_fork'
state_path=docs/'project_management/status/PROJECT_STATE.json'
state=read(state_path)
state['updated_at']='2026-10-21'
state['project_phase']=status
state['next_action']=next_action
local=state['local_work']
local.update(scope='render_readiness_20261021_v1',updated_at='2026-10-21',
    run_root='%OUTPUT_ROOT%/render_readiness_20261021_v1/',execution_status=status,next_action=next_action)
local['current_activity'].update(scope='render_readiness_20261021_v1',status=status,next_action=next_action,
    render_readiness_evidence='%OUTPUT_ROOT%/render_readiness_20261021_v1/media_validation.json')
summary=local['review_configuration_summary_20261021']
summary.update(camera_inherit_level_exposure_change_implemented=True,
    camera_inherit_level_exposure_change_status='UE_shared_helper_live_preview_and_static_MRQ_verified; stale_prepared_requires_rebuild',
    texture_recovery='machine_profile_editor7000_MRQ10240_MB_restored_after_render_bounded_HongKong_smoke',
    formal_render_warmup_implemented=True,formal_render_started=False,first_render_plan_confirmed=False,
    technical_section='SCENE_CAMERA_SEQUENCE.md#2219-曝光继承与渲染预热接入2026-10-21')
local['render_readiness_20261021_v1']={
    'status':status,'technical_document':'technical/unreal/SCENE_CAMERA_SEQUENCE.md',
    'evidence':'%OUTPUT_ROOT%/render_readiness_20261021_v1/media_validation.json',
    'exposure_evidence':'%OUTPUT_ROOT%/render_readiness_20261021_v1/exposure_result.json',
    'local_profile':'%OUTPUT_ROOT%/local_render_profile_v1/profile.json',
    'handoff':'%OUTPUT_ROOT%/render_readiness_20261021_v1/HANDOFF.md',
    'formal_render_started':False,'production_promoted':False,
    'old_four_trials_prepared_rebuilt':False,
    'old_prepared_policy':'Reject stale exposure policy; build new preparation from saved source level for a new plan.',
    'tests':report['tests'],'gpu_observation':report['gpu_observation']}
state['workflow_status']['WF-60']=status
write(state_path,state)

block="""## 当前：曝光继承与纹理预热已接入，渲染规划转交分支（2026-10-21）

- 当前审查基线保持：40人物、21场景及21用户点、25动作、21镜头、横竖两画幅；1428项有效排除沿用保存快照。7发色、服装/鞋库规则不变，用户已调好的关卡后期处理体积不改写。
- 审查相机与正式准备共用关卡曝光继承逻辑，真实UE字段检查通过；旧prepared缺少新曝光策略时要求重新准备，不偷偷复用10月17日旧四片。
- MRQ增加120个引擎预热帧、32个渲染预热采样。本机配置恢复审查7000 MB，并仅在MRQ临时使用10240 MB，正常结束恢复原值。7000 MB试片曾因非流送资源占满预算将衣服2048贴图降到64；10240 MB同场景对照恢复格纹、皮肤及背景细节。
- 香港街道静态3帧1024×576小样成功、3帧解码通过，实际查看第0/2帧；原场景文件、点位、外观、预览、后期体积均保持，预算恢复7000。35次GPU采样最高占用10015 MiB、最低剩余1981 MiB，仅代表本次离散采样。不是全场景/新正式角色装配/动画或高分辨率批量验收。
- 定向测试83通过、1项旧画廊中文断言失败；失败与曝光/预热改动无关，保留记录不扩修。曝光及旧prepared保护另2项通过。首个PIE遇到已有BP_TestPlayer编译提示，继续后完成，后续三次未重复提示；该测试蓝图本身未修复。

下一步：渲染参数、数据规模和首批安排由用户建立的分支会话推进；原会话负责UE资产、场景和面板维护。当前技术接入已完成限定验证，正式批量渲染未启动，R17保持in_progress，父计划继续唯一current。实现与边界见TECHLINK；当前证据为`%OUTPUT_ROOT%/render_readiness_20261021_v1/media_validation.json`，交接为同目录`HANDOFF.md`。

"""
for relative,link in [
    ('project_management/status/PROJECT_STATUS.md','[Technical §22.19](../../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2219-曝光继承与渲染预热接入2026-10-21)'),
    ('project_management/status/workflows/WF-60.md','[Technical §22.19](../../../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2219-曝光继承与渲染预热接入2026-10-21)')]:
    p=docs/relative
    text=p.read_text(encoding='utf-8')
    start=text.index('## 当前：')
    end=text.index('## 前序：',start)
    text=text[:start]+block.replace('TECHLINK',link)+'\n'+text[end:]
    text=text.replace('最近更新：2026-10-21（当前统计与待接续边界同步）',
                      '最近更新：2026-10-21（曝光与纹理预热限定验证完成）')
    p.write_text(text,encoding='utf-8')
p=docs/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
text=p.read_text(encoding='utf-8')
start=text.index('## R17 当前任务：进度同步完成')
text=text[:start]+block.replace('## 当前：','## R17 当前任务：').replace('TECHLINK',
    '[Technical §22.19](../../../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2219-曝光继承与渲染预热接入2026-10-21)')
p.write_text(text,encoding='utf-8')
print('Saved bounded evidence and four current status/plan owners.')
