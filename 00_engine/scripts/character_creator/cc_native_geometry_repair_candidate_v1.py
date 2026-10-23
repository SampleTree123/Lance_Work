"""Offline candidate repair using archived photo geometry; never operates CC/UE.

The local jaw band is a candidate requiring visual review. Full-photo-face,
upper-head anchors, Average body and all points outside that band stay fixed.
"""
from collections import deque
import argparse
import json
from pathlib import Path

import numpy as np

from cc_headshot_geometry_solver_v1 import file_record, read_json, verify_record, points


def adjacency_from_faces(count, faces):
    adjacency = [set() for _ in range(count)]
    for polygon in faces:
        ids = [int(v) for v, _ in polygon]
        if len(ids) < 3 or any(v < 0 or v >= count for v in ids):
            raise ValueError('Invalid Body topology')
        for u, v in zip(ids, ids[1:] + ids[:1]):
            adjacency[u].add(v)
            adjacency[v].add(u)
    return adjacency


def repair_target(source, old_target, weights, head, faces, lash_indices,
                  jaw_seed_indices, protected_indices, rings=6):
    """Relieve a bounded connector band toward photo source; preserve anchors.

    Seeds must be the non-full-face endpoints of audited jaw seam edges. They
    receive distance 1; the photo-face boundary is distance 0. Propagation
    cannot enter photo-face, protected upper scalp, outside-head or lash sets.
    """
    source = points(source, len(source), 'archived photo source')
    count = len(source)
    old = points(old_target, count, 'old desired target')
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (count,) or not np.isfinite(weights).all():
        raise ValueError('Invalid photo weights')
    if not isinstance(rings, int) or isinstance(rings, bool) or not 1 <= rings <= 12:
        raise ValueError('rings must be 1..12')
    def index_set(values, name):
        array = np.asarray(values)
        if array.ndim != 1 or array.dtype.kind not in 'iu' or not len(array):
            raise ValueError('Invalid ' + name)
        values = set(map(int, array))
        if len(values) != len(array) or min(values) < 0 or max(values) >= count:
            raise ValueError('Invalid ' + name)
        return values
    head = index_set(head, 'head indices')
    lash = index_set(lash_indices, 'lash indices')
    seeds = index_set(jaw_seed_indices, 'jaw seeds')
    protected = index_set(protected_indices, 'protected anchors')
    full = set(np.flatnonzero(weights >= .99)) & head
    allowed = head - lash - full - protected
    adjacency = adjacency_from_faces(count, faces)
    if not seeds <= allowed or any(not (adjacency[i] & full) for i in seeds):
        raise ValueError('Jaw seed must be unprotected head skin adjacent to full photo face')
    distance = np.full(count, rings + 1, dtype=int)
    queue = deque(sorted(seeds))
    distance[list(seeds)] = 1
    while queue:
        i = queue.popleft()
        if distance[i] >= rings:
            continue
        for j in sorted(adjacency[i] & allowed):
            if distance[j] > distance[i] + 1:
                distance[j] = distance[i] + 1
                queue.append(j)
    band = np.flatnonzero(distance <= rings)
    t = distance[band] / (rings + 1)
    gain = 1 - t * t * (3 - 2 * t)
    result = old.copy()
    result[band] += gain[:, None] * (source[band] - old[band])
    result[sorted(lash)] = source[sorted(lash)]
    return result, band, distance


