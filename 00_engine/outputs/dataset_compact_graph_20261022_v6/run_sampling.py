"""Run the v6 sampler on a saved explicit legal graph, never invoke UE."""
from __future__ import annotations
import argparse
import hashlib
import inspect
import json
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dataset_local_support_20261021_v3'))
from resample_local import Domain, load_graph, read, write, save_graph
from sample_compact import sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', default='graph_c')
    parser.add_argument('--output', default='candidate_c_seed1')
    parser.add_argument('--seed', type=int, default=2026102261)
    parser.add_argument('--attempts', type=int, default=240)
    parser.add_argument('--sampler', choices=('current', 'v61', 'v62', 'v63', 'v64', 'v65', 'v66', 'v67', 'v68'), default='current')
    parser.add_argument('--split', choices=('all', 'train', 'test'), default='all')
    parser.add_argument('--history-decay', type=float)
    parser.add_argument('--upper-slack', type=float)
    parser.add_argument('--cap2-attempts', type=int)
    parser.add_argument('--identity-capacity-exponent', type=float)
    parser.add_argument('--tail-fallback-after', type=int)
    args = parser.parse_args()
    sampling_function = sample
    if args.sampler == 'v61':
        from sample_compact_v61_snapshot import sample as sampling_function
    elif args.sampler == 'v62':
        from sample_compact_v62_snapshot import sample as sampling_function
    elif args.sampler == 'v63':
        from sample_compact_v63_snapshot import sample as sampling_function
    elif args.sampler == 'v64':
        from sample_compact_v64_snapshot import sample as sampling_function
    elif args.sampler == 'v65':
        from sample_compact_v65_snapshot import sample as sampling_function
    elif args.sampler == 'v66':
        from sample_compact_v66_snapshot import sample as sampling_function
    elif args.sampler == 'v67':
        from sample_compact_v67_snapshot import sample as sampling_function
    elif args.sampler == 'v68':
        from sample_compact_v68_snapshot import sample as sampling_function
    overrides = {}
    if args.history_decay is not None:
        if args.sampler in ('v61', 'v62', 'v63'):
            raise ValueError('history-decay override requires the parameterized current sampler')
        overrides['history_decay'] = args.history_decay
    if args.upper_slack is not None:
        overrides['nonidentity_upper_slack'] = args.upper_slack
    if args.cap2_attempts is not None:
        overrides['cap2_attempts'] = args.cap2_attempts
    if args.identity_capacity_exponent is not None:
        if 'identity_capacity_exponent' not in inspect.signature(sampling_function).parameters:
            raise ValueError('identity-capacity override requires the v67 sampler')
        overrides['identity_capacity_exponent'] = args.identity_capacity_exponent
    if args.tail_fallback_after is not None:
        if 'tail_fallback_after' not in inspect.signature(sampling_function).parameters:
            raise ValueError('tail-fallback override requires the v68 sampler')
        overrides['tail_fallback_after'] = args.tail_fallback_after
    output_root = HERE / args.output
    if (output_root / 'SUMMARY.json').exists():
        raise FileExistsError(f'Preserve existing run; choose a new output name: {output_root}')
    output_root.mkdir(parents=True, exist_ok=True)
    sampler_source = HERE / (f'sample_compact_{args.sampler}_snapshot.py' if args.sampler != 'current' else 'sample_compact.py')
    source_hash = hashlib.sha256(sampler_source.read_bytes()).hexdigest()
    shutil.copyfile(sampler_source, output_root / 'sampler_source.py')
    write(output_root / 'SAMPLER_CODE.json', {'source': str(sampler_source),
                                            'saved_source': 'sampler_source.py',
                                            'sha256': source_hash,
                                            'sampler_selection': args.sampler,
                                            'parameter_overrides': overrides})
    domain, forbidden, summary = Domain(), set(), {}
    started = time.time()
    specs = [(split, total, j) for split, total, j in [('train', 12000, 0), ('test', 2400, 1)]
             if args.split == 'all' or split == args.split]
    for split, total, j in specs:
        source, target = HERE / args.graph / split, HERE / args.output / split
        graph = load_graph(source, domain, forbidden)
        construction = read(source / 'metrics.json').get('construction', {})
        sessions, sampling = sampling_function(graph, total, args.seed + j,
                                    max_attempts=args.attempts, progress_every=1000, **overrides)
        target.mkdir(parents=True, exist_ok=True)
        # Persist diagnostics even if zero sessions make old stats undefined.
        write(target / 'sampling.json', sampling)
        construction.update(sampling=sampling, sample_seed=args.seed + j,
                            source_graph=str(source.resolve()), sampler_selection=args.sampler,
                            sampler_source_sha256=source_hash)
        if sessions:
            metrics = save_graph(target, graph, sessions, construction)
        else:
            for name in ('nodes.json', 'edges.json'):
                shutil.copyfile(source / name, target / name)
            (target / 'sessions.jsonl').write_text('', encoding='utf-8')
            metrics = {'nodes': len(graph.nodes), 'sessions': 0,
                       'registered_edges': len(graph.edges),
                       'construction': construction, 'sampling_blocked': True}
            write(target / 'metrics.json', metrics)
        summary[split] = metrics
        forbidden.update(graph.keys)
        compact = {key: sampling.get(key) for key in (
            'complete', 'sampled_sessions', 'blocked_by', 'axis_counts', 'axis_reuse',
            'nonidentity_relative_deviation', 'edge_reuse_histogram',
            'four_use_edge_fraction', 'start_camera_quota_met',
            'start_camera_quota_deficits', 'single_piece_slot_actual',
            'single_piece_slot_source_conditioned_expectation',
            'single_piece_slot_relative_to_expectation',
            'conditional_wardrobe_mode_counts', 'unused_nodes', 'unused_start_nodes',
            'errors_and_retries', 'forced_coverage_job_count')}
        compact['core_targets'] = sampling.get('edited_attribute_target_coverage', {}).get('wardrobe_core')
        print('SAMPLED', split, json.dumps(compact, ensure_ascii=False), flush=True)
    summary['elapsed_seconds'] = time.time() - started
    summary['selected_splits'] = [split for split, _, _ in specs]
    write(HERE / args.output / 'SUMMARY.json', summary)
    complete = all(summary[split]['construction']['sampling'].get('complete') for split, _, _ in specs)
    print('FINISHED', 'complete' if complete else 'incomplete', summary['elapsed_seconds'], flush=True)
    return 0 if complete else 2


if __name__ == '__main__':
    raise SystemExit(main())
