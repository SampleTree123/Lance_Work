"""Isolated complete-character fixed slots; importable without Unreal.

The pure make_plan() consumes explicit canonical choices, never the old coverage
catalogue. run() is the editor entry (dryrun/preflight/build/migrate/apply/readback).
Only the parent orchestration session should execute editor modes. No mesh,
Skeleton, source v003 Blueprint or official registry is edited by this module.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time
import uuid
from datetime import datetime, timezone

SCRIPTS = Path(__file__).resolve().parent
# Captured once on import, never recalculated from a file changed mid-execution.
LOADED_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import formal_wardrobe_registry_v1 as formal

ENGINE = SCRIPTS.parents[1]
ROOT = ENGINE / 'outputs/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1'
STANDARD = ENGINE / 'outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/standard_candidate_registry.json'
LEVEL = '/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001'
ASSET_ROOT = LEVEL.rsplit('/', 1)[0]
BP_ROOT = ASSET_ROOT + '/FixedSlotRuntime'
SEXES = ('female', 'male')
BASE_ROLES = {'body': 'Body', 'tongue': 'Tongue', 'eyes': 'Eyes',
              'teeth': 'Teeth', 'tearline': 'Tearline', 'eye_occlusion': 'EyeOcclusion'}
SEMANTIC = ('UpperInner', 'UpperOuter', 'Bottom', 'FullBody', 'Footwear')
BUNDLES = tuple(f'BundlePart{i:02d}' for i in range(1, 11))
HAIRS = tuple(f'HairPart{i:02d}' for i in range(1, 18))
BASES = tuple(BASE_ROLES.values())
SLOTS = SEMANTIC + BUNDLES + HAIRS
COMPONENTS = BASES + SLOTS
COPY_TAG = 'DM_CCWH_COPY_POSE'
ACTOR_COPY_PREFIX = 'DM_CCWH_SLOT_COPY_'
COPY_ROUTING_TAG = 'DM_CCWH_CopyRouting'
COPY_ROUTING_VERSION = 'actor_slot_tags_v1'
OWNER_TAG = 'DM_CCWH_FIXED_SLOT_V1'
MODES = {'dryrun', 'preflight', 'build', 'migrate', 'apply', 'readback'}
BUILD_STATE_TAG = 'DM_CCWH_BuildState'
BUILD_CODE_TAG = 'DM_CCWH_BuildCodeSHA256'
DIRECT_FUNCTIONS = {
    'has_tag': '/Script/Engine.Actor:ActorHasTag',
    'leader': '/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent',
}
UNRESOLVED = {
    'human_review_R10': 'pending',
    'visual_fit_and_penetration': 'pending_per_outfit_and_motion',
    'shoe_pose_and_ground_contact': 'not_corrected_by_slot_assembly',
    'body_topology_occlusion': 'not_implemented_no_geometry_or_section_mask_applied',
    'scope': 'prototype_only_not_production_approval',
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def source_record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def blueprint_path(sex):
    if sex not in SEXES:
        raise ValueError('Invalid character sex: ' + str(sex))
    return BP_ROOT + f'/BP_DM_Complete_{sex.title()}_FixedSlots_v001'


def actor_label(sex):
    blueprint_path(sex)
    return f'DM_CCWH_{sex}_Character'


def _owner(asset_id, mesh_path):
    return asset_id + '|' + mesh_path


def stable_outfit_assignments(registry, resolved):
    """Reserve Bundle slots from the whole family, independent of selection order.

    Alternative single-piece garments can share a semantic slot. Accessories and
    additional pieces have stable family-wide owners. A locked bundle reserves
    one deterministic primary for each semantic slot and extras for the rest.
    """
    family = next(f for f in registry['families'] if f['family_id'] == resolved['family_id'])
    reservations, semantic_used = {}, set()
    for asset in sorted(family['assets'], key=lambda a: a['asset_id']):
        for index, mesh in enumerate(sorted(asset['ue_mesh_paths'])):
            fixed = formal.FIXED_SLOT.get(asset['slot'])
            primary = fixed and index == 0
            if family['assembly_mode'] == 'locked_bundle':
                primary = primary and fixed not in semantic_used
            if primary:
                target = fixed
                semantic_used.add(fixed)
            else:
                target = None
            reservations[_owner(asset['asset_id'], mesh)] = target
    extras = sorted(k for k, target in reservations.items() if target is None)
    if len(extras) > len(BUNDLES):
        raise ValueError(f"Stable family accessory map exceeds {len(BUNDLES)}: {family['family_id']}")
    reservations.update({key: BUNDLES[i] for i, key in enumerate(extras)})
    rows, shared_extra = [], 0
    shared_paths = sorted(row['mesh_path'] for row in resolved['assignments']
                          if row['source_component_name'] == resolved.get('shared_shoe_id'))
    for original in sorted(resolved['assignments'], key=lambda r: (r['source_component_name'], r['mesh_path'])):
        row = dict(original)
        key = _owner(row['source_component_name'], row['mesh_path'])
        if key in reservations:
            target = reservations[key]
        elif row['source_component_name'] == resolved.get('shared_shoe_id'):
            if row['mesh_path'] == shared_paths[0]:
                target = 'Footwear'
            else:
                position = len(extras) + shared_extra
                if position >= len(BUNDLES):
                    raise ValueError('Shared shoe pieces exceed stable Bundle capacity')
                target = BUNDLES[position]
                shared_extra += 1
        else:
            raise ValueError('Resolved asset has no stable owner: ' + key)
        row.update(target_component=target, component_name=target, owner_key=key,
                   owner_asset_id=row['source_component_name'], family_id=family['family_id'], kind='clothing',
                   target_kind='fixed_semantic_slot' if target in SEMANTIC else 'reusable_bundle_pool')
        rows.append(row)
    targets = [r['component_name'] for r in rows]
    if len(targets) != len(set(targets)):
        raise ValueError('Stable owner map produced a component collision')
    return sorted(rows, key=lambda r: COMPONENTS.index(r['component_name']))


def _selection(registry, sex, choice):
    allowed = {'family_id', 'group_id', 'family_asset_ids', 'shared_shoe_id', 'hair_id'}
    if not isinstance(choice, dict) or set(choice) - allowed:
        raise ValueError('Unsupported selection fields (pose and occlusion are not implemented)')
    if choice.get('family_id'):
        resolved = formal.resolve_selection(registry, character_sex=sex, **choice)
        clothing = stable_outfit_assignments(registry, resolved)
    else:
        if any(choice.get(key) for key in allowed - {'hair_id'}):
            raise ValueError('A partial outfit requires a legal family and group')
        hair_id = choice.get('hair_id')
        hair = next((h for h in registry['hair_assets'] if h['hair_id'] == hair_id), None)
        if hair_id and (hair is None or not formal.hair_available_to(hair, sex)):
            raise formal.RegistryError(f'Hair is not available to {sex}: {hair_id}')
        fit = formal.hair_fit(hair, sex) if hair else None
        resolved = {'character_sex': sex, 'requested_hair_id': hair_id,
                    'resolved_hair_id': hair_id, 'hair_reason': 'allowed' if hair else 'not_selected',
                    'assignments': [], 'hair_assignments': [],
                    'hair_skeleton_path': fit.get('skeleton_path') if fit else None}
        if fit:
            resolved['hair_assignments'] = [
                {'mesh_path': m['path'], 'source_component_name': hair_id, 'slot': 'scalp_hair'}
                for m in fit['meshes']]
        clothing = []
    hair_rows = sorted(resolved['hair_assignments'], key=lambda r: r['mesh_path'])
    if len(hair_rows) > len(HAIRS):
        raise ValueError('Selected hairstyle exceeds fixed HairPart capacity')
    hairs = []
    for index, original in enumerate(hair_rows):
        row = dict(original)
        row.update(component_name=HAIRS[index], target_component=HAIRS[index], kind='hair',
                   owner_key=_owner(resolved['resolved_hair_id'] + ':' + sex, row['mesh_path']),
                   owner_asset_id=resolved['resolved_hair_id'], target_kind='hair_pool')
        hairs.append(row)
    return resolved, clothing + hairs


def make_plan(registry_path, choices_by_sex, source_registry_path=STANDARD):
    """Pure plan; {} per sex means no clothes and no hair, not a fake index 0 item."""
    registry_path = Path(registry_path).resolve()
    if registry_path == formal.CURRENT_REVIEWED_POOL_REGISTRY.resolve():
        formal.current_registry_path()  # Validate bound publication, even on explicit reads.
    elif registry_path == formal.REVIEWED_POOL_REGISTRY.resolve():
        formal.reviewed_pool_v1_registry_path()  # Explicit historical reproduction.
    registry = formal.read_registry(registry_path)
    if set(choices_by_sex) != set(SEXES):
        raise ValueError('Provide explicit choices for female and male')
    source = read_json(source_registry_path)
    cases = {case['sex']: case for case in source['cases']}
    if set(cases) != set(SEXES) or len(source['cases']) != 2:
        raise ValueError('Expected two unique complete character sources')
    characters = {}
    for sex in SEXES:
        case = cases[sex]
        by_role = {m['role']: m for m in case['meshes']}
        if (not case.get('standard_candidate_ready') or set(by_role) != set(BASE_ROLES)
                or len(case['meshes']) != len(BASE_ROLES)):
            raise ValueError('Complete character must have exactly six ready base meshes: ' + sex)
        resolved, followers = _selection(registry, sex, choices_by_sex[sex])
        base = [{'component_name': name, 'target_component': name, 'mesh_path': by_role[role]['path'],
                 'role': role, 'kind': 'body' if role == 'body' else 'face_support',
                 'owner_key': _owner(case['character_id'], by_role[role]['path'])}
                for role, name in BASE_ROLES.items()]
        assignments = base + followers
        names = [a['component_name'] for a in assignments]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate component assignments')
        characters[sex] = {'case': case, 'blueprint_path': blueprint_path(sex),
                           'actor_label': actor_label(sex), 'choice': dict(choices_by_sex[sex]),
                           'resolved': resolved, 'assignments': assignments,
                           'unused_slots': [name for name in SLOTS if name not in names]}
    plan = {'schema_version': 1, 'level': LEVEL, 'component_names': list(COMPONENTS),
            'component_count': len(COMPONENTS), 'sources': {
                'registry': source_record(registry_path), 'standard_candidate': source_record(source_registry_path)},
            'characters': characters, 'limitations': dict(UNRESOLVED)}
    plan['plan_sha256'] = digest(plan)
    return plan


def _ue():
    return importlib.import_module('unreal')


def _review():
    return importlib.import_module('ue_complete_character_wardrobe_hair_review_v1')


def _base():
    return importlib.import_module('ue_build_modular_outfit_runtime_v2')


def object_path(value):
    return value.get_path_name() if value is not None else None


def _assert_level():
    if _review().world_path() != LEVEL:
        raise RuntimeError('Open the authorized independent review level before this operation')


def _verify_plan(plan):
    unsigned = {k: v for k, v in plan.items() if k != 'plan_sha256'}
    if plan.get('plan_sha256') != digest(unsigned):
        raise RuntimeError('Plan content changed after preparation')
    for record in plan['sources'].values():
        if source_record(record['path']) != record:
            raise RuntimeError('Plan source changed: ' + record['path'])
    published = formal.current_registry_path().resolve()
    if Path(plan['sources']['registry']['path']).resolve() != published:
        raise RuntimeError('Editor runtime requires the published reviewed pool, with no historical fallback')
    if Path(plan['sources']['standard_candidate']['path']).resolve() != STANDARD.resolve():
        raise RuntimeError('Editor runtime requires the authorized complete-character sources')


def preflight(plan):
    """Read/load only. Entire pair is validated before any scene mutation."""
    _assert_level()
    _verify_plan(plan)
    u, review = _ue(), _review()
    review.cache()['compatibility'].clear()  # Do not trust a previous mesh/reference edit.
    prepared = {}
    for sex, character in plan['characters'].items():
        body_path = next(a['mesh_path'] for a in character['assignments'] if a['kind'] == 'body')
        body = u.load_asset(body_path)
        if not isinstance(body, u.SkeletalMesh) or object_path(body.get_editor_property('skeleton')) != character['case']['skeleton']:
            raise RuntimeError('Complete body identity or Skeleton changed: ' + sex)
        loaded = []
        for assignment in character['assignments']:
            mesh = body if assignment['kind'] == 'body' else u.load_asset(assignment['mesh_path'])
            if not isinstance(mesh, u.SkeletalMesh):
                raise RuntimeError('Missing skeletal mesh: ' + assignment['mesh_path'])
            materials = mesh.get_editor_property('materials')
            if not materials or any(m.get_editor_property('material_interface') is None for m in materials):
                raise RuntimeError('Missing material slot: ' + assignment['mesh_path'])
            if assignment['kind'] == 'hair' and object_path(mesh.get_editor_property('skeleton')) != character['resolved']['hair_skeleton_path']:
                raise RuntimeError('Hair fit Skeleton differs from the registry')
            row = dict(assignment, mesh=mesh, label=assignment['component_name'])
            if assignment['kind'] != 'body':
                row['compatibility'] = review.compatibility(body, mesh)
                if row['compatibility']['follow_mode'] == 'copy_pose':
                    bp_path = review.copy_pose_path(mesh)
                    bp = u.load_asset(bp_path)
                    if not isinstance(bp, u.AnimBlueprint) or bp.get_editor_property('target_skeleton') != mesh.get_editor_property('skeleton'):
                        raise RuntimeError('Existing isolated CopyPose Blueprint is missing or mismatched: ' + bp_path)
                    # Validate the actual graph; never silently substitute a generic ABP.
                    from editor_toolset.toolsets.blueprint import BlueprintTools
                    graph = u.BlueprintEditorLibrary.find_graph(bp, 'AnimGraph')
                    nodes = list(BlueprintTools.find_nodes(graph)) if graph else []
                    copies = [n for n in nodes if isinstance(n, u.AnimGraphNode_CopyPoseFromMesh)]
                    if (len(copies) != 1 or not copies[0].get_editor_property('node').get_editor_property('use_attached_parent')
                            or copies[0].get_editor_property('node').get_editor_property('use_mesh_pose')
                            or not copies[0].get_editor_property('node').get_editor_property('copy_curves')
                            or bp.generated_class() is None):
                        raise RuntimeError('Existing CopyPose graph does not use attached Body: ' + bp_path)
                    row['copy_pose_blueprint'] = bp
            loaded.append(row)
        resolved = character['resolved']
        prepared[sex] = {'case': character['case'], 'body_mesh': body, 'assignments': loaded,
                         'followers': [r for r in loaded if r['kind'] != 'body'], 'outfit': resolved,
                         'hair_id': resolved['resolved_hair_id'], 'requested_hair_id': resolved['requested_hair_id'],
                         'blocked_hair_reason': resolved['hair_reason'] if resolved['hair_reason'] == 'deny_all' else None}
    return prepared


def actor_for(sex):
    _assert_level()
    return _review().find(actor_label(sex))


def actor_components(actor):
    if actor is None:
        raise RuntimeError('Fixed-slot actor does not exist; run guarded migration first')
    u = _ue()
    rows = list(actor.get_components_by_class(u.SkeletalMeshComponent))
    result = {c.get_name(): c for c in rows}
    if len(rows) != len(COMPONENTS) or set(result) != set(COMPONENTS):
        raise RuntimeError('Actor does not have the exact 38 fixed components')
    return result


def body_for(sex):
    return actor_components(actor_for(sex))['Body']


def _owned_actor(sex):
    actor = actor_for(sex)
    if actor is None:
        raise RuntimeError('Missing migrated character: ' + sex)
    bp = _ue().load_asset(blueprint_path(sex))
    if bp is None or actor.get_class() != bp.generated_class() or OWNER_TAG not in [str(t) for t in actor.tags]:
        raise RuntimeError('Refusing to edit an unowned actor: ' + actor_label(sex))
    if str(_ue().EditorAssetLibrary.get_metadata_tag(bp, BUILD_STATE_TAG) or '') not in {'', 'complete'}:
        raise RuntimeError('Refusing to use an unfinished fixed-slot Blueprint: ' + sex)
    actor_components(actor)
    return actor


def _palette_node(tools, graph, queries, class_name, required_pins, position):
    u, base = _ue(), _base()
    attempts, candidates = [], []
    for query in queries:
        candidates += [c for c in tools.find_node_types(graph, query) if c not in candidates]
    if class_name == 'K2Node_ExecutionSequence':
        # A broad "Sequence" search also returns many animation functions. Do
        # not instantiate each wrong candidate: that repeats the costly C++
        # registry scan we are specifically removing from this builder.
        candidates = [c for c in candidates if c.rsplit('|', 1)[-1].replace(' ', '').casefold() in {'sequence', '序列'}]
        if len(candidates) != 1:
            raise RuntimeError('Expected one exact Sequence palette type, refusing broad trial creation: ' + repr(candidates))
    for type_id in candidates:
        node = tools.create_node(graph, type_id, position)
        pins = {str(p.get_pin_name()) for p in node.list_all_pins()}
        if isinstance(node, getattr(u, class_name)) and set(required_pins) <= pins:
            return node
        attempts.append({'type': type_id, 'pins': sorted(pins)})
        tools.delete_node(node)
    raise RuntimeError(f'Cannot create {class_name} with required pins: {attempts}')


class BuildCancelled(RuntimeError):
    """Cooperative stop; never interrupts an in-flight Unreal API call."""


class BuildProgress:
    def __init__(self, options=None):
        options = options or {}
        if set(options) - {'build_id', 'progress_path', 'cancel_path'}:
            raise ValueError('Unknown build control option')
        self.build_id = options.get('build_id') or uuid.uuid4().hex
        if not isinstance(self.build_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.build_id):
            raise ValueError('Unsafe build ID')
        folder = ROOT / 'tonight_20261006_v1/runtime'
        self.progress_path = Path(options.get('progress_path', folder / 'fixed_slot_build_progress_v2.json')).resolve()
        self.cancel_path = Path(options.get('cancel_path', folder / 'fixed_slot_build_cancel_v2.json')).resolve()
        for path in (self.progress_path, self.cancel_path):
            if not path.is_relative_to(ROOT.resolve()) or path.suffix.lower() != '.json':
                raise ValueError('Build control paths must be JSON files inside review outputs')
        if self.progress_path == self.cancel_path:
            raise ValueError('Progress and cancellation files must differ')
        self.started = self.previous = time.monotonic()
        self.events = []
        self.last = {}

    def tick(self, phase, sex=None, component=None, check_cancel=True, **details):
        stamp = time.monotonic()
        event = {'phase': phase, 'sex': sex, 'component': component,
                 'at': datetime.now(timezone.utc).isoformat(),
                 'elapsed_seconds': round(stamp - self.started, 3),
                 'since_previous_seconds': round(stamp - self.previous, 3), **details}
        self.previous = stamp
        self.events.append(event)
        self.last = {'schema_version': 2, 'build_id': self.build_id,
                     'loaded_source_sha256': LOADED_SOURCE_SHA256,
                     'cancel_path': str(self.cancel_path), 'progress_path': str(self.progress_path),
                     'status': details.get('status', 'running'), 'latest': event, 'events': self.events}
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.progress_path.with_name(self.progress_path.name + '.' + self.build_id + '.partial')
        temporary.write_text(json.dumps(self.last, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.progress_path)
        if check_cancel and self.cancel_path.exists():
            request = read_json(self.cancel_path)
            if request.get('build_id') == self.build_id and request.get('cancel') is True:
                raise BuildCancelled('Build cancelled at safe boundary: ' + phase + '/' + str(component))


def _direct_node(editor, operation, argument, node_class, pins, position):
    """No palette lookup: exact reflected editor API, then class/pin validation."""
    node = getattr(editor, operation)(argument) if argument is not None else getattr(editor, operation)()
    u = _ue()
    if node is None or not isinstance(node, getattr(u, node_class)):
        raise RuntimeError(f'Direct node creation failed: {operation}({argument})')
    actual = {str(p.get_pin_name()) for p in node.list_all_pins()}
    if not set(pins) <= actual:
        raise RuntimeError(f'Direct node pins differ: {operation}: {sorted(actual)}')
    node.set_node_pos(position)
    return node


def build_construction_graph(blueprint, progress=None, sex=None):
    """Rebind per component on construction, preserving CopyPose across reloads.

    One Sequence fans out to all complete follower branches. Only its creation
    uses the palette. Variables, branches and function calls use direct editor
    APIs; caching a type ID alone would still scan all UE actions per creation.
    """
    from editor_toolset.toolsets.blueprint import BlueprintTools as T
    u, b = _ue(), _base()
    graph = u.BlueprintEditorLibrary.find_graph(blueprint, 'UserConstructionScript')
    nodes = list(T.find_nodes(graph))
    entries = [n for n in nodes if isinstance(n, u.K2Node_FunctionEntry)]
    if len(entries) != 1:
        raise RuntimeError('Construction graph has no unique entry')
    editor = u.BlueprintGraphEditor.get_graph_editor(graph)
    editor.remove_nodes([n for n in nodes if n != entries[0]])
    body = b.only_pin(_direct_node(editor, 'add_get_member_variable_node', u.Name('Body'),
                                  'K2Node_VariableGet', [], u.IntPoint(-300, 100)))
    if progress:
        progress.tick('sequence_palette_begin', sex)
    seq = _palette_node(T, graph, ['Sequence', '序列'], 'K2Node_ExecutionSequence',
                        ['execute', 'then_0', 'then_1'], u.IntPoint(0, 0))
    if progress:
        progress.tick('sequence_palette_complete', sex)
    for _ in range(len(COMPONENTS) - 3):  # Sequence starts with two outputs.
        if not editor.add_node_pin(seq):
            raise RuntimeError('Cannot expand fixed-slot Sequence outputs')
    b.connect(b.find_pin(entries[0], 'then'), b.find_pin(seq, 'execute'))
    for index, name in enumerate(COMPONENTS[1:]):
        x = index * 900
        component = b.only_pin(_direct_node(editor, 'add_get_member_variable_node', u.Name(name),
                                           'K2Node_VariableGet', [], u.IntPoint(x, 180)))
        branch = _direct_node(editor, 'add_branch_node', None, 'K2Node_IfThenElse',
                              ['execute', 'then', 'else', 'Condition'], u.IntPoint(x + 250, 0))
        check = _direct_node(editor, 'add_call_function_node', DIRECT_FUNCTIONS['has_tag'],
                             'K2Node_CallFunction', ['self', 'Tag', 'ReturnValue'], u.IntPoint(x, 350))
        check_pins = {str(p.get_pin_name()) for p in check.list_all_pins()}
        if 'execute' in check_pins:
            b.connect(b.find_pin(seq, f'then_{index}'), b.find_pin(check, 'execute'))
            b.connect(b.find_pin(check, 'then'), b.find_pin(branch, 'execute'))
        else:
            b.connect(b.find_pin(seq, f'then_{index}'), b.find_pin(branch, 'execute'))
        # Actor instance Tags exist before UCS. Component instance data is
        # restored after UCS and therefore cannot select the reload branch.
        b.find_pin(check, 'Tag').set_pin_value(ACTOR_COPY_PREFIX + name)
        b.connect(b.find_pin(check, 'ReturnValue'), b.find_pin(branch, 'Condition'))
        for output, is_copy in [('then', True), ('else', False)]:
            call = _direct_node(editor, 'add_call_function_node', DIRECT_FUNCTIONS['leader'],
                                'K2Node_CallFunction', ['execute', 'then', 'self', 'NewLeaderBoneComponent',
                                'bForceUpdate', 'bInFollowerShouldTickPose'], u.IntPoint(x + 530, 0 if is_copy else 220))
            b.connect(b.find_pin(branch, output), b.find_pin(call, 'execute'))
            b.connect(component, b.find_pin(call, 'self'))
            if not is_copy:
                b.connect(body, b.find_pin(call, 'NewLeaderBoneComponent'))
            b.find_pin(call, 'bForceUpdate').set_pin_value('true')
            b.find_pin(call, 'bInFollowerShouldTickPose').set_pin_value('false')
        if progress:
            progress.tick('graph_component_complete', sex, name, completed=index + 1, total=len(COMPONENTS) - 1)
    return {'mode': COPY_ROUTING_VERSION, 'follower_count': len(COMPONENTS) - 1,
            'copy_pose_tag': COPY_TAG, 'actor_copy_prefix': ACTOR_COPY_PREFIX,
            'node_count': len(T.find_nodes(graph)),
            'builder': 'direct_editor_apis_v2', 'sequence_count': 1,
            'palette_node_creation_count': 1, 'direct_function_paths': dict(DIRECT_FUNCTIONS)}


def parse_call_reference_export(text, node_path):
    """Parse the real UE ObjectExporterT3D format, never display titles."""
    first = text.splitlines()[0] if text else ''
    if (not first.startswith('Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction ')
            or ('ExportPath="/Script/BlueprintGraph.K2Node_CallFunction\'' + node_path + '\'"') not in first):
        raise RuntimeError('Exported node identity/class differs')
    references = re.findall(r'^\s*FunctionReference=\((.*)\)\s*$', text, re.MULTILINE)
    if len(references) != 1:
        raise RuntimeError('Expected exactly one exported FunctionReference')
    fields = references[0]
    names = re.findall(r'(?:^|,)MemberName="([A-Za-z0-9_]+)"(?:,|$)', fields)
    if len(names) != 1:
        raise RuntimeError('Invalid exported member name')
    member = names[0]
    expected = {'ComponentHasTag': 'ActorComponent', 'ActorHasTag': 'Actor',
                'SetLeaderPoseComponent': 'SkinnedMeshComponent'}
    if member not in expected:
        raise RuntimeError('Unexpected serialized function: ' + member)
    parents = re.findall(r'MemberParent="/Script/CoreUObject.Class\'(/Script/Engine\.[A-Za-z0-9_]+)\'"', fields)
    self_context = bool(re.search(r'(?:^|,)bSelfContext=True(?:,|$)', fields))
    if parents:
        if parents != ['/Script/Engine.' + expected[member]] or self_context:
            raise RuntimeError('Unexpected serialized function owner')
    elif not (member == 'ActorHasTag' and self_context and
              ('MemberParent=' not in fields or 'MemberParent=None' in fields)):
        raise RuntimeError('Missing serialized function owner')
    return {'member': member, 'member_parent': parents[0] if parents else None,
            'self_context': self_context}


def _export_call_reference(node, directory):
    # Public API exercised in public_graph_probe_20261005T234809_daa1c6d7.json.
    # UPROPERTY FunctionReference is not exposed to Python in this UE build.
    u = _ue()
    filename = directory / (str(node.get_name()) + '.t3d')
    task = u.AssetExportTask()
    for key, value in {'object': node, 'exporter': u.ObjectExporterT3D(), 'filename': str(filename),
                       'automated': True, 'prompt': False, 'selected': False,
                       'replace_identical': False}.items():
        task.set_editor_property(key, value)
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Read-only node export failed: ' + str(task.get_editor_property('errors')))
    raw = filename.read_bytes()
    text = raw.decode('utf-16' if raw[:2] in {b'\xff\xfe', b'\xfe\xff'} else 'utf-8-sig')
    result = parse_call_reference_export(text, node.get_path_name())
    return {**result, 'node_path': node.get_path_name(), 'path': str(filename),
            'sha256': hashlib.sha256(raw).hexdigest()}


def _call_member(node, directory, evidence):
    row = _export_call_reference(node, directory)
    evidence.append(row)
    return row['member']


def inspect_copy_routing_graph(blueprint):
    """Read-only structural guard; accepts both legacy sequence topologies."""
    from editor_toolset.toolsets.blueprint import BlueprintTools as T
    u, b = _ue(), _base()
    graph = u.BlueprintEditorLibrary.find_graph(blueprint, 'UserConstructionScript')
    nodes, found = list(T.find_nodes(graph)), {}
    directory = ROOT / 'tonight_20261006_v1/runtime/graph_function_evidence' / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    evidence = []

    def single(pin):
        links = list(pin.list_connected_pins())
        if len(links) != 1:
            raise RuntimeError('Expected exactly one link: ' + str(pin.get_pin_name()))
        return links[0]

    for node in nodes:
        if not isinstance(node, u.K2Node_CallFunction):
            continue
        pins = {str(p.get_pin_name()): p for p in node.list_all_pins()}
        if not {'Tag', 'ReturnValue', 'self'} <= set(pins):
            continue
        member, tag = _call_member(node, directory, evidence), str(pins['Tag'].get_pin_value())
        if member not in {'ComponentHasTag', 'ActorHasTag'}:
            raise RuntimeError('Unrecognized tag-call node')
        if member == 'ComponentHasTag':
            if tag != COPY_TAG:
                raise RuntimeError('Unexpected legacy component tag')
            getter = single(pins['self'])
            if not isinstance(getter.get_owning_node(), u.K2Node_VariableGet):
                raise RuntimeError('Legacy tag self is not a component getter')
            name, mode = str(getter.get_pin_name()), 'component_tags'
        else:
            if not tag.startswith(ACTOR_COPY_PREFIX) or pins['self'].list_connected_pins():
                raise RuntimeError('Actor tag must target implicit Actor self')
            name, mode = tag[len(ACTOR_COPY_PREFIX):], COPY_ROUTING_VERSION
        if name not in COMPONENTS[1:] or name in found:
            raise RuntimeError('Unknown/duplicate CopyPose graph slot: ' + name)
        condition = single(pins['ReturnValue'])
        branch = condition.get_owning_node()
        if not isinstance(branch, u.K2Node_IfThenElse) or str(condition.get_pin_name()) != 'Condition':
            raise RuntimeError('Tag result is not the branch condition')
        branch_execute = b.find_pin(branch, 'execute')
        if 'execute' in pins:
            upstream = single(pins['execute'])
            if not single(pins['then']).is_same_native_pin(branch_execute):
                raise RuntimeError('Tag execution does not lead directly to branch')
        else:
            upstream = single(branch_execute)
        for output, is_copy in [('then', True), ('else', False)]:
            call_input = single(b.find_pin(branch, output))
            call = call_input.get_owning_node()
            if (not isinstance(call, u.K2Node_CallFunction) or _call_member(call, directory, evidence) != 'SetLeaderPoseComponent'
                    or str(call_input.get_pin_name()) != 'execute'):
                raise RuntimeError('Unexpected follower branch call')
            component_pin = single(b.find_pin(call, 'self'))
            if (not isinstance(component_pin.get_owning_node(), u.K2Node_VariableGet)
                    or str(component_pin.get_pin_name()) != name):
                raise RuntimeError('Follower branch targets another component')
            leader_pin = b.find_pin(call, 'NewLeaderBoneComponent')
            leader_links = list(leader_pin.list_connected_pins())
            if is_copy:
                if leader_links or str(leader_pin.get_pin_value()) not in {'', 'None', 'nullptr'}:
                    raise RuntimeError('CopyPose branch does not clear the leader')
            elif (len(leader_links) != 1 or str(leader_links[0].get_pin_name()) != 'Body'
                  or not isinstance(leader_links[0].get_owning_node(), u.K2Node_VariableGet)):
                raise RuntimeError('Leader branch does not use Body')
        found[name] = {'node': node, 'branch': branch, 'upstream': upstream, 'mode': mode}
    if set(found) != set(COMPONENTS[1:]):
        raise RuntimeError('Expected all 37 unique follower tag checks')
    modes = {row['mode'] for row in found.values()}
    if len(modes) != 1:
        raise RuntimeError('Mixed routing graph requires explicit recovery from backup')
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps({'method': 'public_ObjectExporterT3D', 'functions': evidence}, indent=2), encoding='utf-8')
    return {'graph': graph, 'nodes': nodes, 'checks': found, 'mode': next(iter(modes)),
            'function_evidence': source_record(manifest)}


def patch_copy_routing_graph(blueprint):
    """Replace ONLY 37 tag checks; caller owns backup, compile and save."""
    from editor_toolset.toolsets.blueprint import BlueprintTools as T
    u, b = _ue(), _base()
    before = inspect_copy_routing_graph(blueprint)
    if before['mode'] == COPY_ROUTING_VERSION:
        return {'replaced_check_count': 0, 'already_patched': True, 'node_count': len(before['nodes'])}
    editor = u.BlueprintGraphEditor.get_graph_editor(before['graph'])
    old_checks = [row['node'] for row in before['checks'].values()]
    unchanged = [node for node in before['nodes'] if node not in old_checks]
    for name in COMPONENTS[1:]:
        row = before['checks'][name]
        old, branch = row['node'], row['branch']
        new = _direct_node(editor, 'add_call_function_node', DIRECT_FUNCTIONS['has_tag'],
                           'K2Node_CallFunction', ['self', 'Tag', 'ReturnValue'], old.get_node_pos())
        if not b.find_pin(new, 'Tag').set_pin_value(ACTOR_COPY_PREFIX + name):
            raise RuntimeError('Cannot set ActorHasTag input: ' + name)
        # Save upstream before disconnection. Other getter and leader-call links
        # are untouched; only the old check and branch execution input change.
        for pin in old.list_all_pins():
            pin.break_pin_links()
        b.find_pin(branch, 'execute').break_pin_links()
        new_pins = {str(p.get_pin_name()) for p in new.list_all_pins()}
        if 'execute' in new_pins:
            b.connect(row['upstream'], b.find_pin(new, 'execute'))
            b.connect(b.find_pin(new, 'then'), b.find_pin(branch, 'execute'))
        else:
            b.connect(row['upstream'], b.find_pin(branch, 'execute'))
        b.connect(b.find_pin(new, 'ReturnValue'), b.find_pin(branch, 'Condition'))
        editor.remove_nodes([old])
    after = inspect_copy_routing_graph(blueprint)
    if (after['mode'] != COPY_ROUTING_VERSION or len(after['nodes']) != len(before['nodes'])
            or any(node not in after['nodes'] for node in unchanged)
            or any(node in after['nodes'] for node in old_checks)):
        raise RuntimeError('Graph replacement identity/count guard failed')
    return {'replaced_check_count': 37, 'already_patched': False, 'node_count': len(after['nodes']),
            'preserved_other_node_count': len(unchanged), 'mode': COPY_ROUTING_VERSION,
            'before_function_evidence': before['function_evidence'], 'after_function_evidence': after['function_evidence']}


def _saved_build_state(bp, plan):
    """Accept old completed v1 assets; only explicitly owned partials can resume."""
    u = _ue()
    if (not isinstance(bp, u.Blueprint)
            or u.EditorAssetLibrary.get_metadata_tag(bp, OWNER_TAG) != digest(list(COMPONENTS))
            or u.EditorAssetLibrary.get_metadata_tag(bp, 'CompleteSourceSHA256') != plan['sources']['standard_candidate']['sha256']):
        raise RuntimeError('Refusing to overwrite an unrecognized Blueprint')
    state = str(u.EditorAssetLibrary.get_metadata_tag(bp, BUILD_STATE_TAG) or '')
    if state in {'', 'complete'}:
        if bp.get_editor_property('status') != u.BlueprintStatus.BS_UP_TO_DATE:
            raise RuntimeError('Previously complete Blueprint is no longer compiled; refusing automatic repair')
        return 'complete'
    if state not in {'in_progress', 'cancelled', 'failed'}:
        raise RuntimeError('Unknown incomplete Blueprint state: ' + state)
    return 'resume'


def _checkpoint_blueprint(bp, state):
    """Save an owned unfinished BP without claiming successful completion."""
    u, errors = _ue(), []
    u.EditorAssetLibrary.set_metadata_tag(bp, BUILD_STATE_TAG, state)
    try:
        u.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        errors.append('compile: ' + str(exc))
    try:
        saved = bool(u.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False))
        if not saved:
            errors.append('save returned false')
    except Exception as exc:
        saved = False
        errors.append('save: ' + str(exc))
    return {'blueprint_path': object_path(bp), 'state': state, 'checkpoint_saved': saved, 'errors': errors}


def _template_handles(bp, subsystem):
    u, b = _ue(), _base()
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    root, by_name = None, {}
    for handle in handles:
        data = b.get_data(handle)
        if u.SubobjectDataBlueprintFunctionLibrary.is_root_component(data):
            root = handle
        if isinstance(b.get_component(handle), u.SkeletalMeshComponent):
            name = str(u.SubobjectDataBlueprintFunctionLibrary.get_variable_name(data))
            if name not in COMPONENTS or name in by_name:
                raise RuntimeError('Unknown/duplicate component in incomplete Blueprint: ' + name)
            by_name[name] = handle
    if root is None:
        raise RuntimeError('Blueprint has no scene root')
    return root, by_name


def build_blueprints(plan, prepared, progress=None):
    _assert_level()
    _verify_plan(plan)
    progress = progress or BuildProgress()
    u, base, reports = _ue(), _base(), {}
    active_bp, sex = None, None
    try:
        progress.tick('build_begin', plan_sha256=plan['plan_sha256'])
        for sex in SEXES:
            destination = blueprint_path(sex)
            progress.tick('blueprint_begin', sex, blueprint_path=destination)
            resumed = False
            if u.EditorAssetLibrary.does_asset_exist(destination):
                bp = u.load_asset(destination)
                if _saved_build_state(bp, plan) == 'complete':
                    reports[sex] = {'blueprint_path': destination, 'reused': True,
                                    'copy_routing': u.EditorAssetLibrary.get_metadata_tag(bp, COPY_ROUTING_TAG) or 'legacy_component_tags_requires_explicit_patch',
                                    'builder_source_sha256': u.EditorAssetLibrary.get_metadata_tag(bp, BUILD_CODE_TAG) or 'not_recorded_by_legacy_builder'}
                    progress.tick('blueprint_reused', sex)
                    continue
                if actor_for(sex) is not None:
                    raise RuntimeError('Incomplete Blueprint is already instanced in the review scene; refusing rebuild')
                resumed = True
            else:
                folder, name = base.blueprint_asset_name(destination)
                factory = u.BlueprintFactory()
                factory.set_editor_property('parent_class', u.Actor)
                bp = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Blueprint, factory)
                if not isinstance(bp, u.Blueprint):
                    raise RuntimeError('Cannot create isolated Blueprint: ' + destination)
                u.EditorAssetLibrary.set_metadata_tag(bp, OWNER_TAG, digest(list(COMPONENTS)))
                u.EditorAssetLibrary.set_metadata_tag(bp, 'CompleteSourceSHA256', plan['sources']['standard_candidate']['sha256'])
            active_bp = bp
            u.EditorAssetLibrary.set_metadata_tag(bp, BUILD_STATE_TAG, 'in_progress')
            u.EditorAssetLibrary.set_metadata_tag(bp, BUILD_CODE_TAG, LOADED_SOURCE_SHA256)
            subsystem = u.get_engine_subsystem(u.SubobjectDataSubsystem)
            root, existing = _template_handles(bp, subsystem)
            base_rows = {r['component_name']: r for r in prepared[sex]['assignments'] if r['component_name'] in BASES}
            body_handle = existing.get('Body')
            for index, component_name in enumerate(COMPONENTS):
                handle = existing.get(component_name)
                if handle is None:
                    handle, failure = subsystem.add_new_subobject(u.AddNewSubobjectParams(
                        parent_handle=root if component_name == 'Body' else body_handle,
                        new_class=u.SkeletalMeshComponent, blueprint_context=bp))
                    if not failure.is_empty() or not subsystem.rename_subobject(handle=handle, new_name=u.Text(component_name)):
                        raise RuntimeError('Cannot create fixed component: ' + component_name)
                component = base.get_component(handle)
                if component_name == 'Body':
                    body_handle = handle
                    component.set_editor_property('propagate_curves_to_followers', True)
                component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
                component.set_editor_property('component_use_fixed_skel_bounds', False)
                if component_name != 'Body':
                    component.set_editor_property('use_bounds_from_leader_pose_component', False)
                component.set_update_animation_in_editor(True)
                component.set_allow_anim_curve_evaluation(True)
                if component_name in base_rows:
                    component.set_skeletal_mesh_asset(base_rows[component_name]['mesh'])
                component.set_visibility(component_name in BASES, False)
                component.set_hidden_in_game(component_name not in BASES)
                progress.tick('template_component_complete', sex, component_name, completed=index + 1, total=len(COMPONENTS))
            progress.tick('initial_compile_begin', sex)
            u.BlueprintEditorLibrary.compile_blueprint(bp)
            progress.tick('initial_compile_complete', sex)
            graph_record = build_construction_graph(bp, progress, sex)
            progress.tick('final_compile_begin', sex)
            u.BlueprintEditorLibrary.compile_blueprint(bp)
            if bp.get_editor_property('status') != u.BlueprintStatus.BS_UP_TO_DATE:
                raise RuntimeError('Fixed-slot Blueprint failed to compile')
            progress.tick('save_begin', sex)
            u.EditorAssetLibrary.set_metadata_tag(bp, BUILD_STATE_TAG, 'complete')
            u.EditorAssetLibrary.set_metadata_tag(bp, COPY_ROUTING_TAG, COPY_ROUTING_VERSION)
            if not u.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False):
                raise RuntimeError('Cannot save fixed-slot Blueprint')
            reports[sex] = {'blueprint_path': destination, 'reused': False, 'resumed_incomplete': resumed,
                            'construction': graph_record, 'builder_source_sha256': LOADED_SOURCE_SHA256}
            active_bp = None
            progress.tick('blueprint_complete', sex)
        progress.tick('build_complete', check_cancel=False, status='complete')
    except Exception as exc:
        state = 'cancelled' if isinstance(exc, BuildCancelled) else 'failed'
        checkpoint = None
        if active_bp is not None:
            progress.tick('checkpoint_begin', sex, check_cancel=False,
                          status='stopping' if state == 'cancelled' else 'failed', error=str(exc))
            try:
                checkpoint = _checkpoint_blueprint(active_bp, state)
            except Exception as checkpoint_error:
                checkpoint = {'checkpoint_saved': False, 'errors': [str(checkpoint_error)]}
        progress.tick('build_' + state, sex, check_cancel=False, status=state,
                      error=str(exc), checkpoint=checkpoint, completed_blueprints=reports)
        raise
    return reports


def _set_instance_property(component, name, value):
    # Editor change notification can rerun the owning Blueprint construction
    # script and destroy every SCS component while this switch holds references.
    # Native setters below perform the needed rendering/animation updates.
    component.set_editor_property(name, value, notify_mode=_ue().PropertyAccessChangeNotifyMode.NEVER)


def _set_override_materials(component, values):
    old = list(component.get_editor_property('override_materials'))
    values = list(values)
    for index in range(max(len(old), len(values))):
        previous = old[index] if index < len(old) else None
        target = values[index] if index < len(values) else None
        if previous != target:
            component.set_material(index, target)  # Native render-state update.
    _set_instance_property(component, 'override_materials', values)


def _set_component(component, row, body):
    u = _ue()
    component.modify()
    _set_override_materials(component, [])
    if component == body:
        if component.get_skeletal_mesh_asset() != row['mesh']:
            raise RuntimeError('Body identity may not change during an outfit switch')
        component.set_visibility(True, False)
        component.set_hidden_in_game(False)
        return
    component.set_leader_pose_component(None, True, False)
    component.set_anim_instance_class(None)
    component.set_skeletal_mesh_asset(row['mesh'] if row else None)
    tags = [t for t in component.get_editor_property('component_tags') if str(t) != COPY_TAG]
    copy = row and row['compatibility']['follow_mode'] == 'copy_pose'
    if copy:
        tags.append(u.Name(COPY_TAG))
    _set_instance_property(component, 'component_tags', tags)
    if row:
        if copy:
            component.set_animation_mode(u.AnimationMode.ANIMATION_BLUEPRINT)
            component.set_anim_instance_class(row['copy_pose_blueprint'].generated_class())
            component.add_tick_prerequisite_component(body)
        else:
            component.remove_tick_prerequisite_component(body)
            component.set_leader_pose_component(body, True, False)
    else:
        component.remove_tick_prerequisite_component(body)
    _set_instance_property(component, 'use_bounds_from_leader_pose_component', bool(row and not copy))
    component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    component.set_update_animation_in_editor(bool(row))
    component.set_component_tick_enabled(bool(row))
    component.set_visibility(bool(row), False)
    component.set_hidden_in_game(not bool(row))


def _snapshot(component):
    return {'mesh': component.get_skeletal_mesh_asset(),
            'materials': list(component.get_editor_property('override_materials')),
            'leader': component.get_editor_property('leader_pose_component'),
            'anim_class': component.get_editor_property('anim_class'),
            'mode': component.get_animation_mode(), 'tags': list(component.get_editor_property('component_tags')),
            'visible': component.is_visible(), 'hidden': component.get_editor_property('hidden_in_game'),
            'tick': component.is_component_tick_enabled(),
            'leader_bounds': component.get_editor_property('use_bounds_from_leader_pose_component')}


def _restore(component, old, body):
    if component == body:
        _set_override_materials(component, old['materials'])
        component.set_visibility(old['visible'], False)
        component.set_hidden_in_game(old['hidden'])
        return  # Body motion/instance are not changed during apply or rollback.
    component.set_leader_pose_component(None, True, False)
    component.set_anim_instance_class(None)
    component.set_skeletal_mesh_asset(old['mesh'])
    _set_override_materials(component, old['materials'])
    _set_instance_property(component, 'component_tags', old['tags'])
    component.set_animation_mode(old['mode'])
    component.set_anim_instance_class(old['anim_class'])
    component.set_leader_pose_component(old['leader'], True, False)
    component.set_visibility(old['visible'], False)
    component.set_hidden_in_game(old['hidden'])
    component.set_component_tick_enabled(old['tick'])
    _set_instance_property(component, 'use_bounds_from_leader_pose_component', old['leader_bounds'])
    if COPY_TAG in [str(t) for t in old['tags']]:
        component.add_tick_prerequisite_component(body)
    else:
        component.remove_tick_prerequisite_component(body)


def expected_actor_copy_tags(assignments):
    names = [r['component_name'] for r in assignments
             if r['component_name'] != 'Body' and r['compatibility']['follow_mode'] == 'copy_pose']
    if len(names) != len(set(names)) or any(n not in COMPONENTS[1:] for n in names):
        raise RuntimeError('Invalid/duplicate CopyPose slot')
    return [ACTOR_COPY_PREFIX + name for name in COMPONENTS[1:] if name in names]


def _set_actor_copy_tags(actor, expected):
    tags = [t for t in actor.get_editor_property('tags') if not str(t).startswith(ACTOR_COPY_PREFIX)]
    _set_instance_property(actor, 'tags', tags + [_ue().Name(t) for t in expected])


def apply_prepared(plan, prepared):
    _assert_level()
    _verify_plan(plan)
    actors = {sex: _owned_actor(sex) for sex in SEXES}
    components = {sex: actor_components(actor) for sex, actor in actors.items()}
    for sex in SEXES:
        if components[sex]['Body'].get_skeletal_mesh_asset() != prepared[sex]['body_mesh']:
            raise RuntimeError('Wrong complete body on fixed-slot actor: ' + sex)
        for name, component in components[sex].items():
            if name != 'Body' and component.get_attach_parent() != components[sex]['Body']:
                raise RuntimeError('Follower detached from same-actor Body: ' + name)
    # This runtime has never installed hidden-bone/section/topology masks. Refuse
    # foreign mask state rather than claiming it was removed by clearing a mesh.
    for actor in actors.values():
        if any(str(t).startswith('DM_CCWH_OCCLUSION_') for t in actor.tags):
            raise RuntimeError('Unsupported body occlusion state; restore its owning mask implementation first')
    snapshots = {sex: {name: _snapshot(c) for name, c in cs.items()} for sex, cs in components.items()}
    actor_tags = {sex: list(actor.get_editor_property('tags')) for sex, actor in actors.items()}
    desired_tags = {sex: expected_actor_copy_tags(prepared[sex]['assignments']) for sex in SEXES}
    try:
        for sex, cs in components.items():
            _set_actor_copy_tags(actors[sex], desired_tags[sex])
            selected = {r['component_name']: r for r in prepared[sex]['assignments']}
            for name in COMPONENTS:
                _set_component(cs[name], selected.get(name), cs['Body'])
        for sex, actor in actors.items():
            current = actor_components(actor)
            changed = [name for name in COMPONENTS if current[name] != components[sex][name]]
            if changed:
                raise RuntimeError('Fixed components were reconstructed during switch: ' + sex + '/' + ','.join(changed))
        result = readback(plan, prepared)
        result['component_identity_stable'] = True
        if not result['success']:
            raise RuntimeError('Post-apply readback failed: ' + json.dumps(result['errors']))
        return result
    except Exception as exc:
        rollback_errors = []
        for sex, original in components.items():
            try:
                _set_instance_property(actors[sex], 'tags', actor_tags[sex])
                if list(actors[sex].get_editor_property('tags')) != actor_tags[sex]:
                    raise RuntimeError('restored actor tags differ')
            except Exception as rollback:
                rollback_errors.append(f'{sex}/actor_tags: {rollback}')
            try:
                cs = actor_components(actors[sex])
            except Exception as rollback:
                rollback_errors.append(f'{sex}/resolve_current_components: {rollback}')
                continue
            expected = {}
            for name, component in cs.items():
                try:
                    old = dict(snapshots[sex][name])
                    if old['leader'] == original['Body']:
                        old['leader'] = cs['Body']
                    expected[name] = old
                    _restore(component, old, cs['Body'])
                except Exception as rollback:
                    rollback_errors.append(f'{sex}/{name}: {rollback}')
            try:
                current = actor_components(actors[sex])
                for name, old in expected.items():
                    if current[name] != cs[name] or _snapshot(current[name]) != old:
                        rollback_errors.append(f'{sex}/{name}: restored state or component identity differs')
            except Exception as rollback:
                rollback_errors.append(f'{sex}/verify_current_components: {rollback}')
        raise RuntimeError(f'Apply failed: {exc}; rollback_errors={rollback_errors}') from exc


def readback(plan, prepared=None):
    """Read only, including after save/reload. Never silently repairs followers."""
    _assert_level()
    if prepared is None:
        prepared = preflight(plan)
    rows, errors = {}, []
    for sex, character in plan['characters'].items():
        actor = _owned_actor(sex)
        cs = actor_components(actor)
        selected = {r['component_name']: r for r in character['assignments']}
        loaded = {r['component_name']: r for r in prepared[sex]['assignments']} if prepared else {}
        tags = [str(t) for t in actor.get_editor_property('tags')]
        slot_tags = [t for t in tags if t.startswith(ACTOR_COPY_PREFIX)]
        expected_tags = expected_actor_copy_tags(prepared[sex]['assignments'])
        if sorted(slot_tags) != sorted(expected_tags):
            errors.append(f'{sex}/actor_copy_tags')
        records = []
        for name in COMPONENTS:
            c, expected = cs[name], selected.get(name)
            mesh = c.get_skeletal_mesh_asset()
            copy = COPY_TAG in [str(t) for t in c.get_editor_property('component_tags')]
            leader = c.get_editor_property('leader_pose_component')
            record = {'component_name': name, 'component_path': object_path(c),
                      'mesh_path': object_path(mesh), 'expected_mesh_path': expected['mesh_path'] if expected else None,
                      'owner_key': expected.get('owner_key') if expected else None,
                      'visible': bool(c.is_visible()), 'hidden_in_game': bool(c.get_editor_property('hidden_in_game')),
                      'override_material_count': len(c.get_editor_property('override_materials')),
                      'leader_is_body': leader == cs['Body'], 'leader_path': object_path(leader),
                      'attach_parent_is_body': c.get_attach_parent() == cs['Body'],
                      'anim_class': object_path(c.get_editor_property('anim_class')),
                      'actor_copy_tag': ACTOR_COPY_PREFIX + name in tags,
                      'follow_mode': 'body' if name == 'Body' else 'copy_pose' if copy else 'leader_pose' if leader else 'none'}
            problems = []
            if record['mesh_path'] != record['expected_mesh_path']:
                problems.append('wrong_mesh_or_stale_unused_slot')
            if record['visible'] != bool(expected) or record['hidden_in_game'] == bool(expected):
                problems.append('visibility')
            if record['override_material_count']:
                problems.append('stale_material_override')
            if name != 'Body':
                if not record['attach_parent_is_body']:
                    problems.append('not_attached_to_body')
                if expected:
                    expected_copy = loaded[name]['compatibility']['follow_mode'] == 'copy_pose' if name in loaded else copy
                    if expected_copy:
                        expected_class = object_path(loaded[name]['copy_pose_blueprint'].generated_class()) if name in loaded else None
                        if leader is not None or not copy or not record['actor_copy_tag'] or not record['anim_class'] or (expected_class and record['anim_class'] != expected_class):
                            problems.append('copy_pose_binding')
                    elif not record['leader_is_body'] or copy or record['actor_copy_tag'] or record['anim_class'] is not None:
                        problems.append('leader_pose_binding')
                elif record['anim_class'] is not None or copy or record['actor_copy_tag']:
                    problems.append('stale_unused_animation')
            record['errors'] = problems
            errors += [f'{sex}/{name}/{p}' for p in problems]
            records.append(record)
        rows[sex] = {'actor_label': actor.get_actor_label(), 'actor_path': object_path(actor),
                     'actor_tags': tags, 'expected_actor_copy_tags': expected_tags,
                     'class': object_path(actor.get_class()), 'component_count': len(cs), 'components': records}
    return {'success': not errors, 'characters': rows, 'errors': errors,
            'plan_sha256': plan['plan_sha256'], 'limitations': dict(UNRESOLVED)}


def _backup_receipt(backup):
    if not isinstance(backup, dict) or set(backup) != {'path', 'sha256'}:
        raise RuntimeError('Migration requires a backup receipt path and SHA256')
    receipt_path = Path(backup['path']).resolve()
    if not receipt_path.is_relative_to(ROOT.resolve()) or source_record(receipt_path)['sha256'] != backup['sha256']:
        raise RuntimeError('Backup receipt is outside review outputs or its hash changed')
    receipt = read_json(receipt_path)
    destination = receipt.get('backup_level', '')
    if (receipt.get('success') is not True or receipt.get('source_level') != LEVEL
            or not destination.startswith(ASSET_ROOT + '/Backups/')
            or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', destination)):
        raise RuntimeError('Receipt does not identify a successful independent review-level backup')
    u = _ue()
    if not isinstance(u.load_asset(destination), u.World):
        raise RuntimeError('Backup World cannot be loaded: ' + destination)
    return receipt


def migrate(plan, prepared, backup):
    """Create two new actors and hide legacy preview actors after verification.

    Old actors are retained in the backed-up review map, hidden and tick-disabled;
    no source assets or original Blueprint actors outside this level are touched.
    A root-only cleanup can be performed separately after human acceptance.
    """
    _assert_level()
    _verify_plan(plan)
    receipt = _backup_receipt(backup)
    u, review = _ue(), _review()
    if any(actor_for(sex) is not None for sex in SEXES):
        raise RuntimeError('Migration is only for an unmigrated pair; use apply afterwards')
    old_bodies = {sex: review.find(f'DM_CCWH_{sex}_Body') for sex in SEXES}
    legacy = []
    pattern = re.compile(r'^DM_CCWH_(female|male)_(Body|Part_[A-Za-z_]+|Cloth_[A-Za-z0-9]+|Hair_\d+)$')
    for actor in review.actors().get_all_level_actors():
        if pattern.fullmatch(actor.get_actor_label()):
            if not isinstance(actor, u.SkeletalMeshActor):
                raise RuntimeError('Unexpected old preview actor class: ' + actor.get_actor_label())
            legacy.append(actor)
    for sex, old in old_bodies.items():
        if old is None or review.component(old).get_skeletal_mesh_asset() != prepared[sex]['body_mesh']:
            raise RuntimeError('Legacy review Body is missing or not the authorized complete character')
    spawned, old_visibility = [], []
    try:
        for sex in SEXES:
            bp = u.load_asset(blueprint_path(sex))
            if not isinstance(bp, u.Blueprint) or _saved_build_state(bp, plan) != 'complete':
                raise RuntimeError('Build the owned fixed-slot Blueprint first: ' + sex)
            old = old_bodies[sex]
            actor = review.actors().spawn_actor_from_class(bp.generated_class(), old.get_actor_location(), old.get_actor_rotation())
            if actor is None:
                raise RuntimeError('Cannot spawn new review character')
            spawned.append(actor)
            actor.set_actor_label(actor_label(sex))
            actor.set_actor_scale3d(old.get_actor_scale3d())
            actor.set_editor_property('tags', [u.Name(OWNER_TAG)])
        result = apply_prepared(plan, prepared)
        for actor in legacy:
            c = review.component(actor)
            old_visibility.append((actor, actor.is_temporarily_hidden_in_editor(), actor.get_editor_property('hidden'),
                                   c.is_component_tick_enabled(), c.is_visible(), c.get_editor_property('hidden_in_game')))
            actor.modify()
            c.modify()
            actor.set_is_temporarily_hidden_in_editor(True)
            actor.set_actor_hidden_in_game(True)
            c.set_component_tick_enabled(False)
            # Component visibility and actor game-hidden state are serialized;
            # temporary editor hiding alone would not survive map reload.
            c.set_visibility(False, False)
            c.set_hidden_in_game(True)
        result['migration'] = {'backup': backup, 'backup_level': receipt['backup_level'],
                               'legacy_hidden_labels': [a.get_actor_label() for a in legacy],
                               'new_actor_labels': [a.get_actor_label() for a in spawned],
                               'source_assets_modified': False}
        return result
    except Exception:
        for actor, editor_hidden, game_hidden, tick, visible, hidden in old_visibility:
            actor.set_is_temporarily_hidden_in_editor(editor_hidden)
            actor.set_actor_hidden_in_game(game_hidden)
            review.component(actor).set_component_tick_enabled(tick)
            review.component(actor).set_visibility(visible, False)
            review.component(actor).set_hidden_in_game(hidden)
        for actor in spawned:
            review.actors().destroy_actor(actor)
        raise


def run(request):
    mode = request.get('mode', 'dryrun')
    if mode not in MODES:
        raise ValueError('Unknown fixed-slot mode: ' + str(mode))
    plan = make_plan(request['registry_path'], request['choices'], request.get('source_registry_path', STANDARD))
    if request.get('expected_plan_sha256', plan['plan_sha256']) != plan['plan_sha256']:
        raise ValueError('Plan no longer matches expected SHA256')
    result = {'mode': mode, 'plan': plan, 'success': True, 'limitations': dict(UNRESOLVED)}
    if mode == 'dryrun':
        return result
    prepared = preflight(plan)
    result['prepared'] = prepared  # In-process data for root camera/animation controller.
    if mode == 'preflight':
        result['compatibility'] = {sex: [{k: v for k, v in row.items() if k not in {'mesh', 'copy_pose_blueprint'}}
                                       for row in entry['followers']] for sex, entry in prepared.items()}
    elif mode == 'build':
        progress = BuildProgress(request.get('build_control'))
        try:
            result['build'] = build_blueprints(plan, prepared, progress)
        except BuildCancelled as exc:
            result.update(success=False, cancelled=True, error=str(exc))
        result['build_progress'] = progress.last
    else:
        if mode == 'migrate':
            result['readback'] = migrate(plan, prepared, request.get('backup'))
        elif mode == 'apply':
            result['readback'] = apply_prepared(plan, prepared)
        else:
            result['readback'] = readback(plan, prepared)
        result['success'] = result['readback']['success']
    return result


if 'DM_FIXED_SLOT_REQUEST' in globals():
    DM_FIXED_SLOT_RESULT = run(globals()['DM_FIXED_SLOT_REQUEST'])
    print('DM_FIXED_SLOT_RESULT=' + json.dumps({k: v for k, v in DM_FIXED_SLOT_RESULT.items() if k != 'prepared'}, ensure_ascii=False))
