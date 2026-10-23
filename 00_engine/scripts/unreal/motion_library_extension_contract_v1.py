"""Read-only, paired motion catalog and face overlay; no publication side effects.

Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
The old five-action catalog and N3 registry remain immutable authorities.
"""
from __future__ import annotations
import copy
from contextlib import contextmanager
from contextvars import ContextVar
import importlib.util
import math
from pathlib import Path
import re

def _private(name):
    spec = importlib.util.spec_from_file_location('_motion_extension_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Fresh validators retain their original __file__ and constants. Observing their
# checked records never monkeypatches the loaded N3 runtime or old module globals.
faces = _private('native_face_library_contract_v1')
pilot = _private('ue_motion_library_face_pilot_v1')
_observed = ContextVar('motion_extension_dependencies', default=None)
_face_evidence, _pilot_record = faces._evidence, pilot.checked_record


def _evidence(record, *args, **kwargs):
    result = _face_evidence(record, *args, **kwargs)
    if _observed.get() is not None:
        _observed.get().append(copy.deepcopy(record))
    return result


def _record(record):
    result = _pilot_record(record)
    if _observed.get() is not None:
        _observed.get().append(copy.deepcopy(record))
    return result


faces._evidence, pilot.checked_record = _evidence, _record


@contextmanager
def trace_dependencies():
    records = []
    token = _observed.set(records)
    try:
        yield records
    finally:
        _observed.reset(token)

RUN = pilot.RUN
MOTION_SCHEMA = 'motion_library_extension_v1'
FACE_SCHEMA = 'motion_face_extension_v1'
FACE_ROOT = pilot.ROOT
SEXES = ('female', 'male')
BASE_REGISTRY_SHA = '0b131c4086d0b2fbb6d837f7ad1a4bd045cbf2b9e369885609476577ddc57489'
read, source = faces.read, faces.source


def checked(record, *, json_file=False):
    return faces._evidence(record, {}, json_file=json_file)


def object_path(value):
    return value if '.' in value else value + '.' + value.rsplit('/', 1)[1]


def validate_motion_catalog(document, base):
    if (document.get('schema') != MOTION_SCHEMA or document.get('status') != 'validated_review'
            or document.get('base_catalog_sources') != base['sources']):
        raise ValueError('Motion catalog must bind the exact current five-action authority')
    result = copy.deepcopy(base)
    seen = {r['action_id'] for rows in base['actions_by_sex'].values() for r in rows}
    motions, paths = set(), set()
    if any([r['index'] for r in base['actions_by_sex'][s]] != list(range(1, 6)) for s in SEXES):
        raise ValueError('Historical action indices must remain exactly 1..5')
    if not isinstance(document.get('actions'), list) or not document['actions']:
        raise ValueError('No paired extension actions')
    for index, action in enumerate(document['actions'], 6):
        mid = action.get('motion_id', '')
        if (not re.fullmatch('[A-Z][A-Z0-9_]{0,79}', mid) or mid in motions
                or action.get('index') != index or not str(action.get('label', '')).strip()
                or set(action.get('variants', {})) != set(SEXES)):
            raise ValueError('Unique paired motion ID, label and contiguous stable index required')
        motions.add(mid)
        source_shas = set()
        for sex in SEXES:
            variant = action['variants'][sex]
            aid = variant.get('action_id', '')
            if not re.fullmatch('ACT_[A-Z0-9_]+', aid) or aid in seen:
                raise ValueError('Duplicate or invalid stable action ID')
            seen.add(aid)
            report, info = pilot.import_source(variant['import_report'], sex)
            # Both exports must come from the same motion, not merely share a label.
            motion = variant['source_motion']
            checked(motion)
            source_shas.add(motion['sha256'])
            export = checked(variant['export_report'], json_file=True)
            if (export.get('success') is not True
                    or not faces._same_record(variant['source_fbx'], report['source_fbx'])):
                raise ValueError('Unsuccessful CC export or FBX/report mismatch')
            # Exact source-motion/export-field binding is supplied by the root's
            # export receipt (the bridge has two historical report layouts).
            receipt = checked(variant['export_binding'], json_file=True)
            if (receipt.get('schema') != 'motion_export_binding_v1' or receipt.get('sex') != sex
                    or not faces._same_record(receipt.get('source_motion'), motion)
                    or not faces._same_record(receipt.get('export_report'), variant['export_report'])
                    or not faces._same_record(receipt.get('source_fbx'), variant['source_fbx'])
                    or receipt.get('source_motion_unchanged') is not True):
                raise ValueError('Missing exact source-motion / carrier / FBX export binding')
            body = report['body_only']
            if (report['protected_sources'][0].get('asset') != faces.SKELETONS[sex]
                    or report['verification'].get('face_reference_baseline', {}).get('asset') != faces.SKELETONS[sex]
                    or variant.get('skeleton_path') != faces.SKELETONS[sex]
                    or variant.get('duration_seconds') != info['duration_seconds']
                    or info['duration_seconds'] < 5 or not math.isfinite(info['duration_seconds'])
                    or variant.get('body_only') != info['original_body']):
                raise ValueError('Wrong shared Skeleton, duration or BodyOnly package')
            asset = object_path(info['original_body']['asset'])
            if asset in paths:
                raise ValueError('Repeated BodyOnly asset')
            paths.add(asset)
            result['actions_by_sex'][sex].append({'index': index, 'label': action['label'],
                'action_id': aid, 'motion_id': mid, 'path': asset, 'source_skeleton': faces.SKELETONS[sex],
                'duration_seconds': info['duration_seconds'], 'extension_variant': copy.deepcopy(variant),
                'asset_file_path': info['original_body']['path']})
        if len(source_shas) != 1:
            raise ValueError('Paired sex variants must use the same original motion SHA')
    return result


def motion_catalog(path, base):
    record = source(path)
    result = validate_motion_catalog(checked(record, json_file=True), base)
    result['sources']['motion_extension'] = record
    return result


def validate_face_overlay(document, motions, *, base_library=None):
    if document.get('schema') != FACE_SCHEMA or document.get('status') != 'validated_review':
        raise ValueError('Unverified face extension')
    sources = document['sources']
    if (not faces._same_record(sources.get('base_registry'), source(faces.PANEL_REGISTRY))
            or sources['base_registry']['sha256'] != BASE_REGISTRY_SHA
            or not faces._same_record(sources.get('motion_catalog'), motions['sources']['motion_extension'])
            or not faces._same_record(sources.get('accepted_selection'), source(faces.ACCEPTED_SELECTION))):
        raise ValueError('Face overlay authority changed')
    # Call the unchanged original validator, with its original globals.
    base_library = faces.catalog(faces.PANEL_REGISTRY) if base_library is None else base_library
    selection = checked(sources['accepted_selection'], json_file=True)
    choices = {(r['sex'], r['face_id']): r for r in selection['entries']}
    expected = {(s, f, a['action_id']): a for s in SEXES for a in motions['actions_by_sex'][s][5:] for f in faces.FACE_IDS}
    visual = checked(sources['root_visual'], json_file=True)
    if (visual.get('reviewer') != 'root_agent' or visual.get('status') != 'reviewed_for_panel'
            or visual.get('scope') != 'representative_combinations_only'
            or not str(visual.get('observations', '')).strip() or not visual.get('evidence')):
        raise ValueError('Representative root visual evidence is required')
    for record in visual['evidence']:
        checked(record)
    seen, paths, entries, cache = set(), set(), [], {}
    for raw in document.get('entries', []):
        row = copy.deepcopy(raw)
        key = (row.get('sex'), row.get('face_id'), row.get('body_action_id'))
        if key not in expected or key in seen:
            raise ValueError('Unexpected or duplicate extension face entry')
        seen.add(key)
        sex, face, aid = key
        choice, action = choices[key[:2]], expected[key]
        asset = faces._asset_path(row.get('animation_path'))
        if (asset in paths or not asset.startswith(FACE_ROOT + '/Composites/' + sex + '/')
                or row.get('skeleton_path') != faces.SKELETONS[sex] or row.get('label') != choice['label_zh']
                or row.get('playback') != {'mode': 'oneshot', 'end_behavior': 'hold_last', 'rate': 1, 'duration_seconds': 5}
                or row.get('native_animation_path') != choice['source_animation']):
            raise ValueError('Invalid extension asset, rig or accepted face playback')
        paths.add(asset)
        faces._package(asset, row['package'], cache)
        proof = action['extension_variant']['import_report']
        evidence = row['evidence']
        if not faces._same_record(evidence.get('native_import'), choice['evidence']['source_report']):
            raise ValueError('Wrong native face evidence')
        comp = checked(evidence['composition'], json_file=True)
        coverage = faces._five_second_composition(comp, sex, asset, choice['asset'], 0, 5, cache)
        task = comp['task']
        if (not faces._same_record(task.get('motion_source_import_report'), proof)
                or task.get('body_mode') != 'animation'
                or not faces._same_record(task.get('accepted_face_selection'), sources['accepted_selection'])
                or not faces._same_record(task.get('accepted_static_report'), choice['evidence']['composition_report'])
                or task.get('panel_integration_task', {}).get('body_action_id') != aid
                or task.get('panel_integration_task', {}).get('face_id') != face):
            raise ValueError('Face composition does not bind the selected motion / accepted face')
        accepted_report = checked(choice['evidence']['composition_report'], json_file=True)
        if task.get('allowed_face_curve_names') != accepted_report['task']['allowed_face_curve_names']:
            raise ValueError('Face curve allowlist changed')
        body = checked(task['body_window_report'], json_file=True)
        verify, mapping = body.get('verification', {}), body.get('mapping', {})
        if (body.get('success') is not True or body.get('sources_unchanged') is not True
                or body.get('new_dirty_packages_outside_target') != [] or body.get('dirty_sources') != []
                or not faces._same_record(body.get('motion_source_import_report'), proof)
                or body.get('task', {}).get('sex') != sex or body['task'].get('action_id') != aid
                or body.get('original_body') != action['extension_variant']['body_only']
                or body.get('original_body') != task.get('original_body')
                or not body.get('destination', '').startswith(FACE_ROOT + '/BodyWindows/' + sex + '/')
                or task.get('body_animation') != body.get('destination')
                or mapping.get('mode') != 'crop_first_five_seconds'
                or any(mapping.get(k) is not False for k in ('face_clock_wraps', 'body_retimed', 'seams_blended'))
                or verify.get('bone_count') != 118 or verify.get('duration_seconds') != 5
                or verify.get('fps') != mapping.get('fps')
                or verify.get('all_frame_count') != round(5 * verify.get('fps', 0)) + 1
                or set(verify.get('max_absolute_errors', {})) != {'bones', 'curves'}
                or any(not math.isfinite(v) or not 0 <= v <= 1e-4 for v in verify['max_absolute_errors'].values())):
            raise ValueError('Five-second crop must preserve all native body frames with no retiming')
        faces._package(body['asset_record']['asset'], body['asset_record'], cache)
        for record in body['sources']:
            checked(record)
        row.update(non_face_validation=coverage, user_acceptance='pending_complete_character_review')
        entries.append(row)
    if seen != set(expected) or not visual.get('animation_paths') or not set(visual['animation_paths']) <= paths:
        raise ValueError('Exact four-face paired motion coverage or visual scope mismatch')
    if {r['sex'] for r in entries if r['animation_path'] in visual['animation_paths']} != set(SEXES):
        raise ValueError('Representative visual evidence must include both sexes')
    return {'schema': FACE_SCHEMA, 'status': 'validated_review', 'sources': copy.deepcopy(sources),
            'entries': copy.deepcopy(base_library['entries']) + entries}


def face_catalog(path, motions):
    record = source(path)
    result = validate_face_overlay(checked(record, json_file=True), motions)
    return dict(result, registry_source=record)


def check_index(index, data):
    counts = [len(data['actions_by_sex'][s]) for s in SEXES]
    if len(set(counts)) != 1 or type(index) is not int or not 0 <= index <= counts[0]:
        raise ValueError('Body action index is outside the exact paired catalog')
    return index


def build_motion_document(pairs, base):
    """Build from exact supplied export/import records; never writes or activates.

Each pair supplies motion_id, label, and female/male variants with action_id,
import_report, source_motion, export_report and export_binding SHA records.
Remaining values are derived from verified import reports, never guessed.
"""
    actions = []
    for index, pair in enumerate(pairs, 6):
        item = copy.deepcopy(pair)
        item['index'] = index
        for sex in SEXES:
            variant = item['variants'][sex]
            report, info = pilot.import_source(variant['import_report'], sex)
            variant.update(source_fbx=report['source_fbx'], body_only=info['original_body'],
                           duration_seconds=info['duration_seconds'], skeleton_path=faces.SKELETONS[sex])
        actions.append(item)
    document = {'schema': MOTION_SCHEMA, 'status': 'validated_review',
                'base_catalog_sources': copy.deepcopy(base['sources']), 'actions': actions}
    validate_motion_catalog(document, base)
    return document


def build_face_document(motions, composition_reports, root_visual):
    """Build the overlay from full reports, then verify the exact derived matrix."""
    choices = {(r['sex'], r['face_id']): r for r in read(faces.ACCEPTED_SELECTION)['entries']}
    rows = []
    for record in composition_reports:
        report = checked(record, json_file=True)
        task = report['task']
        selection = task['panel_integration_task']
        sex, face = task['sex'], selection['face_id']
        choice = choices[(sex, face)]
        asset = object_path(report['destination'])
        package_path = faces.PROJECT_CONTENT / (asset.split('.')[0].removeprefix('/Game/') + '.uasset')
        package = dict(source(package_path), asset=asset)
        rows.append({'sex': sex, 'face_id': face, 'body_action_id': selection['body_action_id'],
            'label': choice['label_zh'], 'animation_path': asset, 'skeleton_path': faces.SKELETONS[sex],
            'native_animation_path': choice['source_animation'], 'package': package,
            'playback': {'mode': 'oneshot', 'end_behavior': 'hold_last', 'rate': 1, 'duration_seconds': 5},
            'evidence': {'native_import': choice['evidence']['source_report'], 'composition': record}})
    document = {'schema': FACE_SCHEMA, 'status': 'validated_review', 'sources': {
        'base_registry': source(faces.PANEL_REGISTRY), 'motion_catalog': motions['sources']['motion_extension'],
        'accepted_selection': source(faces.ACCEPTED_SELECTION), 'root_visual': root_visual}, 'entries': rows}
    validate_face_overlay(document, motions)
    return document
