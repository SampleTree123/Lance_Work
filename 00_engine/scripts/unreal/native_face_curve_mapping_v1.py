"""Offline, fail-closed CC expression to existing UE Morph name correspondence.

No UE/CC imports or application operations. This uses installed official names and preserves
sampled evaluated weights; it does not author performances, infer visemes, solve
bone transforms, or claim that a curve-only animation is a complete facial pose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

VERSION = 'native_face_curve_mapping_v1'
KNOWN_PREFIX = 'CTRL_expressions_'


def token(name):
    """Only remove the known export prefix, underscores and ASCII case.

    Repeated words are significant. Mouth_Mouth_Press_UL is deliberately NOT
    guessed to mean mouthPressUL. Corrections require separate source evidence.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]+', name):
        raise ValueError('Invalid expression/Morph identifier: ' + repr(name))
    return name.removeprefix(KNOWN_PREFIX).replace('_', '').casefold()


def _names(values, label):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(label + ' must be a nonempty list')
    result = list(values)
    for name in result:
        token(name)
    if len(result) != len(set(result)):
        raise ValueError(label + ' contains duplicate names')
    return result


def _index(names, label):
    result = {}
    for name in names:
        key = token(name)
        if key in result:
            raise ValueError(label + ' has ambiguous lexical names: ' + result[key] + ', ' + name)
        result[key] = name
    return result


