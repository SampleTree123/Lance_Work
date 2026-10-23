"""TEMP production candidate: finite Future names based on current public owners.
No module-level UE call/import. Root alone decides whether to copy into production.
Never modifies raw captures, geometry, transforms, assets or editor properties.
"""
import copy
import gc
import hashlib
import json
import re
from pathlib import Path

ROOT = '/Game/FuturisticMetaCity'
DEST = '/Game/Scenes/FuturisticMetaCity'
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/scene_folder_organization_20261012_v1')
ENGINE = Path('D:/UE/UE_5.8/Engine')
SOURCE_SHA = '52b3b97cbdb8e6556c19235750ffbbb5d4bf984bc3d490eb8a9d2507c4f1db7c'
BASE_SHA = '90f73c0ca17f86f3fa1c24e4c4b441f612570f3890367a1318859f26ea2115e8'
FULL_SOURCE_SHA = '0d00d650c5f43123607b36cf840d284d730656d6063d20e3180585725766a989'
SOURCE_HELPER_SHA = 'eae640ee12f0c5a07719f169eea1e7065a06ad4bfc6a50e567e51bca1c620429'
COLLECTOR_SHA = '3ba941d026c6c8ff824c8a08dc34cacb15d9b1ca79fba828ccb99424ceafc7da'
CHILD_CLASSES = (
 ROOT + '/Blueprints/Props/BP_Satellite_Rotating.BP_Satellite_Rotating_C',
 ROOT + '/Blueprints/BP_AlphabetSignMaker.BP_AlphabetSignMaker_C')
SAT_PREFIX = 'BP_Satellite_Rotating_GEN_VARIABLE_BP_Satellite_Rotating_C_CAT_'
SHOW = ROOT + '/Maps/ShowcaseMap'
VIRTUAL = ROOT + '/Maps/VirtualMetaCity'
# These immutable source identities select exactly fourteen stable parent keys.
# Current allocation numbers are never an identity: public parent linkage and
# complete geometry/transform semantics must validate for each concrete pair.
FINITE_SOURCE_NAMES = {SHOW: {SAT_PREFIX + str(v) for v in (3, 4)},
 VIRTUAL: {SAT_PREFIX + str(v) for v in (40,41,43,44,47,49,50,53,54,56,57,60)}}
OFFICIAL_PINS = {
 'Source/Runtime/Engine/Private/Components/ChildActorComponent.cpp': '94b532519b0b0db9934356db0d10e03e86e65e2e15a04eafba053a9968a6970f',
 'Source/Runtime/Engine/Private/Camera/CameraComponent.cpp': '6ccda056998548867f96a8c580abff622276bcae78bafb52ad9b89fb9b378ab4',
 'Source/Runtime/Engine/Classes/Components/SceneComponent.h': 'a9e1cecc43547fe2dc10bae4cfdcb49d3951e89717c16c8c3e1bd0831030b1d5',
 'Source/Runtime/Engine/Classes/GameFramework/Actor.h': '2ee1effb7ab4ac4cf65cf6caa90a27cea45361feefaae0cb673f7265e00bc5c9',
 'Build/Build.version': 'd35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997'}


def require(test, reason):
 if not test:
  raise RuntimeError('Future finite public-owner contract: ' + reason)


def identity(value, m):
    if value is None:
        return None
    return {'path': m.canon(str(value.get_path_name()), ROOT), 'raw_path': str(value.get_path_name()),
            'name': str(value.get_name()), 'class': m.canon(str(value.get_class().get_path_name()), ROOT)}

def numbers(location, rotation, scale):
    return [float(v) for v in (location.x, location.y, location.z, rotation.pitch, rotation.yaw,
                              rotation.roll, scale.x, scale.y, scale.z)]

def actor_world(actor):
    return numbers(actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d())

