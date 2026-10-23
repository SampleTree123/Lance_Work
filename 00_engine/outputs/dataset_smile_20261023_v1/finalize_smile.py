"""Record bounded smile evidence and refresh the existing upload bundle."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

W = Path(__file__).resolve().parents[3]
R = Path(__file__).resolve().parent
B = W / '00_engine/outputs/dataset_server_bundle_20261023_v1'
D = W / '20_planning/data_design/character_creator/full_process'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

assert read(R/'progress.json')['phase']=='completed'
catalog=read(W/'00_engine/assets/character_creator/dataset_smile_v1.json')
assert len(catalog['motions'])==52 and len(catalog['static'])==2
reports=[read(p) for p in sorted((R/'compositions').glob('*.json'))]
assert len(reports)==52 and all(r['success'] and r['sources_unchanged'] and r['verification']['unrelated_curve_keys_identical'] for r in reports)
media=[]
for scope in ('main','references'):
    for p in (R/scope/'jobs').glob('*/media_receipt.json'):
        d=read(p); assert d['status']=='success', str(p)
        media.append({'path':str(p.relative_to(W)), 'receipt':d})
assert len(media)==4, len(media)
lookup={(r['sex'],r['source_animation']) for r in catalog['motions']}
jobs=read(B/'queues/main/main_jobs.json')['jobs']+read(B/'queues/references/carrier_jobs.json')['jobs']
assert all((j['state']['sex'],j['motion']['animation']) in lookup for j in jobs)
evidence={'status':'local_smile_smoke_passed_upload_ready_linux_pending','static_clips':2,'motion_clips':52,
          'main_and_carrier_jobs_covered':len(jobs),'nonfacial_body_preserved_all_composites':True,
          'focused_tests_passed':20,'media':media,'linux_tested':False,
          'smile_catalog_sha256':hashlib.sha256((W/'00_engine/assets/character_creator/dataset_smile_v1.json').read_bytes()).hexdigest()}
write(R/'RESULT.json',evidence)
report='''# 正式渲染统一微笑（2026-10-23）

主视频、动作参考视频、身份照和发型照统一使用原先选定的原生微笑；场景与服装单件图没有人物，不涉及表情。配置图的节点、编辑边、镜头、动作时长、服装、发型、曝光均保持原定义，表情是统一呈现设置，不新增编辑属性。

从保留的男女原始FBX恢复原微笑27–32秒窗口，生成2个静态参考表情片段和52个性别/动作对应的10秒版本。视频沿用五秒原生表情重复，保留原表情中的眼部动作，不声明循环接缝新验收。参考图片固定取微笑首帧；只改变表情，身体保持参考姿势。

52个合成动画逐帧验证成功，原始身体和无关曲线保持；9323个主任务及参考载体的动作映射均覆盖。20项直接相关离线测试通过。实际完成女性正面面部主视频、男性动作参考视频（各10秒/300帧）、女性身份照和男性发型照（各1024方图）。具体媒体回执见RESULT.json。未逐个渲染40人或全部任务，Linux待服务器小批验证。

运行配置：`00_engine/assets/character_creator/dataset_smile_v1.json`；动画目录：`/Game/DataMake/Render/Expressions/SmileV1`。渲染器读取预先生成的动画，服务器不需要重新导入FBX或现场合成表情。渲染策略版本及表情目录摘要参与续跑判断，旧无表情成品不会被视为当前微笑版本。

上传必须使用本次刷新后的脚本、配置包和新增动画；不能沿用上一轮已打包的工程/配置。路径布局保持原方案。最终上传体积及压缩包摘要见BUNDLE_REFRESH_RECEIPT.json。
'''
(R/'REPORT.md').write_text(report,encoding='utf-8')
owner=D/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
with owner.open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-23：正式渲染统一微笑\n\n用户要求所有渲染人物使用微笑。本文拥有 `dataset_smile_runtime_v1.py`（production）、配套 `tests/test_dataset_smile_runtime_v1.py`、主/参考渲染器集成及 `assets/character_creator/dataset_smile_v1.json`；`outputs/dataset_smile_20261023_v1/` 中 build_smile_assets.py、finalize_smile.py 为本轮有界恢复/交付utility，结果与来源恢复证据保留。原微笑动画此前随未用内容清理，已从保留原始FBX的27–32秒窗口恢复，生成2静态＋52生产10秒组合，服务器仅加载生成资产，不现场合成。所有主片/参考载体动作均有映射。\n\n52组合身体/无关曲线保持验证通过；20项直接测试、2段10秒视频和2张静态图实际通过。原微笑包含眼部动作，未新增循环无缝声明。节点/边/任务数量不变，表情作为全局呈现修订；版本与目录摘要使旧无表情成品失效。入口、实现与限制见[本轮报告](../../../../../../00_engine/outputs/dataset_smile_20261023_v1/REPORT.md)。R17、Linux/全量生产仍待完成；上传包使用本轮刷新结果。\n')
statepath=D/'project_management/status/PROJECT_STATE.json'
state=read(statepath)
branch=state['dataset_design_branch_20261021']
branch['render_preparation']['smile_presentation']={k:v for k,v in evidence.items() if k!='media'}
branch['render_preparation']['smile_presentation']['report']='00_engine/outputs/dataset_smile_20261023_v1/REPORT.md'
write(statepath,state)
status=D/'project_management/status/PROJECT_STATUS.md'
s=status.read_text(encoding='utf-8-sig');marker='## 最终流程清理与本地复测完成（2026-10-23）'
new='## 正式渲染统一微笑（2026-10-23）\n\n主片、动作参考、身份及发型图统一原生微笑，2静态＋52动作版本已生成；2段完整视频与2张图本地成功，20项直接测试通过。节点/编辑链数量不变，旧无表情成品不复用。使用[本轮刷新后的上传说明](../../../../../../00_engine/outputs/dataset_server_bundle_20261023_v1/README.md)及[微笑报告](../../../../../../00_engine/outputs/dataset_smile_20261023_v1/REPORT.md)。下一步上传并进行Linux小批对照。\n\n'
assert marker in s;status.write_text(s.replace(marker,new+marker,1),encoding='utf-8')
plan=D/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
with plan.open('a',encoding='utf-8') as f:f.write('\n## R17 上传前统一微笑（2026-10-23）\n\n按用户要求恢复原生微笑并覆盖主片及有人物的参考内容。2静态＋52动作版本、本地2视频＋2图片和20项相关测试通过；节点/边不变，当前表情策略使旧中性表情输出失效。使用dataset_smile_20261023_v1/REPORT.md及本轮上传清单；下一步Linux小批，R17仍in_progress。\n')
path=W/'00_engine/outputs/final_pipeline_cleanup_20261023_v1/refresh_final_bundle.py'
spec=importlib.util.spec_from_file_location('_smile_upload_refresh',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.RUN=R
checks=m.check_current();refresh=m.refresh()
write(R/'BUNDLE_REFRESH_RECEIPT.json',{'checks':checks,'refreshed':True,'refresh':refresh,'expression':'smile'})
transfer=read(B/'TRANSFER_PLAN.json')
paths={r['destination'] for r in transfer['files']}
assert 'workspace/00_engine/assets/character_creator/dataset_smile_v1.json' in paths
assert 'workspace/00_engine/scripts/unreal/dataset_smile_runtime_v1.py' in paths
for row in list(catalog['static'].values())+catalog['motions']:
    assert 'project/Content/'+row['animation'].split('.')[0].removeprefix('/Game/')+'.uasset' in paths
print(json.dumps({'status':evidence['status'],'transfer':refresh},ensure_ascii=False))
