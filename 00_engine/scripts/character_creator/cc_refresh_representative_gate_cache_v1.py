"""Process-local reuse of successful, unchanged representative evidence only.

The real frozen gate still executes on a miss. No character-stage cache,
global file API patches, persisted acceptance, application calls or writes.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
from types import FunctionType

RUN = Path(__file__).resolve().parents[2] / 'outputs/character_refresh_20261018_v1'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def identity(path):
    """Include lexical identity, resolved target, replacement and absence."""
    path = Path(path).absolute()
    resolved = path.resolve(strict=False)
    try:
        lexical = path.lstat()
        current = path.stat()
    except FileNotFoundError:
        return (str(resolved), 'missing')
    return (str(resolved), current.st_dev, current.st_ino, current.st_mode,
            current.st_size, current.st_mtime_ns, current.st_ctime_ns,
            lexical.st_dev, lexical.st_ino, lexical.st_mtime_ns)


def document_key(path):
    if path is None:
        return None
    path = Path(path).resolve()
    try:
        return (str(path), hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError as error:
        # Do not replace the original validator's missing/unreadable failure.
        # An unreadable key can never match a previously successful entry.
        return (str(path), 'unreadable', type(error).__name__)


class RepresentativeGateCache:
    def __init__(self, implementation_pins):
        self.implementation_key = tuple((str(Path(p['path']).resolve()), p['sha256'])
                                        for p in implementation_pins)
        self.entry = None
        self.observed = None
        self.owner = load(RUN / 'refresh_batch_prepare_v1.py', '_cache_private_rep_owner')
        transfer = load(RUN / 'ue_refresh_representative_import_v1.py', '_cache_private_rep_transfer')
        self.owner.transfer = transfer
        # Only these private copies change. Their original functions and the
        # running/current-character modules keep their original globals.
        for module in (self.owner, transfer):
            for name in ('read', 'pin', 'verified'):
                original = getattr(module, name)
                def observed(value, *args, _name=name, _original=original, **kwargs):
                    path = value.get('path') if _name == 'verified' and isinstance(value, dict) else value
                    if isinstance(path, (str, Path)):
                        self.observe(path)
                    return _original(value, *args, **kwargs)
                setattr(module, name, observed)
        original_status = transfer.status
        def status(request_path):
            folder = Path(request_path).resolve(strict=True).parent
            # status chooses by existence; even an absent worker must be part
            # of the closure if the controller file was selected originally.
            for name in ('worker_status.json', 'controller_status.json'):
                self.observe(folder / name)
            return original_status(request_path)
        transfer.status = status

    def observe(self, path):
        if self.observed is not None:
            key = str(Path(path).absolute())
            current = identity(key)
            prior = self.observed.setdefault(key, current)
            if current != prior:
                raise ValueError('Representative input changed during full validation: ' + key)

    @staticmethod
    def unchanged(files):
        try:
            return all(identity(path) == value for path, value in files.items())
        except OSError:
            return False

    def bind(self, serial, order_pin, order_implementation_pins=()):
        original = serial.representative_evidence
        private_globals = dict(original.__globals__)
        private_globals['batch'] = self.owner
        full_gate = FunctionType(original.__code__, private_globals, original.__name__,
                                 original.__defaults__, original.__closure__)
        full_gate.__kwdefaults__ = original.__kwdefaults__
        code_file = str(Path(original.__code__.co_filename).resolve())
        implementation_key = self.implementation_key + tuple(
            (str(Path(p['path']).resolve()), p['sha256']) for p in order_implementation_pins)

        def representative_evidence(plan_path, gate_path):
            key = (str(Path(order_pin['path']).resolve()), order_pin['sha256'],
                   document_key(plan_path), document_key(gate_path),
                   implementation_key, code_file)
            previous = self.entry
            if previous and previous['key'] == key and self.unchanged(previous['files']):
                result = copy.deepcopy(previous['result'])
                if self.unchanged(previous['files']):
                    return result
            # Every miss/change/different key discards the old success before
            # invoking the exact original function. Exceptions cannot be cached.
            self.entry = None
            self.observed = {}
            try:
                for path in (order_pin['path'], code_file,
                             *(p[0] for p in implementation_key)):
                    self.observe(path)
                result = full_gate(plan_path, gate_path)
                if result.get('passed') is not True:
                    return result
                if not self.unchanged(self.observed):
                    raise ValueError('Representative inputs changed across full validation')
                self.entry = {'key': key, 'files': dict(self.observed),
                              'result': copy.deepcopy(result)}
                return result
            finally:
                self.observed = None
        serial.representative_evidence = representative_evidence
        return serial
