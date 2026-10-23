"""Offline same-source skeleton comparison; does not import or modify Unreal assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def _vector(bone, primary, fallback, size):
    value = bone.get(primary, bone.get(fallback))
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"Invalid {primary} for bone {bone.get('name')}")
    value = [float(x) for x in value]
    if not all(math.isfinite(x) for x in value):
        raise ValueError(f"Non-finite {primary}")
    return value


def _index(bones):
    index = {}
    for bone in bones:
        name = bone['name']
        if name in index:
            raise ValueError(f"Duplicate bone {name}")
        index[name] = bone
    return index


def compare_bones(reference_bones, candidate_bones):
    old, new = _index(reference_bones), _index(candidate_bones)
    common = sorted(old.keys() & new.keys())
    parents = []
    translation, rotation, scale = [], [], []
    for name in common:
        a, b = old[name], new[name]
        if a['parent'] != b['parent']:
            parents.append({'name': name, 'reference': a['parent'], 'candidate': b['parent']})
        at = _vector(a, 'translation_cm', 'translation', 3)
        bt = _vector(b, 'translation_cm', 'translation', 3)
        aq = _vector(a, 'rotation_xyzw', 'rotation', 4)
        bq = _vector(b, 'rotation_xyzw', 'rotation', 4)
        ass = _vector(a, 'scale', 'scale', 3)
        bs = _vector(b, 'scale', 'scale', 3)
        translation.append((math.dist(at, bt), name))
        # Quaternion signs are equivalent rotations. Keep raw components otherwise.
        rotation.append((min(math.dist(aq, bq), math.dist(aq, [-v for v in bq])), name))
        scale.append((max(abs(x-y) for x, y in zip(ass, bs)), name))
    tm = max(translation, default=(0., None))
    rm = max(rotation, default=(0., None))
    sm = max(scale, default=(0., None))
    missing, extra = sorted(old.keys()-new.keys()), sorted(new.keys()-old.keys())
    return {
        'reference_bone_count': len(old), 'candidate_bone_count': len(new),
        'missing_bones': missing, 'extra_bones': extra, 'parent_differences': parents,
        'max_translation_difference_cm': tm[0], 'max_translation_difference_mm': tm[0]*10,
        'max_translation_bone': tm[1], 'max_quaternion_sign_equivalent_difference': rm[0],
        'max_quaternion_bone': rm[1], 'max_scale_component_difference': sm[0],
        'max_scale_bone': sm[1],
        'exact_hierarchy_and_local_transform_match': bool(old) and not (
            missing or extra or parents or tm[0] or rm[0] or sm[0]),
    }


def _read(path):
    data = path.read_bytes()
    return json.loads(data.decode('utf-8-sig')), {'path': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest()}


def build_report(run_root):
    reference, provenance = _read(run_root / 'old_reference_rig_snapshot.json')
    manifest, manifest_evidence = _read(run_root / 'complete_character_import_manifest_v1.json')
    manifest_cases = {c['sex']: c for c in manifest['cases']}
    cases = []
    required_roles = {'body', 'tongue', 'eyes', 'teeth', 'tearline', 'eye_occlusion'}
    for sex in ('male', 'female'):
        audit, evidence = _read(run_root / f'FIXED_HEAD_{sex.upper()}_FULL' / 'import_audit.json')
        if audit.get('success') is not True or audit.get('standard_candidate_ready') is not True:
            raise ValueError(f'{sex}: requires final successful import audit')
        if audit.get('sex') != sex:
            raise ValueError('Audit sex mismatch')
        for audit_key, manifest_key in (('source', 'fbx'), ('auto_setup_json', 'json')):
            expected, actual = manifest_cases[sex][manifest_key], audit[audit_key]
            if Path(expected['path']).resolve() != Path(actual['path']).resolve() or expected['sha256'] != actual['sha256']:
                raise ValueError(f'{sex}: source manifest provenance mismatch')
        if {m['role'] for m in audit['meshes']} != required_roles or len(audit['meshes']) != 6:
            raise ValueError(f'{sex}: expected exactly six complete component roles')
        mesh_results = []
        for mesh in audit['meshes']:
            result = compare_bones(reference[sex]['bones'], mesh['bones'])
            mesh_results.append({'role': mesh['role'], 'source_name': mesh['source_name'],
                                 'mesh': mesh['path'], 'skeleton': mesh['skeleton'], **result})
        cases.append({'sex': sex, 'source_fbx': audit['source'], 'source_sidecar': audit['auto_setup_json'],
                      'import_audit': evidence, 'old_body_mesh': reference[sex]['body_mesh'],
                      'old_skeleton': reference[sex]['skeleton_path'], 'new_skeleton': audit['skeleton'],
                      'all_components_match': all(x['exact_hierarchy_and_local_transform_match'] for x in mesh_results),
                      'components': mesh_results})
    return {'schema_version': 1, 'reference_snapshot': provenance, 'source_manifest': manifest_evidence, 'cases': cases,
            'success': all(c['all_components_match'] for c in cases),
            'scope': 'Same historical source per sex: 118-bone hierarchy and local reference transforms across all six imported meshes.',
            'not_established': ['New photo identities sharing these skeletons', 'Dynamic animation or expression behavior',
                                'Cross-sex skeleton compatibility', 'Material or skin-weight deformation quality']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.run_root)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')
    print(json.dumps({'success': report['success'], 'output': str(args.output),
                      'cases': [{k:c[k] for k in ('sex', 'all_components_match')} for c in report['cases']]}))


if __name__ == '__main__':
    main()
