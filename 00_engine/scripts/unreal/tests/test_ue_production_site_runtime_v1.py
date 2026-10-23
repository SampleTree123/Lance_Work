"""Private-module wiring and disk preservation without an Unreal session."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import ue_production_site_runtime_v1 as runtime


@pytest.fixture
def installed(monkeypatch, tmp_path):
    a = runtime.appearance
    monkeypatch.setattr(a, 'formal_runtime', lambda: None)
    choice = {'family_id': None, 'group_id': None, 'slot_choices': {}, 'optional_asset_ids': [],
              'shared_shoe_id': None, 'hair_id': None}
    source = runtime.motion_contract.pin(runtime.__file__)
    data = {'sources': {'wardrobe_registry': source},
            'identities': [{'id': 'F1', 'sex': 'female'}, {'id': 'M1', 'sex': 'male'}],
            'presets_by_sex': {s: [{'choice': choice}] for s in ('female', 'male')},
            'hairs_by_sex': {'female': [], 'male': []},
            'hair_colors': [{'id': 'original'}, {'id': 'blue'}],
            'faces': [{'sex': s, 'face_id': f, 'body_action_id': 'static'}
                      for s in ('female', 'male') for f in ('idle', 'smile', 'displeased', 'sad')]}
    monkeypatch.setattr(a, 'catalog', lambda: copy.deepcopy(data))
    monkeypatch.setattr(a.slots, 'validate_choice', lambda sex, c: {'normalized_choice': copy.deepcopy(c)})
    monkeypatch.setattr(runtime.motion_contract, 'load_contract', lambda: {'motions': [
        {'motion_id': 'walk', 'label_zh': '走路'}]})
    loads = []
    def mode(m):
        loads.append(m)
        return {'mode': m, 'geometry': {'shots': [{'shot_id': m}], 'actions': [], 'input_fingerprint': m},
                'catalog': {'actions': [{'motion_id': 'walk', 'clock': {'duration_seconds': 10 if m == 'production10' else 20}}],
                            'cameras': [{'camera_id': 'front', 'camera_label': '正面'}]},
                'shots': {m: {'shot_id': m}}, 'pins': [], 'source_pins': []}
    monkeypatch.setattr(runtime, 'load_mode', mode)
    events = []
    assembler = SimpleNamespace(invalidate_cache=lambda u: events.append('invalidate'))
    monkeypatch.setitem(sys.modules, 'ue_scene_site_appearance_v1', assembler)
    d = {'local': {'input_fingerprint': 'old'}, 'runtime_inputs': [], 'report': {'old': True},
         'site': {'site_id': 'point', 'map': '/Game/Scenes/A', 'position': {'x': 10, 'y': 20, 'z': 30},
                  'yaw': 17, 'custom_user_field': 'preserve'}, 'preview': {}, 'job': None}
    w = SimpleNamespace(RUN=tmp_path, u=SimpleNamespace())
    w.live = lambda: d
    w.geo = SimpleNamespace(canonical_sha=lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
    w.stamp = lambda: w.geo.canonical_sha({'input': d['local']['input_fingerprint'],
        'site': {k:(d.get('site') or {}).get(k) for k in ('site_id','map','position','yaw')}})
    w.state = lambda: {'review_stamp': w.stamp(), 'report': d.get('report')}
    w.catalog = lambda: {'sites': [], 'scenes': [], 'motions': [{'id': 'old'}], 'cameras': []}
    w.current_map = lambda: '/Game/Scenes/A'
    w.require_site = lambda: d
    w.pause_playback = lambda: events.append('pause')
    w.read = a.io.read
    def old_save(p):
        if 'allowed_combinations' in p:
            d['site']['allowed_combinations']=copy.deepcopy(p['allowed_combinations'])
        path = tmp_path / 'sites/point.json'
        a.io.write(path, {'site': copy.deepcopy(d['site']), 'report': d['report'],
                         'input_fingerprint':d['local']['input_fingerprint']})
        return str(path)
    def old_load(p):
        r = a.io.read(tmp_path / 'sites' / (p['site_id'] + '.json'))
        d['site'], d['report'] = r['site'], r.get('report')
    def old_restore():
        events.append('destroy')
        d.update(site=None, report=None, preview={})
    def dispatch(p):
        if p['action'] == 'save_site':
            w.save_site(p)
        elif p['action'] == 'load_site':
            w.load_site(p)
        elif p['action'] == 'restore':
            w.restore()
        return {'state': w.state()}
    w.save_site, w.load_site, w.restore = old_save, old_load, old_restore
    w.dispatch, w.play = dispatch, lambda p: None
    runtime.install(w)
    yield w, d, events, loads, data


def test_mode_switch_changes_stamp_clears_report_and_refuses_during_check(installed):
    w, d, events, loads, data = installed
    w.state()
    first = w.stamp()
    assert d['source_mode'] == 'production10'
    assert d['report'] is None
    d['report'] = {'stamp': first}
    w.dispatch({'action': 'check_all', 'source_mode': 'full'})
    assert d['source_mode'] == 'full' and d['report'] is None
    assert w.stamp() != first
    assert w.catalog()['motions'][0]['duration_seconds'] == 20
    d['job'] = {'status': 'running'}
    with pytest.raises(ValueError, match='检查进行中'):
        w.dispatch({'action': 'check_all', 'source_mode': 'production10'})
    assert d['source_mode'] == 'full'


def test_status_refresh_returns_full_comparison_catalog_without_changing_selection(installed):
    w, d, events, loads, data = installed
    from scene_site_hair_color_trials_v1 import catalog as trial_catalog
    w.state()
    before = copy.deepcopy(d['appearance_selection'])
    data['hair_colors'] = trial_catalog()
    # The primary adapter resets this context after a source reload while
    # retaining the live user's selection and actors.
    w._production_site_context = None
    runtime.install(w)
    reply = w.dispatch({'action': 'status'})
    colors = reply['catalog']['appearance_catalog']['hair_colors']
    assert [row['id'] for row in colors] == [row['id'] for row in trial_catalog()]
    assert len(colors) == 10 and not any(row.get('experimental') for row in colors)
    assert d['appearance_selection'] == before


def test_appearance_saved_separately_links_and_restores_without_changing_point(installed):
    w, d, events, loads, data = installed
    w.state()
    selected = copy.deepcopy(d['appearance_selection'])
    selected.update(hair_color='blue', face_id='smile')
    reply = w.dispatch({'action': 'save_appearance', 'name': '蓝发微笑', 'appearance_selection': selected})
    config_id = reply['state']['appearance_config_id']
    point_before = copy.deepcopy(d['site'])
    assert not (w.RUN / 'sites/point.json').exists()
    w.dispatch({'action': 'save_site', 'appearance_config_id': config_id})
    saved_bytes = (w.RUN / 'sites/point.json').read_bytes()
    record = json.loads(saved_bytes)
    assert record['site']['appearance_config_id'] == config_id
    assert record['site']['position'] == point_before['position']
    assert record['site']['custom_user_field'] == 'preserve'
    original = runtime.appearance.default_selection(data)
    w.dispatch({'action': 'set_appearance', 'appearance_selection': original})
    assert d['appearance_config_id'] is None
    w.dispatch({'action': 'load_site', 'site_id': 'point'})
    assert d['appearance_selection'] == selected
    assert d['appearance_config_id'] == config_id
    assert (w.RUN / 'sites/point.json').read_bytes() == saved_bytes
    assert d['report'] is None


def test_restore_clears_actor_cache_before_world_objects_are_destroyed(installed):
    w, d, events, loads, data = installed
    w.state()
    w.restore()
    assert events.index('invalidate') < events.index('destroy')


def install_ground_callbacks(w, events):
    def old_snap():
        events.append('collision_snap')
        return {'legacy': True}
    def old_check(job, action, sample):
        events.append(('body_check', sample['bones'], sample['ground_probes']))
        return 'body_checked'
    w.snap, w.check_action_sample = old_snap, old_check
    w.ray, w.sphere, w.check_shot_sample = object(), object(), object()
    preserved = (w.ray, w.sphere, w.check_shot_sample)
    w._production_site_context = None
    runtime.install(w)
    return old_snap, old_check, preserved


@pytest.mark.parametrize('site_id', ['site_98aac485de', 'site_235511f7b9', 'site_cbee266c51'])
def test_fixed_ground_snap_and_checks_share_current_height_without_scene_queries(installed, site_id):
    import ue_ground_height_follow_v1 as ground
    w, d, events, _, _ = installed
    originals = install_ground_callbacks(w, events)
    config = ground.FIXED_SITE_SUPPORT[site_id]
    d['site'] = {'site_id': site_id, 'map': config['map'], 'position': {'x': 123., 'y': -456., 'z': 789.}}
    before = copy.deepcopy(d['site'])
    hit = w.snap()
    assert hit['point'] == [123., -456., 789.]
    assert hit['normal'] == [0., 0., 1.]
    assert hit['support_policy'] == ground.FIXED_SUPPORT_VERSION
    assert 'collision_snap' not in events and d['site'] == before
    sample = {'bones': {'pelvis': [123., -456., 989.]}, 'ground_probes': [{'position': [123., -456., 789.]}]}
    job = {'site': copy.deepcopy(d['site']), 'scope': {'kind': 'current'}}
    assert w.check_action_sample(job, {'motion_id': 'jump'}, sample) == 'body_checked'
    assert events[-1] == ('body_check', sample['bones'], [])
    assert sample['ground_probes']  # Preserve the queued/source sample.
    assert job['scope']['ground_support']['ground_probe_policy'] == 'analytically_covered_infinite_xy'
    assert job['scope']['ground_support']['support_plane'] == hit['support_plane']
    assert (w.ray, w.sphere, w.check_shot_sample) == originals[2]
    # A changed context reinstalls from original callbacks, never old closures.
    w._production_site_context = None
    runtime.install(w)
    assert w._production_site_originals['snap'] is originals[0]
    assert w._production_site_originals['check_action_sample'] is originals[1]
    count = len(events)
    w.check_action_sample(job, {}, sample)
    assert len(events) == count + 1


def test_unconfigured_site_retains_original_snap_and_floor_probes(installed):
    w, d, events, _, _ = installed
    install_ground_callbacks(w, events)
    sample = {'bones': {'pelvis': [0., 0., 100.]}, 'ground_probes': [{'position': [0., 0., 0.]}]}
    job = {'site': d['site'], 'scope': {'kind': 'current'}}
    assert w.snap() == {'legacy': True}
    assert w.check_action_sample(job, {}, sample) == 'body_checked'
    assert events[-1] == ('body_check', sample['bones'], sample['ground_probes'])
    assert 'ground_support' not in job['scope']


def test_correction_publication_reinstalls_overlay_invalidates_cache_and_watches_pins(installed, monkeypatch):
    w, d, events, loads, _ = installed
    a = runtime.appearance
    helper, pointer, manifest, asset = [w.RUN / name for name in ('helper.py', 'active.json', 'correction.json', 'pink.uasset')]
    for path in (helper, pointer, manifest, asset):
        path.write_text('fixture', encoding='utf-8')
    monkeypatch.setattr(a, 'FORMAL_HELPER', helper)
    monkeypatch.setattr(a, 'FORMAL_POINTER', pointer)
    monkeypatch.setattr(a, 'FORMAL_CORRECTIONS', manifest)
    trial_runtime = w.RUN / 'trial_runtime.py'
    monkeypatch.setattr(a, 'FORMAL_COLOR_TRIAL_RUNTIME', trial_runtime)
    trial_shader = w.RUN / 'neutral_shader.uasset'
    monkeypatch.setattr(runtime, 'HAIR_TRIAL_SHADER', trial_shader)
    domain = SimpleNamespace(formal_path_overlay={'old': 'new'},
                             formal_correction_pins=[runtime.motion_contract.pin(manifest), runtime.motion_contract.pin(asset)])
    monkeypatch.setattr(a, 'formal_runtime', lambda: (None, domain))
    monkeypatch.setattr(runtime, 'load_formal_motion_runtime', lambda: None)
    # Catalog/source identity stays the same; only runtime asset binding changes.
    monkeypatch.setattr(a, 'validate_selection', lambda value, data=None: copy.deepcopy(value))
    runtime.install(w)
    w.state()
    assert d['asset_path_overlay'] == {'old': 'new'}
    assert all(pin in d['runtime_inputs'] for pin in domain.formal_correction_pins)
    invalidations = events.count('invalidate')
    runtime.install(w)
    assert events.count('invalidate') == invalidations
    manifest.write_text('updated correction manifest', encoding='utf-8')
    domain.formal_path_overlay = {'old': 'newer'}
    domain.formal_correction_pins[0] = runtime.motion_contract.pin(manifest)
    runtime.install(w)
    w.state()
    assert events.count('invalidate') == invalidations + 1
    assert d['asset_path_overlay'] == {'old': 'newer'}
    trial_runtime.write_text('# added after panel was open', encoding='utf-8')
    runtime.install(w)
    w.state()
    assert events.count('invalidate') == invalidations + 2
    assert runtime.motion_contract.pin(trial_runtime) in d['runtime_inputs']
    sources_before = copy.deepcopy(d['appearance_selection']['sources'])
    trial_shader.write_bytes(b'first saved neutral shader')
    runtime.install(w)
    w.state()
    assert events.count('invalidate') == invalidations + 3
    assert runtime.motion_contract.pin(trial_shader) in d['runtime_inputs']
    trial_shader.write_bytes(b'updated neutral shader')
    runtime.install(w)
    w.state()
    assert events.count('invalidate') == invalidations + 4
    assert runtime.motion_contract.pin(trial_shader) in d['runtime_inputs']
    assert d['appearance_selection']['sources'] == sources_before


def test_retired_exclusions_archived_valid_restrictions_carried_without_old_passes(installed):
    w,d,events,loads,data=installed
    w.state()
    rows=[{'action_id':'MOTION_CAND_018','camera_id':'front','aspect':'portrait','decision':'excluded'},
          {'action_id':'walk','camera_id':'front','aspect':'portrait','decision':'excluded'}]
    d['local']['shots']=[{'motion_id':'walk','camera_id':'front','orientation':'portrait'}]
    old_allowed={'action_id':'walk','camera_id':'side','aspect':'portrait','decision':'allowed'}
    d['site'].update(imported_excluded_combinations=rows,decisions_stamp='old-clock',
                     allowed_combinations=copy.deepcopy(rows)+[old_allowed],issue_reviews={'old':{'status':'acceptable','note':'保留'}})
    path=w.RUN/'sites/point.json'
    runtime.appearance.io.write(path,{'site':copy.deepcopy(d['site']),'report':{'stamp':'old-clock'}})
    original=path.read_bytes()
    w.load_site({'site_id':'point'})
    assert path.read_bytes()==original
    assert d['historical_site_review']['imported_excluded_combinations']==rows
    assert d['historical_site_review']['retired_motion_exclusions']==[rows[0]]
    assert d['pending_exclusion_suggestions']==[]
    assert d['pending_previous_allowed_combinations']==[old_allowed]
    assert d['site']['allowed_combinations']==[rows[1]]
    assert d['site']['decisions_stamp_kind']=='exclusion_intent_only'
    assert d['site']['decisions_stamp']==w.stamp()
    assert d['site']['issue_reviews']=={}
    assert d['report'] is None
    assert Path(d['historical_site_review']['archive']['path']).is_file()
    assert d['migrated_exclusion_intent']['old_allowed_promoted'] is False
    old_stamp=w.stamp()
    w.dispatch({'action':'check_all','source_mode':'full'})
    assert w.stamp()!=old_stamp
    assert d['site']['decisions_stamp']==w.stamp()
    assert d['site']['allowed_combinations']==[rows[1]]
    bound=d['site']['decisions_stamp']
    d['site']['position']['x']+=10
    assert w.stamp()!=bound
    assert d['site']['decisions_stamp']==bound


def test_four_accepted_face_choices_available_for_arbitrary_body(installed):
    w, d, events, loads, data = installed
    selected = runtime.appearance.default_selection(data)
    selected['face_id'] = 'sad'
    assert runtime.appearance.validate_selection(selected, data, body_action_id='MOTION_CAND_031') == selected
    assert {f['face_id'] for f in runtime.appearance.faces_for_action(data, 'female', 'MOTION_CAND_031')} == {
        'none', 'idle', 'smile', 'displeased', 'sad'}


def test_current_saved_restrictions_survive_input_change_but_explicit_removal_wins(installed):
    w,d,events,loads,data=installed
    w.state()
    excluded={'action_id':'walk','camera_id':'front','aspect':'portrait','decision':'excluded'}
    allowed={'action_id':'walk','camera_id':'side','aspect':'portrait','decision':'allowed'}
    d['local']['shots']=[{'motion_id':'walk','camera_id':c,'orientation':'portrait'} for c in ('front','side')]
    d['site'].update(review_runtime='production_site_runtime_v2',decisions_stamp_kind='explicit_current_user_choice',
                     allowed_combinations=[excluded,allowed],issue_reviews={'old':{'status':'acceptable'}})
    d['site']['decisions_stamp']=w.stamp()
    path=w.RUN/'sites/point.json'
    runtime.appearance.io.write(path,{'site':copy.deepcopy(d['site']),'report':{'stamp':w.stamp()},
        'input_fingerprint':d['local']['input_fingerprint']})
    original=path.read_bytes()
    w.load_site({'site_id':'point'})
    assert d['site']['allowed_combinations']==[excluded,allowed]
    assert path.read_bytes()==original
    w.dispatch({'action':'check_all','source_mode':'full'})
    assert d['site']['allowed_combinations']==[excluded]
    assert d['site']['issue_reviews']=={}
    assert d['site']['decisions_stamp_kind']=='exclusion_intent_only'
    assert d['report'] is None
    w.save_site({'allowed_combinations':[]})
    assert 'migrated_exclusion_intent' not in d
    w.dispatch({'action':'check_all','source_mode':'production10'})
    assert d['site']['allowed_combinations']==[]


def test_saved_user_override_precedes_older_imported_default(installed):
    w,d,events,loads,data=installed
    w.state()
    front={'action_id':'walk','camera_id':'front','aspect':'portrait','decision':'excluded'}
    side={'action_id':'walk','camera_id':'side','aspect':'portrait','decision':'excluded'}
    reenabled={**front,'decision':'allowed'}
    d['local']['shots']=[{'motion_id':'walk','camera_id':c,'orientation':'portrait'} for c in ('front','side')]
    d['site'].update(imported_excluded_combinations=[front,side],allowed_combinations=[reenabled,side])
    path=w.RUN/'sites/point.json'
    runtime.appearance.io.write(path,{'site':copy.deepcopy(d['site']),'report':None})
    original=path.read_bytes()
    w.load_site({'site_id':'point'})
    assert d['site']['allowed_combinations']==[side]
    assert d['pending_previous_allowed_combinations']==[reenabled]
    assert d['historical_site_review']['imported_excluded_combinations']==[front,side]
    assert d['migrated_exclusion_intent']['origins'][0]['origin']=='saved_allowed_combinations'
    assert path.read_bytes()==original


def test_formal_motion_publication_requires_explicit_reference_resave_evidence(monkeypatch, tmp_path):
    content = tmp_path / 'Content'
    output = tmp_path / 'runtime'
    output.mkdir()
    policy = {'motions': [{'motion_id': f'MOTION_{i:03d}'} for i in range(26)]}
    contract_path = tmp_path / 'policy.json'
    runtime.appearance.io.write(contract_path, policy)
    monkeypatch.setattr(runtime.motion_contract, 'CONTRACT', contract_path)
    monkeypatch.setattr(runtime.motion_contract, 'load_contract', lambda **kw: copy.deepcopy(policy))
    monkeypatch.setattr(runtime, 'CONTENT', content)
    monkeypatch.setattr(runtime, 'FORMAL_RUN', output)
    monkeypatch.setattr(runtime, 'MOTION_BEFORE', output / 'before.json')
    monkeypatch.setattr(runtime, 'MOTION_ACTIVE', output / 'active.json')
    variants = {}
    for entry in policy['motions']:
        for sex in ('female', 'male'):
            variant = {'shared_skeleton': '/Game/Characters/Skeleton.Shared', 'source_duration_seconds': 12}
            for kind in ('source', 'production10'):
                package = '/Game/Body/' + sex + '/' + entry['motion_id'] + '_' + kind
                path = content / (package.removeprefix('/Game/') + '.uasset')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'verified original bone and curve bytes')
                variant[kind] = {**runtime.motion_contract.pin(path), 'asset': package + '.' + package.rsplit('/', 1)[1]}
            receipt = output / (entry['motion_id'] + '_' + sex + '.json')
            runtime.appearance.io.write(receipt, {'numeric_all_frame_proof': 'fixture'})
            variant['receipt'] = runtime.motion_contract.pin(receipt)
            variants[(entry['motion_id'], sex)] = variant
    monkeypatch.setattr(runtime.motion_contract, 'receipt_variant', lambda entry, sex, **kw:
                        copy.deepcopy(variants[(entry['motion_id'], sex)]))
    runtime.capture_motion_before_relocation()
    formal_path = output / 'formal_asset_catalog.json'
    runtime.appearance.io.write(formal_path, {'schema': 'fixture_formal_catalog'})
    relocation = {'move_receipts': [], 'path_overlay': {}, 'relocated_packages': {}}
    loader = SimpleNamespace(load=lambda: copy.deepcopy(relocation))
    domain = SimpleNamespace(formal_runtime_source=runtime.motion_contract.pin(formal_path))
    monkeypatch.setattr(runtime.appearance, 'formal_runtime', lambda: (loader, domain))
    first = runtime.publish_formal_motion_runtime()
    assert first['variants'] == 52
    # Reference-only serialization changes still require an exact saved package
    # and its current SHA in a successful relocation receipt.
    changed = variants[('MOTION_000', 'female')]['source']
    Path(changed['path']).write_bytes(b'same tracks with relocated skeleton reference')
    with pytest.raises(ValueError, match='没有明确搬移'):
        runtime.publish_formal_motion_runtime()
    receipt_path = output / 'move_receipt.json'
    runtime.appearance.io.write(receipt_path, {'success': True, 'completed': [], 'saved_referencers': [{
        'package': changed['asset'].split('.')[0], **runtime.motion_contract.pin(changed['path'])}]})
    relocation['move_receipts'] = [runtime.motion_contract.pin(receipt_path)]
    runtime.publish_formal_motion_runtime()
    current = runtime.load_formal_motion_runtime()
    assert len(current['variants']) == 52
    assert current['variants'][('MOTION_000', 'female')]['source']['relocation_reserialized']
    assert current['document']['post_relocation_all_frame_revalidation'] is False
    Path(changed['path']).write_bytes(b'unexplained later modification')
    with pytest.raises(ValueError, match='Changed pinned input'):
        runtime.load_formal_motion_runtime()
