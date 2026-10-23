"""Site-bound manual exclusions for the private pair review worker.

Install after the camera-check adapter. Geometry/report stamps retain their
existing meaning; a user's exclusions are bound only to map and site ID.
"""
import copy
from pathlib import Path

VERSION = 1
FIELD = 'manual_site_intent'
SCHEMA = 'pair_review_manual_site_intent_v1'
KEYS = ('action_id', 'camera_id', 'aspect')


def identity(site):
    return {key: site.get(key) for key in ('site_id', 'map')}


def exclusions(rows):
    if not isinstance(rows, list):
        raise ValueError('人工组合清单格式无效。')
    result, seen = [], set()
    for row in rows:
        if (not isinstance(row, dict) or row.get('decision') not in ('allowed', 'excluded')
                or any(not isinstance(row.get(key), str) or not row[key] for key in KEYS)):
            raise ValueError('人工组合清单格式无效。')
        key = tuple(row[k] for k in KEYS)
        if key in seen:
            raise ValueError('人工组合清单包含重复组合。')
        seen.add(key)
        if row['decision'] == 'excluded':
            result.append(copy.deepcopy(row))
    return result


def intent(site, rows):
    return {'schema': SCHEMA, **identity(site), 'excluded_combinations': exclusions(rows)}


def saved_intent(site):
    """An explicit empty snapshot is authoritative, including old saved files."""
    record = site.get(FIELD)
    if record is not None:
        if (not isinstance(record, dict) or record.get('schema') != SCHEMA
                or identity(record) != identity(site)):
            raise ValueError('人工排除清单与拍摄点不一致。')
        return intent(site, record.get('excluded_combinations'))
    rows = site.get('allowed_combinations')
    if rows is None:
        rows = site.get('imported_excluded_combinations', [])
    return intent(site, rows)


def install(current):
    w = current['worker']
    if getattr(w, '_pair_site_intent_version', None) == VERSION:
        return current
    original = {name: getattr(w, name) for name in
                ('stamp', 'state', 'save_site', 'load_site', 'start_check')}

    def ensure(site):
        record = saved_intent(site)
        site[FIELD] = copy.deepcopy(record)
        return record

    def require_identity(request, site):
        if (request.get('decision_site_id') != site.get('site_id')
                or request.get('decision_map') != site.get('map')):
            raise ValueError('人工排除清单属于其他拍摄点，请刷新当前拍摄点。')

    def stamp():
        d = w.live()
        # The production adapter used to refresh exclusion stamps and erase old
        # decisions from inside stamp(). Keep it inert in this private worker.
        previous = d.pop('migrated_exclusion_intent', None)
        try:
            return original['stamp']()
        finally:
            if previous is not None:
                d['migrated_exclusion_intent'] = previous

    def state():
        d = w.synchronize()
        record = ensure(d['site']) if d.get('site') else None
        result = original['state']()
        if record is not None and identity(result) == identity(record):
            excluded = copy.deepcopy(record['excluded_combinations'])
            excluded_keys = {tuple(row[k] for k in KEYS) for row in excluded}
            allowed = [row for row in result.get('allowed_combinations', [])
                       if row.get('decision') == 'allowed'
                       and tuple(row.get(k) for k in KEYS) not in excluded_keys]
            result['allowed_combinations'] = allowed + excluded
            result[FIELD] = copy.deepcopy(record)
        return result

    def save_site(request):
        d = w.require_site()
        site = d['site']
        require_identity(request, site)
        explicit = 'allowed_combinations' in request
        previous = ensure(site)
        selected = intent(site, request['allowed_combinations']) if explicit else previous
        current_stamp = w.stamp()
        bound_stamp = (request.get('decisions_stamp') if explicit or 'issue_reviews' in request
                       else site.get('decisions_stamp'))
        fresh = bound_stamp == current_stamp and w.input_status()['valid']
        # Independent exclusions do not rebind an old issue review or old pass.
        if request.get('issue_reviews') and not fresh:
            raise ValueError('问题审查对应的点位或场景已改变，请刷新后重新确认。')
        adapted = copy.deepcopy(request)
        if not fresh:
            for key in ('allowed_combinations', 'issue_reviews', 'decisions_stamp'):
                adapted.pop(key, None)
        backup = copy.deepcopy(site)
        site[FIELD] = copy.deepcopy(selected)
        try:
            path = original['save_site'](adapted)
        except Exception:
            d['site'] = backup
            raise
        site = d['site']
        site[FIELD] = copy.deepcopy(selected)
        excluded = copy.deepcopy(selected['excluded_combinations'])
        keys = {tuple(row[k] for k in KEYS) for row in excluded}
        allowed = [copy.deepcopy(row) for row in site.get('allowed_combinations', [])
                   if fresh and row.get('decision') == 'allowed'
                   and tuple(row.get(k) for k in KEYS) not in keys]
        site['allowed_combinations'] = allowed + excluded
        if not fresh:
            site['issue_reviews'] = {}
        # Legacy save owns appearance/report serialization. Add the independent
        # intent to that exact record without rebuilding its other fields.
        record = w.read(path)
        record['site'] = copy.deepcopy(site)
        w.write(Path(path), record)
        return path

    def load_site(request):
        sid = request['site_id']
        path = (w.RUN / 'sites' / (sid + '.json')).resolve()
        if path.parent != (w.RUN / 'sites').resolve():
            raise ValueError('无效拍摄点编号。')
        saved = w.read(path)['site']
        selected = saved_intent(saved)
        result = original['load_site'](request)
        d = w.live()
        if identity(d['site']) != identity(selected):
            raise ValueError('载入的人工排除清单与拍摄点不一致。')
        d['site'][FIELD] = copy.deepcopy(selected)
        # Override the legacy imported-row union, especially after an explicit
        # unexclude-all. Historical allowed rows keep their original stamp.
        rows = [row for row in d['site'].get('allowed_combinations', [])
                if row.get('decision') == 'allowed']
        d['site']['allowed_combinations'] = rows + copy.deepcopy(selected['excluded_combinations'])
        return result

    def start_check(request, all_shots=False):
        d = w.require_site()
        require_identity(request, d['site'])
        adapted = copy.deepcopy(request)
        supplied = request.get('excluded_combinations', ensure(d['site'])['excluded_combinations'])
        if not isinstance(supplied, list) or any(not isinstance(row, dict) for row in supplied):
            raise ValueError('人工组合清单格式无效。')
        rows = [dict(row, decision='excluded') for row in supplied]
        exclusions(rows)  # Validate before any check cancellation/mutation.
        adapted['excluded_combinations'] = rows
        # Only exclusions get this bridge past the old stamp-based guard.
        # Job/report stamps are still produced by the unmodified worker.
        adapted['decisions_stamp'] = w.stamp()
        return original['start_check'](adapted, all_shots)

    w.stamp, w.state = stamp, state
    w.save_site, w.load_site, w.start_check = save_site, load_site, start_check
    w._pair_site_intent_version = VERSION
    return current
