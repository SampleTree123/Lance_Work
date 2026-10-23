"""Scoped experimental report/status synchronization; no UE calls."""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DOC = REPO / '20_planning/data_design/character_creator/full_process'


def read(p):
    return p.read_text(encoding='utf-8')


def write(p, text):
    p.write_text(text, encoding='utf-8')


def dump(p, obj):
    write(p, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    runs = json.loads(read(ROOT / 'joint_reserve35/SUMMARY.json'))
    audit_names = ['verification_joint_reserve35.json', 'verification_alternative_roots40.json']
    for name in audit_names:
        a = json.loads(read(ROOT / 'audit' / name))
        assert a['integrity_success'] and not a['all_target_budgets_and_quotas_filled']
        assert a['canonical_cross_split_overlap_count'] == 0
        for path, digest in a['inputs_sha256'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    status = {
        'date': '2026-10-21', 'status': 'second_trial_complete_no_accepted_candidate',
        'structural_integrity_passed': True, 'all_confirmed_sampling_rules_satisfied': False,
        'target_session_quotas_filled': False, 'production_frozen': False,
        'formal_render_started': False, 'shared_UE_modified': False,
        'confirmed_rules_changed': False, 'video_budget_changed': False,
        'targets': {'train': {'nodes': 2500, 'sessions': 12000}, 'test': {'nodes': 500, 'sessions': 2400}},
        'joint_result': {s: {k: runs[s][k] for k in ['nodes', 'sessions', 'unused_nodes', 'sessions_with_revisited_node', 'fork_effect']} for s in ['train', 'test']},
        'reading_entry': 'REPORT.md',
        'next_action': '讨论有限节点预算下的局部候选支持与全目录条件均匀之间的取舍；尚不改变规则，也不渲染当前诊断图。',
        'reference_projection_regenerated': False,
    }
    dump(ROOT / 'trial_status.json', status)

    tech = DOC / 'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
    text = read(tech)
    old_start = text.index('**当前入口（')
    old_end = text.index('\n\n', old_start)
    text = text[:old_start] + '**当前入口（2026-10-21 第二次联合构造）**：用户确认规则仍见[试构建契约](./DATASET_TRIAL_CONTRACT_20261021.md)。最新报告为 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/REPORT.md`。两条改进路线均完成离线实验及保存结果的独立结构检查，但没有同时达到节点预算、链数与全部条件抽样要求；尚无正式渲染候选。v1及两轮夜间研究保留为历史证据，其已被用户撤回的假设不再生效。' + text[old_end:]
    marker = '## 用户确认规则后的第二次联合构造'
    if marker in text:
        text = text[:text.index(marker)].rstrip() + '\n'
    text += '''
## 用户确认规则后的第二次联合构造

本Technical拥有 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/` 全部实验产物；分类为研究试构建、`unclassified_protected`。脚本生命周期均为experimental：`build_joint.py`、`alternative/pooled_exact.py`、`alternative/verify_prefix.py`、`audit/verify_joint.py`、`assemble_delivery.py`。依赖v1目录、正式服装解析和v1独立语义检查器；不进入生产脚本或Render Job。

当前阅读入口 `REPORT.md`，机器状态 `trial_status.json`，交付检查 `delivery_verification.json`。`joint_reserve35/` 保存固定预算内的联合构造，包含未完成提案；`alternative/` 保存完整域抽样的预算前缀及较大抽样诊断汇总；`audit/` 独立核验两条路线。统计支持不足和结构错误分开记录，partial核验不表示配额或采样通过。完整域较大诊断的节点增长不是理论下界，不得用它宣称预算无解。

当前发现：旧图内邻边重归一化放大回访；联合构造能降低回访，但失败重试产生接受偏差，长链缺额明显；完整域抽样条件分布较好，但节点成本大，初始有限根仍有支持偏差。下一步讨论局部候选支持与全目录条件均匀的取舍；用户尚未批准任何规则/预算变更。参考预算未重算，媒体未产出。只检查本轮文件、证据哈希与改动状态，不扩展全仓审计。R17和唯一current计划保持。
'''
    write(tech, text)

    contract = DOC / 'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
    text = read(contract)
    text = text.replace('试构建结果读取同根 `TRIAL_REPORT.md` / `trial_status.json`。', '第一次结果读取同根 `TRIAL_REPORT.md` / `trial_status.json`；最新结果读取 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/REPORT.md` / `trial_status.json`。')
    text = text[:text.index('## 实现未满足项')] + '''## 实现未满足项

v1图内邻边重归一化导致过多回访与条件抽样偏差。v2已完成预算内联合构造和完整域对照，保存结果结构检查通过，但前者只完成1,897/242条训练/测试链，且失败重试仍扭曲分布；后者在预算内只完成699/122条链，初始根也有限。尚无同时满足预算、链数与全部抽样条件的候选，不能直接渲染。上述确认规则未修改；局部候选覆盖的替代解释只是待讨论建议。分辨率、帧率、时长、画幅、最终媒体配置和文本模板未冻结，不使用旧production10媒体参数充当新决策。
'''
    write(contract, text)

    project = DOC / 'project_management/status/PROJECT_STATUS.md'
    text = read(project)
    begin = text.index('## 当前数据集分支：')
    end = text.index('## 当前服装调整：', begin)
    text = text[:begin] + '''## 当前数据集分支：第二次联合构造已完成实验，尚无达标候选（2026-10-21）

确认规则和2,500/500主视频、约12,000/2,400链目标保持，见[试构建契约](../../technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)。最新入口 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/REPORT.md`，机器状态为同根 `trial_status.json`。v1快照和参考投影保留，不套用于新图。

本轮预算内联合构造保存1,897训练链/242测试链，训练完整状态回访约4.48%，但长链缺额明显、失败重试仍产生条件分布偏差。完整域对照在预算内保存699/122链，另有较大抽样的节点成本诊断；该成本不代表理论最低需求。两条保存路线的结构、单属性、服装、父历史和跨split完整节点去重独立检查通过，配额不足单列，未接受为正式数据集。

下一步讨论有限局部候选与全目录条件均匀的实际要求，再定压缩方式；没有擅自改变规则、扩大预算或过滤自然回访。尚未同步新参考预算、未操作UE/资产/点位/曝光、未渲染。R17继续in_progress，唯一主计划及原会话资产维护指针保持。

''' + text[end:]
    write(project, text)

    plan = DOC / 'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
    text = read(plan)
    marker = '## R17 数据集分支：第二次联合构造'
    if marker in text:
        text = text[:text.index(marker)].rstrip() + '\n'
    text += '''
## R17 数据集分支：第二次联合构造（2026-10-21）

已实现并运行预算内按需扩展与完整域抽样两条路线；独立结构核验通过，但链数/配额和条件抽样未同时满足。回访机制已定位，重试接受偏差仍在，不将诊断候选送渲染。最新入口 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/REPORT.md`，所有权归[探索Technical](../../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)。下一步讨论有限候选支持与全目录均匀的取舍，当前规则和预算保持。R17继续in_progress，父计划唯一current，未修改共享UE或启动媒体生产。
'''
    write(plan, text)

    machine = DOC / 'project_management/status/PROJECT_STATE.json'
    raw = read(machine)
    before = json.loads(raw)
    key = 'dataset_design_branch_20261021'
    pos = raw.index('"' + key + '"')
    start = raw.index('{', pos)
    branch, size = json.JSONDecoder().raw_decode(raw[start:])
    branch.update({
        'status': status['status'], 'run_root': '%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/',
        'previous_round_root': '%OUTPUT_ROOT%/dataset_trial_build_20261021_v1/',
        'reading_entry': 'REPORT.md', 'next_action': status['next_action'],
        'scope': ['joint_node_session_construction', 'full_domain_comparison', 'independent_conditional_sampling_diagnostics'],
        'all_confirmed_sampling_rules_satisfied': False, 'structural_integrity_passed': True,
        'evidence': ['REPORT.md', 'trial_status.json', 'joint_reserve35/SUMMARY.json', 'alternative/SUMMARY.json', 'audit/verification_joint_reserve35.json', 'audit/verification_alternative_roots40.json', 'delivery_verification.json'],
    })
    replacement = json.dumps(branch, ensure_ascii=False, indent=2).replace('\n', '\n  ')
    new = raw[:start] + replacement + raw[start + size:]
    after = json.loads(new)
    assert {k:v for k,v in before.items() if k != key} == {k:v for k,v in after.items() if k != key}
    write(machine, new)

    links = 0
    for md in [ROOT / 'REPORT.md']:
        for target in re.findall(r'\]\((\./[^)]+)\)', read(md)):
            assert (md.parent / target).exists(), target
            links += 1
    for py in ROOT.rglob('*.py'):
        ast.parse(read(py), filename=str(py))
    dump(ROOT / 'delivery_verification.json', {
        'success': True, 'scope': 'two saved candidate audits, evidence hashes, report links, Python syntax, scoped project-state update',
        'independent_structural_checks_passed': True, 'production_sampling_accepted': False,
        'session_quotas_filled': False, 'report_links_checked': links,
        'unrelated_project_state_fields_unchanged': True, 'full_repository_audit_run': False,
        'media_validation_run': False,
    })
    files = [p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'DELIVERY_MANIFEST.json']
    dump(ROOT / 'DELIVERY_MANIFEST.json', {'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]})
    print(json.dumps({'success': True, 'files': len(files), 'report_links': links, 'accepted_candidate': False}))


if __name__ == '__main__':
    main()
