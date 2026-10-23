"""Private character revision runtime over the completed 19 October import.

Import is inert. The panel owns the private assembler, editor and scene changes.
The formal 38 components stay intact; all imported lashes are owned attached actors.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import os


SCRIPTS = Path(__file__).resolve().parent
RUN = SCRIPTS.parents[1] / 'outputs/character_refresh_20261018_v1/user_edited_pair_import_20261019_v1'
DELIVERY = RUN / 'delivery.json'
PROJECT = Path('D:/UE/projects/datatry_02/datatry_02.uproject')
UE_ROOT = '/Game/DataMake/Characters/Revisions/CFD40_20261019_v1'
DERIVED_ROOT = '/Game/DataMake/Validation/PairRevision20261019_v1'
IDS = {'CFD40_AF_001': 'female', 'CFD40_AM_001': 'male'}
SOURCES = {
    'CFD40_AF_001': '9045e2e8bcf6155407119c4fb83606daccc9edb861186440f6242fd958236210',
    'CFD40_AM_001': 'e40caaa16bb638050438a28947f9054b51409086e5fd1c6da8a21a90e3b67be5',
}
ROLES = {'body': 'Body', 'eyes': 'Eyes', 'teeth': 'Teeth', 'tongue': 'Tongue',
         'tearline': 'Tearline', 'eye_occlusion': 'EyeOcclusion'}
ASSEMBLER_SHA = '3a4e53a26106a43e3182a9afbde5df02597eb4261d7c87da5821c83fa9f4b603'
CACHE = '_dm_pair_revision_runtime_20261019_v1'


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest()}


def _verify(record):
    actual = _pin(record['path'])
    if actual['sha256'] != record['sha256']:
        raise ValueError('19 October input bytes changed: ' + str(record['path']))
    return actual


def _package(object_path):
    if not object_path.startswith(UE_ROOT + '/'):
        raise ValueError('Outside 19 October character revision: ' + object_path)
    return PROJECT.parent / 'Content' / (object_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def _validate_case(case, audit):
    """Require this exact pair/source; never rehabilitate historical receipts."""
    identifier = case['character_id']
    if identifier not in IDS or case['sex'] != IDS[identifier]:
        raise ValueError('Only AF001 and AM001 are in this revision panel')
    skeleton = '/Game/DataMake/Characters/Skeletons/SKEL_CFDShared_' + IDS[identifier].title() + '_v1'
    skeleton += '.' + skeleton.rsplit('/', 1)[1]
    source = case['source']
    expected_source = Path('D:/UE/exports/character_creator/character_refresh_20261018_v2') / identifier / 'reload_0/character.fbx'
    if (Path(source['path']).resolve() != expected_source.resolve() or source['sha256'] != SOURCES[identifier]
            or audit.get('source') != {k: source[k] for k in ('path', 'sha256')}
            or audit.get('character_id') != identifier or audit.get('sex') != IDS[identifier]
            or audit.get('destination') != UE_ROOT + '/' + identifier
            or case.get('skeleton') != skeleton or audit.get('skeleton') != skeleton
            or any(audit.get(k) is not True for k in ('success', 'standard_candidate_ready',
                'source_unchanged', 'all_source_morph_names_preserved'))):
        raise ValueError('Exact completed user-edited source/import required: ' + identifier)
    rows = audit['meshes']
    base = [r for r in rows if r['role'] != 'eyelashes']
    lashes = [r for r in rows if r['role'] == 'eyelashes']
    if (len(rows) != 8 or len(base) != 6 or {r['role'] for r in base} != set(ROLES)
            or len(lashes) != 2 or {r['name'] for r in lashes} != {'lash_up_bushy', 'lash_low_bushy'}
            or len({r['path'] for r in rows}) != 8):
        raise ValueError('Require six base pieces and both actual imported lash pieces')
    declared = {(r['path'], r['role'], r['morph_count']) for r in case['meshes']}
    if declared != {(r['path'], r['role'], r['morph_count']) for r in rows}:
        raise ValueError('Delivery inventory differs from actual import')
    for row in rows:
        if (row['path'] != UE_ROOT + '/' + identifier + '/Meshes/' + row['name'] + '.' + row['name']
                or row['skeleton'] != skeleton or not row['materials']
                or any(not m['material'] or not m['material'].startswith(UE_ROOT + '/' + identifier + '/') for m in row['materials'])
                or row['morph_source_comparison']['all_source_names_present'] is not True):
            raise ValueError('Part/material/Skeleton/Morph audit differs')
    body = next(r for r in base if r['role'] == 'body')
    body_curves = body['morph_source_comparison']['source_to_imported']
    for row in lashes:
        curves = row['morph_source_comparison']['source_to_imported']
        if len(curves) != 395 or any(body_curves.get(k) != v for k, v in curves.items()):
            raise ValueError('Leader curve propagation requires identical actual imported names')
    return {'character_id': identifier, 'sex': IDS[identifier], 'skeleton': skeleton,
            'base': {ROLES[r['role']]: r['path'] for r in base}, 'followers': copy.deepcopy(lashes)}


def load_configuration(delivery_path=DELIVERY):
    """Offline startup check; pin the new source, import audit and current packages."""
    if Path(delivery_path).resolve() != DELIVERY.resolve():
        raise ValueError('Only the completed 19 October pair delivery is accepted')
    delivery = _read(delivery_path)
    if (delivery.get('status') != 'pair_import_completed_remaining38_not_started'
            or delivery.get('ue_root') != UE_ROOT or len(delivery.get('cases', [])) != 2
            or {r['character_id'] for r in delivery['cases']} != set(IDS)):
        raise ValueError('Wrong pair delivery')
    records = [_pin(DELIVERY), _pin(__file__), _pin(SCRIPTS / 'ue_scene_site_appearance_v1.py')]
    members = {}
    for case in delivery['cases']:
        identifier = case['character_id']
        audit_path = RUN / identifier / identifier / 'import_audit.json'
        status_path = RUN / identifier / 'worker_status.json'
        if Path(case['audit']).resolve() != audit_path.resolve() or Path(case['worker_status']).resolve() != status_path.resolve():
            raise ValueError('Delivery audit/status escaped selected import directory')
        audit, status = _read(audit_path), _read(status_path)
        members[identifier] = _validate_case(case, audit)
        if (status.get('status') != 'completed' or status.get('character_id') != identifier
                or status.get('shared_skeleton_disk_unchanged') is not True
                or status.get('shared_skeleton') != case['skeleton']
                or len(status.get('normal_textures', [])) != 4):
            raise ValueError('Completed pair import and four saved skin Normals required')
        records += [_pin(audit_path), _pin(status_path), _verify(case['source']),
                    _verify(audit['auto_setup_json']), _verify(audit['source_extract'])]
        source_extract = _read(audit['source_extract']['path'])
        if (source_extract.get('source', {}).get('sha256') != SOURCES[identifier]
                or source_extract.get('bone_count') != 118):
            raise ValueError('New source extraction does not bind the 118-bone source')
        objects = [r['path'] for r in audit['meshes']] + status['normal_textures']
        objects += [m['material'] for r in audit['meshes'] for m in r['materials']]
        records += [_pin(_package(p)) for p in sorted(set(objects))]
    pins = list({r['path']: r for r in records}.values())
    return {'schema': 'pair_revision_runtime_20261019_v1', 'ue_root': UE_ROOT,
            'members': members, 'pins': pins, 'inputs': copy.deepcopy(pins),
            'stamps': {r['path']: [Path(r['path']).stat().st_size, Path(r['path']).stat().st_mtime_ns] for r in pins}}


def unchanged(configuration):
    """Cheap command-boundary guard; no file reads or hashes during playback."""
    try:
        return all([Path(p).stat().st_size, Path(p).stat().st_mtime_ns] == signature
                   for p, signature in configuration['stamps'].items())
    except OSError:
        return False


def _path(obj):
    return obj.get_path_name() if obj is not None else None


def _context(u, expected_pid):
    if (os.getpid() != expected_pid or Path(u.Paths.convert_relative_path_to_full(
            u.Paths.get_project_file_path())).resolve() != PROJECT.resolve()):
        raise ValueError('Pair runtime belongs to the exact datatry_02 editor PID')


def _patch_none(assembly):
    source = SCRIPTS / 'ue_scene_site_appearance_v1.py'
    if Path(assembly.__file__).resolve() != source.resolve() or assembly.__name__ == 'ue_scene_site_appearance_v1':
        raise ValueError('Fresh private existing assembler required')
    if _pin(source)['sha256'] != ASSEMBLER_SHA:
        raise ValueError('Existing assembler changed; review bounded None adaptation')
    text = source.read_text(encoding='utf-8')
    replacements = [
        ("        if clip:\n            body.set_position(t, False)\n        result = dict(previous['result'], time_seconds=t)",
         "        if clip:\n            body.set_position(t, False)\n        else:\n            body.set_animation(None)\n            body.override_animation_data(None, False, False, t, 1.)\n        result = dict(previous['result'], time_seconds=t)"),
        ("        body.override_animation_data(clip, False, False, t, 1.)\n        if clip:",
         "        if clip is None:\n            body.set_animation(None)\n        body.override_animation_data(clip, False, False, t, 1.)\n        if clip:")]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError('None animation reset patch no longer unique')
        text = text.replace(old, new)
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'apply_actor')
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), assembly.__dict__)


def _state(assembly):
    return assembly._pair_revision_runtime


def _clear_one(state, key):
    binding = state['bindings'].get(key)
    if binding is None:
        return
    u = state['u']
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    for actor in list(binding['actors']):
        if u.SystemLibrary.is_valid(actor) and not actors.destroy_actor(actor):
            raise RuntimeError('Cannot destroy this owner lash: ' + _path(actor))
        binding['actors'].remove(actor)
    body = binding['body']
    if u.SystemLibrary.is_valid(body):
        state['fixed']._set_instance_property(body, 'propagate_curves_to_followers', binding['old_propagate'])
    state['bindings'].pop(key)


def clear(assembly, subject=None):
    """Release before owner destruction/scene load; clear only this runtime's actors."""
    state = _state(assembly)
    _context(state['u'], state['expected_pid'])
    keys = [_path(subject) if not isinstance(subject, str) else subject] if subject is not None else list(state['bindings'])
    for key in keys:
        _clear_one(state, key)
    if not state['bindings'] and state['watcher'] is not None:
        state['u'].unregister_slate_post_tick_callback(state['watcher'])
        state['watcher'] = None
    assembly.invalidate_cache(state['u'], subject if subject is not None and not isinstance(subject, str) else None)
    return {'released_owners': len(keys), 'remaining_owners': len(state['bindings'])}


