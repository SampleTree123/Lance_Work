"""Opt-in, process-local filesystem relocation for the v11 render dependency graph.

No source JSON, script, source pin, /Game path, or shared imported module is edited.
Use RuntimePaths(...).load_renderer(), or patch_runtime(existing_renderer, ...).
Run this once during a fresh renderer bootstrap, before constructing its worker.
"""
from __future__ import annotations

import builtins
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import pathlib
import re
import sys
import types
import uuid


def _normalized(value):
    return re.sub(r"/+", "/", str(value).replace("\\", "/")).rstrip("/")


class RuntimePaths:
    """Bounded private module graph with explicit source-to-target root mappings.

    workspace_root is the migrated Lance_Work directory. project_file is the
    actual target .uproject, even if its directory/name differs on the server.
    extra_roots is an optional mapping for genuinely consumed external evidence.
    Unknown Windows roots fail when used as filesystem paths, rather than being
    mistaken for Linux relative filenames. Unused historical JSON strings stay.
    """

    def __init__(self, workspace_root, project_file, *, engine_root=None, extra_roots=None):
        self.workspace = Path(workspace_root).resolve()
        self.project_file = Path(project_file).resolve()
        if self.project_file.suffix.lower() != ".uproject":
            raise ValueError("project_file must name the target .uproject file")
        self.scripts = self.workspace / "00_engine/scripts/unreal"
        self.formal = self.workspace / "00_engine/outputs/production_workflow_20261017_v1"
        self.roots = {
            "D:/UE/Lance_Work": self.workspace,
            "D:/UE/projects/datatry_02/datatry_02.uproject": self.project_file,
            "D:/UE/projects/datatry_02": self.project_file.parent,
        }
        if engine_root is not None:
            self.roots["D:/UE/UE_5.8"] = Path(engine_root).resolve()
        self.roots.update({_normalized(k): Path(v).resolve() for k, v in (extra_roots or {}).items()})
        self._roots = sorted(self.roots.items(), key=lambda x: len(x[0]), reverse=True)
        self._destinations = [_normalized(self.workspace), _normalized(self.project_file.parent)]
        self._destinations += [_normalized(v) for k, v in self.roots.items() if k not in ("D:/UE/Lance_Work", "D:/UE/projects/datatry_02/datatry_02.uproject", "D:/UE/projects/datatry_02")]
        self._target_ancestors = {_normalized(p).lower() for v in self.roots.values() for p in (v, *v.parents)}
        self.modules = {}
        self.prefix = "_dataset_relocated_" + uuid.uuid4().hex + "_"
        self.loaded_files = set()
        self.pathlib = types.ModuleType("pathlib")
        self.pathlib.__dict__.update(vars(pathlib))
        owner = self
        native_path = type(Path())

        class RelocatedPath(native_path):
            def __new__(cls, *args, **kwargs):
                combined = Path(*args) if args else Path()
                return super().__new__(cls, owner.relocate_string(str(combined), strict=True), **kwargs)

            def __init__(self, *args, **kwargs):
                # Python 3.12 moved raw-path storage from __new__ to __init__.
                if native_path.__init__ is not object.__init__:
                    combined = Path(*args) if args else Path()
                    super().__init__(owner.relocate_string(str(combined), strict=True), **kwargs)

        self.pathlib.Path = RelocatedPath
        self.json = types.ModuleType("json")
        self.json.__dict__.update(vars(json))
        self.json.loads = lambda text, *a, **kw: self.relocate_document(json.loads(text, *a, **kw))
        self.json.load = lambda stream, *a, **kw: self.json.loads(stream.read(), *a, **kw)
        self.importlib = types.ModuleType("importlib")
        self.importlib.__dict__.update(vars(importlib))
        self.importlib.reload = self.reload
        self.util = types.ModuleType("importlib.util")
        self.util.__dict__.update(vars(importlib.util))
        self.util.spec_from_file_location = self.spec_from_file_location
        self.importlib.util = self.util

    def relocate_string(self, value, *, strict=False):
        raw = _normalized(value)
        # A target may itself be inside an old root (local migration fixtures).
        # Already relocated paths must not acquire a second target prefix.
        if any(raw.lower() == p.lower() or raw.lower().startswith(p.lower() + "/") for p in self._destinations):
            return str(Path(value))
        for source, destination in self._roots:
            if raw.lower() == source.lower() or raw.lower().startswith(source.lower() + "/"):
                tail = raw[len(source):].lstrip("/")
                if ".." in tail.split("/"):
                    raise ValueError("Relocation path escapes its declared source root: " + value)
                return str(destination / tail) if tail else str(destination)
        if strict and re.match(r"^[A-Za-z]:/", raw) and raw.lower() not in self._target_ancestors:
            raise ValueError("Unmapped historical filesystem path; provide extra_roots: " + value)
        return value

    def relocate_document(self, value):
        # In-memory normalization also preserves equality of file-pin dictionaries.
        # Hashes still verify original file bytes, never serialized normalized JSON.
        if isinstance(value, str):
            return self.relocate_string(value)
        if isinstance(value, dict):
            return {self.relocate_string(k) if isinstance(k, str) else k: self.relocate_document(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.relocate_document(v) for v in value]
        return value

    def path(self, value):
        return self.pathlib.Path(value)

    def importer(self, name, globals=None, locals=None, fromlist=(), level=0):
        if not level and name == "pathlib":
            return self.pathlib
        if not level and name == "json":
            return self.json
        if not level and name == "importlib":
            return self.importlib
        if not level and name == "importlib.util":
            return self.util if fromlist else self.importlib
        if not level and "." not in name and (self.scripts / (name + ".py")).is_file():
            return self.load(name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    def _allowed(self, path):
        path = Path(path).resolve()
        return path.parent == self.scripts or path.parent == self.formal

    def _execute(self, module, path):
        path = Path(path).resolve()
        if not self._allowed(path):
            raise ValueError("Private v11 loader only accepts scripts/unreal and the formal runtime directory")
        module.__dict__["__builtins__"] = dict(vars(builtins), __import__=self.importer)
        exec(compile(path.read_text(encoding="utf-8-sig"), str(path), "exec"), module.__dict__)
        self.loaded_files.add(str(path))
        self._after_load(module, path)

    def load(self, name):
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError("Expected a local module name")
        if name in self.modules:
            return self.modules[name]
        path = self.scripts / (name + ".py")
        module = types.ModuleType(self.prefix + name)
        module.__file__, module.__package__ = str(path), ""
        self.modules[name] = module
        sys.modules[module.__name__] = module
        try:
            self._execute(module, path)
        except Exception:
            self.modules.pop(name, None)
            sys.modules.pop(module.__name__, None)
            raise
        return module

    def reload(self, module):
        # Legacy scripts reload their contracts during import. Each is private.
        if module.__name__.startswith(self.prefix):
            return module
        raise ValueError("Refusing to reload a shared module: " + module.__name__)

    def spec_from_file_location(self, name, location=None, *args, **kwargs):
        location = self.path(location) if location is not None else None
        spec = importlib.util.spec_from_file_location(name, location, *args, **kwargs)
        if spec is None or location is None or not self._allowed(location):
            return spec
        original = spec.loader
        owner = self

        class Loader:
            def create_module(self, value):
                method = getattr(original, "create_module", None)
                return method(value) if method else None

            def exec_module(self, module):
                owner._execute(module, location)

            def __getattr__(self, key):
                return getattr(original, key)

        spec.loader = Loader()
        return spec

    def _after_load(self, module, path):
        if getattr(module, "_dataset_runtime_paths_owner", None) is self:
            return
        module._dataset_runtime_paths_owner = self
        self.loaded_files.add(str(path))
        if path.stem == "ue_dataset_reference_v11":
            # Canonical/static and motion branches dynamically load the shared
            # main renderer; keep their entry roots explicit for relocated runs.
            module.S = self.path(self.scripts)
            module.WORKSPACE = self.path(self.workspace)
        # Some old contracts derive project locations as workspace.parent/projects.
        # The server is allowed to keep project and workspace in unrelated roots.
        for key in ("CONTENT", "PROJECT_CONTENT"):
            if isinstance(getattr(module, key, None), Path):
                setattr(module, key, self.path(self.project_file.parent / "Content"))
        if isinstance(getattr(module, "PROJECT", None), Path):
            old = module.PROJECT
            module.PROJECT = self.path(self.project_file if old.suffix.lower() == ".uproject" else self.project_file.parent)
        if path.stem == "motion_library_review_adapter_v1":
            # Its nested PrivateModules graph installs its own importer. Extend
            # that one only, so it shares this relocation policy for stdlib I/O.
            original_class = module.PrivateModules
            owner = self

            class PortablePrivateModules(original_class):
                def importer(self, name, globals=None, locals=None, fromlist=(), level=0):
                    if not level and name in ("pathlib", "json"):
                        return getattr(owner, name)
                    return super().importer(name, globals, locals, fromlist, level)

                def load(self, name):
                    result = super().load(name)
                    owner._after_load(result, Path(result.__file__))
                    return result

            module.PrivateModules = PortablePrivateModules
        if path.stem == "pair_scene_review_20261019_v1":
            # Avoid accidentally reusing a worker created before relocation.
            module.CACHE += "_paths_" + hashlib.sha256(str(self.workspace).encode()).hexdigest()[:12]

    def load_renderer(self):
        return self.load("ue_dataset_render_v11")

    def load_reference_renderer(self):
        return self.load("ue_dataset_reference_v11")

    def report(self):
        return {"schema": "dataset_runtime_paths_v11_v1", "workspace_root": str(self.workspace),
                "project_file": str(self.project_file), "root_mapping": {k: str(v) for k, v in self.roots.items()},
                "loaded_files": sorted(self.loaded_files), "source_documents_modified": False,
                "shared_imported_modules_modified": False, "linux_ue_verified": False}


def patch_runtime(renderer_module, *, workspace_root, project_file, engine_root=None, extra_roots=None,
                  worker_module="ue_dataset_render_v11"):
    """Delegate an already-loaded entrypoint to a new isolated runtime graph.

    Call before its first worker. The caller must keep the returned adapter alive
    and reuse it for the queue. This function does not touch UE or call dispatch.
    """
    adapter = RuntimePaths(workspace_root, project_file, engine_root=engine_root, extra_roots=extra_roots)
    if worker_module not in {"ue_dataset_render_v11", "ue_dataset_reference_v11"}:
        raise ValueError("Expected the main or reference production renderer")
    private = adapter.load(worker_module)
    for name in ("dispatch", "prepare", "renderer", "module", "selection", "signature", "static_prepare", "motion_prepare", "source", "shared_main"):
        if hasattr(private, name):
            setattr(renderer_module, name, getattr(private, name))
    renderer_module._dataset_runtime_paths_v11 = adapter
    return adapter
