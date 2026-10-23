from pathlib import Path
import json, hashlib, os, re, copy

REVIEW=Path(__file__).resolve().parent
RUN=REVIEW.parent
ROOT=Path(__file__).resolve().parents[4]
DOC=ROOT/'20_planning/data_design/character_creator/full_process'
REPORT=REVIEW/'AUDIT_REPORT.md'
assert REPORT.exists(), 'Write the final bounded audit report before recording adoption.'
def readj(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def report_link(path): return '[本轮审计报告]('+os.path.relpath(REPORT,path.parent).replace('\\','/')+')'
assert readj(REVIEW/'fresh_frequency_audit.json')['passed']
assert readj(REVIEW/'fresh_inherited_audit.json')['passed']
assert readj(REVIEW/'structure_findings.json')['passed_supplemental_checks']
assert readj(REVIEW/'reference_findings.json')['passed']
current=readj(RUN/'CURRENT_CANDIDATE.json')
protected=[RUN/'CURRENT_CANDIDATE.json',RUN/'RULES.json',RUN/'DELIVERY.json']
protected += [Path(pin['path']) for pin in current['selected_file_pins']]
protected += [RUN/'selected_candidate/reference_manifest.json',RUN/'selected_candidate/reference_summary.json']
protected={str(p):sha(p) for p in protected if p.exists()}
assert all(sha(Path(pin['path']))==pin['sha256'] for pin in current['selected_file_pins'])
changes=[]
def save(path,text):
    before=sha(path)
    path.write_text(text,encoding='utf-8',newline='\n')
    changes.append({'path':str(path),'before_sha256':before,'sha256':sha(path)})
def replace(path,pairs):
    text=path.read_text(encoding='utf-8-sig')
    for old,new in pairs:
        assert old in text,(str(path),old)
        text=text.replace(old,new,1)
    save(path,text)
def append(path,text):
    old=path.read_text(encoding='utf-8-sig')
    save(path,old.rstrip()+'\n\n'+text.strip()+'\n')

p=DOC/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
replace(p,[('（第十一轮属性回换控制实际结果与独立审计同步）','（第十一轮配置／内容采用与限定复审同步）'),
('**当前入口（第十一轮属性回换控制，离线通过待审）**','**当前入口（第十一轮配置／内容已采用，限定离线复审通过）**'),
('当前待用户审阅采用，媒体规格／动作参考载体／精确场景初帧仍未冻结','用户已采用本候选配置与内容；媒体规格／动作参考载体／精确场景初帧仍未冻结')])
append(p,'''### 第十一版采用与配置／内容复审（2026-10-22）

用户确认“没关系，现在这样就可以了”，采用的是现有v11配置与内容；随后要求重新审计各方面数据、内容和待修改项。'''+report_link(p)+'''是本次复审入口，`review_20261022/fresh_frequency_audit.json`／`fresh_inherited_audit.json`独立重算既有约定，`structure_findings.json`、`reference_findings.json`、`distribution_diagnostics.json`和`coverage_and_edits.json`补充结构、请求、参考与分布诊断。未发现需要重采样节点或链的内容错误；这是限定离线检查结论，不是像素、媒体质量、正式渲染或训练收益接受。

本Technical拥有`review_20261022/`全部实验输出、`audit_reference_semantics.py`、`audit_structure_supplement.py`及`sync_adoption_docs.py`。初始抽样名义男女50/50、分叉时点／父位置均匀是提议规则，不能写成约束选择后最终数据精确服从这些分布：最终训练起始链男女44.03%／55.97%，已披露为采用候选的诊断；不新增精确男女平衡门槛。整体六轴±10%仍通过；逐画幅最大偏差训练横8.41%／竖13.45%，测试横11.29%／竖12.09%，现契约没有每画幅六轴±10%硬门槛，故另列诊断而不追溯制造新失败。

复审发现`selected_candidate/REFERENCES.md`仍把画幅列为未定；本次仅修正文案为横竖双画幅已确定、具体分辨率／帧率／时长及制作实现待冻结。原扫描`reference_findings.json`保留观察事实，后续修正记录在`REFERENCE_REVIEW.md`及`documentation_sync.json`，不把原扫描改写成从未发现问题。历史源planner和已绑定finalizer不修改；未来重建参考说明时应保留此澄清。节点／边／会话／渲染请求／参考清单和CURRENT／RULES／旧交付绑定均未修改。

媒体参数、参考制作与文字模板、动作载体及相位／速度／时长对齐、场景精确初始世界相机／帧签名仍是正式渲染前的待办；当前符号场景键不证明真实初帧可复用。UE二进制与全像素可见性未在本轮重验。R17、唯一current父计划与其他分支保持，不启动UE／媒体／渲染／训练、不晋升生产Gate；本次只做受影响文件链接与哈希核对，不扩展全库审计或catalog重建。
''')

p=DOC/'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
replace(p,[('（第十一轮属性回换控制与离线执行回填）','（第十一轮配置／内容采用与限定复审）'),
('仍待用户采用，未启动UE／媒体／渲染／训练，不晋升生产Gate或关闭R17。','用户已采用v11配置与内容；未启动UE／媒体／渲染／训练，不晋升生产Gate或关闭R17。')])
append(p,'''### 第十一轮采用与复审范围

用户已接受本轮配置与内容，限定复审见'''+report_link(p)+'''。名义男女50/50与分叉均匀提议不等同于最终受约束候选的精确分布；实测偏移列为诊断，不追加未授权门槛。六非身份轴±10%按split整体核验，当前不设逐画幅同一硬门槛；训练竖屏13.45%、测试横／竖11.29%／12.09%已披露。采用不代表最终媒体规格冻结或UE／参考媒体／渲染质量接受；原数据约定保持。
''')

p=DOC/'project_management/status/PROJECT_STATUS.md'
replace(p,[('（第十一轮属性回换控制离线结果同步）','（第十一轮配置／内容已采用，限定复审同步）'),
('## 当前数据集分支：第十一轮属性回换明显减少，离线通过待审（2026-10-22）','## 当前数据集分支：第十一轮配置／内容已采用，限定复审通过（2026-10-22）'),
('下一步审阅剩余长链回换与候选取舍并决定采用，再确认最终媒体规格、参考载体／精确场景初帧及小样。','用户已采用现有配置与内容；后续需确认最终媒体规格、参考载体／精确场景初帧及小样。')])
text=p.read_text(encoding='utf-8')
position=text.index('## 历史第十轮')
adopted='''用户确认当前v11配置与内容可以采用，并要求再次审计。'''+report_link(p)+'''及同目录全新频率／继承、结构／参考检查通过，未发现需要重采样的数据错误；唯一小文案“画幅未定”已修正，原审查发现及修正回执同时保留。训练起始链男女44.03%／55.97%与名义提议50/50不同；逐画幅六轴最大偏差训练横8.41%／竖13.45%、测试横11.29%／竖12.09%，均作为已披露诊断，不新增当前契约没有的分画幅门槛。整体split六轴约束仍通过。

本次采用只覆盖配置与内容。最终媒体参数、参考制作／文字模板、动作载体与时钟对齐、场景精确世界初帧仍待完成；未接受UE／媒体／渲染质量或训练收益。R17与唯一current父计划继续进行，其他分支保持；局部同步回执为`review_20261022/documentation_sync.json`。

'''
save(p,text[:position]+adopted+text[position:])

p=DOC/'project_management/status/workflows/WF-70.md'
replace(p,[('仍为experimental离线候选待用户审阅，不替换第一批正式接受图或GATE-70','v11配置与内容已由用户采用，仍属于experimental离线范围，不替换第一批正式接受图或GATE-70')])
append(p,'''### 第十一轮采用后的限定复审

用户采用当前配置与内容后，重新核对频率、目标／起点／父历史、结构配额、参考与渲染请求；结果见'''+report_link(p)+'''。未发现需要重采样的数据错误，旧画幅未定文案已修正并保留审查／修正记录；最终受约束分布与名义提议的差异、逐画幅六轴残差均已披露，不新增硬门槛。此处不接受媒体／UE像素质量，不晋升生产Gate或关闭R17；正式媒体参数和参考制作继续待定。
''')

p=DOC/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
replace(p,[('下一步用户审阅后决定采用，再确定媒体规格、参考载体／精确初帧及小样；R17仍in_progress','用户已采用本轮配置与内容；后续确定媒体规格、参考载体／精确初帧及小样；R17仍in_progress')])
append(p,'''### 第十一轮用户采用与后续复审

用户接受现有v11配置与内容，随后要求再次审计数据、内容与待修改项。'''+report_link(p)+'''记录限定离线复核通过、实际分布诊断及一处参考说明文案修正，未发现重采样必要；不追加男女精确各半、逐画幅六轴±10%等新门槛。采用范围不包含正式媒体／UE／渲染质量；媒体参数、参考制作与文本、动作载体及时钟、场景精确初帧仍待完成。本计划唯一current、R17继续in_progress，其他需求与分支保持，不自动启动渲染或训练。
''')

p=DOC/'registry/README.md'
replace(p,[('实际采用与未渲染边界查Status','配置／内容已由用户采用；限定复审见`review_20261022/AUDIT_REPORT.md`，媒体／渲染未接受，边界查Status')])

p=DOC/'project_management/status/PROJECT_STATE.json'
text=p.read_text(encoding='utf-8-sig')
state=json.loads(text)
other=copy.deepcopy({k:v for k,v in state.items() if k!='dataset_design_branch_20261021'})
branch=copy.deepcopy(state['dataset_design_branch_20261021'])
branch['status']='configuration_content_accepted_bounded_reaudit_passed_not_rendered'
branch['overall_diversity_accepted']=True
branch['configuration_content_accepted']=True
branch['user_acceptance']={'date':'2026-10-22','statement':'没关系，现在这样就可以了。','scope':'v11 configuration and content only','media_quality_accepted':False,'production_gate_promoted':False}
branch['limitations']['user_adoption']='accepted_configuration_content_only'
branch['next_action']='本轮配置／内容采用及限定复审完成，用户查看review_20261022/AUDIT_REPORT.md与媒体／参考制作待办后讨论后续媒体规格、参考载体／精确场景初帧及小样；R17继续进行。'
branch['evidence_status']='configuration_content_user_accepted; fresh_bounded_structure_frequency_inherited_reference_audits_passed; no_media_acceptance'
branch['scope'].append('configuration_content_user_accepted_with_fresh_bounded_reaudit')
new_evidence=['review_20261022/'+name for name in ['AUDIT_REPORT.md','fresh_frequency_audit.json','fresh_inherited_audit.json','structure_findings.json','reference_findings.json','distribution_diagnostics.json','coverage_and_edits.json','REFERENCE_REVIEW.md','documentation_sync.json']]
branch['evidence']+=new_evidence
diagnostics=readj(REVIEW/'distribution_diagnostics.json')
branch['bounded_reaudit_20261022']={'report':'review_20261022/AUDIT_REPORT.md','passed_offline_checks':True,'candidate_resampling_required':False,'configuration_content_accepted':True,'sex_and_fork_nominal_proposals_are_not_claimed_final_probabilities':True,'train_start_chain_sex':diagnostics['train']['sex_chains'],'per_aspect_six_axis_max_relative_deviation':{s:{a:v['six_axis_maxdev'] for a,v in diagnostics[s]['per_aspect'].items()} for s in ['train','test']},'per_aspect_six_axis_ten_percent_hard_gate_exists':False,'reference_documentation_issue':'REFERENCES.md aspect-unfrozen wording corrected; original reference_findings retained','render_media_accepted':False,'UE_binary_assets_rehashed':False,'full_repository_audit_run':False}
start=text.index('  "dataset_design_branch_20261021": ')
begin=text.index('{',start)
_,length=json.JSONDecoder().raw_decode(text[begin:])
replacement=json.dumps(branch,ensure_ascii=False,indent=2)
replacement='\n'.join(('  '+line if n else line) for n,line in enumerate(replacement.splitlines()))
new_text=text[:begin]+replacement+text[begin+length:]
new_state=json.loads(new_text)
assert other=={k:v for k,v in new_state.items() if k!='dataset_design_branch_20261021'}
save(p,new_text)

p=RUN/'selected_candidate/REFERENCES.md'
replace(p,[('未确定：分辨率、帧率、时长、画幅，以及身份/头发/服装参考拍摄实现','横竖双画幅已确定；未确定：具体分辨率、帧率、时长，以及身份/头发/服装参考拍摄实现')])
p=REVIEW/'REFERENCE_REVIEW.md'
append(p,'''## 后续文案修正记录（2026-10-22）

上述只读扫描如实记录了当时的旧文案；扫描结果`reference_findings.json`保持原样。后续文档同步已将`selected_candidate/REFERENCES.md`末段改为“横竖双画幅已确定；具体分辨率、帧率、时长及参考制作实现等仍待冻结”。此处只改参考说明文案，候选节点、图边、会话、渲染请求和参考清单保持；修正前后文件哈希由`documentation_sync.json`记录。历史源planner和已绑定finalizer保持，未来重建说明时应保留此澄清。

用户接受的是v11配置与内容；本审查与修正均不新增媒体／像素质量、UE或正式渲染接受。
''')

assert all(sha(Path(path))==pin for path,pin in protected.items())
links=[]
for item in changes:
    path=Path(item['path'])
    item['sha256']=sha(path)
    if path.suffix!='.md': continue
    for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in link or link.startswith(('#','mailto:')): continue
        target=link.split('#')[0]
        if not target: continue
        exists=(path.parent/target).resolve().exists()
        links.append({'document':str(path),'target':link,'exists':exists})
assert all(link['exists'] for link in links),[x for x in links if not x['exists']]
unique_changes={}
for item in changes:
    if item['path'] not in unique_changes:
        unique_changes[item['path']]=dict(item)
    else:
        unique_changes[item['path']]['sha256']=item['sha256']
changes=list(unique_changes.values())
receipt={'passed':True,'scope':'localized v11 configuration/content adoption, bounded audit pointers and one reference-document wording fix; no candidate machine files changed','changed_documents':changes,'other_project_state_branches_unchanged':True,'current_plan_and_R17_status_unchanged':True,'acceptance_scope':'configuration and content only; media/render quality and production gates not accepted','protected_machine_files_unchanged':[{'path':k,'sha256':v} for k,v in protected.items()],'original_reference_findings_kept':True,'original_small_documentation_issue_resolution':'fixed REFERENCES.md aspect-unfrozen wording; appended resolution to REFERENCE_REVIEW.md','local_file_links_checked':len(links),'local_file_links_passed':True,'audit_evidence':[{'path':str(REVIEW/name),'sha256':sha(REVIEW/name)} for name in ['AUDIT_REPORT.md','fresh_frequency_audit.json','fresh_inherited_audit.json','structure_findings.json','reference_findings.json','distribution_diagnostics.json','coverage_and_edits.json']],'owned_review_scripts':[{'path':str(p),'sha256':sha(p)} for p in sorted(REVIEW.glob('*.py'))],'skipped':['global catalog or inventory rebuild','full repository documentation audit','UE binary rehash and execution','media/pixel/render quality acceptance','training evaluation']}
(REVIEW/'documentation_sync.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':True,'changed_documents':len(changes),'links_checked':len(links),'protected_machine_files':len(protected),'receipt':str(REVIEW/'documentation_sync.json')},ensure_ascii=False))
