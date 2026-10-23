"""Build a stat-only render transfer plan. Never copies, uploads or hashes assets.

Inspect only the project tree and a static closure of current render code and
its referenced workspace metadata. Outputs are a file ledger plus open issues;
this is deliberately not a claim of Linux runtime validation.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

WORKSPACE = Path(__file__).resolve().parents[3]
METADATA = {".json", ".py", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".csv", ".tsv", ".md", ".txt"}
SKIP_DIRS = {"deriveddatacache", "intermediate", "saved", "windowsbinaries", "__pycache__", ".git", ".vs", ".vscode", "node_modules"}
MEDIA_DIRS = {"frames", "renders", "screenshots", "thumbnails", "videos", "previews", "remote", "logs", "renders_raw"}
SEEDS = ("ue_dataset_render_v11", "ue_dataset_reference_v11", "run_dataset_render_v11", "scene_site_review_panel_v1",
         "encode_render_v11", "render_plan_v11", "reference_plan_v11")
JOB_MANIFESTS = ("pilot_jobs.json", "main_jobs.json", "carrier_jobs.json", "reference_jobs.json",
                 "static_reference_jobs.json", "motion_reference_jobs.json", "static_pilot_jobs.json", "motion_pilot_jobs.json")
MACHINE_LOCAL_PROFILE = "00_engine/outputs/local_render_profile_v1/profile.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def beneath(path, root):
    try:
        # Roots are resolved once; walkers exclude links. Avoid a filesystem
        # resolve/stat of every ancestor for every multi-GB Content file.
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def files_under(path, metadata=False, errors=None):
    if path.is_file():
        yield path
        return
    if not path.is_dir():
        return
    for root, dirs, names in os.walk(path, followlinks=False,
                                    onerror=lambda exc: errors.append(str(exc)) if errors is not None else None):
        current = Path(root)
        dirs[:] = [name for name in dirs if name.lower() not in SKIP_DIRS
                   and not (current.name.lower() == "binaries" and name.lower() in {"win64", "win32", "windows"})
                   and not (metadata and name.lower() in MEDIA_DIRS)
                   and not (current / name).is_symlink()]
        for name in names:
            source = current / name
            if source.is_symlink() or name.lower() in {"session.json", "remote.lock", "driver.lock"}:
                continue
            if metadata and (source.suffix.lower() not in METADATA or name.startswith("TRANSFER_PLAN")):
                continue
            yield source


def static_value(node, env, module_env):
    """Small expression interpreter: paths/constants only, never exec/import."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.BinOp):
        left, right = static_value(node.left, env, module_env), static_value(node.right, env, module_env)
        if isinstance(node.op, ast.Div):
            return Path(left) / right
        if isinstance(node.op, ast.Add):
            return left + right
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(static_value(item, env, module_env) for item in node.elts)
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id in env and isinstance(env[node.value.id], dict):
            return env[node.value.id][node.attr]
        value = static_value(node.value, env, module_env)
        if node.attr in {"parent", "parents", "name", "stem"}:
            return getattr(value, node.attr)
    if isinstance(node, ast.Subscript):
        return static_value(node.value, env, module_env)[static_value(node.slice, env, module_env)]
    if isinstance(node, ast.Call):
        args = [static_value(arg, env, module_env) for arg in node.args]
        if isinstance(node.func, ast.Name) and node.func.id == "Path":
            return Path(*args)
        if isinstance(node.func, ast.Attribute):
            owner = static_value(node.func.value, env, module_env)
            if isinstance(owner, Path) and node.func.attr in {"resolve", "with_name", "with_suffix"}:
                return getattr(owner, node.func.attr)(*args)
    raise ValueError("Dynamic expression")