def scene(component, m):
    """Official BlueprintCallable world getters and reflected public transforms.

    Relative and absolute properties have BlueprintReadWrite/AllowPrivateAccess
    in SceneComponent.h; no private unexposed field is requested or bypassed.
    Missing getters/properties fail the ownership frame and preserve raw maps.
    """
    if component is None:
        return None
    owner = attached = None
    try:
        owner = component.get_owner()
        attached = component.get_attach_parent()
        relative = [component.get_editor_property(k) for k in ('relative_location', 'relative_rotation', 'relative_scale3d')]
        return {'identity': identity(component, m), 'owner': identity(owner, m),
                'relative_transform': numbers(*relative),
                'world_transform': numbers(component.get_world_location(), component.get_world_rotation(), component.get_world_scale()),
                'world_transform_export': component.get_world_transform().export_text(),
                'attach_parent': identity(attached, m), 'attach_socket_name': str(component.get_attach_socket_name()),
                'absolute': {k: bool(component.get_editor_property('absolute_' + k)) for k in ('location', 'rotation', 'scale')}}
    finally:
        owner = attached = None

def class_default(actor, u, m):
    """Public class CDO, explicitly not the private per-instance child template."""
    default = root = None
    try:
        default = u.get_default_object(actor.get_class())
        root = default.root_component
        return {'identity': identity(default, m), 'actor_world_transform': actor_world(default),
                'root': scene(root, m), 'scope': 'Official public class CDO/root; no ChildActorTemplate access or claim.'}
    finally:
        default = root = None

def capture_current_ownership(u, m, expected_map):
    actors = []
    actor = parent = parent_component = parent_owner = child_root = world = proxy = None
    try:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        require(world is not None and world.get_path_name() == expected_map + '.' + expected_map.rsplit('/', 1)[-1], 'wrong map for owner capture')
        actors = list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
        children, cameras = [], []
        for actor in actors:
            class_path = m.canon(str(actor.get_class().get_path_name()), ROOT)
            if class_path in CHILD_CLASSES:
                parent = actor.get_parent_actor()
                parent_component = actor.get_parent_component()
                child_root = actor.root_component
                parent_owner = parent_component.get_owner() if parent_component else None
                if parent_component:
                    require(isinstance(parent_component, u.ChildActorComponent), 'reported parent is not ChildActorComponent')
                    require(parent is not None and parent_owner is not None and parent.get_path_name() == parent_owner.get_path_name(), 'public parent component/actor disagree')
                else:
                    require(parent is None, 'missing parent component but parent actor exists')
                children.append({'child': identity(actor, m), 'child_world_transform': actor_world(actor),
                    'parent_actor': identity(parent, m), 'parent_actor_world_transform': actor_world(parent) if parent else None,
                    'parent_component': scene(parent_component, m), 'child_root': scene(child_root, m),
                    'class_default': class_default(actor, u, m),
                    'public_mapping_key': None if parent_component is None else m.canon(parent_component.get_path_name(), ROOT),
                    'is_public_child_actor': parent_component is not None})
                parent = parent_component = parent_owner = child_root = None
            if actor.get_name() == 'BP_Tram_2' and class_path == ROOT + '/Blueprints/BP_Tram.BP_Tram_C':
                for proxy in actor.get_components_by_class(u.StaticMeshComponent):
                    if proxy.get_class().get_path_name() == '/Script/Engine.CameraProxyMeshComponent':
                        mesh = proxy.get_editor_property('static_mesh')
                        cameras.append({'actor': identity(actor, m), 'actor_world_transform': actor_world(actor),
                            'proxy': scene(proxy, m), 'mesh': identity(mesh, m),
                            'materials': [m.material_signature(u, proxy.get_material(i), ROOT) for i in range(proxy.get_num_materials())]})
                        mesh = None
        keys = [r['public_mapping_key'] for r in children if r['public_mapping_key'] is not None]
        require(len(keys) == len(set(keys)), 'ambiguous same public parent-component identity')
        return {'map': m.canon(expected_map, ROOT), 'children': sorted(children, key=lambda r:r['child']['name']),
                'camera_proxies': cameras,
                'private_scope_not_read': ['ChildActorTemplate', 'ActorOuter', 'native object flags'],
                'source_version_pins': dict(OFFICIAL_PINS)}
    finally:
        actor = parent = parent_component = parent_owner = child_root = world = proxy = None
        actors.clear()
        gc.collect()