def _sync(state):
    u = state['u']
    for key, binding in list(state['bindings'].items()):
        owner, body = binding['owner'], binding['body']
        if (not u.SystemLibrary.is_valid(owner) or not u.SystemLibrary.is_valid(body)
                or _path(body.get_skeletal_mesh_asset()) != binding['member']['base']['Body']
                or any(not u.SystemLibrary.is_valid(a) for a in binding['actors'])):
            _clear_one(state, key)
            continue
        visible = body.is_visible() and not owner.is_temporarily_hidden_in_editor()
        hidden = bool(owner.get_editor_property('hidden') or body.get_editor_property('hidden_in_game'))
        for actor in binding['actors']:
            comp = actor.get_editor_property('skeletal_mesh_component')
            actor.set_is_temporarily_hidden_in_editor(not visible)
            comp.set_visibility(visible, False)
            comp.set_hidden_in_game(hidden)
    if not state['bindings'] and state['watcher'] is not None:
        u.unregister_slate_post_tick_callback(state['watcher'])
        state['watcher'] = None


def _watch(state):
    try:
        _sync(state)
    except Exception as error:
        state['last_error'] = str(error)
        # Do not allow a failed preview callback to keep stale owner wrappers.
        for key in list(state['bindings']):
            _clear_one(state, key)
        _sync(state)


