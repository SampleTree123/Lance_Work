"""Bind the selected byte-identical copies to completed independent audits."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V5 = ROOT.parent / 'dataset_balanced_graph_20261022_v5'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def pin(p):
    return {'path': str(p.resolve()), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    spec = read(ROOT / 'FINAL_SELECTION.json')
    rules = read(ROOT / 'RULES.json')
    rules['status'] = spec['status']
    rules['balancing']['history_axis_penalty_base'] = 0.2
    rules['balancing']['history_axis_penalty_formula'] = 'base_axis_weight * (0.2 ** prior_axis_occurrence_count)'
    rules['balancing']['previous_v5_penalty_base'] = 0.5
    rules['local_target_support']['candidate_sampling_implementation'] = 'v68: exact start-camera quotas, formal-slot support, complete-history 0.2**n, capacity-aware starts and late same-camera fallback; explicit actual-target coverage jobs'
    rules['actual_implementation'] = {
        'selection': 'FINAL_SELECTION.json', 'candidate': 'selected_seed1',
        'nodes': {'train': 3752, 'test': 800}, 'graphs': spec['graphs'],
        'sampling_configuration': spec['sampling_configuration'],
        'audits': [r['audit'] for r in spec['sampling_seeds']],
        'initial_sampling_note': 'Historical ideal marginal preferences above are not guarantees of joint uniformity; the finite local-support graph, coverage and capacity feedback apply. Only start-camera weights have exact integer quotas.',
        'acceptance': 'offline verified; user adoption and visual validation pending'}
    write(ROOT / 'RULES.json', rules)
    write(ROOT / 'CURRENT_CANDIDATE.json', {
        'status': spec['status'], 'primary': str(ROOT / 'selected_seed1'),
        'train': str(ROOT / 'selected_seed1/train'), 'test': str(ROOT / 'selected_seed1/test'),
        'report': str(ROOT / 'REPORT.md'), 'selection': str(ROOT / 'FINAL_SELECTION.json'),
        'alternate_seed_checks': [str(ROOT / f'selected_seed{i}') for i in (2, 3)],
        'alternates_are_additional_samples': False,
        'main_video_nodes': {'train': 3752, 'test': 800},
        'chains': {'train': 12000, 'test': 2400},
        'previous_candidate_preserved': str(V5 / 'candidate_c_seed1'),
        'rendered': False, 'training_started': False})

    verification = []
    for row in spec['sampling_seeds']:
        selected = ROOT / row['assembled_candidate']
        assembly = read(selected / 'ASSEMBLY.json')
        audit = read(ROOT / row['audit'])
        assert audit['passed_hard_checks'] and audit['complete_train_test_audit']
        assert audit['canonical_train_test_overlap'] == 0
        assert audit['full_chain_train_test_overlap'] == 0
        hashes = []
        for split, expected_nodes, expected_chains in [('train',3752,12000),('test',800,2400)]:
            source = assembly['sources'][split]
            for saved_pin in source['files']:
                original = Path(saved_pin['path'])
                copied = selected / split / original.name
                assert pin(original)['sha256'] == saved_pin['sha256'] == pin(copied)['sha256'], copied
            sampler = selected / split / 'sampler_source.py'
            digest = pin(sampler)['sha256']
            assert digest == source['sampler_source']['sha256']
            assert digest == pin(Path(source['sampler_source']['path']))['sha256']
            assert digest == pin(ROOT / 'sample_compact_v68_snapshot.py')['sha256']
            hashes.append(digest)
            result = audit[split]
            assert result['counts']['nodes'] == result['counts']['used_nodes'] == expected_nodes
            assert result['counts']['sessions'] == expected_chains
            assert max(abs(v) for v in result['six_nonidentity_relative_deviation'].values()) <= 0.1
            assert result['soft_targets']['four_use_edge_fraction'] <= 0.005
            sampling = read(selected / split / 'sampling.json')
            assert sampling['complete'] and sampling['start_camera_quota_met']
            assert sampling['start_camera_counts'] == sampling['start_camera_quota']
            assert sampling['history_axis_decay'] == 0.2
            assert sampling['cap2_attempts_before_cap3'] == 12
            assert sampling['nonidentity_upper_slack'] == 0.025
        assert len(set(hashes)) == 1
        verification.append({'candidate': row['assembled_candidate'], 'audit': pin(ROOT / row['audit']),
                             'assembly': pin(selected / 'ASSEMBLY.json'), 'passed': True,
                             'selected_files_byte_identical_to_audited_originals': True,
                             'train_test_sampler_sha256': hashes[0]})

    old_inputs = read(V5 / 'INPUTS_AND_METHODS.json')
    runtime = []
    for old in old_inputs['runtime_source_pins']:
        current = pin(Path(old['path']))
        current['matches_v5_catalog_capture'] = current['sha256'] == old['sha256']
        runtime.append(current)
    assert all(p['matches_v5_catalog_capture'] for p in runtime), 'Runtime sources changed; inspect before finalizing.'
    code_paths = [ROOT / p for p in ['build_compact.py','prune_head_contexts.py','run_sampling.py',
        'sample_compact_v68_snapshot.py','audit_compact.py','package_selection.py',
        'report_selection.py','finalize_selection.py','graph_n/builder_snapshot.py',
        'graph_n/BUILD_CODE.json','graph_t/builder_snapshot.py','graph_t/builder_identity.json']]
    input_paths = [ROOT / p for p in ['graph_n/train/nodes.json','graph_n/train/edges.json',
        'graph_n/train/metrics.json','graph_t/test/nodes.json','graph_t/test/edges.json',
        'graph_t/test/metrics.json','graph_l_fixed/train/nodes.json','graph_l_fixed/train/edges.json',
        'graph_l_fixed/train/metrics.json']]
    # Preserve the inherited helper/catalog dependency pins, but do not relabel old checks as new checks.
    write(ROOT / 'INPUTS_AND_METHODS.json', {
        'generated_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'offline manifests only',
        'selection': spec, 'runtime_source_pins': runtime,
        'catalog_capture_provenance': pin(V5 / 'INPUTS_AND_METHODS.json'),
        'catalog_rebuilt_this_finalization': False,
        'inherited_code_and_input_snapshots': old_inputs['code_and_input_snapshots'],
        'current_code_pins': [pin(p) for p in code_paths],
        'graph_input_pins': [pin(p) for p in input_paths],
        'construction': {'train': 'prune_head_contexts.py default per-family=2/action-count=2 on saved graph_l_fixed; final graph_n',
                         'test': 'graph_t/builder_snapshot.py (HERE adjusted for snapshot location), seed and flags in builder_identity.json; use saved test split',
                         'builder_default_train_is_not_selected_train': True},
        'resampling': {'working_directory': str(ROOT), 'interpreter': 'C:/ProgramData/anaconda3/python.exe',
            'train': '-B run_sampling.py --graph graph_n --output reproduce_train_seed1 --split train --sampler v68 --seed 2026102261 --attempts 240 --history-decay 0.2 --upper-slack 0.025 --cap2-attempts 12 --tail-fallback-after 120',
            'test': '-B run_sampling.py --graph graph_t --output reproduce_test_seed1 --split test --sampler v68 --seed 2026102261 --attempts 240 --history-decay 0.2 --upper-slack 0.025 --cap2-attempts 12 --tail-fallback-after 120',
            'test_seed_note': 'Runner adds one to supplied base seed for test. Other seed bases are 2026102281 and 2026102301.',
            'outputs_must_have_fresh_names': True},
        'verification': verification})
    write(ROOT / 'delivery_verification.json', {
        'passed': True, 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'selected_copy_and_audit_bindings': verification,
        'runtime_source_pins_unchanged_since_v5': True,
        'scope': 'artifact integrity and completed independent offline audit checks; no visual/render check',
        'documentation_check': 'documentation_result_sync.json'})

    marker = '## 本轮收口结果'
    goal = (ROOT / 'GOAL.md').read_text(encoding='utf-8')
    if marker not in goal:
        goal += '\n' + marker + '\n\n已完成离线优化并提前收口：训练3752、测试800，选定selected_seed1，另两种子验证稳定性。21镜头起点配额及合法部位条件分布已改善；全部既定硬要求通过。继续压缩会增加边复用压力，当前保留该版本。详细取舍及未执行的媒体阶段见REPORT.md。\n'
        (ROOT / 'GOAL.md').write_text(goal, encoding='utf-8')
    files = []
    for name in ['GOAL.md','RULES.json','README.md','REPORT.md','FINAL_SELECTION.json','CURRENT_CANDIDATE.json',
                 'comparison.json','sampling_stability.json','INPUTS_AND_METHODS.json','delivery_verification.json',
                 'ITERATIONS.md','documentation_result_sync.json']:
        p = ROOT / name
        if p.exists(): files.append(p)
    for row in spec['sampling_seeds']:
        files.append(ROOT / row['audit'])
        files.extend(p for p in (ROOT / row['assembled_candidate']).rglob('*') if p.is_file())
    write(ROOT / 'DELIVERY_MANIFEST.json', {'status': spec['status'],
        'scope': 'selected delivery and evidence; unselected experiment files intentionally excluded',
        'self_hash_excluded': True, 'files': [pin(p) for p in files]})
    print(json.dumps({'passed': True, 'selected_seeds': len(verification), 'manifest_files': len(files)}))

if __name__ == '__main__':
    main()