def code_closure(workspace):
    folders = [workspace / "00_engine/scripts/unreal", workspace / "00_engine/scripts/dataset"]
    index = {p.stem: p for folder in folders for p in folder.glob("*.py")}
    pending = [index[name] for name in SEEDS if name in index]
    sources, trees, strings = {}, {}, {}
    while pending:
        path = pending.pop()
        if path in sources:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue
        sources[path], trees[path] = text, tree
        values = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        strings[path] = values
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        for value in values:
            if value in index:
                names.add(value)
            names.update(Path(match).stem for match in re.findall(r"[A-Za-z_][A-Za-z_0-9]*\.py\b", value))
        pending.extend(index[name] for name in names if name in index)
    # Resolve module aliases and imported constants across several bounded passes.
    environments = {path.stem: {"__file__": str(path)} for path in sources}
    for _ in range(6):
        for path, tree in trees.items():
            env = environments[path.stem]
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in environments:
                            env[alias.asname or alias.name] = environments[alias.name]
                elif isinstance(node, ast.ImportFrom) and node.module in environments:
                    for alias in node.names:
                        if alias.name in environments[node.module]:
                            env[alias.asname or alias.name] = environments[node.module][alias.name]
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    try:
                        value = static_value(node.value, env, environments)
                    except (ValueError, TypeError, KeyError, AttributeError, IndexError, OSError):
                        continue
                    for target in targets:
                        if isinstance(target, ast.Name):
                            env[target.id] = value
                        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, tuple):
                            for name, item in zip(target.elts, value):
                                if isinstance(name, ast.Name):
                                    env[name.id] = item
    candidates = set()
    for path, values in strings.items():
        for value in values:
            # Direct joined paths remain useful when a parent alias is dynamic.
            for match in re.findall(r"(?:00_engine/)?(?:outputs|assets)/[A-Za-z0-9_./-]+", value.replace("\\", "/")):
                candidates.add(workspace / (match if match.startswith("00_engine/") else "00_engine/" + match))
            if value.endswith((".json", ".py")):
                local = path.parent / value
                if local.is_file():
                    candidates.add(local)
    for env in environments.values():
        candidates.update(value for value in env.values() if isinstance(value, Path))
    return sources, candidates


