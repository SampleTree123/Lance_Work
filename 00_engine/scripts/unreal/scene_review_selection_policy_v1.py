"""Current shooting choices over retained source libraries and historical saves."""
import hashlib
import json

REVISION = 'scene_review_20261020_v2'
RETIRED_MOTION_IDS = frozenset({'MOTION_CAND_007'})  # 四周张望


def filter_mode(data):
    keep = lambda row: row.get('motion_id', row.get('id')) not in RETIRED_MOTION_IDS
    geometry = dict(data['geometry'])
    geometry['actions'] = [r for r in geometry['actions'] if keep(r)]
    geometry['shots'] = [r for r in geometry['shots'] if keep(r)]
    geometry['input_fingerprint'] = hashlib.sha256(json.dumps(
        [data['geometry']['input_fingerprint'], REVISION, sorted(RETIRED_MOTION_IDS)],
        sort_keys=True).encode('utf-8')).hexdigest()
    catalog = dict(data['catalog'])
    catalog['actions'] = [r for r in catalog['actions'] if keep(r)]
    shots = {k: v for k, v in data['shots'].items() if keep(v)}
    frames = {k: v for k, v in data['frames'].items() if k in shots}
    policy = {'revision':REVISION, 'retired_motion_ids':sorted(RETIRED_MOTION_IDS),
              'active_actions':len(geometry['actions']), 'active_shots':len(shots),
              'source_library_modified':False}
    geometry['review_selection_policy'] = policy
    catalog['review_selection_policy'] = policy
    return dict(data, geometry=geometry, catalog=catalog, shots=shots, frames=frames,
                selection_policy=policy)


def install(runtime):
    if getattr(runtime, '_review_selection_policy', None) == REVISION:
        return
    original = runtime.load_mode
    def load_mode(*args, **kwargs):
        return filter_mode(original(*args, **kwargs))
    runtime.load_mode = load_mode
    runtime._review_selection_policy = REVISION


def install_worker(current):
    w = current['worker']
    if getattr(w, '_review_selection_catalog', None) == REVISION:
        return current
    original = w.catalog
    def catalog():
        result = dict(original())
        result['matrix'] = {'motions':len(result['motions']),
                            'cameras':len(result['cameras']), 'aspects':2,
                            'combinations':len(w.live()['local']['shots'])}
        result['review_selection_policy'] = {
            'revision':REVISION, 'retired_motion_ids':sorted(RETIRED_MOTION_IDS)}
        return result
    w.catalog = catalog
    w._review_selection_catalog = REVISION
    return current
