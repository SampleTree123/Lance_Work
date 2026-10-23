"""Private adapters for the unchanged CFD40 controller and UE worker.

Constructing an adapter does not dispatch commands or change a UE scene.
Explicit launchers pass immutable motion/face file records to both endpoints.
Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
"""
from __future__ import annotations
import builtins
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types
import uuid

import motion_library_extension_contract_v1 as extension
import motion_library_panorama_v1 as panorama

SCRIPTS = Path(__file__).resolve().parent
PIN = 'motion_catalog_sha256'
CONFIG_SCHEMA = 'cfd40_motion_extension_configuration_v1'
_VALIDATED = {}  # One immutable pair per process; never persisted as acceptance.


def dependency_snapshot(values):
    """Snapshot only records actually checked, not stale historical JSON fields."""
    records, pending = {}, list(values)
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(v for v in value if isinstance(v, (dict, list)))
            continue
        if not isinstance(value, dict):
            continue
        pending.extend(v for v in value.values() if isinstance(v, (dict, list)))
        if not isinstance(value.get('path'), str) or not isinstance(value.get('sha256'), str):
            continue
        path = Path(value['path'])
        if not path.is_absolute():
            raise ValueError('Dependency record is not absolute')
        path = path.resolve(strict=True)
        if str(path) in records:
            if records[str(path)]['sha256'] != value['sha256']:
                raise ValueError('Conflicting dependency hashes')
            continue
        before = file_stamp(path)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != value['sha256'] or before != file_stamp(path):
            raise ValueError('Dependency changed during cache preparation: ' + str(path))
        records[str(path)] = {'sha256': value['sha256'], 'stamp': before}
    return records


def file_stamp(path):
    path = Path(path)
    stat = path.stat()
    return (str(path.resolve(strict=True)), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def unchanged(records):
    try:
        return all(file_stamp(path) == record['stamp'] for path, record in records.items())
    except OSError:
        return False


class PrivateModules:
    """Execute local dependencies in a private graph, never reload global UE modules.

The legacy modules deliberately reload one another during import. Each private
module is fresh already; their reload calls therefore return the same private
instance. Shared importlib/sys.modules entries are not monkeypatched.
"""
    def __init__(self):
        self.modules = {}
        self.prefix = '_motion_review_' + uuid.uuid4().hex + '_'
        self.importlib = types.ModuleType('importlib')
        self.importlib.__dict__.update(importlib.__dict__)
        self.importlib.reload = self.reload

    def reload(self, module):
        if module in self.modules.values():
            return module
        raise ValueError('Private adapter refuses to reload a shared module: ' + module.__name__)

    def importer(self, name, globals=None, locals=None, fromlist=(), level=0):
        if not level and name == 'importlib':
            return self.importlib
        if not level and name == 'importlib.util':
            return importlib.util if fromlist else self.importlib
        if not level and '.' not in name and (SCRIPTS / (name + '.py')).is_file():
            return self.load(name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    def load(self, name):
        if name in self.modules:
            return self.modules[name]
        path = SCRIPTS / (name + '.py')
        module = types.ModuleType(self.prefix + name)
        module.__file__, module.__package__ = str(path), ''
        module.__dict__['__builtins__'] = dict(vars(builtins), __import__=self.importer)
        self.modules[name] = module
        # Dataclass/typing introspection may look up the private qualified name.
        sys.modules[module.__name__] = module
        try:
            exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), module.__dict__)
            if name == 'cfd_native_batch40_contract_v1':
                module.module = self.load
        except Exception:
            self.modules.pop(name, None)
            sys.modules.pop(module.__name__, None)
            raise
        return module


class BoundCatalog:
    def __init__(self, motion_record, face_record, base_loader):
        self.motion_record, self.face_record = copy.deepcopy(motion_record), copy.deepcopy(face_record)
        self.base_loader = base_loader
        self._snapshot = None

    def load(self):
        key = json.dumps([self.motion_record, self.face_record], sort_keys=True)
        cached = _VALIDATED.get(key)
        if cached and unchanged(cached['dependencies']):
            self._snapshot = copy.deepcopy(cached['result'])
            return self._snapshot
        _VALIDATED.clear()
        with extension.trace_dependencies() as checked_records:
            extension.checked(self.motion_record, json_file=True)
            extension.checked(self.face_record, json_file=True)
            data = extension.motion_catalog(self.motion_record['path'], self.base_loader())
            if data['sources']['motion_extension'] != self.motion_record:
                raise ValueError('Motion catalog changed while reading')
            library = extension.face_catalog(self.face_record['path'], data)
            if library['registry_source'] != self.face_record:
                raise ValueError('Face overlay changed while reading')
        self._snapshot = (data, library)
        dependencies = dependency_snapshot([self.motion_record, self.face_record, data['sources'], checked_records,
            extension.source(__file__), extension.source(extension.__file__), extension.source(extension.pilot.__file__),
            extension.source(panorama.__file__)])
        _VALIDATED[key] = {'result': copy.deepcopy(self._snapshot), 'dependencies': dependencies}
        return data, library

    def library(self):
        # Main load()/validate_request() revalidates before each transaction.
        # Nested identity/appearance helpers reuse that transaction's snapshot.
        if self._snapshot is None:
            self.load()
        extension.checked(self.motion_record, json_file=True)
        extension.checked(self.face_record, json_file=True)
        return self._snapshot[1]