def build(args):
    workspace, project, engine, run = args.workspace.resolve(), args.project_root.resolve(), args.engine_root.resolve(), args.run_root.resolve()
    descriptors = sorted(project.glob("*.uproject"))
    if len(descriptors) != 1:
        raise ValueError("Expected exactly one .uproject")
    uproject = read(descriptors[0])
    errors, ledger, categories, metadata_roots, omitted = [], {}, Counter(), set(), {}

    def add(path, category, root, prefix):
        path = path.absolute()
        if not beneath(path, root):
            errors.append("Outside selected root: " + str(path))
            return
        relative = path.relative_to(root).as_posix()
        if prefix == "workspace" and relative == MACHINE_LOCAL_PROFILE:
            omitted[str(path)] = {"source": str(path), "destination": "workspace/" + relative,
                                  "reason": "machine_name-bound Windows texture-pool profile; omit from transfer, preserve original bytes"}
            return
        try:
            stat = path.stat()
        except OSError as exc:
            errors.append(str(exc))
            return
        destination = prefix + "/" + path.relative_to(root).as_posix()
        ledger[str(path)] = {"source": str(path), "destination": destination, "bytes": stat.st_size,
                             "mtime_ns": stat.st_mtime_ns, "category": category}

    for folder in ("Content", "Config", "Source", "Plugins"):
        for path in files_under(project / folder, errors=errors):
            add(path, "project_" + folder.lower(), project, "project")
    add(descriptors[0], "project_descriptor", project, "project")
    print(json.dumps({"phase": "project_stat", "files": len(ledger)}), file=sys.stderr, flush=True)
    sources, candidates = code_closure(workspace)
    # The selected reference run also owns bindings, motion carriers, validation
    # and operation metadata that are not named by Python import statements.
    # files_under(..., metadata=True) continues to exclude all PNG/MP4/raw media.
    candidates.add(run)
    print(json.dumps({"phase": "code_closure", "modules": len(sources), "path_candidates": len(candidates)}), file=sys.stderr, flush=True)
    # Carry code directories in full to cover dynamically selected private modules;
    # inspect dependencies only in the current worker's static closure.
    for folder in ("unreal", "dataset"):
        for path in files_under(workspace / "00_engine/scripts" / folder, metadata=True, errors=errors):
            add(path, "workspace_code", workspace, "workspace")
    for name in JOB_MANIFESTS:
        path = run / name
        if path.is_file():
            candidates.add(path)
            for job in read(path).get("jobs", []):
                plan = job.get("camera_binding", {}).get("plan_path")
                if plan:
                    plan = Path(plan)
                    candidates.add(plan if plan.is_absolute() else workspace / plan)
    # Runtime trees are selected only where code references outputs/assets.
    for path in candidates:
        path = path.resolve()
        if not beneath(path, workspace) or path == workspace:
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative.startswith(("00_engine/outputs/", "00_engine/assets/")):
            if path.exists():
                metadata_roots.add(path)
    # Do not promote one registry JSON to its entire historical parent tree.
    # Referenced files stay exact; explicit runtime directories retain metadata.
    broad = {workspace / "00_engine/outputs/unreal_character_import", workspace / "00_engine/assets/character_creator"}
    roots = {p for p in metadata_roots if p not in broad}
    roots = {p for p in roots if not any(p != parent and beneath(p, parent) for parent in roots)}
    for root in sorted(roots):
        for path in files_under(root, metadata=True, errors=errors):
            add(path, "workspace_runtime_authority_evidence", workspace, "workspace")
    print(json.dumps({"phase": "metadata_stat", "roots": len(roots), "files": len(ledger)}), file=sys.stderr, flush=True)
    # Follow concrete metadata paths embedded inside selected authority JSONs.
    # Binary imports, FBX, media and model weights remain excluded.
    windows_references, external_metadata, followed = [], set(), set()
    # Inspect only directly referenced authority files and paths they name;
    # do not parse tens of thousands of historical evidence JSONs.
    follow_allowed = {str(p.absolute()) for p in candidates if p.is_file()}
    inspected_values = set()
    probe_limit = getattr(args, "metadata_probe_limit", 400)
    for pass_index in range(3):
        new = []
        for source in sorted(follow_allowed):
            if len(followed) >= probe_limit:
                break
            row = ledger.get(source)
            if row is None:
                continue
            path = Path(row["source"])
            if str(path) not in follow_allowed or path in followed or path.suffix.lower() != ".json" or row["bytes"] > 4 * 1024 * 1024:
                continue
            followed.add(path)
            try:
                payload = read(path)
            except (ValueError, OSError):
                continue
            stack = [payload]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
                elif isinstance(value, str) and len(value) < 1500:
                    if re.match(r"^[A-Za-z]:[/\\]", value):
                        windows_references.append({"file": row["destination"], "value": value})
                    if value in inspected_values:
                        continue
                    inspected_values.add(value)
                    candidate = Path(value)
                    if candidate.suffix.lower() not in METADATA:
                        continue
                    if not candidate.is_absolute():
                        candidate = workspace / candidate
                    if candidate.is_file() and beneath(candidate, workspace) and str(candidate.resolve()) not in ledger:
                        new.append(candidate)
                    elif candidate.is_absolute() and not beneath(candidate, workspace) and candidate.suffix.lower() in {".json", ".py"}:
                        external_metadata.add(str(candidate))
        if not new:
            break
        for path in set(new):
            add(path, "workspace_referenced_metadata", workspace, "workspace")
            follow_allowed.add(str(path.absolute()))
        print(json.dumps({"phase": "authority_paths", "pass": pass_index, "inspected": len(followed), "new": len(new)}), file=sys.stderr, flush=True)
    print(json.dumps({"phase": "authority_paths_done", "inspected": len(followed), "limit": probe_limit}), file=sys.stderr, flush=True)
    latest = args.log or next(iter(sorted((project / "Saved/Logs").glob("*.log"), key=lambda p: p.stat().st_mtime_ns, reverse=True)), None)
    log_evidence, mounted = [], {"Engine": [], "Project": []}
    if latest:
        for line in Path(latest).read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if re.search(r"LogInit: (?:Build:|Engine Version:|Compatible Engine Version:|Command Line:)", line):
                log_evidence.append(line)
            match = re.search(r"Mounting (Engine|Project) plugin (\S+)", line)
            if match:
                mounted[match.group(1)].append(match.group(2))
    plugins = []
    for descriptor in (project / "Plugins").rglob("*.uplugin"):
        data = read(descriptor)
        plugins.append({"name": descriptor.stem, "descriptor": str(descriptor), "version": data.get("VersionName"),
                        "engine_version": data.get("EngineVersion"), "has_source": (descriptor.parent / "Source").is_dir(),
                        "modules": data.get("Modules", []), "linux_status": "not_validated; Win64 binaries excluded; rebuild source or resolve platform allowlist before loading"})
    ledger_rows = sorted(ledger.values(), key=lambda row: row["destination"])
    for row in ledger_rows:
        categories[row["category"]] += row["bytes"]
    issues = [
        {"id": "linux_runtime_unverified", "detail": "Server UE 5.8.1 is user-supplied. Linux RHI/GPU, plugins, fonts, shaders, ffmpeg and decoded sample comparison require server verification."},
        {"id": "authority_absolute_paths", "detail": "Use driver --portable-runtime for isolated mapping of formal runtime JSON/Python paths and pin dictionaries; signed source bytes remain unchanged. This adapter has offline/local evidence, but target Linux branches still require verification. Request prefix mapping alone is insufficient."},
        {"id": "rlplugin_linux", "detail": "Project RLPlugin has Win64-only module allowlist. Retained source does not prove Linux support. Determine whether existing imported assets render without loading this editor importer; otherwise port/rebuild lawfully available source."},
        {"id": "engine_plugins", "detail": "Enabled and log-mounted engine plugins must exist in the user's matching Linux UE build. Engine binaries are not uploaded by this plan; platform-restricted plugins may require an adjusted server project copy."},
        {"id": "static_not_asset_closure", "detail": "All project Content is included conservatively. Worker metadata uses static code/path analysis plus bounded JSON references, not an AssetRegistry or full runtime dependency proof. No whole workspace audit performed."},
        {"id": "snapshot_changes", "detail": "Sizes and mtime were sampled while the local editor may be active; regenerate after rendering before transfer. No multi-GB asset hashes computed."},
        {"id": "ffmpeg_python", "detail": "Server needs Python 3 and ffmpeg with libx264 or imageio-ffmpeg. No Windows Python environment or engine runtime copied."},
        {"id": "machine_texture_profile", "detail": "The local_render_profile_v1/profile.json machine_name-bound record is omitted, never rewritten. Use --pool-mb with a budget chosen for the server GPU; current session/review budget can inherit without the Windows profile."},
    ]
    manifest = {"schema": "dataset_render_transfer_manifest_v11_v1", "generated_at": datetime.now(timezone.utc).isoformat(),
                "operation": "read_only_inventory_no_copy_upload_delete", "hashing": "none; stat size and mtime only",
                "roots": {"project": str(project), "workspace": str(workspace), "engine": str(engine), "run": str(run)},
                "destination_layout": {"project": "target project root", "workspace": "target Lance_Work root; retain relative layout"},
                "project_engine_association": uproject.get("EngineAssociation"), "log": str(latest) if latest else None,
                "log_evidence": log_evidence, "mounted_plugins": mounted, "enabled_project_plugins": [p for p in uproject.get("Plugins", []) if p.get("Enabled")],
                "project_plugin_details": plugins, "inspected_code_closure": sorted(str(p.relative_to(workspace)) for p in sources),
                "metadata_roots": sorted(str(p.relative_to(workspace)) for p in roots),
                "exclude_rules": sorted(SKIP_DIRS | MEDIA_DIRS) + ["Binaries/Win64", "Binaries/Win32", MACHINE_LOCAL_PROFILE, "workspace historical media by metadata extension allowlist"],
                "omitted_files": sorted(omitted.values(), key=lambda row: row["destination"]),
                "total_files": len(ledger_rows), "total_bytes": sum(row["bytes"] for row in ledger_rows), "category_bytes": dict(categories),
                "windows_path_reference_count": len(windows_references), "windows_path_examples": windows_references[:40],
                "metadata_probe": {"inspected_json_files": len(followed), "limit": probe_limit,
                                   "unprobed_candidate_files": len(follow_allowed - {str(p) for p in followed}),
                                   "scope": "bounded authority portability sample, not all metadata audited"},
                "external_metadata_paths": sorted(external_metadata)[:100], "issues": issues, "stat_errors": errors, "files": ledger_rows}
    return manifest


