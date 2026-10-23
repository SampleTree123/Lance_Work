"""Session-only pair preview materials; canonical save/render contracts stay intact.

Install only into the pair's PrivateModules graph. Saved neutral MICs are reused
across roots. Missing colors use transient MIDs over one coverage-corrected
neutral parent per source; no MIC editing API ever receives a MID.
"""
from __future__ import annotations

import copy
import hashlib
import json
import struct

FORMAL_ROOT = '/Game/DataMake/Appearance/Materials'
VERSION = 'pair_preview_material_fast_v1'
REVIEW_ALPHA_MULTIPLIER = 1.5


def _f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


class _CoverageComponent:
    """Run the existing coverage factory on a private, unbound slot proxy."""
    def __init__(self, source, parent):
        self.source, self.material = source, parent

    def get_skeletal_mesh_asset(self):
        return self

    def get_editor_property(self, name):
        if name != 'materials':
            raise ValueError(name)
        return [self]

    @property
    def material_interface(self):
        return self.source

    def get_material(self, index):
        return self.material

    def set_material(self, index, material):
        self.material = material


class Session:
    def __init__(self, graph, u):
        self.u = u
        self.neutral = graph.load('hair_color_neutral_trial_runtime_v1')
        self.original = graph.load('hair_eye_color_runtime_v1')
        self.palette = graph.load('scene_site_hair_color_trials_v1')
        self.coverage = graph.load('ue_hair_coverage_runtime_v1')
        self.original_material = self.neutral.material
        self.original_coverage = self.coverage.apply
        self.original_sha = self.original._sha
        self.original_package_file = self.original.package_file
        self.package_files = {}
        self.hashes, self.sources, self.materials, self.parents, self.dynamic = {}, {}, {}, {}, {}
        self.shader = None

    def sha(self, file):
        # The pair's session input guard owns invalidation. The user explicitly
        # requested no repeated whole-package hashing while browsing previews.
        key = str(file)
        if key not in self.hashes:
            self.hashes[key] = self.original_sha(file)
        return self.hashes[key]

    def package_file(self, asset_path):
        if asset_path not in self.package_files:
            self.package_files[asset_path] = self.original_package_file(asset_path)
        return self.package_files[asset_path]

    def _shader(self):
        if self.shader is None:
            shader = self.u.load_asset(self.neutral.SHADER)
            if shader is None or str(self.u.EditorAssetLibrary.get_metadata_tag(shader, 'DM_NeutralHairTrial')) != 'v1':
                raise RuntimeError('Neutral hair trial shader is missing or incomplete')
            self.shader = shader
        return self.shader

    def specification(self, row, preset, soft=False):
        source_key = (self.original._path(row['source']), row['source_sha256'])
        if source_key not in self.sources:
            self.sources[source_key] = self.neutral.snapshot(self.u.MaterialEditingLibrary, row['source'])
        expected = copy.deepcopy(self.sources[source_key])
        for name, value in self.palette.NEUTRAL_SCALAR_OVERRIDES.get(preset, {}).items():
            if name not in expected['scalar']:
                raise RuntimeError('Hair source lacks white midtone parameter: ' + name)
            expected['scalar'][name] = _f32(value)
        expected['vector']['Base Color Tint'] = [_f32(x) for x in self.palette.NEUTRAL_TINTS[preset]]
        specification = {'version': 2, 'method': self.palette.NEUTRAL_METHOD,
            'source': source_key[0], 'source_sha256': source_key[1],
            'shader_sha256': self.sha(self.original.package_file(self.neutral.SHADER)),
            'base_preset': preset, 'effective_parameters': expected}
        if soft:
            expected['scalar'] = self.neutral.soft_reflection_scalars(expected['scalar'])
            specification['reflection_method'] = self.palette.SOFT_REFLECTION_METHOD
        spec = json.dumps(specification, sort_keys=True)
        key = hashlib.sha256(spec.encode()).hexdigest()[:20]
        return expected, spec, '/NeutralHairTrialsV1/Instances/MI_' + preset + '_' + key

    def existing(self, row, preset, root, soft=False):
        expected, spec, suffix = self.specification(row, preset, soft)
        for directory in dict.fromkeys((root, FORMAL_ROOT)):
            target = directory + suffix
            if not self.u.EditorAssetLibrary.does_asset_exist(target):
                continue
            instance = self.u.load_asset(target)
            if not isinstance(instance, self.u.MaterialInstanceConstant):
                raise RuntimeError('Neutral preview instance has wrong class: ' + target)
            if str(self.u.EditorAssetLibrary.get_metadata_tag(instance, self.neutral.OWNER)) != spec:
                raise RuntimeError('Incomplete or mismatched neutral hair trial instance: ' + target)
            if (self.original._path(instance.get_editor_property('parent')) != self.original._path(self._shader())
                    or self.neutral.snapshot(self.u.MaterialEditingLibrary, instance) != expected):
                raise RuntimeError('Neutral trial parameter inheritance no longer matches source: ' + target)
            return instance
        return None

    def create_base(self, row, root):
        """Copy source overrides and write only values changed by reparenting.

        In particular, setting an unchanged static switch is expensive in the
        editor. A source already carrying the desired value needs no setter.
        """
        u, lib = self.u, self.u.MaterialEditingLibrary
        expected, spec, suffix = self.specification(row, 'black')
        target = root + suffix
        instance = u.EditorAssetLibrary.duplicate_asset(self.original._path(row['source']).split('.')[0], target)
        if not isinstance(instance, u.MaterialInstanceConstant):
            raise RuntimeError('Neutral preview source duplication failed')
        lib.set_material_instance_parent(instance, self._shader())
        actual = self.neutral.snapshot(lib, instance)
        for name, value in expected['scalar'].items():
            if actual['scalar'].get(name) != value:
                lib.set_material_instance_scalar_parameter_value(instance, name, value)
        for name, value in expected['vector'].items():
            if actual['vector'].get(name) != value:
                lib.set_material_instance_vector_parameter_value(instance, name, u.LinearColor(*value))
        for name, value in expected['texture'].items():
            if actual['texture'].get(name) != value:
                texture = u.load_asset(value) if value else None
                if value and texture is None:
                    raise RuntimeError('Neutral preview texture is missing: ' + value)
                lib.set_material_instance_texture_parameter_value(instance, name, texture)
        for name, value in expected['static'].items():
            if actual['static'].get(name) != value:
                lib.set_material_instance_static_switch_parameter_value(instance, name, value)
        lib.update_material_instance(instance)
        if self.neutral.snapshot(lib, instance) != expected:
            raise RuntimeError('Neutral preview parent changed unintended parameters')
        u.EditorAssetLibrary.set_metadata_tag(instance, self.neutral.OWNER, spec)
        if not u.EditorAssetLibrary.save_loaded_asset(instance, False):
            raise RuntimeError('Neutral preview parent save failed')
        return instance

    def coverage_parent(self, row, parent):
        key = (self.original._path(row['source']), self.original._path(parent))
        if key not in self.parents:
            proxy = _CoverageComponent(row['source'], parent)
            receipt = self.original_coverage(self.u, {'HairPart0': proxy})
            if len(receipt['bindings']) != 1:
                raise RuntimeError('Neutral preview source did not receive hair coverage correction')
            binding = receipt['bindings'][0]
            expected = json.dumps({'version': self.coverage.VERSION, 'parent': key[1], 'source': key[0],
                                   'opacity': binding['opacity_repaired'], 'clip': binding['clip']}, sort_keys=True)
            if (str(self.u.EditorAssetLibrary.get_metadata_tag(proxy.material, 'DM_HairCoverage')) != expected
                    or self.original._path(proxy.material.get_editor_property('parent')) != key[1]):
                raise RuntimeError('Incomplete or mismatched hair coverage preview parent')
            self.parents[key] = (self.density_parent(proxy.material, binding), binding)
        return self.parents[key]

    @staticmethod
    def _get(mid, parameter, kind):
        # UE 5.8 declares ScriptName=Get*ParameterValue; older bindings retain
        # K2 prefixes. Both are MID methods, never the MIC editing library.
        method = getattr(mid, 'get_' + kind + '_parameter_value', None)
        if method is None:
            method = getattr(mid, 'k2_get_' + kind + '_parameter_value')
        return method(parameter)

    def material(self, row, root, slot, soft_reflection=False):
        if row['kind'] != 'hair':
            return self.original_material(row, root, slot, soft_reflection)
        self._shader()
        key = (self.original._path(row['source']), row['source_sha256'], row['preset'], root, soft_reflection)
        if key in self.materials:
            return self.materials[key][0], self.materials[key][1], False
        instance = self.existing(row, row['preset'], root, soft_reflection)
        expected, _, _ = self.specification(row, row['preset'], soft_reflection)
        created = False
        if instance is None:
            base_key = ('neutral_base', key[0], key[1], root)
            if base_key not in self.materials:
                base = None
                for preset in self.palette.NEUTRAL_TINTS:
                    base = self.existing(row, preset, root)
                    if base is not None:
                        break
                if base is None:
                    base = self.create_base(row, root)
                    created = True
                self.materials[base_key] = (base, None)
            parent, coverage = self.coverage_parent(row, self.materials[base_key][0])
            instance = self.u.MaterialLibrary.create_dynamic_material_instance(None, parent)
            if not isinstance(instance, self.u.MaterialInstanceDynamic):
                raise RuntimeError('Cannot create transient neutral preview material')
            instance.set_vector_parameter_value('Base Color Tint', self.u.LinearColor(*expected['vector']['Base Color Tint']))
            # A reused white parent must reset the compensation to the source
            # value for nonwhite dyes, avoiding color-order dependent results.
            scalar_names = {name for overrides in self.palette.NEUTRAL_SCALAR_OVERRIDES.values() for name in overrides}
            if soft_reflection:
                scalar_names.update(('Specular Multiplier', 'Roughness Multiplier'))
            for name in scalar_names:
                if name not in expected['scalar']:
                    raise RuntimeError('Hair source lacks preview scalar: ' + name)
                instance.set_scalar_parameter_value(name, expected['scalar'][name])
                if abs(float(self._get(instance, name, 'scalar')) - expected['scalar'][name]) > 1e-5:
                    raise RuntimeError('Neutral preview scalar readback mismatch: ' + name)
            self.original._assert_rgba(self.original._rgba(self._get(instance, 'Base Color Tint', 'vector')),
                                       expected['vector']['Base Color Tint'])
            self.dynamic[self.original._path(instance)] = {'instance': instance, 'source': key[0], 'coverage': dict(coverage)}
        actual = expected['vector']['Base Color Tint']
        self.materials[key] = (instance, actual)
        return instance, actual, created

    def apply_coverage(self, u, components):
        # Existing MICs retain the exact shared correction. The original code
        # deliberately skips MIDs; ours already inherit the corrected MIC.
        pending = []
        for name, component in components.items():
            mesh = component.get_skeletal_mesh_asset()
            if not name.startswith('HairPart') or mesh is None:
                continue
            for index, slot in enumerate(mesh.get_editor_property('materials')):
                instance = component.get_material(index)
                if not isinstance(instance, u.MaterialInstanceDynamic):
                    continue
                record = self.dynamic.get(self.original._path(instance))
                if record is None or record['instance'] != instance or record['source'] != self.original._path(slot.material_interface):
                    raise RuntimeError('Unrecognized dynamic hair material in pair preview')
                row = dict(record['coverage'], component=name, slot=index, material=self.original._path(instance))
                pending.append(row)
        result = self.original_coverage(u, components)
        result['bindings'].extend(pending)
        self.apply_density(components, result['bindings'])
        result['review_alpha_multiplier'] = REVIEW_ALPHA_MULTIPLIER
        return result

    def density_parent(self, material, row):
        if not row.get('opacity_repaired'):
            return material
        u = self.u
        key = self.original._path(material)
        target = '/Game/DataMake/Validation/PairRevision20261019_v1/Materials/Density150/MI_' + hashlib.sha256(key.encode()).hexdigest()[:20]
        parent = u.load_asset(target)
        if parent is None:
            folder, label = target.rsplit('/', 1)
            parent = u.AssetToolsHelpers.get_asset_tools().create_asset(label, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            u.MaterialEditingLibrary.set_material_instance_parent(parent, material)
            props = parent.get_editor_property('base_property_overrides')
            props.set_editor_property('override_opacity_mask_clip_value', True)
            props.set_editor_property('opacity_mask_clip_value', .49)
            parent.set_editor_property('base_property_overrides', props)
            u.MaterialEditingLibrary.update_material_instance(parent)
            if not u.EditorAssetLibrary.save_loaded_asset(parent, False):
                raise RuntimeError('Cannot save Hair134 density edge protection')
        return parent

    def apply_density(self, components, bindings):
        """Uniform review density after color/coverage; exclude invisible slots.

        Hair134's nonzero JPEG border needs a slightly higher clipping floor
        when alpha is amplified, otherwise the old card rectangles reappear.
        """
        u = self.u
        if not hasattr(self, 'density_materials'):
            self.density_materials = {}
        for row in bindings:
            c, index = components[row['component']], row['slot']
            material = c.get_material(index)
            if isinstance(material, u.MaterialInstanceDynamic):
                mid = material
            else:
                key = self.original._path(material)
                if key not in self.density_materials:
                    parent = self.density_parent(material, row)
                    self.density_materials[key] = u.MaterialLibrary.create_dynamic_material_instance(None, parent)
                mid = self.density_materials[key]
                c.set_material(index, mid)
                self.dynamic[self.original._path(mid)] = {'instance': mid, 'source': row['source'], 'coverage': dict(row)}
            mid.set_scalar_parameter_value('Alpha Multiplier', REVIEW_ALPHA_MULTIPLIER)
            row['material'] = self.original._path(mid)
            row['alpha_multiplier'] = REVIEW_ALPHA_MULTIPLIER


def install(graph, u):
    """Install once, exclusively on the caller's private pair module graph."""
    if not hasattr(graph, 'modules'):
        raise TypeError('Pair material acceleration requires a private module graph')
    existing = getattr(graph, '_pair_fast_materials_v1', None)
    if existing is not None:
        return existing
    session = Session(graph, u)
    session.original._sha = session.sha
    session.original.package_file = session.package_file
    session.neutral.material = session.material
    session.coverage.apply = session.apply_coverage
    graph._pair_fast_materials_v1 = session
    return session