def require_pin(request, data):
    if request.get('action') != 'restore':
        extension.check_index(request.get('action_index'), data)
        if request.get(PIN) != data['sources']['motion_extension']['sha256']:
            raise ValueError('Motion catalog changed; reopen the extension panel')


def migrate_request(request, data, *, from_base=False):
    result = copy.deepcopy(request)
    if result.get('action') == 'restore':
        return {'action': 'restore'}
    if from_base:
        if type(result.get('action_index')) is not int or not 0 <= result['action_index'] <= 5 or PIN in result:
            raise ValueError('Only unchanged historical 0..5 indices can migrate')
        old_sha = result.get('face_registry_sha256')
        has_face = any(r['face_id'] != 'none' for r in result['appearance'].values())
        if has_face and old_sha != extension.BASE_REGISTRY_SHA:
            raise ValueError('Only the exact accepted N3 face registry can migrate')
        result[PIN] = data['sources']['motion_extension']['sha256']
        result['face_registry_sha256'] = data['face_library']['registry_source']['sha256'] if has_face else None
    require_pin(result, data)
    return result


def install_configurations(app):
    config = app.configurations
    old_build = config.build_configuration
    def build(result, data, validate):
        document = old_build(result, data, validate)
        document['schema'] = CONFIG_SCHEMA
        return document
    def load(path, data, validate):
        document = app.identities.read(path)
        content = document.get('content', {})
        if config.digest(content) != document.get('content_sha256'):
            raise ValueError('Configuration content hash mismatch')
        if content.get('level') != app.identities.LEVEL or content.get('palette') != data['appearance']:
            raise ValueError('Configuration level/palette differs')
        old = document.get('schema') == config.SCHEMA
        if not old and document.get('schema') != CONFIG_SCHEMA:
            raise ValueError('Unknown configuration schema')
        sources = copy.deepcopy(content.get('sources'))
        if old:
            expected = copy.deepcopy(data['sources'])
            expected.pop('motion_extension')
            expected['native_face_library'] = extension.source(extension.faces.PANEL_REGISTRY)
            if sources != expected:
                raise ValueError('Old configuration identity/wardrobe/palette/source locks changed')
        elif sources != data['sources']:
            raise ValueError('Extension configuration sources changed')
        request = migrate_request(config.portable_request(content['request']), data, from_base=old)
        return validate(request, data)
    config.build_configuration, config.load_configuration = build, load


