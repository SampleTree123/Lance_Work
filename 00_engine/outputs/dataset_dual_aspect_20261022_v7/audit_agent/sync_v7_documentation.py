"""Scoped dataset-branch status update and result-document checks only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from audit_dual_aspect import HERE, pin, read, token

REPO = HERE.parents[3]
FULL = REPO/'20_planning/data_design/character_creator/full_process'
STATE = FULL/'project_management/status/PROJECT_STATE.json'
STATUS = FULL/'project_management/status/PROJECT_STATUS.md'
ROOT = HERE.parent


def main():
    state_text = STATE.read_text(encoding='utf-8-sig')
    document = json.loads(state_text)
    branch_key = 'dataset_design_branch_20261021'
    outside_before = token({k: v for k, v in document.items() if k != branch_key})
    old = document[branch_key]
    previous = deepcopy(old.get('previous_v6_result', old)) if old['run_root'].endswith('dataset_dual_aspect_20261022_v7/') else deepcopy(old)
    audit = read(HERE/'audit_selected.json')
    diagnostic = read(HERE/'selected_per_aspect_diagnostics.json')
    assert audit['passed'] and diagnostic['all_original_overall_event_invariants_preserved']
    stats = deepcopy(previous['primary_candidate_statistics'])
    for split in ('train', 'test'):
        s, a = stats[split], audit['splits'][split]
        s['original_content_nodes'] = s['nodes']
        s['nodes'] = a['actual_render_nodes']
        s['render_nodes_by_aspect'] = a['render_nodes_by_aspect']
        s['chains_by_aspect'] = a['sessions_by_aspect']
        s['additional_render_versions'] = a['additional_render_nodes_over_original']
        s['semantic_per_axis_mean_reuse_ignoring_aspect'] = s.pop('per_axis_mean_reuse')
        s['per_aspect_diagnostics'] = {aspect: {
            'six_axis_max_relative_deviation': d['six_nonidentity_max_relative_deviation'],
            'conditional_single_fraction': d['formal_single_eligible_single_fraction'],
            'single_slot_max_relative_deviation': d['single_slot_max_absolute_relative_deviation']}
            for aspect, d in diagnostic['splits'][split]['by_aspect'].items()}
    stats.pop('node_savings_vs_v5', None)
    stats['content_nodes_total'] = 4552
    stats['actual_render_nodes_total'] = 6150
    stats['additional_render_versions_total'] = 1598
    stats['additional_render_fraction_vs_content'] = 1598/4552
    next_action = '用户审查保原链双画幅selected_candidate的6150主视频成本、分画幅部位残差和参考需求后决定是否采用，再确认最终媒体规格、动作参考载体、场景精确初帧及小样安排；尚未启动UE、渲染或训练。'
    branch = {
        'thread_id': old['thread_id'],
        'status': 'dual_aspect_offline_candidate_verified_pending_user_adoption_not_rendered',
        'run_root': '%OUTPUT_ROOT%/dataset_dual_aspect_20261022_v7/',
        'previous_round_root': '%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/',
        'technical_document': 'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md',
        'confirmed_contract_document': 'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md',
        'reading_entry': 'REPORT.md', 'candidate': 'selected_candidate',
        'current_candidate': 'CURRENT_CANDIDATE.json', 'parent_requirement': 'R17',
        'scope': ['immutable_v6_content_and_all_original_sessions_preserved', 'fixed_aspect_per_complete_history_and_forks',
                  'shared_render_version_cost_control', 'per_aspect_axis_and_wardrobe_diagnostics',
                  'unrendered_requests_and_recomputed_reference_demands'],
        'production_frozen': False, 'formal_render_started': False, 'shared_UE_modified': False,
        'training_started': False, 'next_action': next_action,
        'evidence': ['RULES.json','REPORT.md','CURRENT_CANDIDATE.json','selected_assignment/SOURCES.json',
                     'selected_candidate/ASSEMBLY.json','selected_candidate/SUMMARY.json',
                     'selected_candidate/train/render_requests.json','selected_candidate/test/render_requests.json',
                     'audit_agent/audit_selected.json','audit_agent/selected_per_aspect_diagnostics.json',
                     'selected_candidate/reference_summary.json','selected_candidate/reference_manifest.json',
                     'reference_binding_check.json','documentation_result_sync.json'],
        'source_candidate': '%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/selected_seed1/',
        'all_original_sessions_preserved_exactly_once': True, 'new_chain_sampling_for_selected_candidate': False,
        'structural_integrity_passed': True, 'all_experiment_hard_checks_passed': True,
        'all_confirmed_sampling_rules_satisfied': False,
        'all_registered_nodes_used': True, 'target_node_and_session_quotas_filled': True,
        'overall_diversity_accepted': False, 'offline_candidate_selected': True,
        'evidence_status': 'fixed_aspect_saved_candidate_and_request_binding_independent_checks_passed_not_rendered',
        'primary_candidate_statistics': stats,
        'source_v6_three_sampling_seed_evidence_retained': True,
        'source_sampling_stability_is_not_new_aspect_partition_seed_stability': True,
        'history_axis_decay': .2, 'wardrobe_conditional_50_50_relaxed': False,
        'test_full_value_coverage_required': False,
        'aspect_selection_policy': read(ROOT/'selected_assignment/SOURCES.json')['policy'],
        'selected_assignment_sources': {'train': 'partition_agent/economy/train', 'test': 'partition_agent/axis_balanced/test'},
        'budget_revision': {'user_authorized_moderate_increase_for_dual_aspect': True,
                            'previous_train_max': 5000, 'previous_test_max': 800,
                            'aspect_copies_count_as_render_nodes': True,
                            'aspect_copies_count_as_new_content_or_structural_sessions': False},
        'limitations': {'user_adoption': 'pending', 'final_media_profile': 'unfrozen',
                        'camera_binding_scope': 'existing orientation-specific local trajectory template, not final site world trajectory',
                        'per_camera_aspect_split_exact_half_required': False,
                        'camera_aspect_split_working_range': 'approximately_20_to_80_percent',
                        'per_aspect_asset_full_coverage_required': False,
                        'per_aspect_slot_balance_not_all_uniform': True,
                        'train_coats_landscape_actual_expected': [93,119.5],
                        'train_coats_portrait_actual_expected': [71,46.5],
                        'test_portrait_coats_actual_expected': [1,3.5],
                        'test_portrait_skirts_actual_expected': [7,4],
                        'motion_reference_carrier_and_exact_scene_initial_frame_pending': True,
                        'per_value_frequency_uniformity_claimed': False,
                        'reuse_near_two_is_soft': True},
        'previous_v6_result': previous,
    }
    # Replace only the dataset branch's JSON value; other state values stay exact.
    marker = '"'+branch_key+'": '
    start = state_text.index(marker) + len(marker)
    _, length = json.JSONDecoder().raw_decode(state_text[start:])
    replacement = json.dumps(branch, ensure_ascii=False, indent=2).replace('\n','\n  ')
    STATE.write_text(state_text[:start]+replacement+state_text[start+length:], encoding='utf-8')
    after = read(STATE)
    outside_after = token({k: v for k, v in after.items() if k != branch_key})
    assert outside_before == outside_after, 'An unrelated state branch changed'
    text = STATUS.read_text(encoding='utf-8-sig')
    start = text.index('## 当前数据集分支：')
    end = text.index('## 当前服装调整：', start)
    replacement = '''## 当前数据集分支：保留原链的第七轮双画幅离线候选已验证，待采用（2026-10-22）

当前主候选`%OUTPUT_ROOT%/dataset_dual_aspect_20261022_v7/selected_candidate`，由同根`CURRENT_CANDIDATE.json`与`selected_assignment/SOURCES.json`绑定。入口为`REPORT.md`；所有权归[探索Technical](../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)，确认语义见[试构建契约](../../technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)。第六轮`selected_seed1`全部4,552个非画幅内容状态、12,000／2,400条原链及43,800／8,760次编辑完整保留，每条链连同分支固定一个画幅，不将副本计为新结构链。

实际主视频请求训练4,963、测试1,187，总6,150；相对4,552个内容状态增加1,598个画幅版本（35.1%）。用户已允许链数横竖近似与主视频数适度超过旧5,000／800预算，参考另计。选择使用同一政策：先控制共享节点成本，任一画幅六非身份轴偏差>10%才细化；训练经济档未触发，测试触发，用额外65个节点改善。每画幅均覆盖男女、21起始镜头和七轴，镜头画幅分配约20–80%，不声称每镜头精确各半。

独立`audit_agent/audit_selected.json`通过：全部原链完整历史／fork、正式合法性、去画幅跨split隔离、实际used节点和每节点唯一请求／镜头库绑定均通过。整体原编辑次数、训练全属性真实目标覆盖、239核心件真正换入、L5与去画幅具体边复用保持；带画幅边最高3次。`audit_agent/selected_per_aspect_diagnostics.json`另确认整体axes/modes/conditional及部位实际数／正式期望exact保持。

分画幅六轴最大偏差训练横1.99%／竖6.08%、测试横5.37%／竖8.52%。条件single训练横50.016%／竖47.402%、测试横53.077%／竖50.791%。不能写成各部位全面均衡：训练外套横93次vs条件期望119.5、竖71vs46.5；测试竖外套1vs3.5、裙子7vs4是低量残差。便宜的重采样备选已独立审核，但有训练换衣支持与分布回归，保留比较而不混入主候选。

最终候选参考需求已重算，`reference_summary.json`／`reference_manifest.json`与根`reference_binding_check.json`绑定52,560次步骤链接；仍为未渲染需求。现有camera plan的尺寸／时钟仅作局部轨迹模板，最终媒体规格、动作参考载体和场景精确初帧尚待确认。下一步用户审查是否采用，再确定这些事项与小样安排；未改共享UE、资产、点位、曝光，未启动参考媒体／渲染／训练，R17继续in_progress，唯一current父计划和其他分支local_work保持。

'''
    STATUS.write_text((text[:start]+replacement+text[end:]).replace('（仅数据集分支第六轮离线候选结果同步）','（仅数据集分支第七轮双画幅离线候选结果同步）'),encoding='utf-8')
    authority_paths = [STATE,STATUS,FULL/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md',
                       FULL/'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md',
                       FULL/'registry/README.md',FULL/'project_management/status/workflows/WF-70.md',
                       FULL/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md']
    required = ['REPORT.md','CURRENT_CANDIDATE.json','RULES.json','selected_candidate/ASSEMBLY.json',
                'selected_candidate/reference_manifest.json','selected_candidate/reference_summary.json',
                'reference_binding_check.json','audit_agent/audit_selected.json','audit_agent/selected_per_aspect_diagnostics.json']
    missing = [p for p in required if not (ROOT/p).exists()]
    result = {'schema': 'v7_targeted_documentation_result_sync_v1',
              'scope': 'Changed dataset branch authorities and explicit final-candidate evidence only',
              'changed_authorities': [pin(p) for p in authority_paths],
              'candidate_evidence': [pin(ROOT/p) for p in required if (ROOT/p).exists()],
              'targeted_navigation_and_status_checks': pin(HERE/'targeted_documentation_checks.json') if (HERE/'targeted_documentation_checks.json').exists() else None,
              'missing_required_evidence': missing,
              'unrelated_project_state_semantically_preserved': outside_before == outside_after,
              'unrelated_project_state_canonical_sha256': hashlib.sha256(outside_before.encode()).hexdigest(),
              'current_plan_id_preserved': after['current_plan_id'] == document['current_plan_id'],
              'local_work_preserved': after['local_work'] == document['local_work'],
              'parent_requirement': 'R17', 'requirement_status': 'in_progress',
              'candidate_independent_audit_passed': audit['passed'],
              'overall_original_event_invariants_preserved': diagnostic['all_original_overall_event_invariants_preserved'],
              'production_gate_promoted': False, 'rendered': False,
              'full_repository_audit_or_catalog_rebuild_run': False,
              'not_run_reason': 'User scope is a targeted sync and final selected-candidate checks; no full-tree audit or unrelated catalog rebuild.',
              'status': 'passed_targeted_checks' if not missing else 'pending_final_evidence'}
    (ROOT/'documentation_result_sync.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status': result['status'], 'missing': missing, 'unrelated_state_preserved': outside_before == outside_after},ensure_ascii=False))


if __name__ == '__main__':
    main()
