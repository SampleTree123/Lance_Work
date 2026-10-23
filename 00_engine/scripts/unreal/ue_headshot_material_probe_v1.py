"""Auto Setup material witness, confined to the independent Headshot project."""
import ast
import hashlib
import json
from pathlib import Path
import traceback
import unreal

ROOT = Path(r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1')
REPO = Path(r'D:\UE\Lance_Work')
RUN = Path(globals()['DM_HS_NORMAL_RUN']).resolve()
PROJECT = ROOT / 'ue_material_probe_project_v1'
TAG = globals()['DM_HS_NORMAL_TAG']
if RUN.parent != ROOT.resolve() or not RUN.name.startswith('ue_normal_probe_material_') or not TAG.replace('_', '').isalnum():
    raise RuntimeError('Invalid isolated material run')
if Path(unreal.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Independent material project required')
OUT = RUN / (TAG + '_materials.json')
if OUT.exists():
    raise RuntimeError('Refusing to overwrite evidence')
manifest = json.loads((RUN / 'inputs.json').read_text(encoding='utf-8'))
destination = manifest['material_witness_root']
if not destination.startswith('/Game/HeadshotMaterialWitness/'):
    raise RuntimeError('Invalid material witness destination')
if unreal.EditorAssetLibrary.does_directory_exist(destination):
    raise RuntimeError('Witness already exists; use a new destination')
source = manifest['sources'][0]
for path, expected in [(source['path'], source['sha256']), (manifest['material_source_json'], manifest['material_source_json_sha256'])]:
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise RuntimeError('Source hash mismatch: ' + path)

# Reuse only the existing option-copy/enforcer definitions; the production
# importer has an unconditional main(), which must not execute in this project.
helper = REPO / '00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py'
names = {'copy_fbx_import_options', 'configure_cc_factory_import_ui', 'register_factory_ui_enforcer'}
tree = ast.parse(helper.read_text(encoding='utf-8-sig'))
definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in definitions} == names
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(helper), 'exec'), globals())
report = dict(success=False, source=source, destination=destination,
    engine_version=unreal.SystemLibrary.get_engine_version(),
    helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), reused_helpers=sorted(names),
    scope='Auto Setup material witness only. Geometry, rig and witness morphs are not acceptance inputs.',
    implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

def flush(phase):
    report['phase'] = phase
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    unreal.log('Headshot material probe: ' + phase)

try:
    flush('configure')
    factory = unreal.CCFbxFactory()
    options = unreal.FbxImportUI()
    options.set_editor_properties(dict(automated_import_should_detect_type=False,
        import_as_skeletal=True, import_mesh=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        import_animations=False, import_materials=True, import_textures=True, create_physics_asset=False, skeleton=None))
    options.get_editor_property('skeletal_mesh_import_data').set_editor_properties(dict(
        import_morph_targets=False, update_skeleton_reference_pose=False, use_t0_as_ref_pose=False,
        normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS))
    report['factory_import_ui_path'] = configure_cc_factory_import_ui(factory, options)
    handle, enforcement = register_factory_ui_enforcer(factory, options)
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=source['path'], destination_path=destination,
        automated=True, save=True, replace_existing=False, replace_existing_settings=False,
        factory=factory, options=options))
    flush('importing_auto_setup_witness')
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    except RuntimeError as exc:
        report['import_exception'] = str(exc)
    finally:
        unreal.unregister_slate_pre_tick_callback(handle)
    report['enforcement'] = enforcement
    report['returned'] = list(task.get_editor_property('imported_object_paths'))
    flush('inspect_materials')
    records = []
    for path in unreal.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False):
        asset = unreal.load_asset(path)
        if asset is None:
            records.append(dict(path=path, load_error=True)); continue
        row = dict(path=path, name=asset.get_name(), asset_class=asset.get_class().get_name())
        if isinstance(asset, unreal.SkeletalMesh):
            row['slots'] = [dict(index=i, name=str(slot.get_editor_property('material_slot_name')),
                imported_name=str(slot.get_editor_property('imported_material_slot_name')),
                material=slot.get_editor_property('material_interface').get_path_name() if slot.get_editor_property('material_interface') else None)
                for i, slot in enumerate(asset.get_editor_property('materials'))]
        if isinstance(asset, unreal.MaterialInstanceConstant):
            parent = asset.get_editor_property('parent')
            row['parent'] = parent.get_path_name() if parent else None
            row['textures'] = [dict(parameter=str(t.get_editor_property('parameter_info').get_editor_property('name')),
                texture=t.get_editor_property('parameter_value').get_path_name() if t.get_editor_property('parameter_value') else None)
                for t in asset.get_editor_property('texture_parameter_values')]
        records.append(row)
    report['assets'] = records
    meshes = [r for r in records if r.get('asset_class') == 'SkeletalMesh']
    if not meshes or any(not s['material'] or s['material'].startswith('/Engine/') for r in meshes for s in r['slots']):
        raise RuntimeError('Witness has missing/default material slots')
    if not any(r.get('parent', '').startswith('/Game/CC_Shaders/') for r in records):
        raise RuntimeError('Auto Setup did not produce CC shader instances')
    if not unreal.EditorAssetLibrary.save_directory(destination, only_if_is_dirty=False, recursive=True):
        raise RuntimeError('Could not save witness')
    report['success'] = True
    flush('complete')
except Exception:
    report['error'] = traceback.format_exc()
    flush('failed')
    raise
finally:
    unreal.SystemLibrary.quit_editor()
