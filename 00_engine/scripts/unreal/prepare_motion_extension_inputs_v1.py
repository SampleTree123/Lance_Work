"""Prepare paired review inputs from an explicit root-reviewed selection only.

No UE/CC import, registry publication, active pointer edit or default UI change.
Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import re

import complete_character_slot_review_contract_v1 as base_contract
import motion_library_extension_contract_v1 as extension

RUN = extension.RUN
ACCEPTED_SCHEMA = 'motion_panel_accepted_candidates_v1'
NOTES = RUN / 'selection_review_notes_v1.json'


def checked_json(path):
    record = extension.source(path)
    return extension.checked(record, json_file=True), record


def accepted_entries(document, notes):
    if (document.get('schema') != ACCEPTED_SCHEMA or document.get('reviewer') != 'root_agent'
            or document.get('scope') != 'explicit_reviewed_candidates_for_panel_not_human_final_acceptance'
            or not isinstance(document.get('accepted_candidates'), list) or not document['accepted_candidates']):
        raise ValueError('Root must supply a nonempty explicit reviewed candidate selection')
    if notes.get('schema') != 'motion_selection_review_notes_v1':
        raise ValueError('Expected the recorded candidate Chinese-label notes')
    labels = {r['candidate_id']: r for r in notes['entries']}
    if len(labels) != len(notes['entries']):
        raise ValueError('Duplicate candidate labels')
    seen = set()
    for row in document['accepted_candidates']:
        identifier = row.get('candidate_id', '')
        review = row.get('visual_review', {})
        if (not re.fullmatch(r'MOTION_CAND_[0-9]{3}', identifier) or identifier in seen or identifier not in labels
                or review.get('status') != 'accepted_for_panel'
                or not isinstance(review.get('observations'), str) or not review['observations'].strip()
                or not isinstance(review.get('evidence'), list) or not review['evidence']):
            raise ValueError('Duplicate/unknown candidate or missing explicit visual decision: ' + identifier)
        for record in review['evidence']:
            extension.checked(record)
        overrides = row.get('variants', {})
        if overrides and set(overrides) != set(extension.SEXES):
            raise ValueError('Variant overrides must specify both sexes')
        for variant in overrides.values():
            if set(variant) != {'import_report', 'preparation_manifest', 'export_binding'}:
                raise ValueError('Only exact import, preparation and export binding paths can be overridden')
            if any(not isinstance(p, str) or not Path(p).is_absolute() for p in variant.values()):
                raise ValueError('Variant override paths must be absolute')
        seen.add(identifier)
    return copy.deepcopy(document['accepted_candidates']), labels


def variant_paths(row, sex):
    overrides = row.get('variants', {})
    if overrides:
        return {key: Path(value) for key, value in overrides[sex].items()}
    slug = row['candidate_id'].lower() + '_' + sex
    return {'import_report': RUN / 'imports' / (slug + '_v1.json'),
        'preparation_manifest': RUN / 'face_pilots' / (slug + '_v1_native5_v1') / 'preparation_manifest.json',
        'export_binding': RUN / 'export_bindings' / (slug + '_export01.json')}


def collect_variant(row, note, sex, accepted_faces):
    paths = variant_paths(row, sex)
    for key, path in paths.items():
        if not path.resolve().is_relative_to(RUN.resolve()) or not path.is_file():
            raise ValueError('Missing or foreign exact ' + key + ': ' + str(path))
    imported_record = extension.source(paths['import_report'])
    imported, info = extension.pilot.import_source(imported_record, sex)
    manifest, manifest_record = checked_json(paths['preparation_manifest'])
    binding, binding_record = checked_json(paths['export_binding'])
    if (manifest.get('schema') != extension.pilot.SCHEMA or manifest.get('sex') != sex
            or not extension.faces._same_record(manifest.get('source_import_report'), imported_record)
            or not extension.faces._same_record(manifest.get('selection'), extension.source(extension.faces.ACCEPTED_SELECTION))
            or binding.get('schema') != 'motion_export_binding_v1' or binding.get('sex') != sex
            or binding.get('source_motion_unchanged') is not True
            or binding.get('source_motion', {}).get('sha256') != note['source_motion']['sha256']
            or not extension.faces._same_record(binding.get('source_fbx'), imported['source_fbx'])):
        raise ValueError('Wrong preparation/import/export/source-motion binding for ' + row['candidate_id'] + '/' + sex)
    action_id = manifest['action_id']
    variant = {'action_id': action_id, 'import_report': imported_record,
        'source_motion': binding['source_motion'], 'export_report': binding['export_report'], 'export_binding': binding_record}
    reports, seen = [], set()
    if len(manifest.get('composition_tasks', [])) != 4:
        raise ValueError('Preparation manifest must reference four explicit face tasks')
    for task_path in manifest['composition_tasks']:
        envelope, task_record = checked_json(task_path)
        task = envelope.get('task', {})
        face = task.get('face_id')
        if (envelope.get('schema') != extension.pilot.SCHEMA
                or not extension.faces._same_record(envelope.get('import_report'), imported_record)
                or task.get('sex') != sex or task.get('body_action_id') != action_id
                or face not in extension.faces.FACE_IDS or face in seen):
            raise ValueError('Missing/duplicate/foreign face composition task')
        report_path = Path(task['report_path'])
        if not report_path.resolve().is_relative_to(RUN.resolve()):
            raise ValueError('Composition report escaped the expansion run')
        report, record = checked_json(report_path)
        actual_task = report.get('task', {})
        choice = accepted_faces[(sex, face)]
        if (actual_task.get('panel_integration_task') != task
                or not extension.faces._same_record(actual_task.get('motion_source_import_report'), imported_record)
                or not extension.faces._same_record(actual_task.get('accepted_face_selection'), manifest['selection'])
                or not extension.faces._same_record(actual_task.get('accepted_static_report'), choice['evidence']['composition_report'])):
            raise ValueError('Composition result differs from its exact requested source/face')
        extension.faces._five_second_composition(report, sex, extension.object_path(report['destination']), choice['asset'], 0, 5, {})
        body = extension.checked(actual_task['body_window_report'], json_file=True)
        if (body.get('success') is not True or body.get('sources_unchanged') is not True
                or body.get('new_dirty_packages_outside_target') != [] or body.get('dirty_sources') != []
                or body.get('original_body') != info['original_body']
                or body.get('task', {}).get('sex') != sex or body['task'].get('action_id') != action_id
                or not extension.faces._same_record(body.get('motion_source_import_report'), imported_record)
                or body.get('mapping', {}).get('mode') != 'crop_first_five_seconds'):
            raise ValueError('Composition does not use the verified native five-second body crop')
        seen.add(face)
        reports.append((face, record))
    reports.sort(key=lambda item: extension.faces.FACE_IDS.index(item[0]))
    return variant, [record for _, record in reports], manifest_record


def prepare(accepted_path, notes_path=NOTES):
    accepted, accepted_record = checked_json(accepted_path)
    notes, notes_record = checked_json(notes_path)
    rows, labels = accepted_entries(accepted, notes)
    selection = extension.read(extension.faces.ACCEPTED_SELECTION)
    accepted_faces = {(r['sex'], r['face_id']): r for r in selection['entries']}
    pairs, reports, preparations = [], [], []
    for row in rows:
        note = labels[row['candidate_id']]
        pair = {'motion_id': row['candidate_id'], 'label': note['label_zh'], 'variants': {}}
        for sex in extension.SEXES:
            variant, composites, proof = collect_variant(row, note, sex, accepted_faces)
            pair['variants'][sex] = variant
            reports.extend(composites)
            preparations.append(proof)
        pairs.append(pair)
    # Reuse exactly the existing paired source contract before emitting inputs.
    # This builds only an in-memory document, not a registry or active pointer.
    extension.build_motion_document(pairs, base_contract.catalog())
    return {'pairs_v1.json': {'pairs': pairs}, 'reports_v1.json': {'composition_reports': reports},
        'preparation_receipt_v1.json': {'schema': 'motion_extension_input_preparation_v1',
            'status': 'inputs_prepared_not_published', 'accepted_selection': accepted_record,
            'label_source': notes_record, 'candidate_ids': [r['candidate_id'] for r in rows],
            'paired_action_count': len(pairs), 'composition_report_count': len(reports),
            'preparation_manifests': preparations, 'first_new_index': 6,
            'new_index_order': 'explicit_accepted_candidates_order', 'root_visual_created': False,
            'registry_written': False, 'ui_activated': False, 'human_acceptance': 'pending',
            'scope': 'numeric_checked_inputs_for_separately_reviewed_explicit_candidates; final_faces_builder_still_required'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted', type=Path, required=True)
    parser.add_argument('--notes', type=Path, default=NOTES)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    if not destination.is_relative_to(RUN.resolve()) or destination.exists():
        raise ValueError('Use a new output directory inside the motion expansion run')
    values = prepare(args.accepted, args.notes)
    destination.mkdir(parents=True, exist_ok=False)
    for name, document in values.items():
        with (destination / name).open('x', encoding='utf-8') as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'output': str(destination), 'paired_actions': len(values['pairs_v1.json']['pairs']),
                      'published': False, 'activated': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