def _bind(state, actor, member):
    u, fixed = state['u'], state['fixed']
    components = fixed.actor_components(actor)
    body = components['Body']
    if _path(body.get_skeletal_mesh_asset()) != member['base']['Body']:
        raise ValueError('Apply the six 19 October base meshes before binding lashes')
    prepared = []
    for row in member['followers']:
        mesh = u.load_asset(row['path'])
        if not isinstance(mesh, u.SkeletalMesh) or _path(mesh.get_editor_property('skeleton')) != member['skeleton']:
            raise ValueError('Actual new lash/Skeleton differs')
        materials = [{'name': str(m.get_editor_property('material_slot_name')),
                      'material': _path(m.get_editor_property('material_interface'))} for m in mesh.get_editor_property('materials')]
        compatibility = state['review'].compatibility(body.get_skeletal_mesh_asset(), mesh)
        if materials != row['materials'] or compatibility['follow_mode'] != 'leader_pose' or compatibility['extra_reference_bones']:
            raise ValueError('New exact-name shared-Skeleton lash leader binding required')
        prepared.append({'mesh': mesh, 'compatibility': compatibility})
    binding = {'owner': actor, 'body': body, 'member': member, 'actors': [],
               'old_propagate': bool(body.get_editor_property('propagate_curves_to_followers'))}
    state['bindings'][_path(actor)] = binding
    try:
        fixed._set_instance_property(body, 'propagate_curves_to_followers', True)
        for row, assignment in zip(member['followers'], prepared):
            follower = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(
                u.SkeletalMeshActor, actor.get_actor_location(), actor.get_actor_rotation(), transient=True)
            if follower is None:
                raise RuntimeError('Could not create an owned lash actor')
            binding['actors'].append(follower)
            follower.set_actor_label(state['prefix'] + 'Lash_' + row['name'])
            follower.set_owner(actor)
            if not follower.attach_to_component(body, '', u.AttachmentRule.SNAP_TO_TARGET,
                    u.AttachmentRule.SNAP_TO_TARGET, u.AttachmentRule.SNAP_TO_TARGET, False):
                raise RuntimeError('Could not attach lash to exact Body')
            comp = follower.get_editor_property('skeletal_mesh_component')
            fixed._set_component(comp, assignment, body)
            fixed._set_instance_property(comp, 'use_attach_parent_bound', True)
            comp.set_allow_anim_curve_evaluation(True)
            comp.add_tick_prerequisite_component(body)
        if state['watcher'] is None:
            state['watcher'] = u.register_slate_post_tick_callback(lambda _dt: _watch(state))
        _sync(state)
    except Exception:
        _clear_one(state, _path(actor))
        raise


