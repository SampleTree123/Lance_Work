"""Isolated full-character import and source-versus-UE rig inventory.

Run in UE with DM_COMPLETE_CHARACTER_MANIFEST. Existing destinations are audited
again, never treated as successful merely because their meshes exist. No scene,
formal library, animation asset, or shared production Skeleton is changed.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import traceback

try:
    import unreal
except ImportError:
    unreal = None  # Pure boundary/name tests can import this module offline.

REPO = Path(__file__).resolve().parents[3]
UE_ROOT = '/Game/DataMake/Validation/CompleteCharacterSkeleton20261005'
REPORT_ROOT = REPO / '00_engine/outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1'
WITNESS_SUBDIR = 'MaterialWitness'
WITNESS_AUTOMATED = True
SPLIT_SUBDIR = 'Meshes'
REQUIRED_CASE_SEXES = ('male', 'female')
SHARED_SKELETON_PATH = None
READONLY_WITNESS_ROOT = None
SAFE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_]{0,63}$')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=str)+'\n', encoding='utf-8')
    temporary.replace(path)


def guard(path):
    package = str(path).split('.',1)[0]
    if not package.startswith(UE_ROOT + '/'):
        raise ValueError('Asset mutation outside isolated pilot: ' + str(path))


def source_record(case, field):
    value = case[field]
    record = value if isinstance(value, dict) else {'path':value, 'sha256':case[field+'_sha256']}
    if not isinstance(record.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',record['sha256']):
        raise ValueError('Expected source SHA for '+field)
    if sha(record['path']) != record['sha256']:
        raise ValueError('Changed source '+field)
    return {'path':str(Path(record['path']).resolve()), 'sha256':record['sha256']}


def morph_comparison(source_names, actual_names, mesh_name):
    """Exact mesh-prefix removal and observed UE space sanitation; never fuzzy."""
    def normalized(name, imported=False):
        if not imported:
            return name.replace(' ','_')
        for prefix in (mesh_name+'__', mesh_name+'_', mesh_name+'.'):
            if name.casefold().startswith(prefix.casefold()):
                return name[len(prefix):].replace(' ','_')
        return name.replace(' ','_')
    expected = sorted(set(str(n) for n in source_names))
    actual = sorted(str(n) for n in actual_names)
    source_map,actual_map = {},{}
    for name in expected:
        source_map.setdefault(normalized(name),[]).append(name)
    for name in actual:
        actual_map.setdefault(normalized(name,True),[]).append(name)
    source_collisions = {key:value for key,value in source_map.items() if len(value)>1}
    actual_collisions = {key:value for key,value in actual_map.items() if len(value)>1}
    source_to_imported,imported_to_source = {},{}
    for key in source_map.keys()&actual_map.keys():
        if key not in source_collisions and key not in actual_collisions:
            source_to_imported[source_map[key][0]] = actual_map[key][0]
            imported_to_source[actual_map[key][0]] = source_map[key][0]
    missing = sorted(name for key,names in source_map.items() if key not in actual_map for name in names)
    unexpected = sorted(name for key,names in actual_map.items() if key not in source_map for name in names)
    return {'source_unique_names':len(expected), 'imported_count':len(actual),
            'normalization':'exact source mesh prefix removal; literal spaces to underscores (observed UE name sanitation)',
            'missing':missing,'unexpected':unexpected,
            'source_to_imported':source_to_imported,'imported_to_source':imported_to_source,
            'source_normalization_collisions':source_collisions,'actual_normalization_collisions':actual_collisions,
            'normalized_collisions':sum(len(names)-1 for names in actual_collisions.values()),
            'all_source_names_present':not missing and not source_collisions and not actual_collisions,
            'missing_reason':'Unclassified: source zero-delta versus importer loss requires source-delta evidence; no presumed exemption.' if missing else None}


def slot_material_map(meshes):
    result = {}
    for mesh in meshes:
        for slot in mesh.get_editor_property('materials'):
            material = slot.get_editor_property('material_interface')
            if material is None:
                raise RuntimeError('Witness has an empty material')
            for field in ('material_slot_name','imported_material_slot_name'):
                key = str(slot.get_editor_property(field))
                if not key or key == 'None':
                    continue
                if key in result and result[key].get_path_name() != material.get_path_name():
                    raise RuntimeError('Ambiguous witness material '+key)
                result[key] = material
    return result


def assets(root):
    return [unreal.load_asset(path) for path in unreal.EditorAssetLibrary.list_assets(root,recursive=True,include_folder=False)]


def save(asset):
    guard(asset.get_path_name())
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):
        raise RuntimeError('Save failed '+asset.get_path_name())


def configure_split(pipeline):
    mesh = pipeline.get_editor_property('mesh_pipeline')
    common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
    normal = pipeline.get_editor_property('common_meshes_properties')
    mesh.set_editor_properties({'import_skeletal_meshes':True,'import_static_meshes':False,
        'combine_skeletal_meshes_behavior':unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE,
        'import_morph_targets':True,'morph_threshold_position':0.0,'create_physics_asset':False,'physics_asset':None,
        'skeletal_mesh_import_content_type':unreal.InterchangeSkeletalMeshContentType.ALL,
        'update_skeleton_reference_pose':False})
    shared = unreal.load_asset(SHARED_SKELETON_PATH) if SHARED_SKELETON_PATH else None
    if SHARED_SKELETON_PATH and not isinstance(shared, unreal.Skeleton):
        raise RuntimeError('Explicit shared Skeleton is missing')
    common.set_editor_properties({'skeleton':shared,'try_auto_select_skeleton':False,
        'import_only_animations':False,'use_t0_as_ref_pose':False})
    normal.set_editor_properties({'recompute_normals':True,'recompute_tangents':True,
        'convert_statics_in_bone_hierarchy_to_skeletals':True})
    pipeline.get_editor_property('animation_pipeline').set_editor_property('import_animations',False)
    material = pipeline.get_editor_property('material_pipeline')
    material.set_editor_property('import_materials',False)
    material.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
    values = {'mesh':{key:str(mesh.get_editor_property(key)) for key in (
        'combine_skeletal_meshes_behavior','import_morph_targets','morph_threshold_position','create_physics_asset','skeletal_mesh_import_content_type','update_skeleton_reference_pose')},
        'common':{key:str(common.get_editor_property(key)) for key in ('skeleton','try_auto_select_skeleton','use_t0_as_ref_pose','import_only_animations')},
        'normal':{key:bool(normal.get_editor_property(key)) for key in (
            'recompute_normals','recompute_tangents','convert_statics_in_bone_hierarchy_to_skeletals')}}
    if (not mesh.get_editor_property('import_morph_targets') or common.get_editor_property('use_t0_as_ref_pose')
            or mesh.get_editor_property('update_skeleton_reference_pose') or common.get_editor_property('skeleton') != shared):
        raise RuntimeError('Import option readback failed')
    return values


def import_split(fbx, root):
    existing = [a for a in assets(root) if isinstance(a,unreal.SkeletalMesh)]
    if existing:
        return {'resumed_existing_for_audit':True}
    pipeline_path = root+'/P_CompleteCharacter'
    pipeline = unreal.load_asset(pipeline_path)
    if pipeline is None:
        original = unreal.load_asset('/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline')
        pipeline = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('P_CompleteCharacter',root,original)
    settings = configure_split(pipeline)
    save(pipeline)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    params = unreal.ImportAssetParameters()
    params.set_editor_properties({'is_automated':True,'force_show_dialog':False,'replace_existing':False,
        'override_pipelines':[unreal.SoftObjectPath(pipeline.get_path_name())]})
    cvar = 'Interchange.FeatureFlags.Import.FBX'
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, cvar + ' 1')
    try:
        manager.import_asset(root,manager.create_source_data(fbx['path']),params)
    finally:
        unreal.SystemLibrary.execute_console_command(world, cvar + ' ' + str(previous))
    return {'settings':settings,'resumed_existing_for_audit':False}


def import_witness(fbx, root):
    existing = [a for a in assets(root) if isinstance(a,unreal.SkeletalMesh)]
    if existing:
        return {'resumed_existing_for_audit':True}
    helper = REPO/'00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py'
    names = {'copy_fbx_import_options','configure_cc_factory_import_ui','register_factory_ui_enforcer'}
    nodes = [n for n in ast.parse(helper.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace = {'unreal':unreal}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),namespace)
    factory, options = unreal.CCFbxFactory(), unreal.FbxImportUI()
    options.set_editor_properties({'automated_import_should_detect_type':False,'import_as_skeletal':True,
        'import_mesh':True,'mesh_type_to_import':unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        'import_animations':False,'import_materials':True,'import_textures':True,'create_physics_asset':False,'skeleton':None})
    options.get_editor_property('skeletal_mesh_import_data').set_editor_properties({'import_morph_targets':False,
        'update_skeleton_reference_pose':False,'use_t0_as_ref_pose':False,'normal_import_method':unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS})
    namespace['configure_cc_factory_import_ui'](factory,options)
    handle,enforcement = namespace['register_factory_ui_enforcer'](factory,options)
    task = unreal.AssetImportTask()
    task.set_editor_properties({'filename':fbx['path'],'destination_path':root,'automated':WITNESS_AUTOMATED,'save':True,
        'replace_existing':False,'replace_existing_settings':False,'factory':factory,'options':options})
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    except RuntimeError as error:
        # The known Auto Setup factory can report an exception after producing
        # shader assets. Never infer success here: exact material audit follows.
        enforcement['import_exception'] = str(error)
    finally:
        unreal.unregister_slate_pre_tick_callback(handle)
    return {'enforcement':enforcement,'helper_sha256':sha(helper),'resumed_existing_for_audit':False}


def configure_exact_source_normal_textures(sidecar, witness_root):
    declared = {}
    def visit(value):
        if isinstance(value,dict):
            normal = value.get('Textures',{}).get('Normal',{}).get('Texture Path')
            if normal:
                physical = (Path(sidecar['path']).parent/normal).resolve()
                if not physical.is_file():
                    raise RuntimeError('Missing exact declared Normal texture '+str(physical))
                declared[str(physical)] = sha(physical)
            for child in value.values():
                visit(child)
        elif isinstance(value,list):
            for child in value:
                visit(child)
    visit(read(sidecar['path']))
    records = []
    for texture in assets(witness_root):
        if not isinstance(texture,unreal.Texture2D):
            continue
        data = texture.get_editor_property('asset_import_data')
        physical = [str(Path(p).resolve()) for p in data.extract_filenames()] if data else []
        matches = sorted(set(physical)&set(declared))
        if not matches:
            continue
        if len(matches)!=1:
            raise RuntimeError('Ambiguous Normal texture source')
        guard(texture.get_path_name())
        before = {'srgb':bool(texture.get_editor_property('srgb')),
                  'compression':str(texture.get_editor_property('compression_settings'))}
        texture.set_editor_properties({'srgb':False,'compression_settings':unreal.TextureCompressionSettings.TC_NORMALMAP})
        save(texture)
        if texture.get_editor_property('srgb') or texture.get_editor_property('compression_settings')!=unreal.TextureCompressionSettings.TC_NORMALMAP:
            raise RuntimeError('Normal texture metadata readback failed')
        records.append({'texture':texture.get_path_name(),'source':matches[0],'sha256':declared[matches[0]],'before':before,
                        'after':{'srgb':False,'compression':'TC_NORMALMAP'}})
    return {'method':'exact CC JSON Normal declaration + imported physical filename, no filename guessing',
            'declared_normal_sources':len(declared),'corrected_textures':records,
            'unmatched_normal_sources':sorted(set(declared)-{r['source'] for r in records})}


def bone_inventory(mesh):
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot inspect reference skeleton')
    rows = []
    for name in modifier.get_all_bone_names():
        transform = modifier.get_bone_transform(name,False)
        t,s,q = transform.translation,transform.scale3d,transform.rotation
        row = {'name':str(name),'parent':str(modifier.get_parent_name(name)),
            'translation_cm':[float(getattr(t,a)) for a in 'xyz'],
            'rotation_xyzw':[float(getattr(q,a)) for a in 'xyzw'],
            'scale':[float(getattr(s,a)) for a in 'xyz']}
        if not all(math.isfinite(v) for key in ('translation_cm','rotation_xyzw','scale') for v in row[key]):
            raise RuntimeError('Nonfinite reference bone transform')
        rows.append(row)
    if not rows:
        raise RuntimeError('Empty reference bone list')
    return rows  # No commit/add/replace method is ever called.


def skeleton_reference_inventory(skeleton):
    """Read USkeleton's own reference pose, not a mesh's identity-specific pose."""
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError('Cannot inspect a missing Skeleton')
    pose = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
    names = list(unreal.AnimPoseExtensions.get_bone_names(pose))
    if not names or len(set(str(name) for name in names)) != len(names):
        raise RuntimeError('Skeleton reference bone names are empty or duplicated')
    rows = []
    for name in names:
        transform = unreal.AnimPoseExtensions.get_ref_bone_pose(pose,name,unreal.AnimPoseSpaces.LOCAL)
        t,s,q = transform.translation,transform.scale3d,transform.rotation
        row = {'name':str(name),
               'translation_cm':[float(getattr(t,a)) for a in 'xyz'],
               'rotation_xyzw':[float(getattr(q,a)) for a in 'xyzw'],
               'scale':[float(getattr(s,a)) for a in 'xyz']}
        if not all(math.isfinite(v) for key in ('translation_cm','rotation_xyzw','scale') for v in row[key]):
            raise RuntimeError('Nonfinite Skeleton reference pose')
        rows.append(row)
    return sorted(rows,key=lambda row:row['name'])


def audit_bound_normal_textures(sidecar, fbx, meshes, audit_only=False):
    """Resolve CC source material -> actual Normal Map, including FBX embeds."""
    declarations = {}
    def visit(value):
        if isinstance(value, dict):
            for name, material in value.get('Materials', {}).items():
                normal = material.get('Textures', {}).get('Normal', {}).get('Texture Path')
                if normal:
                    physical = str((Path(sidecar['path']).parent / normal).resolve())
                    if name in declarations and declarations[name] != physical:
                        raise RuntimeError('Conflicting declared Normal source for ' + name)
                    declarations[name] = physical
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(read(sidecar['path']))
    bindings = []
    for mesh in meshes:
        for slot in mesh.get_editor_property('materials'):
            name = str(slot.get_editor_property('material_slot_name'))
            if name not in declarations:
                continue
            material = slot.get_editor_property('material_interface')
            texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(material, 'Normal Map')
            if not isinstance(texture, unreal.Texture2D):
                raise RuntimeError('Missing declared Normal Map binding ' + name)
            data = texture.get_editor_property('asset_import_data')
            physical = {str(Path(p).resolve()).casefold() for p in data.extract_filenames()} if data else set()
            embedded = fbx['path'].casefold() in physical
            external = declarations[name].casefold() in physical
            if not embedded and not external:
                raise RuntimeError('Normal texture has unrelated provenance ' + name)
            if texture.get_editor_property('srgb') or texture.get_editor_property('compression_settings') != unreal.TextureCompressionSettings.TC_NORMALMAP:
                if audit_only:
                    raise RuntimeError('Saved Normal texture metadata incorrect ' + name)
                guard(texture.get_path_name())
                texture.set_editor_properties({'srgb': False, 'compression_settings': unreal.TextureCompressionSettings.TC_NORMALMAP})
                save(texture)
            bindings.append({'slot': name, 'material': material.get_path_name(), 'normal_texture': texture.get_path_name(),
                'declared_source': declarations[name], 'declared_source_sha256': sha(declarations[name]),
                'embedded_fbx_provenance': embedded, 'external_png_provenance': external,
                'srgb': bool(texture.get_editor_property('srgb')),
                'compression': str(texture.get_editor_property('compression_settings'))})
    if {b['slot'] for b in bindings} != set(declarations):
        raise RuntimeError('Declared material Normal bindings incomplete')
    return {'passed': True, 'bindings': bindings, 'source_texture_pixel_equivalence_claimed': False,
            'scope': 'Exact JSON material slot and Normal Map parameter; embedded FBX or exact external source provenance'}


def skin_inventory(mesh):
    copied = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,unreal.DynamicMesh(),
        unreal.GeometryScriptCopyMeshFromAssetOptions(),
        unreal.GeometryScriptMeshReadLOD(lod_type=unreal.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
    if 'SUCCESS' not in str(copied[-1]):
        raise RuntimeError('Cannot extract source-model skin weights')
    dynamic = copied[0]
    ids = unreal.GeometryScript_MeshQueries.get_all_vertex_i_ds(dynamic)
    vertices = list(unreal.GeometryScript_List.convert_index_list_to_array(ids[1]))
    invalid, largest, used = 0,0,set()
    digest = hashlib.sha256()
    for vertex in vertices:
        result = unreal.GeometryScript_BoneWeights.get_vertex_bone_weights(dynamic,vertex)
        pairs = sorted((int(w.bone_index),float(w.weight)) for w in result[1]) if result[-1] else []
        if not pairs or not all(i>=0 and math.isfinite(w) and w>=0 for i,w in pairs) or abs(sum(w for _,w in pairs)-1)>.002:
            invalid += 1
        largest = max(largest,len(pairs)); used.update(i for i,w in pairs if w>0)
        digest.update(json.dumps([int(vertex),pairs],separators=(',',':')).encode())
    if not vertices or invalid:
        raise RuntimeError('Invalid source-model skin weights: '+str(invalid))
    return {'lod':0,'representation':'SOURCE_MODEL','vertices':len(vertices),'invalid_vertices':invalid,
        'max_influences':largest,'used_bone_indices':sorted(used),'indexed_weights_sha256':digest.hexdigest()}


def audit_mesh(mesh, expectation, fbx):
    data = mesh.get_editor_property('asset_import_data')
    physical = [str(Path(p).resolve()) for p in data.extract_filenames()] if data else []
    if fbx['path'] not in physical:
        raise RuntimeError('Existing mesh has different FBX provenance '+mesh.get_name())
    morphs = sorted(str(m.get_name()) for m in mesh.get_editor_property('morph_targets') if m)
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    source_name = expectation['source_name']
    comparison = morph_comparison(expectation.get('expected_morph_names',[]),morphs,source_name)
    slots = [{'name':str(s.get_editor_property('material_slot_name')),
        'material':s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None}
        for s in mesh.get_editor_property('materials')]
    if any(not s['material'] or s['material'].startswith('/Engine/') for s in slots):
        raise RuntimeError('Default/missing split material '+mesh.get_name())
    return {'path':mesh.get_path_name(),'name':mesh.get_name(),'source_name':source_name,'role':expectation['role'],
        'skeleton':mesh.get_editor_property('skeleton').get_path_name(), 'morph_names':morphs,'morph_count':len(morphs),
        'morph_source_comparison':comparison,'bones':bone_inventory(mesh),'skinweights':skin_inventory(mesh),
        'lod0_vertices':subsystem.get_num_verts(mesh,0),'lod_count':subsystem.get_lod_count(mesh),'materials':slots}


def main(manifest_path, audit_only=False):
    if not isinstance(SPLIT_SUBDIR, str) or not SAFE.fullmatch(SPLIT_SUBDIR):
        raise ValueError('Split subdirectory must be a safe single asset directory name')
    if not isinstance(WITNESS_SUBDIR, str) or not SAFE.fullmatch(WITNESS_SUBDIR):
        raise ValueError('Witness subdirectory must be a safe single asset directory name')
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_relative_to(REPORT_ROOT.resolve()):
        raise ValueError('Manifest must be inside the bounded pilot output')
    manifest = read(manifest_path)
    if (not REQUIRED_CASE_SEXES or any(sex not in ('male', 'female') for sex in REQUIRED_CASE_SEXES)
            or manifest.get('schema_version') != 1
            or sorted(c.get('sex', '') for c in manifest.get('cases', [])) != sorted(REQUIRED_CASE_SEXES)):
        raise ValueError('Manifest sex/count differs from the explicit import scope')
    result = {'schema_version':1,'cases':[],'common_skeleton_adopted':False,'visual_acceptance':'pending',
              'engine_version':unreal.SystemLibrary.get_engine_version(),'manifest_sha256':sha(manifest_path)}
    for case in manifest['cases']:
        identifier = case['character_id']
        if not SAFE.fullmatch(identifier):
            raise ValueError('Unsafe character_id')
        destination = UE_ROOT+'/'+identifier
        split_root = destination + '/' + SPLIT_SUBDIR
        witness_root = READONLY_WITNESS_ROOT or (destination + '/' + WITNESS_SUBDIR)
        if split_root == witness_root:
            raise ValueError('Split and witness directories must differ')
        if READONLY_WITNESS_ROOT and not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', READONLY_WITNESS_ROOT):
            raise ValueError('Invalid explicit read-only witness asset root')
        shared_before = None
        if SHARED_SKELETON_PATH:
            guard(SHARED_SKELETON_PATH)
            shared_before = skeleton_reference_inventory(unreal.load_asset(SHARED_SKELETON_PATH))
        folder = REPORT_ROOT/identifier
        fbx,sidecar = source_record(case,'fbx'),source_record(case,'json')
        extract_ref = source_record(case,'source_extract') if case.get('source_extract') else None
        extract = read(extract_ref['path']) if extract_ref else {}
        signature = hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
        state_path = folder/'import_state.json'
        if audit_only and (not state_path.exists() or read(state_path).get('status') != 'audited'):
            raise ValueError('Read-only audit requires an already completed import')
        if state_path.exists():
            if read(state_path)['input_fingerprint'] != signature:
                raise ValueError('Existing import input/config changed; new character_id required')
            old_state = read(state_path)
            if old_state.get('status') == 'audited' and old_state.get('split_subdir', 'Meshes') != SPLIT_SUBDIR:
                raise ValueError('Completed import split directory cannot change')
        else:
            if unreal.EditorAssetLibrary.does_directory_exist(destination):
                raise ValueError('Existing UE destination has no protected import state')
            write(state_path,{'input_fingerprint':signature,'fbx':fbx,'json':sidecar,'status':'pending'})
        report = {'success':False,'source':fbx,'auto_setup_json':sidecar,'character_id':identifier,'sex':case['sex'],
                  'destination':destination,'witness_root':witness_root,'split_root':split_root,'implementation_sha256':sha(__file__)}
        try:
            report['audit_only'] = bool(audit_only)
            if SHARED_SKELETON_PATH:
                shared_names = {bone['name'] for bone in shared_before}
                source_names = {bone['name'] for bone in extract.get('bones', [])}
                if not source_names or source_names != shared_names:
                    raise RuntimeError('Source and shared Skeleton bone name sets must match before import')
            if audit_only or READONLY_WITNESS_ROOT:
                report['witness_import'] = {'mode':'saved_asset_readback'}
            else:
                report['witness_import'] = import_witness(fbx,witness_root)
                report['normal_texture_setup'] = configure_exact_source_normal_textures(sidecar,witness_root)
            witnesses = [a for a in assets(witness_root) if isinstance(a,unreal.SkeletalMesh)]
            materials = slot_material_map(witnesses)
            expected = case['expected_meshes']
            # Check the same exact source material names before loading the
            # split geometry. A canceled witness must not start a split import.
            for wanted in expected:
                for name in wanted.get('expected_materials', []):
                    if name not in materials:
                        raise RuntimeError('No unique exact Auto Setup material for '+name)
            if audit_only:
                report['split_import'] = {'mode':'saved_asset_readback'}
            else:
                report['split_import'] = import_split(fbx,split_root)
            split_assets = assets(split_root)
            if any(isinstance(a,(unreal.AnimSequence,unreal.PhysicsAsset)) for a in split_assets):
                raise RuntimeError('Unexpected animation or physics asset')
            meshes = [a for a in split_assets if isinstance(a,unreal.SkeletalMesh)]
            if len(meshes) != len(expected):
                raise RuntimeError('Complete part count differs from FBX source')
            # Give the one newly imported character Skeleton a stable, readable
            # name rather than inheriting the first FBX part's name (Tongue).
            imported_skeletons = {m.get_editor_property('skeleton').get_path_name() for m in meshes}
            if len(imported_skeletons) != 1:
                raise RuntimeError('Parts imported with multiple character Skeletons')
            skeleton_source = next(iter(imported_skeletons))
            standard_path = SHARED_SKELETON_PATH.split('.', 1)[0] if SHARED_SKELETON_PATH else split_root + '/SKEL_CC5_' + case['sex'].title() + '_Average_Complete_v1'
            guard(skeleton_source)
            guard(standard_path)
            if skeleton_source.split('.', 1)[0] != standard_path:
                if SHARED_SKELETON_PATH:
                    raise RuntimeError('Importer did not bind the explicitly selected shared Skeleton')
                if audit_only:
                    raise RuntimeError('Saved Skeleton does not use the expected standard name')
                if unreal.EditorAssetLibrary.does_asset_exist(standard_path):
                    raise RuntimeError('Standard Skeleton destination already belongs to another import')
                if not unreal.EditorAssetLibrary.rename_asset(skeleton_source, standard_path):
                    raise RuntimeError('Cannot name isolated character Skeleton')
            rows = []
            for wanted in expected:
                aliases = {str(n).casefold() for n in (
                    [wanted['source_name'],wanted.get('model_name',wanted['source_name'])]+wanted.get('ue_name_aliases',[]))}
                source_rows = [r for r in extract.get('expected_meshes',[]) if r['source_name'].casefold()==wanted['source_name'].casefold()]
                if len(source_rows)==1:
                    aliases.add(source_rows[0].get('model_name',wanted['source_name']).casefold())
                matches = [m for m in meshes if m.get_name().casefold() in aliases]
                if len(matches)!=1:
                    raise RuntimeError('Missing/ambiguous source mesh '+wanted['source_name'])
                mesh = matches[0]
                slots = list(mesh.get_editor_property('materials'))
                for slot in slots:
                    candidates = {materials[str(slot.get_editor_property(key))].get_path_name():materials[str(slot.get_editor_property(key))]
                        for key in ('material_slot_name','imported_material_slot_name') if str(slot.get_editor_property(key)) in materials}
                    if len(candidates)!=1:
                        raise RuntimeError('No unique exact Auto Setup material for '+str(slot.get_editor_property('material_slot_name')))
                    expected_material = next(iter(candidates.values()))
                    if audit_only:
                        current = slot.get_editor_property('material_interface')
                        if not current or current.get_path_name() != expected_material.get_path_name():
                            raise RuntimeError('Saved Auto Setup material binding differs')
                    else:
                        slot.set_editor_property('material_interface',expected_material)
                if audit_only:
                    if mesh.get_editor_property('physics_asset'):
                        raise RuntimeError('Saved split mesh unexpectedly has a physics asset')
                else:
                    mesh.set_editor_properties({'materials':slots,'physics_asset':None})
                    save(mesh)
                audited = audit_mesh(mesh,wanted,fbx)
                if len(source_rows)==1:
                    deltas = {r['name']:r['max_position_delta_cm'] for r in source_rows[0].get('morph_position_deltas',[])}
                    audited['morph_source_comparison']['missing_source_deltas_cm'] = {
                        name:deltas.get(name) for name in audited['morph_source_comparison']['missing']}
                rows.append(audited)
            skeletons = sorted(set(row['skeleton'] for row in rows))
            if len(skeletons)!=1 or (skeletons[0].split('.', 1)[0] != standard_path if SHARED_SKELETON_PATH else not skeletons[0].startswith(destination+'/')):
                raise RuntimeError('Parts do not share one newly isolated character Skeleton')
            report['bound_normal_texture_audit'] = audit_bound_normal_textures(sidecar, fbx, meshes, audit_only=audit_only or bool(READONLY_WITNESS_ROOT))
            if SHARED_SKELETON_PATH:
                shared_after = skeleton_reference_inventory(unreal.load_asset(SHARED_SKELETON_PATH))
                report['shared_skeleton_reference_audit'] = {'path':SHARED_SKELETON_PATH,
                    'before':shared_before, 'after':shared_after, 'unchanged':shared_before == shared_after,
                    'scope':'USkeleton independent bone names and local T/Q/S readback; parent hierarchy is audited separately from imported mesh/source trees',
                    'mesh_reference_pose_identity_equality_required':False}
                if shared_before != shared_after:
                    raise RuntimeError('Shared Skeleton reference pose changed during import')
            actual_bones = {b['name'] for row in rows for b in row['bones']}
            required_bones = {b['name'] for b in extract.get('bones',[])}
            report['source_bone_comparison'] = {'source_bone_count':len(required_bones),
                'imported_union_bone_count':len(actual_bones),'missing_source_bones':sorted(required_bones-actual_bones),
                'extra_imported_bones':sorted(actual_bones-required_bones)}
            if required_bones-actual_bones:
                raise RuntimeError('Source bones missing after import')
            if SHARED_SKELETON_PATH:
                expected_parents = {b['name']:b['parent'] if b['parent'] in required_bones else None
                                    for b in extract['bones']}
                hierarchy_differences = []
                for row in rows:
                    actual_parents = {b['name']:b['parent'] if b['parent'] in required_bones else None
                                      for b in row['bones']}
                    if actual_parents != expected_parents:
                        hierarchy_differences.append(row['path'])
                report['source_mesh_hierarchy_audit'] = {'passed':not hierarchy_differences,
                    'different_meshes':hierarchy_differences,
                    'scope':'Each imported mesh parent hierarchy versus its exact FBX source; not independent USkeleton parent introspection'}
                if hierarchy_differences:
                    raise RuntimeError('Shared imported mesh hierarchy differs from source')
            if sha(fbx['path'])!=fbx['sha256'] or sha(sidecar['path'])!=sidecar['sha256']:
                raise RuntimeError('Source changed during import')
            report.update(success=True,meshes=rows,skeleton=skeletons[0],source_unchanged=True,
                all_source_morph_names_preserved=all(row['morph_source_comparison']['all_source_names_present'] for row in rows),
                source_limitations=case.get('source_limitations',[]),eyebrows_scope=case.get('eyebrows_scope'),
                source_extract=extract_ref, runtime_motion_acceptance='not_tested')
            report['standard_candidate_ready'] = report['all_source_morph_names_preserved']
            if not audit_only:
                # Recovery must not resave the interrupted sibling mesh packages.
                unreal.EditorAssetLibrary.save_directory(destination if SPLIT_SUBDIR == 'Meshes' else split_root,only_if_is_dirty=False,recursive=True)
            write(state_path,{'input_fingerprint':signature,'fbx':fbx,'json':sidecar,'status':'audited','split_subdir':SPLIT_SUBDIR,'report_path':str(folder/'import_audit.json')})
        except Exception:
            report['error'] = traceback.format_exc()
            write(folder/'import_audit.json',report)
            raise
        write(folder/'import_audit.json',report)
        result['cases'].append({'character_id':identifier,'sex':case['sex'],'skeleton':report['skeleton'],
            'meshes':[{k:row[k] for k in ('path','role','morph_count')} for row in rows],
            'audit':str(folder/'import_audit.json'),'standard_candidate_ready':report['standard_candidate_ready']})
        write(REPORT_ROOT/'standard_candidate_registry.json',result)
        unreal.log('Complete character pilot audited '+identifier+' parts='+str(len(rows)))
    return result


if globals().get('DM_COMPLETE_CHARACTER_MANIFEST'):
    main(globals()['DM_COMPLETE_CHARACTER_MANIFEST'], audit_only=bool(globals().get('DM_COMPLETE_CHARACTER_AUDIT_ONLY')))
