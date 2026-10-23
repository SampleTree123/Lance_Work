"""Injected-Unreal, copy-only skin audit/variant helper for the October 12 pilot.

Import is inert. Never edits a mesh, parent material, source MIC or source texture.
Root owns UE connection, source selection, scene copies, validation and rendering.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = '/Game/DataMake/Validation/SkinDetailOptimization20261012'
PROJECT = Path('D:/UE/projects/datatry_02')
ROLES = ('Head', 'Body', 'Arm', 'Leg')
REGISTRY = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/cfd_native_batch40_20261006_v1/imported_character_registry.json')


def path(obj):
    return obj.get_path_name() if obj else None


def pin(asset_path):
    package = asset_path.split('.')[0]
    if not package.startswith('/Game/'):
        return None
    filename = PROJECT/'Content'/(package[6:]+'.uasset')
    return {'path': str(filename), 'sha256': hashlib.sha256(filename.read_bytes()).hexdigest()}


def assert_project(u):
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong project')


def owned(value):
    if not value.startswith(ROOT+'/') or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', value):
        raise ValueError('Destination must be a new owned package')
    return value


def property_value(obj, name):
    try:
        value = obj.get_editor_property(name)
        return value if isinstance(value, (str, bool, int, float)) or value is None else str(value)
    except Exception as exc:
        return {'unavailable': str(exc)}


def material_audit(u, material):
    lib = u.MaterialEditingLibrary
    result = {'path': path(material), 'file': pin(path(material)), 'parents': [], 'scalars': {}, 'vectors': {}, 'textures': {}}
    current = material
    seen = set()
    while isinstance(current, u.MaterialInstanceConstant):
        parent = current.get_editor_property('parent')
        if parent is None or path(parent) in seen:
            break
        seen.add(path(parent))
        result['parents'].append({'path': path(parent), 'file': pin(path(parent))})
        current = parent
    for name in lib.get_scalar_parameter_names(material):
        result['scalars'][str(name)] = float(lib.get_material_instance_scalar_parameter_value(material, name))
    for name in lib.get_vector_parameter_names(material):
        v = lib.get_material_instance_vector_parameter_value(material, name)
        result['vectors'][str(name)] = [v.r, v.g, v.b, v.a]
    for name in lib.get_texture_parameter_names(material):
        tex = lib.get_material_instance_texture_parameter_value(material, name)
        if tex is None:
            result['textures'][str(name)] = None
            continue
        row = {'path': path(tex), 'file': pin(path(tex)), 'properties': {k: property_value(tex, k) for k in (
            'srgb', 'compression_settings', 'lod_group', 'lod_bias', 'max_texture_size', 'never_stream', 'flip_green_channel', 'mip_gen_settings')}}
        for key, fn in [('size_x', 'blueprint_get_size_x'), ('size_y', 'blueprint_get_size_y')]:
            try:
                row[key] = int(getattr(tex, fn)())
            except Exception as exc:
                row[key] = {'unavailable': str(exc)}
        try:
            row['import_sources'] = list(tex.get_editor_property('asset_import_data').extract_filenames())
        except Exception:
            row['import_sources'] = []
        result['textures'][str(name)] = row
    return result


def character_skin(u, character_id):
    """Read the six-part registry and actual body material slots, without mutation."""
    assert_project(u)
    document = json.loads(REGISTRY.read_text(encoding='utf-8-sig'))
    cases = [r for r in document['cases'] if r['character_id'] == character_id]
    if len(cases) != 1:
        raise ValueError('Unknown character')
    case = cases[0]
    body_path = next(m['path'] for m in case['meshes'] if m['role'] == 'body')
    mesh = u.load_asset(body_path)
    if not isinstance(mesh, u.SkeletalMesh):
        raise ValueError('Body mesh unavailable')
    rows = {}
    for index, slot in enumerate(mesh.get_editor_property('materials')):
        slot_name = str(slot.get_editor_property('material_slot_name'))
        for role in ROLES:
            if slot_name == 'Std_Skin_'+role+'_Pbr':
                mat = slot.get_editor_property('material_interface')
                rows[role] = {'slot_index': index, 'slot_name': slot_name, 'material': material_audit(u, mat)}
    if set(rows) != set(ROLES):
        raise ValueError('Expected four exact skin slots: '+str(rows.keys()))
    return {'character_id': character_id, 'sex': case['sex'], 'body_mesh': body_path,
            'body_file': pin(body_path), 'skeleton': case['skeleton'], 'skins': rows}


def import_texture(u, filename, destination, *, normal=False, srgb=False):
    """Fresh source import, avoiding historical copied platform-data defects."""
    owned(destination)
    source = Path(filename).resolve(strict=True)
    if source.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.bmp'):
        raise ValueError('Unsupported explicit texture source')
    if u.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError('Refusing texture overwrite: '+destination)
    if normal and srgb:
        raise ValueError('Normal must be linear')
    compression = u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT
    group = u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_CHARACTER
    factory = u.TextureFactory()
    factory.set_editor_properties({'compression_settings': compression, 'lod_group': group,
                                   'defer_compression': False, 'create_material': False})
    folder, name = destination.rsplit('/', 1)
    task = u.AssetImportTask()
    task.set_editor_properties({'filename': str(source), 'destination_path': folder, 'destination_name': name,
        'automated': True, 'save': False, 'replace_existing': False, 'factory': factory})
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(destination)
    if not isinstance(texture, u.Texture2D):
        raise RuntimeError('Texture import failed')
    texture.set_editor_properties({'srgb': srgb, 'compression_settings': compression, 'lod_group': group,
                                  'never_stream': True, 'flip_green_channel': False})
    if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('Texture save failed')
    return {'asset': path(texture), 'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'normal': normal, 'srgb': srgb}


def clone_variant(u, source_audit, variant_id, *, scalars=None, vectors=None, textures=None):
    """Copy four MICs; accept only explicit existing parameter names/owned textures.

    Overrides are role -> parameter -> value. Texture values are already-imported
    asset paths inside this pilot. Returns slot -> new material mapping for a
    copied scene's component overrides; it never sets skeletal mesh materials.
    """
    assert_project(u)
    if not re.fullmatch(r'[A-Za-z0-9_]+', variant_id):
        raise ValueError('Invalid variant identifier')
    overrides = (scalars or {}, vectors or {}, textures or {})
    if any(set(v)-set(ROLES) for v in overrides):
        raise ValueError('Only four skin roles may change')
    lib = u.MaterialEditingLibrary
    staged = []
    # Validate all four roles before creating any asset.
    for role, row in source_audit['skins'].items():
        source = row['material']['path']
        target = owned(ROOT+'/'+source_audit['character_id']+'/'+variant_id+'/MI_Skin_'+role)
        if u.EditorAssetLibrary.does_asset_exist(target):
            raise ValueError('Variant exists; choose a new revision')
        if pin(source) != row['material']['file']:
            raise ValueError('Source changed since audit')
        mat = u.load_asset(source)
        if not isinstance(mat, u.MaterialInstanceConstant):
            raise ValueError('Expected source MIC')
        for group, key in zip(overrides, ('scalars', 'vectors', 'textures')):
            if set(group.get(role, {}))-set(row['material'][key]):
                raise ValueError('Unknown '+role+' '+key+' parameter')
        for value in overrides[0].get(role, {}).values():
            if not math.isfinite(float(value)):
                raise ValueError('Nonfinite scalar')
        for value in overrides[1].get(role, {}).values():
            if len(value) != 4 or not all(math.isfinite(float(x)) for x in value):
                raise ValueError('Vector must have four finite values')
        for value in overrides[2].get(role, {}).values():
            owned(value.split('.')[0])
            if not isinstance(u.load_asset(value), u.Texture2D):
                raise ValueError('Owned texture missing')
        staged.append((role, row, source, target))
    result = {'character_id': source_audit['character_id'], 'variant_id': variant_id, 'overrides': [], 'materials': {}}
    for role, row, source, target in staged:
        mat = u.EditorAssetLibrary.duplicate_asset(source, target)
        if mat is None:
            raise RuntimeError('MIC duplicate failed')
        for name, value in overrides[0].get(role, {}).items():
            lib.set_material_instance_scalar_parameter_value(mat, name, float(value))
            if abs(float(lib.get_material_instance_scalar_parameter_value(mat, name))-float(value)) > 1e-5:
                raise RuntimeError('Scalar readback failed: '+name)
        for name, value in overrides[1].get(role, {}).items():
            lib.set_material_instance_vector_parameter_value(mat, name, u.LinearColor(*value))
            actual = lib.get_material_instance_vector_parameter_value(mat, name)
            if max(abs(a-b) for a,b in zip((actual.r,actual.g,actual.b,actual.a), value)) > 1e-5:
                raise RuntimeError('Vector readback failed: '+name)
        for name, value in overrides[2].get(role, {}).items():
            tex = u.load_asset(value)
            lib.set_material_instance_texture_parameter_value(mat, name, tex)
            if path(lib.get_material_instance_texture_parameter_value(mat, name)) != path(tex):
                raise RuntimeError('Texture readback failed: '+name)
        if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
            raise RuntimeError('Material save failed')
        result['overrides'].append({'slot_index': row['slot_index'], 'slot_name': row['slot_name'], 'material': path(mat)})
        result['materials'][role] = material_audit(u, mat)
    if pin(source_audit['body_mesh']) != source_audit['body_file']:
        raise RuntimeError('Source mesh changed unexpectedly')
    for _, row, source, _ in staged:
        if pin(source) != row['material']['file']:
            raise RuntimeError('Source material changed unexpectedly')
    result['source_mesh_and_materials_unchanged'] = True
    return result


def apply_to_copied_component(u, component, variant):
    """Apply only in an explicitly loaded pilot world. Caller saves that world."""
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if not world.get_path_name().startswith(ROOT+'/'):
        raise ValueError('Load the copied pilot world before changing overrides')
    if component.get_world() != world:
        raise ValueError('Component belongs to another world')
    for row in variant['overrides']:
        component.set_material(row['slot_index'], u.load_asset(row['material']))
        if path(component.get_material(row['slot_index'])) != row['material']:
            raise RuntimeError('Component material assignment failed')
    return {'world': path(world), 'component': path(component), 'variant': variant['variant_id']}
