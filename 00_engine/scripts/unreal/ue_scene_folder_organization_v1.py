"""Root-serialized UE scene relocation, preserving historical receipts.

Owned by Character Factory SCENE_CAMERA_SEQUENCE section 13. No MRQ work.
"""
from pathlib import Path
import json
import hashlib
import re
from datetime import datetime, timezone

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/scene_folder_organization_20261012_v1')
PROJECT = Path('D:/UE/projects/datatry_02')
ENTRY = '/Game/DataMake/Validation/CameraMotionPilot20261009/MapsV2/L_cam_01_static_front_v003'
INDEX = Path('D:/UE/Lance_Work/00_engine/outputs/camera_motion_scene_alignment_20261012_v1/scenes/gallery_scene_index_v1.json')

# Exactly three original unused redirectors may retire with complete evidence.
# The original baseline remains immutable; no other missing identity is allowed.
KOWLOON_BASELINE_SHA256 = '714f9a9d5a34372265879e99b02f12b894d66592b89d118ac4c402fa726ed1b0'
KOWLOON_REDIRECTOR_BACKUP_SHA256 = 'b8d437f96e7f892400f0fa20fdc13b64b9042fcca126c765cd00417141f58e26'
KOWLOON_REDIRECTOR_BACKUP = Path('D:/UE/Lance_Work/00_engine/temp/scene_folder_organization_20261012_v1/rollback/Content/Kowloon/Blueprints/Windows/BP_Two_Windows_01.uasset')

# Official UE 5.8.1 (CL 56057345) CoreRedirects, BaseEngine.ini:1181.
# Only this fully qualified class pair is equivalent. Package/object identities
# and actor classes in map signatures are not rewritten by this alias.
MRQ_CONFIG_CLASS_REDIRECT = {
    'old_name': '/Script/MovieRenderPipelineCore.MoviePipelineMasterConfig',
    'new_name': '/Script/MovieRenderPipelineCore.MoviePipelinePrimaryConfig',
    'source': 'D:/UE/UE_5.8/Engine/Config/BaseEngine.ini',
    'section': 'CoreRedirects', 'source_line': 1181,
    'source_sha256': 'dc5b359ee95ccff0ccdfa4181b2875451b4a33474c0bb896fd8fef23aed1bf8e',
    'engine_version': '5.8.1-56057345+++UE5+Release-5.8',
    'build_source': 'D:/UE/UE_5.8/Engine/Build/Build.version',
    'build_sha256': 'd35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997'}

def write(name, data):
    RUN.mkdir(parents=True, exist_ok=True)
    path = RUN / name
    data['observed_at'] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return path

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def dirty(u):
    return sorted({p.get_name() for p in (
        list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) +
        list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()))})

def guard(u):
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
        raise RuntimeError('MRQ active: scene move prohibited')
    pending = dirty(u)
    if pending:
        raise RuntimeError('Unsaved packages preserved: ' + repr(pending))
    if str(u.Paths.get_project_file_path()).replace('\\', '/').lower() != str(PROJECT / 'datatry_02.uproject').lower():
        # Some editor builds return a relative project filename.
        if Path(u.Paths.get_project_file_path()).resolve() != (PROJECT / 'datatry_02.uproject').resolve():
            raise RuntimeError('Unexpected project')

def assets(u, root):
    return sorted((a for a in u.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(root, recursive=True)
                   if str(a.asset_class_path.asset_name) != 'DirectoryPlaceholder'),
                  key=lambda a: str(a.package_name))

def asset_record(a):
    return {'package': str(a.package_name), 'name': str(a.asset_name),
            'class': str(a.asset_class_path.package_name) + '.' + str(a.asset_class_path.asset_name)}

# Official UE 5.8.1 CoreRedirects, BaseEngine.ini:1326. Registry asset
# class only; package/name and map actor/component classes remain strict.
USER_DEFINED_STRUCT_CLASS_REDIRECT = {
    'old_name': '/Script/Engine.UserDefinedStruct',
    'new_name': '/Script/CoreUObject.UserDefinedStruct',
    'source': 'D:/UE/UE_5.8/Engine/Config/BaseEngine.ini',
    'section': 'CoreRedirects', 'source_line': 1326,
    'declaration': '+ClassRedirects=(OldName="/Script/Engine.UserDefinedStruct",NewName="/Script/CoreUObject.UserDefinedStruct")',
    'source_sha256': 'dc5b359ee95ccff0ccdfa4181b2875451b4a33474c0bb896fd8fef23aed1bf8e',
    'engine_version': '5.8.1-56057345+++UE5+Release-5.8',
    'build_source': 'D:/UE/UE_5.8/Engine/Build/Build.version',
    'build_sha256': 'd35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997'}


def canonical_registry_class(class_name):
    """Only two exact fully qualified official registry asset-class pairs."""
    for redirect in (MRQ_CONFIG_CLASS_REDIRECT, USER_DEFINED_STRUCT_CLASS_REDIRECT):
        if class_name.casefold() == redirect['old_name'].casefold():
            return redirect['new_name']
    return class_name


def normalized_records(rows, canonical_classes=True):
    # Early pilot records used Struct repr, which includes a transient memory
    # address. Preserve that original receipt, comparing its class fields only.
    result = []
    for row in rows:
        row = dict(row)
        if row['class'].startswith('<Struct '):
            match = re.search(r'package_name: "([^"]+)", asset_name: "([^"]+)"', row['class'])
            if not match:
                raise ValueError('Cannot normalize legacy class record')
            row['class'] = match[1] + '.' + match[2]
        if canonical_classes:
            row['class'] = canonical_registry_class(row['class'])
        result.append(row)
    return result


def class_redirect_witness(rows):
    """Pin each exact official registry asset-class alias only when used."""
    classes = {row['class'].casefold() for row in normalized_records(rows, canonical_classes=False)}
    witnesses = []
    if MRQ_CONFIG_CLASS_REDIRECT['old_name'].casefold() in classes:
        source = Path(MRQ_CONFIG_CLASS_REDIRECT['source'])
        build = Path(MRQ_CONFIG_CLASS_REDIRECT['build_source'])
        declaration = '+ClassRedirects=(OldName="' + MRQ_CONFIG_CLASS_REDIRECT['old_name'] + '", NewName="' + MRQ_CONFIG_CLASS_REDIRECT['new_name'] + '")'
        if (sha(source) != MRQ_CONFIG_CLASS_REDIRECT['source_sha256']
                or sha(build) != MRQ_CONFIG_CLASS_REDIRECT['build_sha256']
                or declaration not in source.read_text(encoding='utf-8-sig').splitlines()):
            raise RuntimeError('Official MRQ asset-class alias source or engine version changed')
        witnesses.append(dict(MRQ_CONFIG_CLASS_REDIRECT))
    if USER_DEFINED_STRUCT_CLASS_REDIRECT['old_name'].casefold() in classes:
        redirect = USER_DEFINED_STRUCT_CLASS_REDIRECT
        source, build = Path(redirect['source']), Path(redirect['build_source'])
        if (sha(source) != redirect['source_sha256']
                or sha(build) != redirect['build_sha256']
                or redirect['declaration'] not in source.read_text(encoding='utf-8-sig').splitlines()):
            raise RuntimeError('Official UserDefinedStruct asset-class alias source or engine version changed')
        witnesses.append(dict(redirect))
    return witnesses

def registry_identities(rows):
    # UE package/object/class names are FNames: identity is case-insensitive.
    # Renaming may refresh the display case from the physical uasset filename.
    return sorted(tuple(row[key].casefold() for key in ('package', 'name', 'class'))
                  for row in normalized_records(rows))

