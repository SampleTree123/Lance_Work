"""Opt-in four-map hook inside the proven editor-closed PRELASH closure.

Private runner/closure instances preserve all frozen execution code. Only the
saved-pixel callback and final stability capture gain a real Normal-family gate.
No separate repair job, scene reload, render, or extra SaveProject is added.
"""
import importlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parent
FROZEN = {
    'cc_run_character_refresh_v1': '80c6c4c479dbdbb158a24dd830f76859b4e3d6727b13e7125c848ea2bfb02a72',
    'cc_refresh_closed_assembly_v1': 'f5ce68aa133d7e585a8da46a881bda8592d00d2c97b0c5257b59996ecc26e2bc',
    'cc_probe_refresh_skin_normal_restore_v1': 'e006a14092c55da20465c5c498aeacf1a47be33229a34637251397566e02b52d',
}
SKINS = frozenset(('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg'))


def private_module(name, api):
    path = DIRECTORY / (name + '.py')
    if api.sha256_file(str(path)) != FROZEN[name]:
        raise ValueError('Frozen assembly/Normal implementation changed: ' + name)
    spec = importlib.util.spec_from_file_location('_normal_closure_private_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def own_maps(c):
    """Bind the live same-run after_skin capture, source and selected skin."""
    from cc_skin_detail_experiment_v1 import MISSING_TEXTURE_SHA256
    config, api = c.report['config'], c.api
    for record in (config['source_project'], config['assets']['skin']):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Same-case source or selected skin changed')
    pin = c.report['pixel_stages']['after_skin']
    expected = Path(c.output_dir) / 'pixels_after_skin/materials.json'
    if Path(pin['path']).resolve() != expected.resolve() or api.sha256_file(pin['path']) != pin['sha256']:
        raise ValueError('Exact same-run after_skin evidence required')
    recorded = api.read_json(pin['path'])
    def rows(snapshot):
        found = [r for r in snapshot['materials'] if
                 (r['owner'], r['mesh']) == ('avatar', 'CC_Base_Body') and r['material'] in SKINS]
        if len(found) != 4 or {r['material'] for r in found} != SKINS:
            raise ValueError('Exactly four same-case skin materials required')
        return {r['material']: r for r in found}
    disk, live = rows(recorded), rows(c.pixel_snapshots['after_skin'])
    maps = {}
    for material in sorted(SKINS):
        record = disk[material]['textures'].get('bump')
        if not record or record != live[material]['textures'].get('bump'):
            raise ValueError('Live and pinned own after_skin maps differ')
        if record['sha256'] in MISSING_TEXTURE_SHA256 or api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Actual immutable own Normal map required, never warning')
        image = api.QtGui.QImage(record['path'])
        if image.isNull() or (image.width(), image.height()) != (2048, 2048) or (record['width'], record['height']) != (2048, 2048):
            raise ValueError('Real decoded own2048 map required')
        maps[material] = record
    return maps


def missing_materials(snapshot, maps, api, engine):
    rows = {(r['owner'], r['mesh'], r['material']): r for r in snapshot['materials']}
    missing = []
    for material in sorted(SKINS):
        row = rows[('avatar', 'CC_Base_Body', material)]
        if not any(row['textures'].get(channel) for channel in ('normal', 'bump')):
            missing.append(material)
        else:
            # Healthy maps are not rewritten; a different real map is not missing.
            engine.verify_restored_maps(snapshot, {material: maps[material]}, api)
    return missing


class NormalHook:
    def __init__(self, context):
        self.c = context
        self.engine = private_module('cc_probe_refresh_skin_normal_restore_v1', context.api)
        self.maps = None
        self.first_reload = None
        self.report = dict(policy='own_after_skin_four_maps_missing_only_Normal_write',
                           writes=[], captures={}, checks={}, complete=False,
                           implementation_sha256=context.api.sha256_file(__file__), frozen_implementations=FROZEN,
                           scope='Normal writes read back through actual Bump/Normal domains; direct getters recorded separately. Eight standard channels only.')
        context.report['skin_normal_closure'] = self.report

    def capture(self, label):
        import cc_refresh_material_pixels_v1 as pixels
        import cc_skin_detail_experiment_v1 as exporter
        from cc_probe_refresh_skin_material_readonly_v1 import CHANNELS
        c, api = self.c, self.c.api
        if int(c.avatar().GetSubdivMeshLevel()) != 0:
            raise ValueError('Normal closure requires actual0')
        widget = c.ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()), *c.ui.SELECTORS['editor'])
        if widget.isChecked() or str(widget.text()) != 'Activate Editor':
            raise ValueError('Normal closure requires actually closed editor')
        destination = os.path.join(c.output_dir, 'skin_normal_closure', 'pixels_' + label)
        if os.path.exists(destination):
            raise ValueError('Refuse reused Normal capture')
        scoped = pixels.ScopedApi(api)
        scoped.MATERIAL_TEXTURE_CHANNELS = list(CHANNELS)
        try:
            value = exporter.capture_materials(c.avatar(), destination, scoped)
        except Exception:
            path = os.path.join(destination, 'materials.json')
            if not os.path.isfile(path):
                raise
            value = api.read_json(path)
        bad = []
        for row in value['materials']:
            for channel, image_record in row['textures'].items():
                image = api.QtGui.QImage(image_record['path'])
                if image.isNull() or (image.width(), image.height()) != (image_record['width'], image_record['height']):
                    bad.append((row['material'], channel))
        errors = [e for e in value.get('observation_errors', []) if
                  str(e.get('stage', '')).startswith('texture:') or e.get('stage') in dict(CHANNELS)]
        skins = {r['material'] for r in value['materials'] if
                 r['owner'] == 'avatar' and r['mesh'] == 'CC_Base_Body' and r['material'] in SKINS and r['textures'].get('diffuse')}
        support = {r['mesh'] for r in value['materials']}
        value.update(pixel_capture_complete=not bad and not errors and skins == SKINS and pixels.SUPPORT_MESHES <= support,
                     decode_errors=bad, texture_errors=errors, channel_scope=list(CHANNELS))
        path = os.path.join(destination, 'materials.json')
        api.write_json(value, path)
        self.report['captures'][label] = api.bodyfit_freeze_file_record(path)
        c.checkpoint('skin_normal_' + label)
        if not value['pixel_capture_complete']:
            raise ValueError('Actual eight-channel Normal closure capture incomplete')
        return value

    def before_saved(self):
        c, api = self.c, self.c.api
        if self.maps is not None:
            raise ValueError('Normal restoration may run only once')
        self.maps = own_maps(c)
        self.report.update(character_id=c.report['config']['character_id'], source_project=c.report['config']['source_project'],
                           selected_skin=c.report['config']['assets']['skin'], after_skin=c.report['pixel_stages']['after_skin'], maps=self.maps)
        before = self.capture('before_writes')
        missing = missing_materials(before, self.maps, api, self.engine)
        self.report['missing_before'] = missing
        component = c.avatar().GetMaterialComponent()
        for material in missing:
            record = self.maps[material]
            raw = component.LoadImageToTexture('CC_Base_Body', material, api.RLPy.EMaterialTextureChannel_Normal, record['path'])
            self.report['writes'].append(dict(material=material, source=record, write_constant='EMaterialTextureChannel_Normal', status=c.probe.status_record(raw)))
            c.checkpoint('skin_normal_write_' + material)
            api.checked('Restore own skin Normal ' + material, raw)
        after = self.capture('after_writes')
        check = self.engine.pixel_compare(before, after, api, allow_four_normal_pairs=True)
        self.report['checks']['write_only_four_normal_pairs'] = check
        self.report['checks']['after_writes_real_maps'] = self.engine.verify_restored_maps(after, self.maps, api)
        c.checkpoint()
        if not check['passed']:
            raise ValueError('Normal writes changed protected material pixels')

    def gate(self, label):
        if self.maps is None:
            raise ValueError('Normal restoration must precede saved/reload checks')
        actual = self.capture(label)
        self.report['checks'][label + '_real_maps'] = self.engine.verify_restored_maps(actual, self.maps, self.c.api)
        if label == 'first_reload':
            # Retain existing first SkinGen serialization policy for other skin
            # channels; the real Normal maps themselves never receive allowance.
            self.first_reload = actual
        elif label == 'same_sha_reload':
            if self.first_reload is None:
                raise ValueError('First reload baseline required')
            check = self.engine.pixel_compare(self.first_reload, actual, self.c.api)
            self.report['checks']['eight_channels_same_sha_stable'] = check
            if not check['passed']:
                raise ValueError('Eight-channel same-SHA product pixels changed')
            self.report['complete'] = True
        self.c.checkpoint()