def canonical(value, m):
    if isinstance(value, dict):
        return {k: canonical(v, m) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v, m) for v in value]
    return m.canon(value, ROOT) if isinstance(value, str) else value


def renamed_frame(value, new_identity, old_identity):
    if isinstance(value, dict):
        return {k: renamed_frame(v, new_identity, old_identity) for k, v in value.items()}
    if isinstance(value, list):
        return [renamed_frame(v, new_identity, old_identity) for v in value]
    if value == new_identity['name']:
        return old_identity['name']
    if isinstance(value, str) and (value == new_identity['path'] or value.startswith(new_identity['path'] + '.')):
        return old_identity['path'] + value[len(new_identity['path']):]
    return value


def public_key_map(frame):
    rows = frame['children']
    names = [r['child']['name'] for r in rows]
    keys = [r['public_mapping_key'] for r in rows if r['is_public_child_actor']]
    require(len(names) == len(set(names)) and all(keys) and len(keys) == len(set(keys)), 'duplicate child name/parent key')
    for row in rows:
        if row['is_public_child_actor']:
            comp = row['parent_component']
            require(comp and comp['identity']['class'] == '/Script/Engine.ChildActorComponent'
                    and comp['identity']['path'] == row['public_mapping_key']
                    and comp['owner'] == row['parent_actor']
                    and row['child_root']['owner'] == row['child']
                    and row['child_root']['attach_parent'] == comp['identity'], 'public owner/attach mismatch')
        else:
            require(row['public_mapping_key'] is None and row['parent_actor'] is None and row['parent_component'] is None,
                    'non-child has parent')
    return {r['public_mapping_key']: r for r in rows if r['is_public_child_actor']}