def markdown(manifest):
    lines = ["# v11 服务器上传清单", "", "本文件由只读目录统计生成，没有复制、上传、删除或大文件哈希操作。", "",
             f"合计 **{manifest['total_files']:,} 个文件，{manifest['total_bytes'] / 1024**3:.2f} GiB**。逐文件可执行清单见 `TRANSFER_PLAN.json` 的 `files`：每项含源路径、目标相对路径、大小和修改时间。", "",
             "目标路径以 `project/`、`workspace/` 两个逻辑根表示，上传工具将其分别映射到服务器工程目录和 Lance_Work 目录。保留相对布局；仅传 scripts 不足以运行正式角色/服装目录。", "", "## 纳入范围", ""]
    for category, size in manifest["category_bytes"].items():
        lines.append(f"- `{category}`：{size / 1024**3:.3f} GiB")
    lines += ["", "包含完整 Content、Config、uproject，存在时包含 Source 和插件描述/Source/资源；工作区包含 unreal、dataset 代码以及当前依赖指向的 runtime、authority、evidence 元数据。历史 PNG/视频/FBX 和缓存不作为工作区上传项。", "", "## 已启动编辑器证据", ""]
    lines += ["- `" + value + "`" for value in manifest["log_evidence"]]
    lines += ["", "## 插件", ""]
    for plugin in manifest["project_plugin_details"]:
        lines.append(f"- {plugin['name']} {plugin['version']}，标记引擎 {plugin['engine_version']}；Source存在：{plugin['has_source']}。模块平台限制：`{json.dumps(plugin['modules'], ensure_ascii=False)}`。Linux未验证。")
    lines += ["", "## 未确定项与服务器进入条件", ""]
    translations = {
        "linux_runtime_unverified": "服务器使用用户同步的 UE 5.8.1；尚需核实 Linux GPU/RHI、插件、字体、着色器及一个完整10秒样本的解码和画面一致性。",
        "authority_absolute_paths": f"在抽查的已选元数据中发现 {manifest['windows_path_reference_count']:,} 个 Windows绝对路径引用。服务器命令须显式带 `--portable-runtime`，由隔离入口在内存中重定位正式路径和pin字典，保留源JSON bytes及其SHA。只有请求前缀映射不足以处理内部引用；目标Linux读取分支仍需实测。",
        "rlplugin_linux": "RLPlugin模块仅声明Win64，Windows二进制已排除。Source随清单保留，但这不代表可直接编译Linux。先验证已导入资产是否无需加载该编辑器导入插件；如仍需则评估源码兼容和Linux重编译。",
        "engine_plugins": "服务器UE必须具备工程启用和日志加载的对应Engine插件；本清单不上传Windows引擎。Win64专用插件需在服务器工程副本上作平台适配，不能直接认定全部可用。",
        "static_not_asset_closure": "Content完整保留以避免漏掉贴图/材质/地图依赖；工作区元数据来自当前worker静态依赖和有限JSON引用追踪。动态生成路径仍需服务器预检，不宣称完整运行依赖验证。",
        "snapshot_changes": "统计时本地UE可能继续保存资产；上传前在渲染停止后重新生成清单。当前仅stat大小和mtime，无数十GB内容哈希。",
        "ffmpeg_python": "服务器需Python3及可用libx264的FFmpeg或imageio-ffmpeg；本机Windows Python环境不在清单中。",
        "machine_texture_profile": "Windows本机 `00_engine/outputs/local_render_profile_v1/profile.json` 已从清单排除，原文件未改写。它绑定machine_name；服务器应不带它，用 `--pool-mb` 明确传入按服务器GPU实测选择的MRQ纹理池预算。",
    }
    lines += ["- " + translations[item["id"]] for item in manifest["issues"]]
    lines += [f"- 元数据路径抽查上限 {manifest['metadata_probe']['limit']} 个JSON，本次读取 {manifest['metadata_probe']['inspected_json_files']} 个；未逐份审计全部历史证据。可通过 `--metadata-probe-limit` 调整抽查规模。"]
    if manifest["stat_errors"]:
        lines += ["", "统计错误：", ""] + ["- " + value for value in manifest["stat_errors"]]
    lines += ["", "## 重新生成", "", "```text", "python 00_engine/scripts/dataset/build_render_transfer_manifest_v11.py --project-root <工程目录> --engine-root <引擎目录> --workspace <Lance_Work目录> --run-root <本次运行目录>", "```", "", "本脚本只生成清单，实际上传方式和服务器目的目录由后续明确设置。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--project-root", type=Path, default=WORKSPACE.parent / "projects/datatry_02")
    parser.add_argument("--engine-root", type=Path, default=WORKSPACE.parent / "UE_5.8")
    parser.add_argument("--run-root", type=Path, default=WORKSPACE / "00_engine/outputs/dataset_render_pilot_20261023_v1")
    parser.add_argument("--log", type=Path)
    parser.add_argument("--metadata-probe-limit", type=int, default=400)
    args = parser.parse_args(argv)
    manifest = build(args)
    args.run_root.mkdir(parents=True, exist_ok=True)
    (args.run_root / "TRANSFER_PLAN.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.run_root / "TRANSFER_PLAN.md").write_text(markdown(manifest), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("total_files", "total_bytes", "category_bytes", "windows_path_reference_count", "stat_errors")}, ensure_ascii=False))
    return 1 if manifest["stat_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
