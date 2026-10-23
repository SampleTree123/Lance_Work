"""Independent, read-only audit of aspect reassignment against immutable v6.

Candidate train/test folders use nodes.json, edges.json, sessions.jsonl.
Origin fields original_node_id/original_session_id are optional: canonical state
without aspect and unchanged session id provide independent fallback mappings.
All output is restricted to this audit_agent directory. No UE imports or writes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUTPUTS = HERE.parents[1]
BASELINE = OUTPUTS / 'dataset_compact_graph_20261022_v6/selected_seed1'
RULES_SOURCE = OUTPUTS / 'dataset_balanced_graph_20261022_v5/audit_candidate.py'
CAMERA_PLAN = OUTPUTS / 'production_workflow_20261017_v1/camera_library/production10/camera_plan.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sessions(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def token(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def load_rules():
    spec = importlib.util.spec_from_file_location('_independent_v5_aspect_rules', RULES_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Rules()


def without_aspect(state):
    return {k: v for k, v in state.items() if k != 'aspect'}


def audit(candidate, baseline=BASELINE, copies=1, require_render_requests=False):
    candidate, baseline = Path(candidate).resolve(), Path(baseline).resolve()
    rules = load_rules()
    camera_plan = read(CAMERA_PLAN)
    shots = {s['shot_id']: s for s in camera_plan['shots']}
    errors, counts = [], Counter()

    def error(kind, detail):
        counts[kind] += 1
        if len(errors) < 100:
            errors.append({'kind': kind, 'detail': detail})

    report = {'schema': 'independent_dual_aspect_preservation_audit_v1',
              'candidate': str(candidate), 'immutable_baseline': str(baseline),
              'expected_copies_per_original_session': copies,
              'scope': 'Saved offline manifests only; no media existence or UE acceptance',
              'inputs': [pin(__file__), pin(RULES_SOURCE), pin(CAMERA_PLAN)], 'splits': {}}
    split_keys, split_chains = {}, {}
    for split in ('train', 'test'):
        root, base = candidate / split, baseline / split
        for folder in (root, base):
            report['inputs'] += [pin(folder / name) for name in ('nodes.json', 'edges.json', 'sessions.jsonl')]
        oldrows, rows = read(base / 'nodes.json'), read(root / 'nodes.json')
        old = {r['id']: r for r in oldrows}
        oldstate = defaultdict(list)
        for row in oldrows:
            oldstate[token(without_aspect(row['state']))].append(row['id'])
        states, origin, canonical = {}, {}, {}
        for row in rows:
            nid, state = row['id'], row['state']
            if nid in states:
                error('duplicate_node_id', [split, nid])
            states[nid] = state
            matches = oldstate[token(without_aspect(state))]
            if len(matches) != 1:
                error('nonaspect_state_has_no_unique_original', [split, nid, matches])
                continue
            origin[nid] = matches[0]
            if 'original_node_id' in row and row['original_node_id'] != matches[0]:
                error('declared_original_node_mismatch', [split, nid])
            try:
                invalid = rules.valid_state(state)
                if invalid:
                    error('invalid_formal_state', [split, nid, invalid])
                canonical[nid] = token(rules.canonical(state))
            except Exception as exc:
                error('invalid_state_exception', [split, nid, str(exc)])
        if len(set(canonical.values())) != len(canonical):
            error('duplicate_actual_render_state', split)
        # Canonical comparison normalizes actual wardrobe state; removing the
        # aspect context makes cross-split leakage independent of framing.
        split_keys[split] = {token((lambda c: (c[0], *c[2:]))(rules.canonical(s))) for s in states.values()}
        oldedges = {token(e): e for e in read(base / 'edges.json')}
        edges = read(root / 'edges.json')
        edge_map = {}
        for edge in edges:
            u, v = edge['source'], edge['target']
            if u not in states or v not in states:
                error('dangling_graph_edge', [split, u, v])
                continue
            if (u, v) in edge_map:
                error('duplicate_graph_edge', [split, u, v])
            edge_map[u, v] = edge
            try:
                actual = rules.edge(states[u], states[v])
                if any(edge.get(k) != actual.get(k) for k in ('axis', 'mode', 'slot')):
                    error('graph_edge_semantics_mismatch', [split, u, v])
                original_edge = {**edge, 'source': origin[u], 'target': origin[v]}
                if token(original_edge) not in oldedges:
                    # Provenance additions do not change the original edge.
                    original_edge = {k: original_edge[k] for k in ('source', 'target', 'axis', 'mode', 'slot') if k in original_edge}
                    if token(original_edge) not in oldedges:
                        error('invented_nonaspect_graph_edge', [split, u, v])
            except Exception as exc:
                error('invalid_graph_edge', [split, u, v, str(exc)])
        oldsessions = sessions(base / 'sessions.jsonl')
        original_sessions = {s['id']: s for s in oldsessions}
        current = sessions(root / 'sessions.jsonl')
        seen_ids, seen_original_aspect = set(), set()
        session_counts, aspect_counts, kindlength = Counter(), Counter(), Counter()
        edgeuse, nonaspect_edgeuse, used, structures = Counter(), Counter(), set(), set()
        semantic_chains = set()
        for session in current:
            sid = session['id']
            if sid in seen_ids:
                error('duplicate_session_id', [split, sid])
            seen_ids.add(sid)
            original_id = session.get('original_session_id', session.get('source_session_id', sid))
            if original_id not in original_sessions:
                error('missing_original_session', [split, sid, original_id])
                continue
            original = original_sessions[original_id]
            session_counts[original_id] += 1
            h, steps = session['history'], session['steps']
            if len(h) != session['length'] + 1 or len(steps) != session['length']:
                error('session_length_invalid', [split, sid])
            if any(n not in states for n in h):
                error('dangling_session_node', [split, sid])
                continue
            aspects = {states[n]['aspect'] for n in h}
            if len(aspects) != 1:
                error('mixed_aspect_session', [split, sid, sorted(aspects)])
            aspect = next(iter(aspects))
            if session.get('aspect', aspect) != aspect:
                error('declared_session_aspect_mismatch', [split, sid])
            if (original_id, aspect) in seen_original_aspect:
                error('duplicate_original_session_same_aspect', [split, sid])
            seen_original_aspect.add((original_id, aspect))
            aspect_counts[aspect] += 1
            kindlength[f"{aspect}:{session['kind']}:L{session['length']}"] += 1
            mapped_history = [origin.get(n) for n in h]
            mapped_steps = [{**st, 'source': origin.get(st['source']), 'target': origin.get(st['target'])} for st in steps]
            if mapped_history != original['history']:
                error('original_history_changed', [split, sid])
            if mapped_steps != original['steps']:
                error('original_steps_changed', [split, sid])
            for field in ('kind', 'length', 'fork_round'):
                if session.get(field) != original.get(field):
                    error('original_session_logic_changed', [split, sid, field])
            branch_rounds = []
            for index, st in enumerate(steps, 1):
                pos = st['source_position']
                if not isinstance(pos, int) or not 0 <= pos < index or h[pos] != st['source'] or h[index] != st['target']:
                    error('history_parent_not_fully_inherited', [split, sid, index])
                if pos != index - 1:
                    branch_rounds.append(index)
                pair = st['source'], st['target']
                if pair not in edge_map or any(st.get(k) != edge_map[pair].get(k) for k in ('axis', 'mode', 'slot')):
                    error('session_step_unregistered_or_mismatched', [split, sid, index])
                edgeuse[pair] += 1
                nonaspect_edgeuse[origin.get(pair[0]), origin.get(pair[1])] += 1
            wanted_branches = [] if session['kind'] == 'linear' else [session['fork_round']]
            if branch_rounds != wanted_branches:
                error('fork_logic_invalid', [split, sid, branch_rounds])
            used.update(h)
            structure = token({'history': mapped_history, 'steps': mapped_steps,
                               'kind': session['kind'], 'length': session['length'], 'fork_round': session['fork_round']})
            structures.add(structure)
            semantic_chains.add(token({'history': [rules.canonical({**states[n], 'aspect': 'landscape'}) for n in h],
                                       'source_positions': [st['source_position'] for st in steps],
                                       'axes': [st['axis'] for st in steps], 'modes': [st['mode'] for st in steps]}))
        missing = sorted(set(original_sessions) - set(session_counts))
        wrong_copies = {sid: n for sid, n in session_counts.items() if n != copies}
        if missing or wrong_copies:
            error('original_sessions_not_exactly_preserved', [split, missing[:10], dict(list(wrong_copies.items())[:10])])
        if used != set(states):
            error('unused_render_nodes', [split, len(set(states) - used)])
        if max(nonaspect_edgeuse.values(), default=0) > 4 * copies:
            error('original_edge_use_cap_exceeded', split)
        split_chains[split] = semantic_chains
        unique_base = len({token({'history': s['history'], 'steps': s['steps'], 'kind': s['kind'],
                                 'length': s['length'], 'fork_round': s['fork_round']}) for s in oldsessions})
        if len(structures) != unique_base:
            error('unique_structural_session_count_changed', [split, len(structures), unique_base])
        origin_aspects = defaultdict(set)
        for nid in used:
            origin_aspects[origin[nid]].add(states[nid]['aspect'])
        report['splits'][split] = {
            'original_nodes': len(old), 'actual_render_nodes': len(used),
            'canonical_actual_render_nodes': len(set(canonical.values())),
            'unique_nonaspect_states': len(origin_aspects),
            'nodes_duplicated_across_aspects': sum(len(a) == 2 for a in origin_aspects.values()),
            'additional_render_nodes_over_original': len(used) - len(old),
            'render_nodes_by_aspect': dict(Counter(states[n]['aspect'] for n in used)),
            'sessions': len(current), 'unique_original_sessions': len(session_counts),
            'unique_structural_sessions_ignoring_aspect': len(structures),
            'original_unique_structural_sessions': unique_base,
            'sessions_by_aspect': dict(aspect_counts), 'sessions_by_aspect_kind_length': dict(kindlength),
            'edit_occurrences': sum(edgeuse.values()), 'max_actual_edge_reuse': max(edgeuse.values(), default=0),
            'max_edge_reuse_ignoring_aspect': max(nonaspect_edgeuse.values(), default=0),
            'graph_edges': len(edges), 'used_graph_edges': len(edgeuse),
            'aspect_copies_count_as_new_structures': False}
        request_path = root / 'render_requests.json'
        request_check = {'present': request_path.exists(), 'required': require_render_requests,
                         'preset_dimensions_are_not_a_frozen_final_media_profile': True}
        if not request_path.exists():
            if require_render_requests:
                error('render_requests_missing', split)
        else:
            report['inputs'].append(pin(request_path))
            requests = read(request_path)
            requested = Counter()
            before = sum(counts.values())
            for request in requests:
                nid = request['node_id']
                requested[nid] += 1
                if nid not in used:
                    error('render_request_unknown_or_unused_node', [split, nid])
                    continue
                state = states[nid]
                if request.get('original_node_id') != origin[nid] or request.get('aspect') != state['aspect']:
                    error('render_request_identity_or_aspect_mismatch', [split, nid])
                if request.get('state') != state:
                    error('render_request_state_mismatch', [split, nid])
                binding = request.get('camera_binding', {})
                try:
                    if Path(binding['plan_path']).resolve() != CAMERA_PLAN.resolve():
                        error('render_request_camera_plan_path_mismatch', [split, nid])
                    shot = shots[binding['shot_id']]
                    for field in ('shot_id', 'motion_id', 'camera_id', 'orientation', 'width', 'height', 'trajectory_sha256'):
                        if binding.get(field) != shot[field]:
                            error('render_request_camera_binding_mismatch', [split, nid, field])
                    if (shot['motion_id'], shot['camera_id'], shot['orientation']) != (state['action'], state['camera'], state['aspect']):
                        error('render_request_camera_key_mismatch', [split, nid])
                except (KeyError, TypeError) as exc:
                    error('render_request_camera_binding_invalid', [split, nid, str(exc)])
            if set(requested) != used or any(n != 1 for n in requested.values()):
                error('render_requests_not_one_per_used_node', [split, len(requested), len(used)])
            request_check.update({'request_count': len(requests), 'unique_node_count': len(requested),
                                  'passed': before == sum(counts.values())})
        report['splits'][split]['render_request_check'] = request_check
    report['cross_split_overlap_ignoring_aspect'] = len(split_keys['train'] & split_keys['test'])
    if report['cross_split_overlap_ignoring_aspect']:
        error('cross_split_nonaspect_state_overlap', report['cross_split_overlap_ignoring_aspect'])
    report['cross_split_structural_chain_overlap_ignoring_aspect'] = len(split_chains['train'] & split_chains['test'])
    if report['cross_split_structural_chain_overlap_ignoring_aspect']:
        error('cross_split_nonaspect_chain_overlap', report['cross_split_structural_chain_overlap_ignoring_aspect'])
    report['error_counts'] = dict(counts)
    report['errors_first_100'] = errors
    report['passed'] = not counts
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', '--root', dest='candidate', type=Path, required=True)
    p.add_argument('--baseline', type=Path, default=BASELINE)
    p.add_argument('--copies', type=int, choices=(1, 2), default=1)
    p.add_argument('--require-render-requests', action='store_true')
    p.add_argument('--output', type=Path, default=HERE / 'audit_latest.json')
    a = p.parse_args()
    destination = a.output.resolve()
    if destination.parent != HERE or destination.suffix != '.json':
        raise ValueError('Audit output must be an audit_agent/*.json file')
    result = audit(a.candidate, a.baseline, a.copies, a.require_render_requests)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'errors': result['error_counts'],
                      'splits': result['splits'], 'output': str(destination)}, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