def comparison_from_public_frames(m, source_row, current_public, after, raw_relative):
    """Pure comparison. All public frames must match source after identity only.

    Source keys restrict fourteen eligible actors. A different decimal allocation
    is accepted only for one of those actual public parent associations, after
    every other public field and the actor's full signature/relative are equal.
    It never provides a general path/suffix comparator.
    """
    original = canonical(source_row['ownership']['value'], m)
    live = canonical(current_public, m)
    path = original['map']
    require(path in FINITE_SOURCE_NAMES and live['map'] == path and after['map'] == path, 'wrong map')
    require(original['source_version_pins'] == live['source_version_pins'] == OFFICIAL_PINS, 'builder pins')
    require(original['private_scope_not_read'] == live['private_scope_not_read'], 'capture scope changed')
    oldkeys, newkeys = public_key_map(original), public_key_map(live)
    require(set(oldkeys) == set(newkeys) and len(oldkeys) == (12 if path == SHOW else 62), 'complete public key set')
    eligible = {k for k, r in oldkeys.items() if r['child']['name'] in FINITE_SOURCE_NAMES[path]}
    require(len(eligible) == (2 if path == SHOW else 12), 'finite original parent identity set')
    oldactors = {r['name']: r for r in source_row['capture']['signature']['actors']}
    newactors = {r['name']: r for r in after['actors']}
    oldrel = {r['name']: r for r in source_row['capture']['component_transforms']}
    newrel = {r['name']: r for r in raw_relative}
    require(len(oldactors) == source_row['capture']['signature']['actor_count']
            and len(newactors) == after['actor_count'] == len(oldactors)
            and len(oldrel) == len(newrel) == len(oldactors), 'duplicate/missing full actor records')
    aliases = []
    for key, old in oldkeys.items():
        new = newkeys[key]
        a, b = old['child'], new['child']
        if a['name'] != b['name']:
            require(key in eligible and a['class'] == b['class'] == CHILD_CLASSES[0]
                    and re.fullmatch(re.escape(SAT_PREFIX) + r'[0-9]+', b['name'])
                    and a['path'] == path + '.' + path.rsplit('/', 1)[-1] + ':PersistentLevel.' + a['name']
                    and b['path'] == path + '.' + path.rsplit('/', 1)[-1] + ':PersistentLevel.' + b['name'],
                    'name change outside exact fourteen public parent associations')
            require(old == renamed_frame(new, b, a), 'child full public semantics changed (including yaw)')
            require(a['name'] in oldactors and b['name'] in newactors
                    and oldactors[a['name']]['class'] == newactors[b['name']]['class'] == CHILD_CLASSES[0],
                    'actual signature has wrong mapped actor/class')
            compare_actor = copy.deepcopy(newactors[b['name']])
            compare_actor['name'] = a['name']
            compare_rel = copy.deepcopy(newrel[b['name']])
            compare_rel['name'] = a['name']
            require(m.signature_equal(oldactors[a['name']], compare_actor)
                    and oldrel[a['name']] == compare_rel, 'mapped actor geometry/material/transform changed')
            aliases.append({'source_name': a['name'], 'current_name': b['name'], 'parent_key': key,
                            'source_object': a['path'], 'current_object': b['path']})
        else:
            require(old == new, 'unchanged child public semantics differ (including sign yaw)')
    require([r for r in original['children'] if not r['is_public_child_actor']]
            == [r for r in live['children'] if not r['is_public_child_actor']], 'standalone selected actor changed')
    camera_alias = None
    if path == SHOW:
        require(len(original['camera_proxies']) == len(live['camera_proxies']) == 1, 'exact proxy count')
        old, new = original['camera_proxies'][0], live['camera_proxies'][0]
        a, b = old['proxy']['identity'], new['proxy']['identity']
        key = path + '.ShowcaseMap:PersistentLevel.BP_Tram_2.Camera'
        require(old['actor']['name'] == new['actor']['name'] == 'BP_Tram_2'
                and a['class'] == b['class'] == '/Script/Engine.CameraProxyMeshComponent'
                and a['name'] == 'CameraProxyMeshComponent_0'
                and re.fullmatch(r'CameraProxyMeshComponent_[0-9]+', b['name'])
                and old['proxy']['attach_parent']['path'] == new['proxy']['attach_parent']['path'] == key,
                'wrong finite camera public owner/attach identity')
        require(old == renamed_frame(new, b, a), 'camera full public semantics changed')
        camera_alias = {'actor': 'BP_Tram_2', 'source_name': a['name'], 'current_name': b['name'], 'parent_key': key}
    else:
        require(original['camera_proxies'] == live['camera_proxies'] == [], 'unexpected camera proxy')
    signature_copy, relative_copy = copy.deepcopy(after), copy.deepcopy(raw_relative)
    amap = {r['current_name']: r['source_name'] for r in aliases}
    for rows in (signature_copy['actors'], relative_copy):
        for actor in rows:
            if actor['name'] in amap:
                actor['name'] = amap[actor['name']]
            if camera_alias and actor['name'] == camera_alias['actor']:
                proxy = [c for c in actor['components'] if c['name'] == camera_alias['current_name']]
                require(len(proxy) == 1, 'camera full capture occurrence')
                proxy[0]['name'] = camera_alias['source_name']
                actor['components'].sort(key=lambda c: c['name'])
                src = oldactors[actor['name']] if rows is signature_copy['actors'] else oldrel[actor['name']]
                require(m.signature_equal(src, actor) if rows is signature_copy['actors'] else src == actor,
                        'camera owner full signature/relative changed')
        rows.sort(key=lambda r: r['name'])
    require(len({r['name'] for r in signature_copy['actors']}) == len(signature_copy['actors'])
            and len({r['name'] for r in relative_copy}) == len(relative_copy), 'comparison identity collision')
    witness = {'schema': 'futuristic_current_public_owner_finite_names_v1', 'map': path,
               'source_ownership_sha256': SOURCE_SHA, 'baseline_sha256': BASE_SHA,
               'source_full903_sha256': FULL_SOURCE_SHA, 'public_key_count': len(oldkeys),
               'satellite_parent_scope_count': len(eligible), 'satellite_pairs': aliases,
               'camera_pair': camera_alias, 'current_public_ownership_raw': current_public,
               'all_public_fields_equal_source_after_identity_only': True,
               'scope': 'Only concrete names at fourteen source public parent identities and one public camera attachment; no transform/mesh/material/relative values changed. Generic full comparisons still required.'}
    return signature_copy, relative_copy, witness


