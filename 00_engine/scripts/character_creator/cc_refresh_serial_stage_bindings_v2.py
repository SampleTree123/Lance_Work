"""Normal-complete PRELASH adapter over the frozen serial v1 controller.

No scheduler or new receipt promotion. Offline prepare requires root's final
dispatcher SHA; pending/failed behavior and existing representative_gate remain
entirely owned by v1. No existing order/state or implementation is overwritten.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
ORIGINAL = DIRECTORY / 'cc_refresh_serial_stage_bindings_v1.py'
ORIGINAL_SHA = '82f4a1b1599e4f4d6d327bab1d5da132070229f8b9e798402578b86416a930c9'
MODE = 'character_refresh_normals'
SKINS = frozenset(('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg'))
NORMAL_DEPENDENCIES = tuple(DIRECTORY / name for name in (
    'cc_refresh_skin_normal_closure_v1.py', 'cc_probe_refresh_skin_normal_restore_v1.py',
    'cc_probe_refresh_skin_material_readonly_v1.py', 'cc_refresh_material_pixels_v1.py',
    'cc_skin_detail_experiment_v1.py', 'cc_repair_headshot_support_materials_v1.py'))


class FileImage:
    """Only the QImage methods used by the frozen RGBA comparison, off CC."""
    Format_RGBA8888 = 'file_decoded_RGBA'
    def __init__(self, path):
        from PIL import Image
        self.image = None
        try:
            with Image.open(path) as value:
                value.load()
                self.image = value.convert('RGBA')
        except Exception:
            pass
    def isNull(self):
        return self.image is None
    def width(self):
        return self.image.width if self.image is not None else 0
    def height(self):
        return self.image.height if self.image is not None else 0
    def convertToFormat(self, _format):
        return self
    def __eq__(self, other):
        return isinstance(other, FileImage) and self.image is not None and other.image is not None and self.image.size == other.image.size and self.image.tobytes() == other.image.tobytes()


def assert_normal_report(report, library, serial):
    """Re-read actual pinned captures; missing-twice flags cannot complete a step."""
    import cc_probe_refresh_skin_normal_restore_v1 as engine
    from cc_skin_detail_experiment_v1 import MISSING_TEXTURE_SHA256
    config = library['refresh_assembly']
    observed = report['config']
    normal = report.get('skin_normal_closure', {})
    if (library.get('diagnostic_mode') != MODE or config.get('restore_four_skin_normals_after_editor_close') is not True
            or observed.get('restore_four_skin_normals_after_editor_close') is not True
            or normal.get('complete') is not True or normal.get('character_id') != config['character_id']
            or observed['character_id'] != config['character_id']
            or normal.get('source_project') != config['source_project'] or observed['source_project'] != config['source_project']
            or normal.get('selected_skin') != config['assets']['skin'] or observed['assets']['skin'] != config['assets']['skin']
            or normal.get('after_skin') != report['pixel_stages']['after_skin']
            or normal.get('implementation_sha256') != serial.bind(NORMAL_DEPENDENCIES[0])['sha256']):
        raise ValueError('Actual same-case Normal-complete PRELASH report required')
    for record in (normal['source_project'], normal['selected_skin'], normal['after_skin']):
        serial.verify(record, 'Normal same-case input')
    after_skin = serial.read(normal['after_skin']['path'])
    rows = {(r['owner'], r['mesh'], r['material']): r for r in after_skin['materials']}
    maps = normal['maps']
    if set(maps) != SKINS:
        raise ValueError('Exactly four own after_skin maps required')
    for material, record in maps.items():
        if record != rows[('avatar', 'CC_Base_Body', material)]['textures'].get('bump') or record['sha256'] in MISSING_TEXTURE_SHA256:
            raise ValueError('Normal source differs from own after_skin actual image')
        serial.verify(record, 'Normal source image')
        image = FileImage(record['path'])
        if image.isNull() or (image.width(), image.height()) != (2048, 2048) or (record['width'], record['height']) != (2048, 2048):
            raise ValueError('Real decoded2048 Normal source required')
    snapshots = {}
    expected_labels = {'before_writes', 'after_writes', 'first_reload', 'same_sha_reload'}
    if set(normal['captures']) != expected_labels:
        raise ValueError('Actual write/reload Normal captures required')
    boundary = Path(report['summary_path']).resolve().parent / 'skin_normal_closure'
    for label, record in normal['captures'].items():
        serial.verify(record, 'Actual Normal capture')
        if Path(record['path']).resolve() != boundary / ('pixels_' + label) / 'materials.json':
            raise ValueError('Normal capture is outside its actual PRELASH output')
        snapshot = serial.read(record['path'])
        if snapshot.get('pixel_capture_complete') is not True:
            raise ValueError('Incomplete actual eight-channel Normal capture')
        for row in snapshot['materials']:
            for texture in row['textures'].values():
                serial.verify(texture, 'Actual captured standard-channel PNG')
                if texture['sha256'] in MISSING_TEXTURE_SHA256:
                    raise ValueError('Warning cannot be an actual captured image')
        snapshots[label] = snapshot
    api = SimpleNamespace(QtGui=SimpleNamespace(QImage=FileImage))
    for label in ('after_writes', 'first_reload', 'same_sha_reload'):
        engine.verify_restored_maps(snapshots[label], maps, api)
    if not engine.pixel_compare(snapshots['before_writes'], snapshots['after_writes'], api, allow_four_normal_pairs=True)['passed']:
        raise ValueError('Normal restoration changed other actual material pixels')
    if not engine.pixel_compare(snapshots['first_reload'], snapshots['same_sha_reload'], api)['passed']:
        raise ValueError('Actual eight-channel same-SHA product is not stable')
    return True


def controller():
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA:
        raise ValueError('Frozen serial v1 changed')
    spec = importlib.util.spec_from_file_location('_normal_complete_private_serial_v1', ORIGINAL)
    serial = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serial)
    # v1 functions resolve these globals privately, including their own command
    # paths. Public v1 module, source, old orders and states are never modified.
    serial.__file__ = str(Path(__file__).resolve())
    serial.SCHEMA = 'cfd40_refresh_serial_stage_bindings_v2'
    dependencies = serial.dependency_paths
    serial.dependency_paths = lambda: list(dict.fromkeys(dependencies() + [ORIGINAL] + list(NORMAL_DEPENDENCIES)))
    compile_prelash = serial.original_prelash_library
    def original_prelash_library(person, source, backup):
        library = compile_prelash(person, source, backup)
        library['diagnostic_mode'] = MODE
        library['refresh_assembly']['restore_four_skin_normals_after_editor_close'] = True
        return library
    serial.original_prelash_library = original_prelash_library
    old_tick, old_completed, old_facts = serial.stage_tick, serial.completed_report, serial.verify_stage_facts
    def stage_tick(state, step_id, library, filename, driver, validate):
        def checked(report):
            validate(report)
            if step_id == '01_prelash':
                assert_normal_report(report, library, serial)
        return old_tick(state, step_id, library, filename, driver, checked)
    def completed_report(state, step_id, filename, driver):
        report = old_completed(state, step_id, filename, driver)
        if step_id == '01_prelash':
            assert_normal_report(report, serial.read(state['steps'][step_id]['library']['path']), serial)
        return report
    def verify_stage_facts(state, driver):
        old_facts(state, driver)
        if 'prelash_report' in state['facts']:
            report = serial.read(state['facts']['prelash_report']['path'])
            assert_normal_report(report, serial.read(state['steps']['01_prelash']['library']['path']), serial)
    serial.stage_tick, serial.completed_report, serial.verify_stage_facts = stage_tick, completed_report, verify_stage_facts
    return serial


def prepare(geometry_order, session_backup, output, dispatcher_sha256):
    serial = controller()
    dispatcher = DIRECTORY / 'cc_validate_body_reconstruction.py'
    if not dispatcher_sha256 or serial.bind(dispatcher)['sha256'] != dispatcher_sha256:
        raise ValueError('Root-confirmed final dispatcher SHA required before new offline prepare')
    text = dispatcher.read_text(encoding='utf-8-sig')
    if '"character_refresh_normals": "cc_refresh_skin_normal_closure_v1"' not in text or text.count('"character_refresh_normals"') < 4:
        raise ValueError('Final dispatcher must contain the reviewed four-site Normal route')
    return serial.prepare(geometry_order, session_backup, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('prepare', 'advance'), required=True)
    for name in ('geometry-order', 'session-backup', 'output', 'order', 'character-id', 'gate', 'completed-transfer-manifest', 'dispatcher-sha256'):
        parser.add_argument('--' + name)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not all((args.geometry_order, args.session_backup, args.output, args.dispatcher_sha256)) or args.execute:
            parser.error('Offline prepare requires geometry-order/session-backup/output/root final dispatcher-sha256; never execute')
        value = prepare(args.geometry_order, args.session_backup, args.output, args.dispatcher_sha256)
        result = dict(status=value['status'], people=len(value['cases']), output=args.output, application_dispatched=False)
    else:
        if not args.order or not args.character_id:
            parser.error('Advance requires an existing v2 order and explicit character-id')
        result = controller().advance(args.order, args.character_id, args.gate, args.execute, args.completed_transfer_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