def owned(assembly, subject=None):
    state = _state(assembly)
    key = _path(subject) if subject is not None and not isinstance(subject, str) else subject
    return [a for k, b in state['bindings'].items() if key is None or k == key
            for a in b['actors'] if state['u'].SystemLibrary.is_valid(a)]


def readback(assembly, subject=None):
    state = _state(assembly)
    _sync(state)
    key = _path(subject) if subject is not None and not isinstance(subject, str) else subject
    owners = []
    for owner_key, binding in state['bindings'].items():
        if key is not None and key != owner_key:
            continue
        body = binding['body']
        rows = []
        for actor in binding['actors']:
            comp = actor.get_editor_property('skeletal_mesh_component')
            rows.append({'actor': _path(actor), 'owner': _path(actor.get_owner()),
                         'mesh': _path(comp.get_skeletal_mesh_asset()),
                         'leader': _path(comp.get_editor_property('leader_pose_component')),
                         'attached_to': _path(comp.get_attach_parent()),
                         'attach_parent_bounds': bool(comp.get_editor_property('use_attach_parent_bound')),
                         'tick': comp.is_component_tick_enabled()})
        count = len(binding['owner'].get_components_by_class(state['u'].SkeletalMeshComponent))
        expected = {r['path'] for r in binding['member']['followers']}
        owners.append({'owner': owner_key, 'character_id': binding['member']['character_id'],
            'root_component_count': count, 'followers': rows,
            'propagate_curves_to_followers': bool(body.get_editor_property('propagate_curves_to_followers')),
            'structural_pass': count == 38 and len(rows) == len(expected) and {r['mesh'] for r in rows} == expected
                and all(r['owner'] == owner_key and r['leader'] == _path(body)
                        and r['attached_to'] == _path(body) and r['attach_parent_bounds'] for r in rows),
            'evaluated_morph_pixels_verified': False})
    return {'revision': UE_ROOT, 'owners': owners, 'visual_acceptance': 'pending_actual_review'}