def finish(context):
    hook = NormalHook(context)
    original_stage = context.pixel_stage
    def pixel_stage(label):
        if label == 'saved':
            hook.before_saved()
        original_stage(label)
        if label == 'reloaded':
            hook.gate('first_reload')
    class Pixels:
        def __getattr__(self, name):
            return getattr(context.pixels, name)
        def capture_stage(self, avatar, output, label, api):
            value = context.pixels.capture_stage(avatar, output, label, api)
            # The frozen closure's only direct capture is its final same-SHA
            # rendered stability checkpoint; other captures use pixel_stage.
            if label != 'reloaded' or Path(output) != Path(context.output_dir) / 'same_sha_stability':
                raise ValueError('Unexpected direct frozen closure capture')
            hook.gate('same_sha_reload')
            return value
    c = SimpleNamespace(**vars(context))
    c.pixel_stage, c.pixels = pixel_stage, Pixels()
    target = private_module('cc_refresh_closed_assembly_v1', context.api).finish(c)
    if not hook.report['complete']:
        raise ValueError('Real four Normal maps and eight-channel stability not verified')
    return target


def run(library, output_dir, log, api):
    config = library['refresh_assembly']
    if (config.get('restore_four_skin_normals_after_editor_close') is not True or
            config.get('finalize_editor_closed') is not True or config.get('capture_pixel_evidence') is not True):
        raise ValueError('Explicit editor-closed Normal restoration opt-in required')
    runner = private_module('cc_run_character_refresh_v1', api)
    class Imports:
        def __getattr__(self, name):
            return getattr(importlib, name)
        def import_module(self, name):
            if name == 'cc_refresh_closed_assembly_v1':
                return SimpleNamespace(finish=finish, __file__=__file__)
            return importlib.import_module(name)
    runner.importlib = Imports()
    return runner.run(library, output_dir, log, api)