def controller(motion_record, face_record):
    graph = PrivateModules()
    app = graph.load('run_cfd_native_batch40_modular_review_v1')
    panel, identities = app.panel, app.identities
    identities.CONFIG_ROOT = extension.RUN / 'panel/configurations'
    binding = BoundCatalog(motion_record, face_record, panel.contract.catalog)
    old_load, old_initial, old_validate, old_verify = app.load_catalog, app.initial_request, app.validate_request, app.verify_result
    original_boundary = app._validate
    def base_boundary(request, data):
        index = extension.check_index(request['action_index'], data)
        # Delegate all historical clothing, camera and boolean checks; only its
        # fixed upper bound is obsolete. The true index is returned unchanged.
        original_boundary(panorama.legacy_request(dict(request, action_index=min(index, 5))), data)
        return copy.deepcopy(request)
    app._validate = base_boundary
    # The paired base catalog was already checked by BoundCatalog. Reusing its
    # snapshot here avoids the old controller independently rehashing old clips.
    app._load = lambda: copy.deepcopy((binding._snapshot or binding.load())[0])
    def load():
        motion_data, library = binding.load()
        data = old_load()
        data['actions_by_sex'] = motion_data['actions_by_sex']
        data['sources']['motion_extension'] = motion_record
        data['face_library'] = library
        data['sources']['native_face_library'] = library['registry_source']
        return data
    identities.face_catalog = binding.library
    def migrate(appearance, old_sha, library):
        if old_sha == extension.BASE_REGISTRY_SHA:
            if any(r['face_id'] not in ('none',) + extension.faces.FACE_IDS for r in appearance.values()):
                raise ValueError('Unknown accepted face ID')
            return copy.deepcopy(appearance), [{'migration': 'unchanged_N3_faces_to_motion_overlay'}]
        if old_sha != library['registry_source']['sha256']:
            raise ValueError('Unknown face registry; explicit reselection required')
        return copy.deepcopy(appearance), []
    identities.face_library.migrate_legacy_appearance = migrate
    def initial(data, saved=None):
        result = old_initial(data, saved)
        result[PIN] = data['sources']['motion_extension']['sha256']
        return result
    def validate(request, data=None):
        if request.get('action') == 'restore':
            return {'action': 'restore'}
        data = load() if data is None else data
        require_pin(request, data)
        stripped = {k: v for k, v in request.items() if k != PIN}
        return dict(old_validate(stripped, data), **{PIN: request[PIN]})
    def verify(result, request):
        value = old_verify(result, request)
        if request.get('action') != 'restore' and result.get('sources', {}).get('motion_extension') != motion_record:
            raise ValueError('UE did not bind this exact motion catalog')
        if request.get('action') != 'restore' and (result.get('motion_review_view', {}).get('success') is not True
                or result['motion_review_view'].get('framing') != request['framing']):
            raise ValueError('UE did not verify the requested regular/panorama framing and auxiliary light')
        return value
    app.load_catalog = panel.load_catalog = load
    app.initial_request = panel.initial_request = initial
    app.validate_request = panel.validate_request = validate
    app.verify_result = panel.verify_result = verify
    panel.STATE_KEYS += (PIN,)
    panel.WORKER = SCRIPTS / 'ue_cfd40_motion_extension_review_v1.py'
    def payload(request):
        return (f'import sys,runpy\nsys.path.insert(0,{str(SCRIPTS)!r})\n'
            f'runpy.run_path({str(panel.WORKER)!r},run_name="__main__",init_globals='
            f'{{"DM_SLOT_REVIEW_REQUEST":{request!r},"DM_MOTION_CATALOG":{motion_record!r},"DM_MOTION_FACE_REGISTRY":{face_record!r}}})')
    panel.command_payload = payload
    # Observation uses the same strict receipt validation but a new evidence root.
    identities.face_library.PANEL_RUN = extension.RUN / 'panel'
    old_observation = app.record_observation
    def observation(*args, **kwargs):
        data = copy.deepcopy(kwargs['data'])
        data['face_library']['schema'] = identities.face_library.SCHEMA_V2
        kwargs['data'] = data
        return old_observation(*args, **kwargs)
    app.record_observation = panel.record_observation = observation
    install_configurations(app)
    parser = app.build_parser
    app.build_parser = panel.build_parser = lambda: panorama.extend_parser(parser())
    panorama.install_button(app)
    # Stage creates/saves blueprints and is outside this extension's remit.
    app.stage = lambda *a, **k: (_ for _ in ()).throw(ValueError('Use the existing staged CFD40 level; extension cannot stage'))
    app._private_graph = graph
    return app


def worker(motion_record, face_record):
    graph = PrivateModules()
    app = graph.load('ue_cfd_native_batch40_modular_review_v1')
    review, legacy, identities = app.review, app.legacy, app.identities
    binding = BoundCatalog(motion_record, face_record, review.contract.catalog)
    review.contract.catalog = lambda: binding.load()[0]
    # BoundCatalog retained the original callable, so this is not recursive.
    identities.face_catalog = binding.library
    original_current = app.current_request
    original_inner = app._current
    def inner(incoming):
        data = review.contract.catalog()
        previous_path = app.ROOT / 'current_case.json'
        previous = identities.read(previous_path).get('request', {}) if previous_path.is_file() else {}
        index = incoming.get('action_index', previous.get('action_index', 0))
        extension.check_index(index, data)
        framing = incoming.get('framing', previous.get('framing', 'full'))
        result = original_inner(panorama.legacy_request(dict(incoming, action_index=min(index, 5), framing=framing)))
        result['action_index'] = index
        result['framing'] = framing
        return result
    app._current = inner
    def current(incoming):
        if incoming.get('action') == 'restore':
            return {'action': 'restore'}
        request = original_current(incoming)
        require_pin(request, review.contract.catalog())
        return request
    app.current_request = review.current_request = current
    original_action = legacy.action_asset
    def action_asset(entry, row):
        variant = row.get('extension_variant')
        if variant is None:
            return original_action(entry, row)
        extension.checked(variant['body_only'])
        u = app.unreal
        animation = u.load_asset(row['path'])
        if (not isinstance(animation, u.AnimSequence)
                or app.fixed.object_path(animation.get_editor_property('skeleton')) != row['source_skeleton']
                or app.fixed.object_path(entry['body_mesh'].get_editor_property('skeleton')) != row['source_skeleton']
                or abs(float(animation.get_play_length()) - row['duration_seconds']) > 1e-6):
            raise ValueError('BodyOnly asset/identity has the wrong shared Skeleton or duration')
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if row['path'].split('.')[0] in dirty or row['source_skeleton'].split('.')[0] in dirty:
            raise ValueError('Motion/shared Skeleton is dirty; refusing stale package proof')
        return animation
    legacy.action_asset = action_asset
    old_plan = app.load_plan
    def plan(request, data):
        result, prepared = old_plan(request, data)
        result['sources']['motion_extension'] = copy.deepcopy(motion_record)
        result['plan_sha256'] = app.fixed.digest({k: v for k, v in result.items() if k != 'plan_sha256'})
        return result, prepared
    app.load_plan = review.load_plan = plan
    app._panorama_view = panorama.install_worker(app)
    app._private_graph = graph
    return app