def install(assembly, *, u, expected_pid, configuration=None):
    """Install once in a private graph; callable in all existing primary scenes."""
    _context(u, expected_pid)
    if hasattr(assembly, '_pair_revision_runtime'):
        raise ValueError('Reuse installed private pair assembler; do not stack wrappers')
    configuration = load_configuration() if configuration is None else configuration
    night_review = configuration.get('schema') == 'night_character_review_20261020_v1'
    if night_review:
        from night_character_review_v1 import DELIVERY as night_delivery
        if (configuration.get('ue_root') != UE_ROOT or len(configuration.get('members', {})) != 40
                or _pin(night_delivery) not in configuration['pins']):
            raise ValueError('需要完整40人导入交接配置。')
    elif (configuration.get('schema') != 'pair_revision_runtime_20261019_v1'
            or set(configuration.get('members', {})) != set(IDS) or configuration.get('ue_root') != UE_ROOT
            or not unchanged(configuration)):
        raise ValueError('Fresh verified 19 October pair configuration required')
    # Only load_configuration's exact pinned delivery can authorize installation.
    if not night_review and (_pin(DELIVERY) not in configuration['pins'] or any(configuration['members'][k]['sex'] != IDS[k] for k in IDS)):
        raise ValueError('Configuration is not bound to the actual pair delivery')
    for case in ([] if night_review else _read(DELIVERY)['cases']):
        audit = _read(case['audit'])
        if (_pin(case['audit']) not in configuration['pins']
                or _validate_case(case, audit) != configuration['members'][case['character_id']]):
            raise ValueError('Configuration members differ from actual completed import')
    _patch_none(assembly)
    formal = assembly.contract.formal_runtime()
    if formal is None:
        raise ValueError('Current published wardrobe/hair runtime required')
    people = formal[1].identities.identity_catalog()['by_id']
    overlays = {}
    for identifier, member in configuration['members'].items():
        old = people[identifier]
        if old['skeleton'] != member['skeleton'] or {r['role'] for r in old['meshes']} != set(ROLES):
            raise ValueError('Formal identity/Skeleton changed')
        overlays[identifier] = {r['path']: member['base'][ROLES[r['role']]] for r in old['meshes']}
    state = {'u': u, 'expected_pid': expected_pid, 'configuration': configuration, 'overlays': overlays,
             'bindings': {}, 'watcher': None, 'fixed': assembly.fixed, 'review': assembly.review,
             'prefix': 'DM_SiteReview_Pair19_', 'last_error': None}
    assembly._pair_revision_runtime = state
    assembly.CACHE_KEY = CACHE + '_assembly'
    assembly.ASSET_ROOT = DERIVED_ROOT + '/Materials'
    assembly.COMPOSITE_ROOT = DERIVED_ROOT + '/Expressions'
    assembly.FOLLOWER_ROOT = DERIVED_ROOT + '/Followers'
    original = assembly.apply_actor

    def apply_actor(api, actor, selection, t, motion, **kwargs):
        _context(api, expected_pid)
        identifier = selection.get('character_id')
        if identifier not in configuration['members'] or selection.get('sex') != configuration['members'][identifier]['sex']:
            raise ValueError('所选角色不在本次导入目录中。')
        member = configuration['members'][identifier]
        owner_key = _path(actor)
        binding = state['bindings'].get(owner_key)
        if binding and binding['member']['character_id'] != identifier:
            _clear_one(state, owner_key)  # Clear while the old Body is still intact.
        if selection.get('face_id') == 'none':
            for comp in assembly.fixed.actor_components(actor).values():
                comp.clear_morph_targets()
            for follower in owned(assembly, actor):
                follower.get_editor_property('skeletal_mesh_component').clear_morph_targets()
        kwargs['path_overlay'] = {**(kwargs.get('path_overlay') or {}), **overlays[identifier]}
        result = original(api, actor, selection, t, motion, **kwargs)
        if len(result['components']) != 38 or any(result['components'].get(k) != v for k, v in member['base'].items()):
            raise RuntimeError('Actual 38-slot/new six-piece readback differs')
        if owner_key not in state['bindings']:
            _bind(state, actor, member)
        _sync(state)
        return dict(result, pair_revision=readback(assembly, actor))

    assembly.apply_actor = apply_actor
    return assembly


def install_worker(worker, assembly):
    """Include lashes in occlusion ignores and cleanup before map/owner release."""
    if hasattr(worker, '_pair_revision_hooks'):
        raise ValueError('Reuse installed pair worker')
    state = _state(assembly)
    original = {key: getattr(worker, key) for key in ('owned', 'trace_ignored', 'restore')}
    state['prefix'] = worker.PREFIX
    def unique(values):
        return list({_path(a): a for a in values if worker.u.SystemLibrary.is_valid(a)}.values())
    worker.owned = lambda: unique(list(original['owned']()) + owned(assembly))
    worker.trace_ignored = lambda: unique(list(original['trace_ignored']()) + owned(assembly))
    def restore():
        clear(assembly)
        return original['restore']()
    worker.restore = restore
    worker._pair_revision_hooks = original
    return worker