def build_candidate(attempt_dir, output_dir, rings=6):
    """Bind archive inputs by their original SHA records and emit a new target."""
    from cc_compare_headshot_geometry_v1 import read_obj, head_ids
    attempt = Path(attempt_dir).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Refusing existing candidate output')
    geometry_report = read_json(attempt / '06_geometry_target/geometry_report.json')
    array_record = geometry_report['target_geometry']
    verify_record(array_record)
    template = attempt / '03_capture/before_body.obj'
    world_path = attempt / '03_capture/before_world_mesh.json'
    expected = {Path(r['path']).resolve(): r for r in geometry_report['inputs']}
    for path in (template, world_path):
        if path.resolve() not in expected:
            raise ValueError('Archive lacks source provenance')
        verify_record(expected[path.resolve()])
    source_capture = read_json(world_path)
    if source_capture.get('working_subdivision_level') != 0 or source_capture.get('world_target_eligible') is not True:
        raise ValueError('Archive source is not verified SubD0')
    body, uv, faces = read_obj(template)
    head = head_ids()
    policy = read_json(Path(__file__).with_name('cc_base_assembly_geometry_policy_v2.json'))
    lash = np.asarray(policy['policies']['CCAPP_EYELASHES_284c3a142668']['indices'], dtype=int)
    # Native topology membership only; the assembly displacement allowance is
    # deliberately not consumed by this repair.
    if len(lash) != 704 or not np.array_equal(lash, np.arange(13411, 14115)):
        raise ValueError('Unexpected native lash topology')
    verify_record(geometry_report['reference_config'])
    references = read_json(geometry_report['reference_config']['path'])
    verify_record(references['shared']['head_partition'])
    verify_record(references['shared']['operator_topology_obj'])
    _, ref_uv, ref_faces = read_obj(references['shared']['operator_topology_obj']['path'])
    if faces != ref_faces or not np.array_equal(uv, ref_uv):
        raise ValueError('Body topology/UV differs from locked operator')
    with np.load(array_record['path'], allow_pickle=False) as arrays:
        source = arrays['source_world'].copy()
        old = arrays['desired_world'].copy()
        weights = arrays['weights'].copy()
    if not np.array_equal(source, np.asarray(source_capture['vertices'], dtype=float)):
        raise ValueError('Archived photo source does not match verified capture')
    adjacency = adjacency_from_faces(len(source), faces)
    full = head[weights[head] >= .99]
    # This only selects the lower disconnected seam component for a candidate;
    # it is not a new globally accepted anatomical partition.
    lower_cut = float((source[full, 2].min() + source[full, 2].max()) / 2)
    full_set = set(map(int, full))
    lash_set = set(map(int, lash))
    head_set = set(map(int, head))
    seeds = sorted({j for i in full if source[i, 2] < lower_cut
                    for j in adjacency[i] if j in head_set and j not in lash_set
                    and weights[j] == 0 and source[j, 2] < lower_cut})
    protected = head[source[head, 2] >= source[full, 2].max()]
    desired, band, distance = repair_target(source, old, weights, head, faces, lash,
                                           seeds, protected, rings)
    edges = np.asarray([(i, j) for i in range(len(source)) for j in adjacency[i] if i < j])
    seed_set = set(seeds)
    seam_edges = np.asarray([(i, j) for i in full_set for j in adjacency[i] if j in seed_set])
    affected = np.unique(np.concatenate([band, lash]))
    outside = np.setdiff1d(np.arange(len(source)), affected)
    def max_mm(a, b, ids):
        return float(np.linalg.norm(a[ids] - b[ids], axis=1).max() * 10)
    def jump(a, selected):
        delta = a - source
        return float(np.linalg.norm(delta[selected[:, 0]] - delta[selected[:, 1]], axis=1).max() * 10)
    report = {'schema_version': 1, 'status': 'offline_candidate_requires_fresh_CC_calibration_and_visual_review',
              'implementation': file_record(__file__), 'archive_geometry_report': file_record(attempt / '06_geometry_target/geometry_report.json'),
              'inputs': [array_record, expected[template], expected[world_path], geometry_report['reference_config'],
                         references['shared']['head_partition'], references['shared']['operator_topology_obj'],
                         file_record(Path(__file__).with_name('cc_base_assembly_geometry_policy_v2.json'))],
              'rings': rings, 'jaw_seed_indices': seeds, 'jaw_band_vertices': len(band),
              'protected_upper_head_vertices': len(protected), 'lower_seam_cut_z_cm': lower_cut,
              'photo_lash_old_error_max_mm': max_mm(old, source, lash),
              'photo_lash_candidate_error_max_mm': max_mm(desired, source, lash),
              'fullface_change_from_old_max_mm': max_mm(desired, old, full),
              'upper_head_change_from_old_max_mm': max_mm(desired, old, protected),
              'outside_repair_change_from_old_max_mm': max_mm(desired, old, outside),
              'jaw_seam_displacement_jump_old_mm': jump(old, seam_edges),
              'jaw_seam_displacement_jump_candidate_mm': jump(desired, seam_edges),
              'skin_edges_displacement_jump_old_mm': jump(old, edges[edges[:, 1] < 13411]),
              'skin_edges_displacement_jump_candidate_mm': jump(desired, edges[edges[:, 1] < 13411]),
              'limitations': ['Lower seam and six-ring width require representative visual confirmation.',
                              'Unchanged upper-head anchors are geometric; no universal anatomical mask is claimed.',
                              'No CC application, baking, export, morph or visual acceptance is implied.']}
    output.mkdir(parents=True)
    np.savez_compressed(output / 'candidate_desired_world.npz', desired_world=desired,
                        archived_photo_source=source, old_desired_world=old, weights=weights,
                        head_indices=head, lash_indices=lash, jaw_seed_indices=np.asarray(seeds),
                        jaw_band_indices=band, protected_upper_head_indices=protected,
                        jaw_distance=distance)
    report['candidate_arrays'] = file_record(output / 'candidate_desired_world.npz')
    (output / 'candidate_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-attempt', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--rings', type=int, default=6)
    args = parser.parse_args()
    print(json.dumps(build_candidate(args.source_attempt, args.output, args.rings), indent=2))