def read_pinned(path, pin):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin, 'evidence SHA changed: ' + str(path))
    return json.loads(raw)


def validated_map_comparison(u, m, root, base_path, base, before, after, raw_relative):
    if root != ROOT:
        return after, raw_relative, None
    require(Path(base_path).resolve() == (RUN / 'baseline_FuturisticMetaCity_v1.json').resolve(), 'literal baseline')
    pinned_base = read_pinned(base_path, BASE_SHA)
    require(base == pinned_base and before in base['maps'], 'caller baseline changed')
    original = read_pinned(RUN / 'futuristic_generated_ownership_source_v2.json', SOURCE_SHA)
    full = read_pinned(RUN / 'futuristic_original_missing_dependency_witness_v2.json', FULL_SOURCE_SHA)
    require(original['schema'] == 'futuristic_generated_ownership_v2' and original['mode'] == 'source'
            and original['success'] and original['errors'] == [] and original['dirty_after'] == []
            and original['entry_restore']['success'] and original['saved_assets'] is False
            and original['camera_render_started'] is False and original['identity_mapping_accepted'] is False
            and original['baseline_sha256'] == BASE_SHA and original['helper_sha256'] == SOURCE_HELPER_SHA
            and original['candidate_sha256'] == COLLECTOR_SHA and original['source_witness_sha256'] == FULL_SOURCE_SHA
            and original['scoped_files_before'] == original['scoped_files_after'], 'original public-owner receipt')
    require(full['success'] and full['errors'] == [] and full['saved_source_assets'] is False
            and full['baseline_sha256'] == BASE_SHA
            and full['source_proof_before'] == full['source_proof_after']
            and full['backup_proof_before'] == full['backup_proof_after']
            and full['source_proof_before']['files'] == full['backup_proof_before']['files']
            and len(full['actual_assets']) == len(full['source_proof_before']['files']) == 903
            and m.registry_identities(full['actual_assets']) == m.registry_identities(base['assets']), 'full original903 identity/bytes')
    sourcefiles = {r['relative']: r for r in full['source_proof_before']['files']}
    require(all(sourcefiles.get(r['relative']) == r for r in original['scoped_files_before']), 'original map/Blueprint byte scope')
    for rel, pin in OFFICIAL_PINS.items():
        require(hashlib.sha256((ENGINE / rel).read_bytes()).hexdigest() == pin, 'official builder/version pin')
    source_rows = {r['capture']['signature']['map']: r for r in original['maps']}
    require(set(source_rows) == {SHOW, VIRTUAL}, 'original map set')
    for original_map in base['maps']:
        r = source_rows[original_map['map']]
        require(r['capture']['success'] and r['ownership']['success']
                and m.compare_map(original_map, r['capture']['signature'])[0]
                and m.compare_component_transforms(base['component_transforms'][original_map['map']], r['capture']['component_transforms']),
                'actual source full signature/relative differs from baseline')
    require(not m.dirty(u), 'current capture dirty')
    current = None
    error = None
    try:
        # JSON round-trip returns only plain data; no World/actor wrappers escape.
        current = json.loads(json.dumps(capture_current_ownership(u, m, DEST + before['map'][len(ROOT):])))
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    gc.collect()
    require(error is None, 'current public owner capture failed: ' + str(error))
    require(not m.dirty(u), 'public owner capture dirtied editor')
    return comparison_from_public_frames(m, source_rows[before['map']], current, after, raw_relative)