def normalize_object_path_case(value):
    if isinstance(value, dict):
        return {k: normalize_object_path_case(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_object_path_case(v) for v in value]
    return value.casefold() if isinstance(value, str) and value.startswith('/') else value


def signature_equal(left, right):
    """Only MID scalar/vector floats have tolerance; all other data exact."""
    import math
    def parameter_equal(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(parameter_equal(a[k], b[k]) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(parameter_equal(x, y) for x, y in zip(a, b))
        if type(a) in (float, int) and type(b) in (float, int):
            return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
        return a == b
    def exact(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys(): return False
            mid = a.get('kind') == b.get('kind') == 'MaterialInstanceDynamic'
            return all((parameter_equal(a[k], b[k]) if mid and k in ('scalar', 'vector') else exact(a[k], b[k])) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
        return a == b
    return exact(normalize_object_path_case(left), normalize_object_path_case(right))

def suspend_view_history(u):
    """Temporarily empty editor-only viewport history, never scene defaults.

    UE's native CDO reference check includes this cache and otherwise cancels
    unattended world renames. Preserve the user's original INI for restoration.
    """
    settings = PROJECT / 'Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini'
    preserved = RUN / 'editor_view_history_before_v1.ini'
    if not preserved.exists():
        preserved.write_bytes(settings.read_bytes())
    text = preserved.read_text(encoding='utf-8-sig')
    lines = [line for line in text.splitlines() if line.startswith('EditorViews=')]
    if len(lines) != 1:
        raise RuntimeError('Unknown editor view-history layout, preserved')
    # The editor is restarted with an empty EditorViews INI entry before moves.
    # Do not use editor console SET here: it is not dispatched in this build.
    write('editor_view_history_suspension_v1.json', {
        'scope': 'Native editor viewport history CDO only; source scenes and project settings unchanged',
        'backup': str(preserved), 'backup_sha256': sha(preserved),
        'restoration_required': True, 'method': 'editor restart with targeted saved-INI cache reset'})

def inventory(u):
    guard(u)
    registry = u.AssetRegistryHelpers.get_asset_registry()
    index = json.loads(INDEX.read_text(encoding='utf-8-sig'))
    roots = sorted({root for s in index['scenes'] for root in s['content_roots']})
    options = u.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                               include_hard_package_references=True)
    rows = []
    for root in roots:
        entries = assets(u, root)
        packages = {str(a.package_name) for a in entries}
        external = set()
        for package in packages:
            external.update(str(p) for p in (registry.get_referencers(package, options) or [])
                            if str(p) not in packages)
        rows.append({'root': root, 'asset_count': len(entries),
                     'assets': [asset_record(a) for a in entries],
                     'external_referencers': sorted(external),
                     'maps': [str(a.package_name) for a in entries if str(a.asset_class_path.asset_name) == 'World']})
    result = {'schema': 'scene_relocation_ue_inventory_v1', 'success': True,
              'engine': u.SystemLibrary.get_engine_version(), 'roots': rows,
              'dirty': dirty(u), 'camera_render_started': False}
    write('ue_inventory_v1.json', result)
    print('Scene inventory saved:', len(rows), 'roots')
    return result

def canon(path, root):
    path = str(path)
    new = '/Game/Scenes/' + root.removeprefix('/Game/')
    if path.casefold() == new.casefold() or path.casefold().startswith(new.casefold() + '/') or path.casefold().startswith(new.casefold() + '.'):
        return root + path[len(new):]
    return path

def material_signature(u, material, root, legacy=False):
    if material is None:
        return None
    if legacy or not isinstance(material, u.MaterialInstanceDynamic):
        return canon(material.get_path_name(), root)
    parent = material.get_editor_property('parent')
    base = material.get_base_material()
    result = {'kind': 'MaterialInstanceDynamic',
              'parent': material_signature(u, parent, root),
              'base': canon(base.get_path_name(), root) if base else None}
    # MaterialEditingLibrary getters for instances accept MIC only. Enumerate
    # through that library, but query actual MID values with its reflected API.
    for kind in ('scalar', 'vector', 'texture'):
        names = getattr(u.MaterialEditingLibrary, 'get_' + kind + '_parameter_names')(material)
        values = {}
        for name in sorted(names, key=lambda n: str(n).casefold()):
            value = getattr(material, 'get_' + kind + '_parameter_value')(name)
            if kind == 'scalar': value = float(value)
            elif kind == 'vector': value = [float(getattr(value, k)) for k in ('r', 'g', 'b', 'a')]
            else: value = canon(value.get_path_name(), root) if value else None
            values[str(name).casefold()] = value
        result[kind] = values
    # Name-only enumeration is not enough for layered overrides. Fail closed
    # rather than silently treating a layer parameter as the global parameter.
    node = material
    while isinstance(node, u.MaterialInstance):
        for kind in ('scalar', 'vector', 'texture'):
            for override in node.get_editor_property(kind + '_parameter_values'):
                info = override.get_editor_property('parameter_info')
                if info.get_editor_property('association') != u.MaterialParameterAssociation.GLOBAL_PARAMETER:
                    raise RuntimeError('Layered MID parameter requires explicit info-based signature')
        node = node.get_editor_property('parent')
    return result


def signature(u, map_path, root, legacy_materials=False):
    world = u.EditorLoadingAndSavingUtils.load_map(map_path)
    if not world:
        raise RuntimeError('Map failed to load: ' + map_path)
    expected = map_path + '.' + map_path.rsplit('/', 1)[-1]
    if world.get_path_name().casefold() != expected.casefold():
        raise RuntimeError('Wrong world loaded')
    actors = []
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
        components = []
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = c.get_editor_property('static_mesh')
            materials = [c.get_material(i) for i in range(c.get_num_materials())]
            components.append({'name': c.get_name(), 'mesh': canon(mesh.get_path_name(), root) if mesh else None,
                               'materials': [material_signature(u, m, root, legacy_materials) for m in materials],
                               'instances': c.get_instance_count() if isinstance(c, u.InstancedStaticMeshComponent) else None})
        actors.append({'name': actor.get_name(), 'class': canon(actor.get_class().get_path_name(), root),
                       'transform': [round(float(x), 4) for x in (loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll,
                                                                 scale.x, scale.y, scale.z)],
                       'components': sorted(components, key=lambda x: x['name'])})
    return {'map': canon(map_path, root), 'actor_count': len(actors),
            'actors': sorted(actors, key=lambda a: a['name']),
            'levels': sorted(canon(level.get_path_name(), root) for level in u.EditorLevelUtils.get_levels(world))}

def settled_signature(u, map_path, root, legacy_materials=False):
    """Warm initial construction, unload, then capture a fresh actual load."""
    signature(u, map_path, root, legacy_materials=legacy_materials)
    if not u.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry'):
        raise RuntimeError('Neutral unload failed')
    return signature(u, map_path, root, legacy_materials=legacy_materials)


def loading_protocol():
    proof = RUN / 'original_load_completion_probe_v1.json'
    if not proof.is_file():
        raise RuntimeError('Original load-completion evidence missing')
    return {'method': 'preload_target_unload_EngineEntry_reload_capture',
            'neutral_map': '/Engine/Maps/Entry', 'evidence_path': str(proof), 'evidence_sha256': sha(proof)}


def component_transforms(u):
    result = []
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        components = []
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            loc, rot, scale = (c.get_editor_property(key) for key in
                               ('relative_location', 'relative_rotation', 'relative_scale3d'))
            components.append({'name': c.get_name(), 'transform': [round(float(x), 4) for x in
                               (loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll, scale.x, scale.y, scale.z)]})
        result.append({'name': actor.get_name(), 'components': sorted(components, key=lambda x: x['name'])})
    return sorted(result, key=lambda a: a['name'])

def source_file_proof(root, physical_root, manifest_path):
    physical_root = Path(physical_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    if not manifest['success'] or root not in manifest['completed_roots']:
        raise RuntimeError('Root lacks completed rollback manifest')
    original = (PROJECT / 'Content' / root.removeprefix('/Game/')).resolve()
    expected = {}
    for f in manifest['files']:
        try: rel = Path(f['source']).resolve().relative_to(original).as_posix()
        except ValueError: continue
        expected[rel] = {'relative': rel, 'bytes': f['bytes'], 'sha256': f['sha256']}
    actual = {p.relative_to(physical_root).as_posix(): p for p in physical_root.rglob('*') if p.is_file()}
    if not expected or set(actual) != set(expected):
        raise RuntimeError('Original copy file set differs from pinned backup')
    for rel, p in sorted(actual.items()):
        if p.stat().st_size != expected[rel]['bytes'] or sha(p) != expected[rel]['sha256']:
            raise RuntimeError('Original copy SHA mismatch: ' + rel)
    return {'root': root, 'physical_root': str(physical_root), 'manifest_sha256': sha(manifest_path),
            'files': [expected[k] for k in sorted(expected)], 'success': True}


def collect_cold_baseline(u, root, physical_root, restore_map, receipt_filename=None):
    """Root-controlled isolated ORIGINAL project only. Never saves assets."""
    slug = root.removeprefix('/Game/').replace('/', '_')
    filename = receipt_filename or ('cold_baseline_' + slug + '_v1.json')
    if Path(filename).name != filename or not re.fullmatch(r'cold_baseline_' + re.escape(slug) + r'_v[1-9][0-9]*\.json', filename):
        raise ValueError('Invalid versioned cold baseline receipt filename')
    target = RUN / filename
    base_path = RUN / ('baseline_' + slug + '_v1.json')
    if target.exists() or root == '/Game/Synthwave_city':
        raise RuntimeError('Preserve existing cold baseline and Synthwave history')
    content_root = Path(u.Paths.project_content_dir()).resolve() / root.removeprefix('/Game/')
    if content_root.resolve() != Path(physical_root).resolve() or Path(u.Paths.project_dir()).resolve() == PROJECT.resolve():
        raise RuntimeError('Cold baseline requires exact isolated original root')
    if dirty(u) or u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor() or u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
        raise RuntimeError('Cold baseline requires clean idle original project')
    manifest = RUN / 'backup_manifest_v1.json'
    proof_before = source_file_proof(root, physical_root, manifest)
    base = json.loads(base_path.read_text(encoding='utf-8-sig'))
    entries = [asset_record(a) for a in assets(u, root)]
    if registry_identities(entries) != registry_identities(base['assets']):
        raise RuntimeError('Cold asset identities differ from warm baseline')
    maps, relative = [], {}
    try:
        for old in base['maps']:
            maps.append(settled_signature(u, old['map'], root))
            relative[old['map']] = component_transforms(u)
    finally:
        if not u.EditorLoadingAndSavingUtils.load_map(restore_map):
            raise RuntimeError('Cold baseline restore failed')
    proof_after = source_file_proof(root, physical_root, manifest)
    if proof_before != proof_after or dirty(u):
        raise RuntimeError('Cold source changed or remains dirty')
    return write(target.name, {'schema': 'scene_relocation_cold_baseline_v1', 'signature_format': 'mid_parameters_v2',
        'root': root, 'success': True, 'warm_baseline_sha256': sha(base_path), 'backup_manifest_sha256': sha(manifest),
        'source_proof_before': proof_before, 'source_proof_after': proof_after, 'assets': entries, 'maps': maps,
        'component_transforms': relative, 'saved_source_assets': False, 'loading_protocol': loading_protocol(),
        'scope': 'Isolated original cold load; full source SHA verified before/after. Only signatures supplement frozen warm baseline; identities unchanged.'})


def select_verification_baseline(root, base_path):
    warm = json.loads(Path(base_path).read_text(encoding='utf-8-sig'))
    slug = root.removeprefix('/Game/').replace('/', '_')
    pattern = re.compile(r'cold_baseline_' + re.escape(slug) + r'_v([1-9][0-9]*)\.json')
    candidates = [(int(match.group(1)), p) for p in RUN.glob('cold_baseline_' + slug + '_v*.json')
                  if (match := pattern.fullmatch(p.name))]
    if not candidates or root == '/Game/Synthwave_city':
        return warm, None
    # Latest numeric revision is authoritative even when invalid/failed.
    # Never silently fall back to an older success after a newer failure.
    cold_path = max(candidates, key=lambda item: item[0])[1]
    cold = json.loads(cold_path.read_text(encoding='utf-8-sig'))
    manifest_path = RUN / 'backup_manifest_v1.json'
    if (not cold.get('success') or cold.get('saved_source_assets') is not False or cold.get('root') != root or
        cold.get('signature_format') != 'mid_parameters_v2' or cold['warm_baseline_sha256'] != sha(base_path) or
        cold['backup_manifest_sha256'] != sha(manifest_path)):
        raise RuntimeError('Cold baseline pins/format invalid')
    proof = cold['source_proof_before']
    if proof != cold['source_proof_after'] or not proof['success'] or proof['manifest_sha256'] != sha(manifest_path) or proof['root'] != root:
        raise RuntimeError('Cold baseline source proofs differ')
    original = (PROJECT / 'Content' / root.removeprefix('/Game/')).resolve()
    expected = []
    for f in json.loads(manifest_path.read_text(encoding='utf-8-sig'))['files']:
        try: rel = Path(f['source']).resolve().relative_to(original).as_posix()
        except ValueError: continue
        expected.append({'relative': rel, 'bytes': f['bytes'], 'sha256': f['sha256']})
    if not expected or sorted(expected, key=lambda r:r['relative']) != proof['files']:
        raise RuntimeError('Cold proof lacks exact manifest file coverage')
    if registry_identities(cold['assets']) != registry_identities(warm['assets']) or sorted(m['map'] for m in cold['maps']) != sorted(m['map'] for m in warm['maps']):
        raise RuntimeError('Cold asset/map identities differ from warm baseline')
    if set(cold['component_transforms']) != {m['map'] for m in cold['maps']}:
        raise RuntimeError('Cold component transforms incomplete')
    return cold, {'path': str(cold_path), 'sha256': sha(cold_path), 'backup_manifest_sha256': cold['backup_manifest_sha256'],
                  'scope': cold['scope'], 'signature_format': cold['signature_format']}


def baseline(u, root):
    guard(u)
    slug = root.removeprefix('/Game/').replace('/', '_')
    path = RUN / ('baseline_' + slug + '_v1.json')
    if path.exists():
        raise RuntimeError('Baseline already exists, preserve it')
    entries = assets(u, root)
    maps = [str(a.package_name) for a in entries if str(a.asset_class_path.asset_name) == 'World']
    signatures, relative = [], {}
    for m in maps:
        signatures.append(settled_signature(u, m, root))
        relative[m] = component_transforms(u)
    result = {'schema': 'scene_relocation_baseline_v1', 'root': root,
              'assets': [asset_record(a) for a in entries],
              'maps': signatures, 'component_transforms': relative, 'success': True,
              'signature_format': 'mid_parameters_v2', 'loading_protocol': loading_protocol()}
    # Do not save the loaded source maps. Restore a neutral map before renaming.
    u.EditorLoadingAndSavingUtils.load_map(ENTRY)
    if dirty(u):
        raise RuntimeError('Baseline loading made packages dirty: ' + repr(dirty(u)))
    write(path.name, result)
    print('Baseline saved:', slug, len(entries), 'assets', len(maps), 'maps')

def move(u, root):
    guard(u)
    if root == '/Game/StarterContent' or not root.startswith('/Game/') or root.startswith('/Game/Scenes/'):
        raise ValueError('Protected or invalid scene root')
    slug = root.removeprefix('/Game/').replace('/', '_')
    baseline_path = RUN / ('baseline_' + slug + '_v1.json')
    baseline_data = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
    backup = json.loads((RUN / 'backup_manifest_v1.json').read_text(encoding='utf-8-sig'))
    if root not in backup['completed_roots'] or not backup['success']:
        raise RuntimeError('Verified rollback copy missing')
    destination = '/Game/Scenes/' + root.removeprefix('/Game/')
    destination_assets = assets(u, destination)
    if any(str(a.asset_class_path.asset_name) != 'DirectoryPlaceholder' for a in destination_assets):
        raise RuntimeError('Destination contains assets; inspect instead of overwrite')
    current = [asset_record(a) for a in assets(u, root)]
    if registry_identities(current) != registry_identities(baseline_data['assets']):
        raise RuntimeError('Source registry changed since baseline')
    suspend_view_history(u)
    intent = {'schema': 'scene_relocation_move_v1', 'root': root, 'destination': destination,
              'status': 'moving', 'success': False, 'baseline_sha256': sha(baseline_path),
              'method': 'UE EditorAssetSubsystem.rename_directory', 'camera_render_started': False}
    write('move_' + slug + '_v1.json', intent)
    succeeded = u.get_editor_subsystem(u.EditorAssetSubsystem).rename_directory(root, destination)
    intent['rename_returned'] = bool(succeeded)
    intent['dirty_after_rename'] = dirty(u)
    write('move_' + slug + '_v1.json', intent)
    if not succeeded:
        raise RuntimeError('UE rename reported failure; inspect partial relocation')
    pending = list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if pending and not u.EditorLoadingAndSavingUtils.save_packages(pending, True):
        raise RuntimeError('Cannot save renamed assets and referencers')
    intent['status'] = 'renamed_pending_verification'
    intent['dirty_after_save'] = dirty(u)
    write('move_' + slug + '_v1.json', intent)
    print('Scene renamed, verification pending:', root)

def compare_map(before, after, random_profiles=None):
    """Only proven palm-tree mesh/material alternatives may vary.

    All actor/component identities, transforms, instances, other meshes/materials
    and loaded levels remain strict. Profiles come from the isolated original
    scene, never from the moved scene under test.
    """
    if not random_profiles:
        return signature_equal(before, after), []
    import copy
    left, right = normalize_object_path_case(copy.deepcopy(before)), normalize_object_path_case(copy.deepcopy(after))
    random_profiles = {key.casefold(): {json.dumps(normalize_object_path_case(json.loads(p)), sort_keys=True)
                                       for p in values} for key, values in random_profiles.items()}
    permitted = []
    if len(left['actors']) != len(right['actors']):
        return False, []
    for a, b in zip(left['actors'], right['actors']):
        if a['name'] != b['name'] or a['class'] != b['class'] or len(a['components']) != len(b['components']):
            return False, []
        for x, y in zip(a['components'], b['components']):
            key = (a['class'] + '|' + x['name']).casefold()
            if x == y or key not in random_profiles or x['name'] != y['name']:
                continue
            def profile(c):
                return json.dumps({'mesh': c['mesh'], 'materials': c['materials']}, sort_keys=True)
            if profile(x) not in random_profiles[key] or profile(y) not in random_profiles[key]:
                return False, []
            permitted.append({'actor': a['name'], 'component': x['name']})
            y['mesh'], y['materials'] = x['mesh'], x['materials']
    return signature_equal(left, right), permitted

def compare_component_transforms(before, after, actor_classes=None, yaw_profiles=None):
    import copy
    left, right = copy.deepcopy(before), copy.deepcopy(after)
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a['name'] != b['name'] or len(a['components']) != len(b['components']):
            return False
        for x, y in zip(a['components'], b['components']):
            key = (actor_classes or {}).get(a['name'], '') + '|' + x['name']
            if x['name'] == y['name'] and key in (yaw_profiles or {}):
                if x['transform'][4] not in yaw_profiles[key] or y['transform'][4] not in yaw_profiles[key]:
                    return False
                y['transform'][4] = x['transform'][4]
    return left == right

# Japanese Village is a second independently pinned contract, never a general
# redirector exclusion. Its independent original-source target proof is required.
JAPANESE_BASELINE_SHA256 = 'de33a7b2a1a899efd32857e79d8bcb7ac537ad57067dd5555f6d61c4a295f7d6'
JAPANESE_REDIRECTOR_BACKUP_SHA256 = 'd44b489762eab059b1363e3d601e25dd1f83cd469becf4ce082da28931b4bce1'
JAPANESE_REDIRECTOR_BACKUP = Path('D:/UE/Lance_Work/00_engine/temp/scene_folder_organization_20261012_v1/rollback/Content/Japanese_Village/HDRI/pizzo_pernice_puresky_4k.uasset')


def japanese_verification_asset_contract(root, base_path, base):
    """Exclude only the one pinned Japanese Village redirector ID after validating proof.

    Missing proof keeps the original strict set. Other roots never use this
    exception. Asset, map and reference evidence is checked, not just flags.
    """
    proof_path = RUN / 'japanese_redirector_retirement_v1.json'
    if root != '/Game/Japanese_Village' or not proof_path.exists():
        return base['assets'], None

    def require(condition, message):
        if not condition:
            raise RuntimeError('Invalid Japanese_Village redirector retirement proof: ' + message)

    def same_path(left, right):
        return Path(left).resolve().as_posix().casefold() == Path(right).resolve().as_posix().casefold()

    def records(value):
        require(isinstance(value, list) and all(isinstance(r, dict) and set(r) == {'package', 'name', 'class'}
                and all(isinstance(v, str) and v for v in r.values()) for r in value), 'malformed asset records')
        return registry_identities(value)

    def under_old(package):
        require(isinstance(package, str), 'non-string package path')
        p = package.casefold()
        return p == root.casefold() or p.startswith(root.casefold() + '/')

    try:
        proof = json.loads(proof_path.read_text(encoding='utf-8-sig'))
        require(proof['schema'] == 'japanese_redirector_retirement_v1' and proof['success'] is True,
                'schema or success')
        destination = '/Game/Scenes/Japanese_Village'
        require(proof['root'] == root and proof['destination'] == destination and base['root'] == root,
                'root or destination')
        require(proof['camera_render_started'] is False, 'camera rendering started')
        require(proof['baseline_sha256'] == JAPANESE_BASELINE_SHA256 and sha(base_path) == JAPANESE_BASELINE_SHA256,
                'baseline hash')
        require(base == json.loads(Path(base_path).read_text(encoding='utf-8-sig')), 'baseline argument changed')
        backup = proof['original_backup']
        require(same_path(backup['path'], JAPANESE_REDIRECTOR_BACKUP)
                and backup['sha256'] == JAPANESE_REDIRECTOR_BACKUP_SHA256
                and sha(JAPANESE_REDIRECTOR_BACKUP) == JAPANESE_REDIRECTOR_BACKUP_SHA256, 'original backup pin')

        names = ('pizzo_pernice_puresky_4k',)
        old_package = root + '/HDRI/pizzo_pernice_puresky_4k'
        original_prefab = root + '/HDRI/SKY_HDRI'
        new_prefab = destination + '/HDRI/SKY_HDRI'
        retired = [{'package': old_package, 'name': n, 'class': '/Script/CoreUObject.ObjectRedirector'} for n in names]
        require(records(proof['retired_redirectors']) == records(retired), 'retired IDs differ')
        require(len(base['assets']) == 616 and records([r for r in base['assets'] if r in retired]) == records(retired),
                'original 616 identities or redirectors changed')
        expected_assets = [r for r in base['assets'] if r not in retired]
        require(len(expected_assets) == 615, 'retirement exceeds exactly one ID')

        target_pin = proof['original_target_witness']
        target_path = RUN / 'japanese_original_redirector_targets_v1.json'
        require(same_path(target_pin['path'], target_path) and target_pin['sha256'] == sha(target_path),
                'original target witness hash or path')
        original = json.loads(target_path.read_text(encoding='utf-8-sig'))
        require(original['schema'] == 'japanese_original_redirector_targets_v1' and original['success'] is True
                and original['root'] == root and original['source'] == 'isolated_original_backup_project'
                and original['camera_render_started'] is False and original['saved_source_packages'] == [],
                'original target witness protocol')
        require(all(original[key] == JAPANESE_REDIRECTOR_BACKUP_SHA256 for key in
                    ('original_backup_sha256', 'source_sha256_before', 'source_sha256_after')),
                'original source hash changed')
        source_project = Path(original['source_project'])
        source_file = Path(original['source_package_file'])
        require(source_project.is_absolute() and source_project.is_file() and source_project.suffix.casefold() == '.uproject'
                and not same_path(source_project, PROJECT / 'datatry_02.uproject')
                and same_path(source_file, source_project.parent / 'Content/Japanese_Village/HDRI/pizzo_pernice_puresky_4k.uasset')
                and sha(source_file) == JAPANESE_REDIRECTOR_BACKUP_SHA256, 'isolated source package')
        targets = [{'object_path': old_package + '.pizzo_pernice_puresky_4k', 'target': original_prefab + '.SKY_HDRI'}]
        require(original['original_redirector_targets'] == targets, 'original redirector targets')
        resolved_targets = [dict(targets[0], resolved_destination=new_prefab + '.SKY_HDRI')]
        require(proof['original_redirector_targets'] == resolved_targets, 'resolved redirector targets')

        actual_assets = proof['actual_assets']
        records(actual_assets)
        require(all(r['package'].startswith(destination + '/') for r in actual_assets), 'asset outside destination')
        actual = [dict(r, package=canon(r['package'], root)) for r in actual_assets]
        require(len(actual) == 615 and records(actual) == records(expected_assets), 'real asset identities differ')
        maps = proof['actual_maps']
        require(isinstance(maps, list) and len(maps) == len(base['maps']) == 23
                and [m['map'] for m in maps] == [m['map'] for m in base['maps']], '23 map identities')
        require(all(compare_map(before, after)[0] for before, after in zip(base['maps'], maps)), 'map signatures differ')
        relative = proof['component_transforms']
        require(isinstance(relative, dict) and set(relative) == set(base['component_transforms'])
                and all(compare_component_transforms(before, relative[path]) for path, before in base['component_transforms'].items()),
                'component transforms differ')

        old_packages = proof['old_packages']
        require(isinstance(old_packages, list) and all(under_old(p) for p in old_packages)
                and len(set(old_packages)) == len(old_packages) and old_package in old_packages, 'old package coverage')
        referencers = proof['old_referencers']
        require(isinstance(referencers, dict) and set(referencers) == set(old_packages)
                and all(isinstance(refs, list) and all(isinstance(r, str) and r in old_packages for r in refs)
                        for refs in referencers.values()), 'old root has outside referencers or incomplete evidence')
        dependencies = proof['destination_dependencies']
        require(isinstance(dependencies, dict) and set(dependencies) == {r['package'] for r in actual_assets}
                and all(isinstance(deps, list) and all(not under_old(p) for p in deps) for deps in dependencies.values()),
                'destination refers to old root or incomplete evidence')
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError('Invalid Japanese_Village redirector retirement proof: missing or malformed evidence') from exc

    witness = {'path': str(proof_path), 'sha256': sha(proof_path),
               'baseline_sha256': JAPANESE_BASELINE_SHA256,
               'original_backup': dict(backup), 'original_target_witness': dict(target_pin),
               'original_redirector_targets': resolved_targets, 'retired_redirectors': retired,
               'scope': 'Exactly the original unused HDRI texture redirector; all 615 real identities and 23 maps remain strict'}
    return expected_assets, witness


URBAN_BASELINE_SHA256 = '53308d60d3bd9cab47e0a3606c003a88d0248a6bdc34d12e2398995dfaa24a3f'
URBAN_MATERIAL_BACKUP_SHA256 = '37b97ff708b16b6ef3f175b76aaf8ce6bf749c20e7bd1a5cbfe2163b2cd4abb7'
URBAN_MATERIAL_BACKUP = Path('D:/UE/Lance_Work/00_engine/temp/scene_folder_organization_20261012_v1/rollback/Content/UrbanJapan/Materials/MI_Ubc_Building.uasset')
URBAN_ROOT = '/Game/UrbanJapan'
URBAN_DESTINATION = '/Game/Scenes/UrbanJapan'
URBAN_OLD_MATERIAL = URBAN_ROOT + '/Materials/MI_Ubc_Building.MI_BuildingDetails05'
URBAN_NEW_MATERIAL = URBAN_DESTINATION + '/Materials/MI_Ubc_Building.MI_Ubc_Building'
URBAN_PARAMETER_ARRAYS = tuple(kind + '_parameter_values' for kind in (
    'scalar', 'vector', 'double_vector', 'texture', 'texture_collection',
    'parameter_collection', 'runtime_virtual_texture', 'sparse_volume_texture', 'font'))
URBAN_STATIC_PARAMETER_SCOPE = ('Official named global static-switch values and override states at every MIC parent, '
                                'plus base defaults; protected/private static parameter structs are not read')


class _UrbanMaterialWitness(dict):
    """Only the fully validated one-object recovery can activate comparison."""


def urban_material_parameters(u, asset):
    """Read only MIC parameters through official reflected UE APIs.

    No missing property is ignored. Exported structs retain layer associations,
    indices, override flags and expression GUIDs; effective getters supplement
    the authored arrays. Identity itself is recorded by the surrounding proof.
    """
    if not isinstance(asset, u.MaterialInstanceConstant):
        raise RuntimeError('Urban material signature requires MaterialInstanceConstant')

    def text(value):
        if not isinstance(value, str) or not value:
            raise RuntimeError('Urban material signature has empty struct export')
        # Struct text embeds object paths inside quotes/parentheses. Normalize
        # only the scene prefix at a path boundary, preserving every leaf name.
        return re.sub(re.escape(URBAN_DESTINATION) + r'(?=[/.])', URBAN_ROOT, value, flags=re.IGNORECASE)

    def path(value):
        return canon(value.get_path_name(), URBAN_ROOT) if value else None

    def exported_array(name):
        return [text(entry.export_text()) for entry in asset.get_editor_property(name)]

    try:
        parent, base = asset.get_editor_property('parent'), asset.get_base_material()
        result = {'schema': 'urban_material_parameters_v1', 'class': '/Script/Engine.MaterialInstanceConstant',
                  'parent': path(parent), 'base': path(base), 'effective': {},
                  'parameter_arrays': {name: exported_array(name) for name in URBAN_PARAMETER_ARRAYS},
                  'base_property_overrides': text(asset.get_editor_property('base_property_overrides').export_text()),
                  'static_parameter_scope': URBAN_STATIC_PARAMETER_SCOPE,
                  'static_switch_hierarchy': [],
                  'additional_properties': {
                      'user_scene_texture_overrides': exported_array('user_scene_texture_overrides'),
                      'lightmass_settings': text(asset.get_editor_property('lightmass_settings').export_text()),
                      'phys_material': path(asset.get_editor_property('phys_material')),
                      'phys_material_mask': path(asset.get_editor_property('phys_material_mask')),
                      'subsurface_profile': path(asset.get_editor_property('subsurface_profile')),
                      'nanite_override_material': text(asset.get_editor_property('nanite_override_material').export_text())}}
        for kind in ('scalar', 'vector', 'texture', 'static_switch'):
            names = getattr(u.MaterialEditingLibrary, 'get_' + kind + '_parameter_names')(asset)
            values = {}
            for name in sorted(names, key=lambda n: str(n).casefold()):
                key = str(name).casefold()
                if key in values:
                    raise RuntimeError('Urban material has duplicate parameter names: ' + key)
                value = getattr(u.MaterialEditingLibrary, 'get_material_instance_' + kind + '_parameter_value')(asset, name)
                if kind == 'scalar': value = float(value)
                elif kind == 'vector': value = [float(getattr(value, k)) for k in ('r', 'g', 'b', 'a')]
                elif kind == 'texture': value = path(value)
                else: value = bool(value)
                values[key] = value
            result['effective'][kind] = values
        node, seen = asset, set()
        while node:
            node_path = node.get_path_name()
            if node_path.casefold() in seen:
                raise RuntimeError('Urban material parent cycle')
            seen.add(node_path.casefold())
            is_instance = isinstance(node, u.MaterialInstanceConstant)
            if not is_instance and not isinstance(node, u.Material):
                raise RuntimeError('Urban static-switch parent must be MIC or base Material')
            values = {}
            for name in sorted(u.MaterialEditingLibrary.get_static_switch_parameter_names(node), key=lambda n: str(n).casefold()):
                key = str(name).casefold()
                if key in values:
                    raise RuntimeError('Urban parent has duplicate static-switch names: ' + key)
                if is_instance:
                    value = u.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(node, name)
                    overridden = u.MaterialEditingLibrary.is_material_instance_parameter_overridden(node, name)
                else:
                    value = u.MaterialEditingLibrary.get_material_default_static_switch_parameter_value(node, name)
                    overridden = False
                values[key] = {'value': bool(value), 'overridden': bool(overridden)}
            result['static_switch_hierarchy'].append({'material': '$SELF' if node is asset else path(node),
                'kind': 'MaterialInstanceConstant' if is_instance else 'Material', 'values': values})
            node = node.get_editor_property('parent') if is_instance else None
        return result
    except Exception as exc:
        raise RuntimeError('Urban material parameter capture failed; no property was omitted: ' + str(exc)) from exc


def urban_comparison_signature(value, witness):
    """Comparison copy only; raw signatures and generic canon stay unchanged."""
    if (not isinstance(witness, _UrbanMaterialWitness)
            or witness.get('object_path_alias') != {'old': URBAN_OLD_MATERIAL, 'new': URBAN_NEW_MATERIAL}):
        raise RuntimeError('Urban material comparison requires validated witness')
    if isinstance(value, dict):
        return {k: urban_comparison_signature(v, witness) for k, v in value.items()}
    if isinstance(value, list):
        return [urban_comparison_signature(v, witness) for v in value]
    if isinstance(value, str):
        if value.casefold() == URBAN_NEW_MATERIAL.casefold():
            return URBAN_OLD_MATERIAL
        return canon(value, URBAN_ROOT)
    return value


def urban_verification_asset_contract(root, base_path, base):
    """Preserve all 486 records, accepting only one proven object-name repair."""
    proof_path = RUN / 'urban_material_relocation_v1.json'
    if root != URBAN_ROOT or not proof_path.exists():
        return base['assets'], None

    def require(condition, message):
        if not condition:
            raise RuntimeError('Invalid UrbanJapan material relocation proof: ' + message)

    def same_path(a, b):
        return Path(a).resolve().as_posix().casefold() == Path(b).resolve().as_posix().casefold()

    def records(rows):
        require(isinstance(rows, list) and all(isinstance(r, dict) and set(r) == {'package', 'name', 'class'}
                and all(isinstance(v, str) and v for v in r.values()) for r in rows), 'malformed asset records')
        ids = registry_identities(rows)
        require(len(ids) == len(set(ids)), 'duplicate asset records')
        return ids

    def signature(data):
        require(isinstance(data, dict) and data['schema'] == 'urban_material_parameters_v1'
                and data['class'] == '/Script/Engine.MaterialInstanceConstant', 'material signature format')
        require(all(isinstance(data[k], str) and data[k] for k in
                    ('parent', 'base', 'base_property_overrides')), 'incomplete material settings')
        require(data['static_parameter_scope'] == URBAN_STATIC_PARAMETER_SCOPE, 'static parameter proof scope')
        hierarchy = data['static_switch_hierarchy']
        require(isinstance(hierarchy, list) and len(hierarchy) >= 2 and hierarchy[0]['material'] == '$SELF'
                and hierarchy[0]['kind'] == 'MaterialInstanceConstant' and hierarchy[-1]['kind'] == 'Material'
                and hierarchy[-1]['material'] == data['base'] and hierarchy[1]['material'] == data['parent']
                and all(isinstance(node, dict) and set(node) == {'material', 'kind', 'values'}
                        and isinstance(node['material'], str) and node['material']
                        and node['kind'] == ('Material' if i == len(hierarchy) - 1 else 'MaterialInstanceConstant')
                        and isinstance(node['values'], dict) and all(isinstance(name, str) and name
                            and isinstance(v, dict) and set(v) == {'value', 'overridden'}
                            and type(v['value']) is bool and type(v['overridden']) is bool
                            for name, v in node['values'].items()) for i, node in enumerate(hierarchy)),
                'complete named static-switch parent hierarchy')
        require(isinstance(data['effective'], dict)
                and set(data['effective']) == {'scalar', 'vector', 'texture', 'static_switch'}
                and all(isinstance(v, dict) for v in data['effective'].values()), 'effective parameters incomplete')
        arrays = data['parameter_arrays']
        require(isinstance(arrays, dict) and set(arrays) == set(URBAN_PARAMETER_ARRAYS)
                and all(isinstance(v, list) and all(isinstance(x, str) and x for x in v) for v in arrays.values()),
                'override parameter arrays incomplete')
        return data

    def pinned_json(pin, filename):
        path = RUN / filename
        require(same_path(pin['path'], path) and pin['sha256'] == sha(path), 'linked evidence hash or path')
        return json.loads(path.read_text(encoding='utf-8-sig'))

    try:
        proof = json.loads(proof_path.read_text(encoding='utf-8-sig'))
        require(proof['schema'] == 'urban_material_relocation_v1' and proof['success'] is True
                and proof['camera_render_started'] is False, 'schema or completion flags')
        require(proof['root'] == root and base['root'] == root
                and proof['destination'] == URBAN_DESTINATION, 'root or destination')
        require(proof['baseline_sha256'] == URBAN_BASELINE_SHA256 and sha(base_path) == URBAN_BASELINE_SHA256
                and base == json.loads(Path(base_path).read_text(encoding='utf-8-sig')), 'original baseline changed')
        backup = proof['original_backup']
        require(same_path(backup['path'], URBAN_MATERIAL_BACKUP)
                and backup['sha256'] == URBAN_MATERIAL_BACKUP_SHA256
                and sha(URBAN_MATERIAL_BACKUP) == URBAN_MATERIAL_BACKUP_SHA256, 'original backup pin')

        original_pin = proof['original_material_witness']
        original = pinned_json(original_pin, 'urban_original_material_signature_v1.json')
        require(original['schema'] == 'urban_original_material_signature_v1' and original['success'] is True
                and original['root'] == root and original['source'] == 'isolated_original_backup_project'
                and original['baseline_sha256'] == URBAN_BASELINE_SHA256
                and original['object_path'] == URBAN_OLD_MATERIAL
                and original['saved_source_packages'] == [] and original['camera_render_started'] is False,
                'isolated original signature protocol')
        require(all(original[k] == URBAN_MATERIAL_BACKUP_SHA256 for k in
                    ('original_backup_sha256', 'source_sha256_before', 'source_sha256_after')), 'original source changed')
        source_project, source_file = Path(original['source_project']), Path(original['source_package_file'])
        require(source_project.is_absolute() and source_project.is_file() and source_project.suffix.casefold() == '.uproject'
                and not same_path(source_project, PROJECT / 'datatry_02.uproject')
                and same_path(source_file, source_project.parent / 'Content/UrbanJapan/Materials/MI_Ubc_Building.uasset')
                and sha(source_file) == URBAN_MATERIAL_BACKUP_SHA256, 'isolated original source file')

        move_pin = proof['move_receipt']
        moved = pinned_json(move_pin, 'urban_material_move_v1.json')
        require(moved['schema'] == 'urban_material_move_v1' and moved['success'] is True
                and moved['rename_returned'] is True and moved['camera_render_started'] is False
                and moved['root'] == root and moved['destination'] == URBAN_DESTINATION
                and moved['baseline_sha256'] == URBAN_BASELINE_SHA256
                and moved['method'] == 'UE EditorAssetSubsystem.rename_loaded_asset'
                and moved['source_object_path'] == URBAN_OLD_MATERIAL
                and moved['destination_object_path'] == URBAN_NEW_MATERIAL and moved['dirty_after'] == [],
                'official single-object move receipt')
        original_signature = signature(original['material_signature'])
        require(all(signature_equal(original_signature, signature(s)) for s in
                    (moved['material_before'], moved['material_after'], proof['current_material_signature'])),
                'original/before/after/current material parameters differ')

        old_record = {'package': URBAN_ROOT + '/Materials/MI_Ubc_Building',
                      'name': 'MI_BuildingDetails05', 'class': '/Script/Engine.MaterialInstanceConstant'}
        require(len(base['assets']) == 486 and records(base['assets']).count(registry_identities([old_record])[0]) == 1,
                'original 486 records or exceptional identity changed')
        expected = [dict(r, name='MI_Ubc_Building') if r == old_record else dict(r) for r in base['assets']]
        actual = proof['actual_assets']
        records(actual)
        require(len(actual) == 486 and all(r['package'].startswith(URBAN_DESTINATION + '/') for r in actual)
                and records([dict(r, package=canon(r['package'], root)) for r in actual]) == records(expected),
                'all 486 actual asset identities must remain exact')
        require(proof['old_assets'] == [], 'source root still has registered assets')
        dependencies = proof['destination_dependencies']
        require(isinstance(dependencies, dict) and set(dependencies) == {r['package'] for r in actual}
                and all(isinstance(deps, list) and all(isinstance(p, str)
                        and not (p.casefold() == root.casefold() or p.casefold().startswith(root.casefold() + '/'))
                        for p in deps) for deps in dependencies.values()), 'old dependencies or incomplete reference coverage')
        witness = _UrbanMaterialWitness(path=str(proof_path), sha256=sha(proof_path), baseline_sha256=URBAN_BASELINE_SHA256,
            original_backup=dict(backup), original_material_witness=dict(original_pin), move_receipt=dict(move_pin),
            object_path_alias={'old': URBAN_OLD_MATERIAL, 'new': URBAN_NEW_MATERIAL},
            scope='Exactly one MIC object-name repair; all 486 records and two complete maps remain strict')
        maps = proof['actual_maps']
        require(isinstance(maps, list) and len(maps) == len(base['maps']) == 2
                and [canon(m['map'], root) for m in maps] == [m['map'] for m in base['maps']]
                and all(m['map'].startswith(URBAN_DESTINATION + '/') for m in maps), 'two raw destination map identities')
        require(all(compare_map(b, urban_comparison_signature(a, witness))[0]
                    for b, a in zip(base['maps'], maps)), 'complete map signatures differ')
        relative = proof['component_transforms']
        require(isinstance(relative, dict) and set(relative) == set(base['component_transforms'])
                and all(compare_component_transforms(b, relative[p]) for p, b in base['component_transforms'].items()),
                'component transforms differ')
    except (KeyError, TypeError, ValueError, OSError, AttributeError) as exc:
        raise RuntimeError('Invalid UrbanJapan material relocation proof: missing or malformed evidence') from exc
    return expected, witness



POST_COMPATIBILITY_CONTRACT_SHA256 = '3e63dea55f52940298dccc3c19f8e024c5f57167c11771add006f2ca7f2c458e'
_POST_COMPATIBILITY_MODULE = None
def post_compatibility_module():
    import importlib.util
    global _POST_COMPATIBILITY_MODULE
    contract_path = Path(__file__).with_name('ue_post_city_compatibility_contract_v1.py')
    if sha(contract_path) != POST_COMPATIBILITY_CONTRACT_SHA256:
        raise RuntimeError('Post finite compatibility contract code SHA differs')
    if _POST_COMPATIBILITY_MODULE is None:
        spec = importlib.util.spec_from_file_location('scene_post_compatibility_actual_v1', contract_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _POST_COMPATIBILITY_MODULE = module
    if Path(_POST_COMPATIBILITY_MODULE.__file__).resolve() != contract_path.resolve():
        raise RuntimeError('Unexpected Post compatibility module path')
    return _POST_COMPATIBILITY_MODULE

def verification_asset_contract(root, base_path, base):
    """Exclude only the 3 pinned Kowloon redirector IDs after validating proof.

    Missing proof keeps the original strict set. Other roots never use this
    exception. Asset, map and reference evidence is checked, not just flags.
    """
    if root == '/Game/PostCity':
        import sys
        proof_path = RUN / 'post_exact_package_compatibility_fresh_after_cleanup_v5.json'
        return post_compatibility_module().validated_asset_contract(sys.modules[__name__], root, base_path, base, sha(proof_path))
    if root == URBAN_ROOT:
        return urban_verification_asset_contract(root, base_path, base)
    if root == '/Game/Japanese_Village':
        return japanese_verification_asset_contract(root, base_path, base)
    proof_path = RUN / 'kowloon_redirector_retirement_v1.json'
    if root != '/Game/Kowloon' or not proof_path.exists():
        return base['assets'], None

    def require(condition, message):
        if not condition:
            raise RuntimeError('Invalid Kowloon redirector retirement proof: ' + message)

    def same_path(left, right):
        return Path(left).resolve().as_posix().casefold() == Path(right).resolve().as_posix().casefold()

    def records(value):
        require(isinstance(value, list) and all(isinstance(r, dict) and set(r) == {'package', 'name', 'class'}
                and all(isinstance(v, str) and v for v in r.values()) for r in value), 'malformed asset records')
        return registry_identities(value)

    def under_old(package):
        require(isinstance(package, str), 'non-string package path')
        p = package.casefold()
        return p == root.casefold() or p.startswith(root.casefold() + '/')

    try:
        proof = json.loads(proof_path.read_text(encoding='utf-8-sig'))
        require(proof['schema'] == 'kowloon_redirector_retirement_v1' and proof['success'] is True,
                'schema or success')
        destination = '/Game/Scenes/Kowloon'
        require(proof['root'] == root and proof['destination'] == destination and base['root'] == root,
                'root or destination')
        require(proof['camera_render_started'] is False, 'camera rendering started')
        require(proof['baseline_sha256'] == KOWLOON_BASELINE_SHA256 and sha(base_path) == KOWLOON_BASELINE_SHA256,
                'baseline hash')
        require(base == json.loads(Path(base_path).read_text(encoding='utf-8-sig')), 'baseline argument changed')
        backup = proof['original_backup']
        require(same_path(backup['path'], KOWLOON_REDIRECTOR_BACKUP)
                and backup['sha256'] == KOWLOON_REDIRECTOR_BACKUP_SHA256
                and sha(KOWLOON_REDIRECTOR_BACKUP) == KOWLOON_REDIRECTOR_BACKUP_SHA256, 'original backup pin')

        names = ('BP_Two_Windows_01', 'BP_Two_Windows_01_C', 'Default__BP_Two_Windows_01_C')
        old_package = root + '/Blueprints/Windows/BP_Two_Windows_01'
        original_prefab = root + '/Blueprints/Prefabs/BP_Two_Windows_01'
        new_prefab = destination + '/Blueprints/Prefabs/BP_Two_Windows_01'
        retired = [{'package': old_package, 'name': n, 'class': '/Script/CoreUObject.ObjectRedirector'} for n in names]
        require(records(proof['retired_redirectors']) == records(retired), 'retired IDs differ')
        require(len(base['assets']) == 465 and records([r for r in base['assets'] if r in retired]) == records(retired),
                'original 465 identities or redirectors changed')
        expected_assets = [r for r in base['assets'] if r not in retired]
        require(len(expected_assets) == 462, 'retirement exceeds exactly three IDs')

        target_pin = proof['original_target_witness']
        target_path = RUN / 'kowloon_original_redirector_targets_v1.json'
        require(same_path(target_pin['path'], target_path) and target_pin['sha256'] == sha(target_path),
                'original target witness hash or path')
        original = json.loads(target_path.read_text(encoding='utf-8-sig'))
        require(original['schema'] == 'kowloon_original_redirector_targets_v1' and original['success'] is True
                and original['root'] == root and original['source'] == 'isolated_original_backup_project'
                and original['camera_render_started'] is False and original['saved_source_packages'] == [],
                'original target witness protocol')
        require(all(original[key] == KOWLOON_REDIRECTOR_BACKUP_SHA256 for key in
                    ('original_backup_sha256', 'source_sha256_before', 'source_sha256_after')),
                'original source hash changed')
        source_project = Path(original['source_project'])
        source_file = Path(original['source_package_file'])
        require(source_project.is_absolute() and source_project.is_file() and source_project.suffix.casefold() == '.uproject'
                and not same_path(source_project, PROJECT / 'datatry_02.uproject')
                and same_path(source_file, source_project.parent / 'Content/Kowloon/Blueprints/Windows/BP_Two_Windows_01.uasset')
                and sha(source_file) == KOWLOON_REDIRECTOR_BACKUP_SHA256, 'isolated source package')
        targets = [{'object_path': old_package + '.' + n, 'target': original_prefab + '.' + n} for n in names]
        require(original['original_redirector_targets'] == targets, 'original redirector targets')
        resolved_targets = [dict(t, resolved_destination=new_prefab + '.' + n) for t, n in zip(targets, names)]
        require(proof['original_redirector_targets'] == resolved_targets, 'resolved redirector targets')

        actual_assets = proof['actual_assets']
        records(actual_assets)
        require(all(r['package'].startswith(destination + '/') for r in actual_assets), 'asset outside destination')
        actual = [dict(r, package=canon(r['package'], root)) for r in actual_assets]
        require(len(actual) == 462 and records(actual) == records(expected_assets), 'real asset identities differ')
        maps = proof['actual_maps']
        require(isinstance(maps, list) and len(maps) == len(base['maps']) == 3
                and [m['map'] for m in maps] == [m['map'] for m in base['maps']], 'three map identities')
        require(all(compare_map(before, after)[0] for before, after in zip(base['maps'], maps)), 'map signatures differ')
        relative = proof['component_transforms']
        require(isinstance(relative, dict) and set(relative) == set(base['component_transforms'])
                and all(compare_component_transforms(before, relative[path]) for path, before in base['component_transforms'].items()),
                'component transforms differ')

        old_packages = proof['old_packages']
        require(isinstance(old_packages, list) and all(under_old(p) for p in old_packages)
                and len(set(old_packages)) == len(old_packages) and old_package in old_packages, 'old package coverage')
        referencers = proof['old_referencers']
        require(isinstance(referencers, dict) and set(referencers) == set(old_packages)
                and all(isinstance(refs, list) and all(isinstance(r, str) and r in old_packages for r in refs)
                        for refs in referencers.values()), 'old root has outside referencers or incomplete evidence')
        dependencies = proof['destination_dependencies']
        require(isinstance(dependencies, dict) and set(dependencies) == {r['package'] for r in actual_assets}
                and all(isinstance(deps, list) and all(not under_old(p) for p in deps) for deps in dependencies.values()),
                'destination refers to old root or incomplete evidence')
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError('Invalid Kowloon redirector retirement proof: missing or malformed evidence') from exc

    witness = {'path': str(proof_path), 'sha256': sha(proof_path),
               'baseline_sha256': KOWLOON_BASELINE_SHA256,
               'original_backup': dict(backup), 'original_target_witness': dict(target_pin),
               'original_redirector_targets': resolved_targets, 'retired_redirectors': retired,
               'scope': 'Exactly the three original unused Windows redirectors; all 462 real identities and all maps remain strict'}
    return expected_assets, witness


FUTURISTIC_PUBLIC_OWNER_CONTRACT_SHA256 = '8eb7cf849eb863c0d49a2dd7badbf9963758bf923b269f2287235f3823b1c05f'
KYOTO_SHOWCASE_TIE_CONTRACT_SHA256 = '6fe1ea04a69592ff101626496709305f8b53c20fd934f5b5a45f93f26a0c8d07'


def finite_map_comparison_signature(u, root, base_path, base, before, after, raw_relative):
    """Only reviewed finite per-root comparison copies; generic checks stay strict.

    Call after existing Urban/Water handling and before compare_map. Never use
    the return value to overwrite raw receipt maps or original source evidence.
    """
    if root == '/Game/PostCity':
        import sys
        compared, relative, witness = post_compatibility_module().validated_map_comparison(u, sys.modules[__name__], root, base_path, base, before, after, raw_relative)
        if witness is not None:witness['expected_contract_sha256'] = POST_COMPATIBILITY_CONTRACT_SHA256
        return compared, relative, witness
    if root == '/Game/FuturisticMetaCity':
        import importlib
        import sys
        contract_path = Path(__file__).with_name('ue_futuristic_public_owner_contract_v1.py')
        if sha(contract_path) != FUTURISTIC_PUBLIC_OWNER_CONTRACT_SHA256:
            raise RuntimeError('Future finite public-owner contract code SHA differs')
        import ue_futuristic_public_owner_contract_v1 as contract
        if Path(contract.__file__).resolve() != contract_path.resolve():
            raise RuntimeError('Unexpected Future finite contract module path')
        contract = importlib.reload(contract)
        compared, relative, witness = contract.validated_map_comparison(
            u, sys.modules[__name__], root, base_path, base, before, after, raw_relative)
        witness['expected_contract_sha256'] = FUTURISTIC_PUBLIC_OWNER_CONTRACT_SHA256
        return compared, relative, witness
    if root != '/Game/KyotoAlley' or before.get('map') != '/Game/KyotoAlley/Maps/KyotoAlley_Showcase':
        return after, raw_relative, None
    import importlib
    import sys
    contract_path = Path(__file__).with_name('ue_kyoto_showcase_tie_contract_v1.py')
    if sha(contract_path) != KYOTO_SHOWCASE_TIE_CONTRACT_SHA256:
        raise RuntimeError('Kyoto finite tie contract code SHA differs')
    import ue_kyoto_showcase_tie_contract_v1 as contract
    if Path(contract.__file__).resolve() != contract_path.resolve():
        raise RuntimeError('Unexpected Kyoto finite contract module path')
    contract = importlib.reload(contract)
    compared, witness = contract.validated_kyoto_tie_comparison(
        sys.modules[__name__], root, base_path, base, before, after)
    witness['expected_contract_sha256'] = KYOTO_SHOWCASE_TIE_CONTRACT_SHA256
    return compared, raw_relative, witness


def verify(u, root, receipt_filename=None):
    guard(u)
    slug = root.removeprefix('/Game/').replace('/', '_')
    base_path = RUN / ('baseline_' + slug + '_v1.json')
    base, cold_witness = select_verification_baseline(root, base_path)
    expected_assets, contract_witness = verification_asset_contract(root, base_path, base)
    urban_witness = contract_witness if root == URBAN_ROOT else None
    post_witness = contract_witness if root == '/Game/PostCity' else None
    retirement_witness = None if urban_witness or post_witness else contract_witness
    if post_witness:
        import sys
        post_witness = post_compatibility_module().validate_live(u, sys.modules[__name__], post_witness, expected_assets)
    destination = '/Game/Scenes/' + root.removeprefix('/Game/')
    raw_actual = [asset_record(a) for a in assets(u, destination)]
    actual = [dict(row, package=canon(row['package'], root)) for row in raw_actual]
    canonical_class_aliases = class_redirect_witness(expected_assets + actual)
    if registry_identities(actual) != registry_identities(expected_assets):
        raise RuntimeError('Relocated asset identity/class set differs')
    current_material_signature = None
    if urban_witness:
        current_material = u.get_editor_subsystem(u.EditorAssetSubsystem).load_asset(URBAN_NEW_MATERIAL)
        if not current_material or current_material.get_path_name().casefold() != URBAN_NEW_MATERIAL.casefold():
            raise RuntimeError('Urban recovered material cannot be loaded at exact destination identity')
        current_material_signature = urban_material_parameters(u, current_material)
        proof = json.loads(Path(urban_witness['path']).read_text(encoding='utf-8-sig'))
        if sha(urban_witness['path']) != urban_witness['sha256'] or not signature_equal(
                current_material_signature, proof['current_material_signature']):
            raise RuntimeError('Urban material changed since validated recovery proof')
    if retirement_witness or urban_witness or post_witness:
        if assets(u, root):
            raise RuntimeError('Retired source root still contains registered assets: ' + root)
        registry = u.AssetRegistryHelpers.get_asset_registry()
        options = u.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
        for asset in actual:
            package = destination + asset['package'][len(root):]
            dependencies = registry.get_dependencies(package, options) or []
            if any(str(p).casefold() == root.casefold() or str(p).casefold().startswith(root.casefold() + '/') for p in dependencies):
                raise RuntimeError('Relocated asset still depends on the retired source root: ' + root)
    profiles, yaw_profiles, actor_classes, witness = {}, {}, {}, None
    if root == '/Game/Synthwave_city':
        probe_path = RUN / 'pilot_original_repeat_probe_v1.json'
        probe = json.loads(probe_path.read_text(encoding='utf-8-sig'))
        first, second = probe['samples']
        if first['signature'] == second['signature']:
            raise RuntimeError('Original random-tree witness incomplete')
        allowed_classes = {root + '/Blueprint/' + n + '.' + n + '_C' for n in ('BP_road_01', 'BP_tree_decoration')}
        for sample in probe['samples']:
            for actor in sample['signature']['actors']:
                if actor['class'] not in allowed_classes:
                    continue
                for c in actor['components']:
                    if c['name'] not in ('SM_palm_tree_01', 'SM_palm_tree_02'):
                        continue
                    if c['mesh'] not in {root + '/Meshes/Tree/SM_palm_tree_0' + str(i) + '.SM_palm_tree_0' + str(i) for i in (1, 2, 3)}:
                        raise RuntimeError('Unexpected original palm profile')
                    key = actor['class'] + '|' + c['name']
                    profiles.setdefault(key, set()).add(json.dumps({'mesh': c['mesh'], 'materials': c['materials']}, sort_keys=True))
            actor_classes.update({a['name']: a['class'] for a in sample['signature']['actors']})
            for actor in sample['component_transforms']:
                for c in actor['components']:
                    key = actor_classes[actor['name']] + '|' + c['name']
                    if key in profiles:
                        yaw_profiles.setdefault(key, set()).add(c['transform'][4])
        if not compare_map(first['signature'], second['signature'], profiles)[0] or not compare_component_transforms(first['component_transforms'], second['component_transforms'], actor_classes, yaw_profiles):
            raise RuntimeError('Original witness has variability beyond proven palm profiles and finite yaw choices')
        witness = {'path': str(probe_path), 'sha256': sha(probe_path), 'scope': 'Only original-source random palm mesh/material profiles and observed yaw choices; component positions and scale remain exact'}
    maps = []
    differences = []
    random_variations = []
    water_name_witnesses = []
    finite_map_comparison_witnesses = []
    raw_component_transforms = {}
    for before in base['maps']:
        new_path = destination + before['map'][len(root):]
        # Urban keeps raw destination paths in the receipt. Its one exceptional
        # material reference is canonicalized only in a validated comparison copy.
        raw_after = settled_signature(u, new_path, destination if urban_witness else root,
                                      legacy_materials=base.get('signature_format') != 'mid_parameters_v2')
        maps.append(raw_after)
        after = urban_comparison_signature(raw_after, urban_witness) if urban_witness else raw_after
        if root == '/Game/Medieval_Environment':
            import sys
            import ue_medieval_water_contract_v1 as medieval_water
            after, water_witness = medieval_water.validated_map_signature(
                u, sys.modules[__name__], root, base_path, base, before, after)
            water_name_witnesses.append(water_witness)
        raw_relative = component_transforms(u)
        raw_component_transforms[new_path] = raw_relative
        after, compared_relative, finite_witness = finite_map_comparison_signature(u, root, base_path, base, before, after, raw_relative)
        if finite_witness is not None:
            finite_map_comparison_witnesses.append(finite_witness)
        same, permitted = compare_map(before, after, profiles)
        random_variations.extend(dict(item, map=new_path) for item in permitted)
        if not same:
            differences.append({'map': new_path, 'actor_count_before': before['actor_count'],
                                'actor_count_after': after['actor_count']})
        expected_transforms = base.get('component_transforms', {}).get(before['map'])
        if root == '/Game/Synthwave_city' and before['map'].endswith('/L_showcase_synthwave_city'):
            expected_transforms = probe['samples'][0]['component_transforms']
        if expected_transforms is not None and not compare_component_transforms(expected_transforms, compared_relative, actor_classes, yaw_profiles):
            differences.append({'map': new_path, 'component_transforms_differ': True})
    u.EditorLoadingAndSavingUtils.load_map(ENTRY)
    result = {'schema': 'scene_relocation_verified_v1', 'root': root, 'destination': destination,
              'success': not differences and not dirty(u), 'baseline_sha256': sha(base_path),
              'asset_count': len(actual), 'map_count': len(maps), 'maps': maps,
              'original_asset_count': len(base['assets']),
              'raw_original_asset_records': base['assets'], 'raw_asset_records': raw_actual,
              'canonical_class_aliases': canonical_class_aliases,
              'retired_redirectors': retirement_witness['retired_redirectors'] if retirement_witness else [],
              'redirector_retirement_witness': retirement_witness,
              'post_compatibility_witness': post_witness,
              'material_relocation_witness': urban_witness,
              'current_material_signature': current_material_signature,
              'water_name_witnesses': water_name_witnesses,
              'finite_map_comparison_witnesses': finite_map_comparison_witnesses,
              'component_transforms': raw_component_transforms,
              'current_production_helper_sha256': sha(Path(__file__)),
              'differences': differences, 'dirty': dirty(u), 'camera_render_started': False,
              'original_randomization_witness': witness, 'permitted_random_tree_variations': random_variations,
              'cold_original_baseline': cold_witness, 'signature_format': base.get('signature_format', 'legacy_object_paths_v1'),
              'loading_protocol': loading_protocol(),
              'comparison_tolerance': {'scope': 'MID scalar/vector numeric parameters only; raw signatures retained; all other fields exact', 'rel_tol': 1e-6, 'abs_tol': 1e-6},
              'verification_scope': 'registered asset identities/classes and actual loaded map actor transforms, static meshes, material references, instances and loaded levels; does not prove exact pixels'}
    filename = receipt_filename or ('verified_' + slug + '_v1.json')
    if Path(filename).name != filename or not filename.startswith('verified_' + slug + '_v') or not filename.endswith('.json'):
        raise ValueError('Invalid verification receipt filename')
    if (RUN / filename).exists():
        raise RuntimeError('Verification receipt already exists; preserve history and choose new version')
    write(filename, result)
    if not result['success']:
        raise RuntimeError('Map structural comparison failed; preserved details')
    print('Scene verification passed:', root, len(actual), 'assets', len(maps), 'maps')
