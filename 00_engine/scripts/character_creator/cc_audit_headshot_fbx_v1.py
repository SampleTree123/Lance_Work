"""Read-only binary FBX inventory for the bounded Headshot route experiment.

Checks stored meshes, morph channels, skeleton links and raw array hashes.
Does not evaluate skinning or replace the independent Autodesk SDK check.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np


class Reader:
    def __init__(self, path):
        self.path = Path(path)
        self.file = self.path.open('rb')
        if self.file.read(23) != b'Kaydara FBX Binary  \x00\x1a\x00':
            raise ValueError('Not a binary FBX')
        self.version = struct.unpack('<I', self.file.read(4))[0]
        self.header = struct.Struct('<QQQB' if self.version >= 7500 else '<IIIB')
        self.size = self.path.stat().st_size

    def prop(self):
        kind = self.file.read(1).decode('ascii')
        scalars = {'Y': 'h', 'C': '?', 'I': 'i', 'F': 'f', 'D': 'd', 'L': 'q'}
        if kind in scalars:
            fmt = struct.Struct('<' + scalars[kind])
            return fmt.unpack(self.file.read(fmt.size))[0]
        if kind in ('S', 'R'):
            size = struct.unpack('<I', self.file.read(4))[0]
            raw = self.file.read(size)
            if len(raw) != size:
                raise ValueError('Truncated string/raw property')
            return raw.decode('utf-8', errors='strict') if kind == 'S' else {'raw_sha256': hashlib.sha256(raw).hexdigest()}
        arrays = {'f': '<f4', 'd': '<f8', 'l': '<i8', 'i': '<i4', 'b': 'u1', 'c': 'i1'}
        if kind not in arrays:
            raise ValueError('Unsupported property kind ' + repr(kind))
        count, encoding, size = struct.unpack('<III', self.file.read(12))
        raw = self.file.read(size)
        if len(raw) != size or encoding not in (0, 1):
            raise ValueError('Invalid array payload')
        data = zlib.decompress(raw) if encoding else raw
        dtype = np.dtype(arrays[kind])
        if len(data) != count * dtype.itemsize:
            raise ValueError('Array size does not match element count')
        return np.frombuffer(data, dtype=dtype)

    def node(self):
        raw = self.file.read(self.header.size)
        if len(raw) != self.header.size:
            raise ValueError('Truncated node header')
        end, count, prop_bytes, name_length = self.header.unpack(raw)
        if end == 0:
            if any(raw):
                raise ValueError('Invalid node terminator')
            return None
        if end > self.size or end <= self.file.tell():
            raise ValueError('Invalid node end offset')
        name = self.file.read(name_length).decode('utf-8')
        start = self.file.tell()
        props = [self.prop() for _ in range(count)]
        if self.file.tell() - start != prop_bytes:
            raise ValueError('Property byte count mismatch')
        children = []
        while self.file.tell() < end:
            child = self.node()
            if child is None:
                break
            children.append(child)
        if self.file.tell() != end:
            raise ValueError('Node end mismatch')
        return {'name': name, 'props': props, 'children': children}


def packed(node):
    def value(p):
        if isinstance(p, np.ndarray):
            return {'dtype': p.dtype.str, 'count': int(p.size),
                    'sha256': hashlib.sha256(p.tobytes()).hexdigest()}
        return p
    return {'name': node['name'], 'props': [value(p) for p in node['props']],
            'children': [packed(c) for c in node['children']]}


def read_nodes(path):
    reader = Reader(path)
    nodes = []
    try:
        while True:
            node = reader.node()
            if node is None:
                break
            nodes.append(node)
    finally:
        reader.file.close()
    return reader.version, {n['name']: n for n in nodes}


def semantic_objects(top):
    objects = {o['props'][0]: o for o in top['Objects']['children']}
    parents, children, property_parents = {}, {}, {}
    for edge in top['Connections']['children']:
        p = edge['props']
        if p[0] == 'OO' and p[1] in objects and p[2] in objects:
            parents.setdefault(p[1], []).append(p[2])
            children.setdefault(p[2], []).append(p[1])
        elif p[0] == 'OP' and p[1] in objects and (p[2] in objects or p[2] == 0):
            property_parents.setdefault(p[1], []).append((p[2], p[3:]))
    cache = {}

    def key(oid):
        if oid == 0:
            return 'Root:0'
        if oid in cache:
            return cache[oid]
        obj = objects[oid]
        name = obj['props'][1].split('\x00')[0]
        subtype = obj['props'][2] if len(obj['props']) > 2 else ''
        base = obj['name'] + ':' + subtype + ':' + name
        if subtype == 'SelectionSet':
            # CC may emit several identically named selection sets for disjoint
            # vertex selections. Their child payloads, excluding object IDs,
            # distinguish the sets without relying on file object order.
            members = []
            for child_id in children.get(oid, []):
                child = objects[child_id]
                if child['name'] == 'SelectionNode':
                    value = packed(child)
                    value['props'] = value['props'][1:]
                    members.append(value)
            digest = hashlib.sha256(json.dumps(sorted(members, key=lambda x: json.dumps(x)), sort_keys=True).encode()).hexdigest()
            base += '@members:' + digest
        if obj['name'] in ('AnimationCurveNode', 'AnimationCurve'):
            pp = property_parents.get(oid, [])
            if len(pp) != 1:
                raise ValueError('Ambiguous animation property parent: ' + base)
            base = key(pp[0][0]) + '/' + base + '@' + json.dumps(pp[0][1])
        if subtype in ('Skin', 'Cluster', 'BlendShape', 'BlendShapeChannel', 'Shape') or obj['name'] == 'SelectionNode':
            pp = parents.get(oid, [])
            if len(pp) != 1:
                raise ValueError('Ambiguous semantic parent: ' + base)
            base = key(pp[0]) + '/' + base
        if subtype == 'Cluster':
            bones = [x for x in children.get(oid, []) if objects[x]['name'] == 'Model']
            if len(bones) != 1:
                raise ValueError('Ambiguous cluster bone')
            base += '@' + key(bones[0])
        cache[oid] = base
        return base

    out = {}
    for oid, obj in objects.items():
        semantic = key(oid)
        if semantic in out:
            raise ValueError('Nonunique FBX semantic identity: ' + semantic)
        out[semantic] = obj
    return out, cache


def compare(a_path, b_path):
    av, a = read_nodes(a_path)
    bv, b = read_nodes(b_path)
    ao, aid = semantic_objects(a)
    bo, bid = semantic_objects(b)
    report = {'a': str(a_path), 'b': str(b_path), 'version_equal': av == bv,
              'object_count_equal': len(ao) == len(bo), 'structural_errors': [],
              'array_differences': [], 'shape_max_vertex_delta_mm': 0.0,
              'mesh_max_vertex_delta_mm': 0.0, 'skin_weights_max_abs_delta': 0.0,
              'skin_bind_matrix_max_abs_delta': 0.0, 'nonfinite_arrays': []}
    report['semantic_object_keys_equal'] = ao.keys() == bo.keys()
    report['semantic_keys_only_a'] = sorted(ao.keys() - bo.keys())
    report['semantic_keys_only_b'] = sorted(bo.keys() - ao.keys())
    for i in sorted(ao.keys() & bo.keys()):
        an, bn = ao[i], bo[i]
        ac = {n['name']: n for n in an['children']}
        bc = {n['name']: n for n in bn['children']}
        if ac.keys() != bc.keys():
            report['structural_errors'].append('Object child schema mismatch at ' + str(i))
            continue
        subtype = an['props'][2] if len(an['props']) > 2 else ''
        for name in ac:
            if len(ac[name]['props']) != 1 or not isinstance(ac[name]['props'][0], np.ndarray):
                continue
            x, y = ac[name]['props'][0], bc[name]['props'][0]
            if not isinstance(y, np.ndarray) or x.shape != y.shape or x.dtype != y.dtype:
                report['structural_errors'].append('Array schema mismatch at {} {}'.format(i, name))
                continue
            finite = np.isfinite(x) & np.isfinite(y)
            invalid = not bool(finite.all())
            if invalid:
                report['nonfinite_arrays'].append({'object_index': i, 'array': name,
                    'a_nonfinite': int((~np.isfinite(x)).sum()),
                    'b_nonfinite': int((~np.isfinite(y)).sum())})
            with np.errstate(over='ignore'):
                differences = np.abs(x[finite].astype(float)-y[finite].astype(float))
            overflow = bool(np.isinf(differences).any())
            maximum = float(differences.max()) if differences.size and not overflow else (None if overflow else 0.0)
            if maximum or invalid or overflow:
                report['array_differences'].append({'object_index': i, 'name': an['props'][1],
                    'subtype': subtype, 'array': name, 'max_abs_delta': maximum,
                    'nonfinite_input': invalid, 'finite_subtraction_overflow': overflow})
            if name == 'Vertices' and subtype in ('Mesh', 'Shape'):
                if invalid or overflow:
                    raise ValueError('Nonfinite or overflowing vertex comparison at ' + i)
                key = 'shape_max_vertex_delta_mm' if subtype == 'Shape' else 'mesh_max_vertex_delta_mm'
                d = np.linalg.norm((x-y).reshape(-1, 3), axis=1).max()*10 if x.size else 0.0
                report[key] = max(report[key], float(d))
            elif subtype == 'Cluster' and name == 'Weights':
                if invalid or overflow:
                    raise ValueError('Nonfinite or overflowing skin weight comparison at ' + i)
                report['skin_weights_max_abs_delta'] = max(report['skin_weights_max_abs_delta'], maximum)
            elif subtype == 'Cluster' and name in ('Transform', 'TransformLink', 'TransformAssociateModel'):
                if invalid or overflow:
                    raise ValueError('Nonfinite or overflowing bind matrix comparison at ' + i)
                report['skin_bind_matrix_max_abs_delta'] = max(report['skin_bind_matrix_max_abs_delta'], maximum)
            elif x.dtype.kind in 'iu' and maximum:
                report['structural_errors'].append('Integer indices differ at {} {}'.format(i, name))
    def links(top, ids):
        rows = [[n['props'][0]] + [ids.get(v, str(v)) for v in n['props'][1:3]] + n['props'][3:]
                for n in top['Connections']['children']]
        return sorted(rows, key=lambda x: json.dumps(x))
    report['connections_equal_after_id_remap'] = links(a, aid) == links(b, bid)
    report['numeric_repeatability_passed'] = (
        report['semantic_object_keys_equal'] and report['connections_equal_after_id_remap']
        and not report['structural_errors'] and not report['array_differences']
        and not report['nonfinite_arrays'])
    report['scope'] = 'Stored numeric repeatability, not CC/UE rendered or posed mesh verification'
    return report


def audit(path):
    version, top = read_nodes(path)
    objects = top['Objects']['children']
    result = {'source': str(path), 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
              'fbx_version': version, 'meshes': [], 'shapes': [], 'blend_shape_channels': [],
              'skin_clusters': [], 'models': [], 'textures': [],
              'scope': 'Stored binary FBX data; no posed-skin or engine-render acceptance'}
    for obj in objects:
        props = obj['props']
        if len(props) < 3:
            continue
        oid, raw_name, subtype = props[:3]
        name = raw_name.split('\x00')[0]
        row = {'id': oid, 'name': name, 'type': subtype}
        children = {c['name']: c for c in obj['children']}
        if obj['name'] == 'Geometry' and subtype in ('Mesh', 'Shape'):
            raw_vertices = children['Vertices']['props'][0]
            if raw_vertices.size % 3:
                raise ValueError('Invalid vertex triplets')
            vertices = raw_vertices.reshape(-1, 3)
            if not np.isfinite(vertices).all():
                raise ValueError('Nonfinite vertex coordinate')
            row.update(vertex_count=len(vertices), vertices_sha256=hashlib.sha256(raw_vertices.tobytes()).hexdigest(),
                       bounds=[vertices.min(0).tolist(), vertices.max(0).tolist()])
            if subtype == 'Mesh':
                indices = children['PolygonVertexIndex']['props'][0]
                decoded = np.where(indices < 0, -indices - 1, indices)
                if decoded.size and (decoded.min() < 0 or decoded.max() >= len(vertices)):
                    raise ValueError('Out-of-range polygon index')
                row.update(polygon_count=int((indices < 0).sum()),
                           topology_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                           attributes=[packed(c) for c in obj['children'] if c['name'].startswith('LayerElement')])
                result['meshes'].append(row)
            else:
                row['shape_data'] = [packed(c) for c in obj['children'] if c['name'] != 'Vertices']
                result['shapes'].append(row)
        elif obj['name'] == 'Deformer' and subtype in ('BlendShapeChannel', 'Cluster'):
            row['data'] = [packed(c) for c in obj['children']]
            result['blend_shape_channels' if subtype == 'BlendShapeChannel' else 'skin_clusters'].append(row)
        elif obj['name'] == 'Model':
            row['data'] = [packed(c) for c in obj['children']]
            result['models'].append(row)
        elif obj['name'] == 'Texture':
            row['files'] = {k: v['props'] for k, v in children.items() if k in ('FileName', 'RelativeFilename')}
            result['textures'].append(row)
    result['connections'] = [n['props'] for n in top['Connections']['children']]
    result['global_settings'] = packed(top['GlobalSettings'])
    return result


def audit_normals(path):
    """Locate invalid stored normals without changing or normalizing FBX data.

    Shape normals can be deltas, so zero and non-unit vectors are permitted.
    The generous component bound of 16 only flags plainly implausible data;
    passing this check is not a shading or morph-normal acceptance result.
    """
    version, top = read_nodes(path)
    rows = []
    for obj in top['Objects']['children']:
        if obj['name'] != 'Geometry' or len(obj['props']) < 3:
            continue
        name, subtype = obj['props'][1].split('\x00')[0], obj['props'][2]
        if subtype not in ('Mesh', 'Shape'):
            continue

        def visit(node, node_path):
            if node['name'] == 'Normals' and len(node['props']) == 1:
                values = node['props'][0]
                if not isinstance(values, np.ndarray):
                    raise ValueError('Normal payload is not an array')
                finite = np.isfinite(values)
                bad = (~finite) | (np.abs(values) > 16.0)
                examples = np.flatnonzero(bad)[:8]
                rows.append({'geometry': name, 'subtype': subtype,
                             'node_path': node_path, 'component_count': int(values.size),
                             'triplet_layout': values.size % 3 == 0,
                             'nonfinite_components': int((~finite).sum()),
                             'abs_gt_16_components': int((finite & (np.abs(values) > 16)).sum()),
                             'finite_max_abs': float(np.max(np.abs(values[finite]))) if finite.any() else None,
                             'examples': [{'component_index': int(i), 'value': repr(float(values[i]))} for i in examples]})
            for child in node['children']:
                visit(child, node_path + '/' + child['name'])

        visit(obj, 'Geometry')
    return {'source': str(path), 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'fbx_version': version, 'normal_arrays': rows,
            'suspect_array_count': sum(bool(r['nonfinite_components'] or r['abs_gt_16_components'] or not r['triplet_layout']) for r in rows),
            'scope': 'Read-only stored-normal sanity check, not engine-render or posed-normal acceptance'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fbx', required=True)
    p.add_argument('--compare', help='Second FBX for numeric repeat-export comparison')
    p.add_argument('--normals-only', action='store_true', help='Inspect stored mesh and shape normal arrays')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Refusing to overwrite existing FBX audit')
    if args.compare and args.normals_only:
        p.error('--compare and --normals-only are mutually exclusive')
    report = audit_normals(args.fbx) if args.normals_only else (compare(args.fbx, args.compare) if args.compare else audit(args.fbx))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.normals_only:
        print(json.dumps({k: v for k, v in report.items() if k != 'normal_arrays'}))
    elif args.compare:
        print(json.dumps({k: v for k, v in report.items() if k != 'array_differences'}))
    else:
        print(json.dumps({k: len(report[k]) for k in ('meshes', 'shapes', 'blend_shape_channels', 'skin_clusters', 'models', 'textures')}))
