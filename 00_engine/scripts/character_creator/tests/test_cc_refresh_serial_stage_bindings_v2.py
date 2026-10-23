"""Only Normal adapter changes; original durable stages remain delegated."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_serial_stage_bindings_v2 as v2
import cc_refresh_serial_stage_bindings_v1 as v1


def pin(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return pin(path)


def fixture(tmp_path):
    image = tmp_path / 'own_selected_skin_normal.png'
    Image.new('RGBA', (2048, 2048), (128, 128, 255, 255)).save(image)
    texture = dict(pin(image), width=2048, height=2048)
    source, skin = tmp_path / 'own.ccProject', tmp_path / 'own.ccSkin'
    source.write_bytes(b'own source'); skin.write_bytes(b'own skin')
    rows = [dict(owner='avatar', mesh='CC_Base_Body', material=m, textures={'bump': texture}) for m in sorted(v2.SKINS)]
    after = write(tmp_path / 'pixels_after_skin/materials.json', dict(materials=rows))
    config = dict(character_id='CFD40_UNIT_001', source_project=pin(source), assets={'skin': pin(skin)}, restore_four_skin_normals_after_editor_close=True)
    library = dict(diagnostic_mode=v2.MODE, refresh_assembly=config)
    report = dict(config=copy.deepcopy(config), summary_path=str(tmp_path / 'refresh_partial_report.json'), pixel_stages={'after_skin': after})
    normal = dict(complete=True, character_id=config['character_id'], source_project=config['source_project'], selected_skin=config['assets']['skin'],
                  after_skin=after, maps={m:texture for m in v2.SKINS}, captures={}, implementation_sha256=pin(v2.NORMAL_DEPENDENCIES[0])['sha256'])
    report['skin_normal_closure'] = normal
    for label in ('before_writes', 'after_writes', 'first_reload', 'same_sha_reload'):
        captured = copy.deepcopy(rows)
        if label == 'before_writes':
            for row in captured:
                row['textures'] = {}
        captured.append(dict(owner='avatar/1:CC_Base_Eye', mesh='CC_Base_Eye', material='Std_Cornea', textures={'opacity': texture}))
        normal['captures'][label] = write(tmp_path / 'skin_normal_closure' / ('pixels_' + label) / 'materials.json', dict(materials=captured, pixel_capture_complete=True))
    return report, library, v2.controller()


def mutate_capture(report, label, mutate):
    record = report['skin_normal_closure']['captures'][label]
    path = Path(record['path'])
    value = json.loads(path.read_text())
    mutate(value)
    report['skin_normal_closure']['captures'][label] = write(path, value)


def test_private_serial_reuses_durable_controller_and_exact_frozen_recipe():
    old_schema, old_compile = v1.SCHEMA, v1.original_prelash_library
    serial = v2.controller()
    assert serial.SCHEMA.endswith('_v2') and v1.SCHEMA == old_schema
    assert v1.original_prelash_library is old_compile
    assert serial.advance.__code__.co_code == v1.advance.__code__.co_code
    assert serial.new_state.__code__.co_code == v1.new_state.__code__.co_code
    dependencies = serial.dependency_paths()
    assert v2.ORIGINAL in dependencies and all(p in dependencies for p in v2.NORMAL_DEPENDENCIES)
    person = next(p for p in serial.batch.checked_plan(serial.RUN / 'batch_preparation_v7.json')['cases'] if p['character_id'] not in serial.batch.REPS)
    source = person['original_project']
    old = v1.original_prelash_library(person, source, source)
    actual = serial.original_prelash_library(person, source, source)
    assert actual.pop('diagnostic_mode') == v2.MODE
    assert actual['refresh_assembly'].pop('restore_four_skin_normals_after_editor_close') is True
    old.pop('diagnostic_mode')
    assert actual == old


def test_prepare_requires_roots_final_dispatcher_sha_before_writing_any_order(tmp_path):
    target = tmp_path / 'not_created.json'
    with pytest.raises(ValueError, match='Root-confirmed final dispatcher SHA'):
        v2.prepare('unused_geometry', 'unused_backup', target, 'not-final-sha')
    assert not target.exists()


def test_actual_pinned_four_maps_and_stable_captures_pass(tmp_path):
    report, library, serial = fixture(tmp_path)
    assert v2.assert_normal_report(report, library, serial)


def test_complete_flags_cannot_accept_real_missing_on_both_reloads(tmp_path):
    report, library, serial = fixture(tmp_path)
    def missing(snapshot):
        for row in snapshot['materials']:
            if row['material'] in v2.SKINS:
                row['textures'] = {}
    mutate_capture(report, 'first_reload', missing)
    mutate_capture(report, 'same_sha_reload', missing)
    with pytest.raises(ValueError, match='no actual decoded'):
        v2.assert_normal_report(report, library, serial)


def test_actual_other_material_change_is_rejected_despite_passed_flags(tmp_path):
    report, library, serial = fixture(tmp_path)
    changed = tmp_path / 'wrong_eye.png'
    Image.new('RGBA', (2048, 2048), (5, 5, 5, 255)).save(changed)
    def wrong(snapshot):
        snapshot['materials'][-1]['textures']['opacity'] = dict(pin(changed), width=2048, height=2048)
    mutate_capture(report, 'after_writes', wrong)
    with pytest.raises(ValueError, match='other actual material pixels'):
        v2.assert_normal_report(report, library, serial)


def test_same_case_source_identity_and_existing_facts_are_rechecked(tmp_path, monkeypatch):
    report, library, serial = fixture(tmp_path)
    report['skin_normal_closure']['source_project'] = dict(path='other.ccProject', sha256='other')
    with pytest.raises(ValueError, match='same-case Normal-complete'):
        v2.assert_normal_report(report, library, serial)
    # Restoring an already-completed PRELASH fact must rerun the new real-image
    # validator; original v1 stage verification still executes first.
    report['skin_normal_closure']['source_project'] = library['refresh_assembly']['source_project']
    report_path, library_path = tmp_path / 'report.json', tmp_path / 'library.json'
    report_pin = write(report_path, report); library_pin = write(library_path, library)
    state = dict(facts={'prelash_report':report_pin}, steps={'01_prelash':dict(status='completed', library=library_pin, outputs={'report':report_pin})})
    calls = []
    driver = type('Driver', (), {'verify_completed_step':lambda self, state, step: calls.append(step)})()
    monkeypatch.setattr(v2, 'assert_normal_report', lambda *args: (_ for _ in ()).throw(ValueError('real-image rechecked')))
    with pytest.raises(ValueError, match='real-image rechecked'):
        serial.verify_stage_facts(state, driver)
    assert len(calls) == 1