def load_official_name_map(forward_ini, reverse_json=None):
    """Read CC's installed [CC2MH] map, allowing identical duplicate lines.

    Installed version contains six repeated identical entries. Conflicting
    repeats and contradictory available reverse mappings are rejected.
    """
    path = Path(forward_ini).resolve()
    raw = path.read_bytes()
    mapping, section = {}, None
    for line in raw.decode('utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith((';', '#')):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
            continue
        if section != 'CC2MH':
            continue
        if '=' not in line:
            raise ValueError('Invalid official expression mapping line')
        source, target = (value.strip() for value in line.split('=', 1))
        token(source)
        token(target)
        if source in mapping and mapping[source] != target:
            raise ValueError('Conflicting official mapping for ' + source)
        mapping[source] = target
    if not mapping or len(set(mapping.values())) != len(mapping):
        raise ValueError('Official mapping is empty or has multiple sources for one target')
    records = [{'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}]
    reverse_missing = []
    if reverse_json is not None:
        reverse, record = read_record(reverse_json)
        records.append(record)
        reverse = reverse['Mappings']
        for source, target in mapping.items():
            if target not in reverse:
                reverse_missing.append(target)
            elif reverse[target] != source:
                raise ValueError('Official forward/reverse maps disagree on ' + source)
    return {'curve_map': mapping, 'sources': records, 'reverse_missing': sorted(reverse_missing)}


def build_mapping(expression_names, meshes, exported_expression_names, official_name_map=None):
    """Bind names to both a CC-exported profile and actual selected UE meshes.

    exported_expression_names must come from the matching CC profile's FBX JSON
    Expression keys. The caller records provenance and confirms the profile UID.
    Official mappings take precedence; otherwise only exact unchanged names are
    accepted. No inferred spelling/semantic aliases. Missing source names remain explicit and may only pass if sampled as zero.
    Every mapped destination must exist on at least one selected mesh. Per-mesh
    bindings state which components accept each mapped curve.
    """
    names = _names(expression_names, 'CC expression names')
    _index(names, 'CC expressions')
    exported = _names(exported_expression_names, 'Exported profile names')
    _index(exported, 'Exported profile')
    exported_set = set(exported)
    official_name_map = official_name_map or {}
    if not isinstance(meshes, list) or not meshes:
        raise ValueError('Actual UE mesh inventory is required')
    inventories = {}
    for row in meshes:
        path = row['path']
        if not isinstance(path, str) or not path.startswith('/Game/') or path in inventories:
            raise ValueError('Invalid or repeated mesh path')
        inventories[path] = set(_names(row['morph_names'], 'UE Morph names'))
    all_targets = set().union(*inventories.values())
    mapped, missing = {}, {}
    for name in names:
        target = official_name_map.get(name, name)
        if target not in exported_set:
            missing[name] = 'no_official_or_exact_exported_profile_name'
        elif target not in all_targets:
            missing[name] = 'exported_name_missing_from_selected_ue_meshes'
        else:
            mapped[name] = target
    component_curves = {
        path: sorted(set(mapped.values()) & morphs)
        for path, morphs in inventories.items()
    }
    return {'version': VERSION, 'source_names': names, 'curve_map': mapped,
            'unmapped': missing, 'component_curves': component_curves,
            'scope': 'Official/exact name correspondence; evaluated curve and bone validation remain required.'}


def map_samples(mapping, samples, *, zero_tolerance=0.0):
    """Convert evaluated CC weights without clamping or inventing missing data.

    Times are copied from CC frame/tick evidence. There is deliberately no assumed
    60fps, no percent conversion, and no multiplier for expressiveness: sampled
    final weights require independent reference validation before production.
    Unmapped nonzero data, missing samples, or nonfinite values fail closed.
    """
    if mapping.get('version') != VERSION:
        raise ValueError('Unsupported mapping version')
    if not isinstance(zero_tolerance, (int, float)) or isinstance(zero_tolerance, bool) or not math.isfinite(zero_tolerance) or zero_tolerance < 0:
        raise ValueError('Invalid zero tolerance')
    if not isinstance(samples, list) or not samples:
        raise ValueError('Nonempty sampled performance required')
    expected = set(mapping['source_names'])
    if set(mapping['curve_map']) | set(mapping['unmapped']) != expected or set(mapping['curve_map']) & set(mapping['unmapped']):
        raise ValueError('Mapping does not partition all CC source channels')
    if len(set(mapping['curve_map'].values())) != len(mapping['curve_map']):
        raise ValueError('Multiple source expressions map to one target')
    result, activity = [], set()
    previous = -1
    for row in samples:
        frame = row['frame']
        if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0 or frame <= previous:
            raise ValueError('Frames must be unique ascending nonnegative integers')
        previous = frame
        weights = row['weights']
        if not isinstance(weights, dict) or set(weights) != expected:
            raise ValueError('Sample must contain every source expression exactly once')
        converted = {}
        for name, value in weights.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Nonfinite or nonnumeric sampled expression: ' + name)
            if name in mapping['unmapped']:
                if abs(value) > zero_tolerance:
                    raise ValueError('Active expression has no proven mapping: ' + name)
                continue
            target = mapping['curve_map'][name]
            converted[target] = float(value)
            if abs(value) > zero_tolerance:
                activity.add(target)
        converted_row = {'frame': frame, 'curves': converted}
        if 'ticks' in row:
            ticks = row['ticks']
            if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 0:
                raise ValueError('Invalid source time ticks')
            converted_row['ticks'] = ticks
        result.append(converted_row)
    return {'samples': result, 'active_curve_names': sorted(activity),
            'unmapped_zero_only': dict(mapping['unmapped']),
            'zero_tolerance': float(zero_tolerance),
            'bone_animation_included': False,
            'complete_facial_animation_verified': False}


def read_record(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return json.loads(raw), {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def exported_profile_names(document):
    """Find exactly one exported CC avatar Expression dictionary."""
    found = []
    def visit(value):
        if not isinstance(value, dict):
            return
        if isinstance(value.get('Expression'), dict) and 'ExpressionSet' in value:
            found.append(value['Expression'])
        for child in value.values():
            if isinstance(child, dict):
                visit(child)
    visit(document)
    if len(found) != 1 or not found[0]:
        raise ValueError('Expected exactly one nonempty exported CC Expression profile')
    return list(found[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspection', required=True)
    parser.add_argument('--ue-inventory', required=True)
    parser.add_argument('--profile-json', required=True)
    parser.add_argument('--official-forward-ini', required=True)
    parser.add_argument('--official-reverse-json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    inspection, source = read_record(args.inspection)
    if not inspection.get('success') or not inspection.get('source_unchanged'):
        raise ValueError('Native source inspection must have succeeded with immutable sources')
    inventory, inventory_source = read_record(args.ue_inventory)
    profile, profile_source = read_record(args.profile_json)
    official = load_official_name_map(args.official_forward_ini, args.official_reverse_json)
    mapping = build_mapping(inspection['expression_names'], inventory['meshes'], exported_profile_names(profile), official['curve_map'])
    converted = map_samples(mapping, inspection['samples'])
    report = {'version': VERSION, 'sources': [source, inventory_source, profile_source] + official['sources'],
              'mapping': mapping, 'converted': converted,
              'profile_uid': inspection.get('profile_uid'),
              'scope': 'Offline sampled curve conversion; not a complete animation acceptance.'}
    with Path(args.output).open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
