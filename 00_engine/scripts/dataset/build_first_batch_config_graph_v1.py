"""Build and validate the first-batch configuration graph.

The builder is intentionally strict: it only consumes frozen asset records and
never invents unresolved identities, outfits, scene bindings, or UE paths.  A
single source manifest expands into the asset lock, required CC/UE exports,
deduplicated render nodes, atomic edit edges, render jobs, and deterministic
3--5 step edit chains defined by Config Graph Schema V1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "config_graph_v1"
SOURCE_SCHEMA_VERSION = "first_batch_graph_source_v1"
SAMPLER_VERSION = "first_batch_chain_sampler_v1"
EDIT_FIELDS = {
    "E1": "identity_id",
    "E2": "outfit_id",
    "E3": "action_id",
    "E7": "camera_id",
    "E11": "expression_id",
}
AXIS_WEIGHTS = {
    # E7 only exists on the two Happy camera states. Its selection weight is
    # deliberately higher so the final corpus, rather than each adjacency
    # list, still clears the 10% camera-edit coverage contract.
    "E1": 0.22,
    "E2": 0.22,
    "E3": 0.12,
    "E7": 0.32,
    "E11": 0.12,
}
CHAIN_CLASSES = ("progressive", "rollback", "closed_cycle")
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ConfigGraphError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_id(prefix: str, value: object) -> str:
    return f"{prefix}_{hashlib.sha256(canonical_bytes(value)).hexdigest()[:16]}"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigGraphError(f"Could not read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ConfigGraphError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    temporary.replace(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigGraphError(message)


def require_id(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(SAFE_ID.fullmatch(value)), f"Invalid {label}: {value!r}")
    return value


def index_assets(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = source.get("assets")
    require(isinstance(assets, list) and assets, "assets must be a non-empty list")
    indexed: dict[str, dict[str, Any]] = {}
    allowed_types = {
        "identity",
        "bodyfit",
        "outfit",
        "action",
        "expression",
        "scene",
        "camera",
        "lighting",
        "anchor",
    }
    for raw in assets:
        require(isinstance(raw, dict), "Every asset must be an object")
        asset = dict(raw)
        asset_id = require_id(asset.get("asset_id"), "asset_id")
        require(asset_id not in indexed, f"Duplicate asset_id: {asset_id}")
        require(asset.get("asset_type") in allowed_types, f"Unsupported asset_type for {asset_id}")
        require(asset.get("sex_compatibility") in ("female", "male", "unisex"), f"Invalid sex compatibility for {asset_id}")
        require(asset.get("status") in ("frozen", "validated"), f"Asset is not frozen or validated: {asset_id}")
        require(isinstance(asset.get("source_ref"), str) and asset["source_ref"], f"Missing source_ref for {asset_id}")
        require(not re.match(r"^[A-Za-z]:[\\/]", asset["source_ref"]), f"Absolute source_ref is not portable: {asset_id}")
        require(bool(SHA256.fullmatch(str(asset.get("content_sha256", "")))), f"Invalid content_sha256 for {asset_id}")
        require(isinstance(asset.get("version"), str) and asset["version"], f"Missing version for {asset_id}")
        asset.setdefault("constraints", {})
        indexed[asset_id] = asset
    return indexed


def require_asset(
    assets: dict[str, dict[str, Any]],
    asset_id: object,
    asset_type: str,
    sex: str | None = None,
) -> dict[str, Any]:
    checked_id = require_id(asset_id, f"{asset_type}_id")
    require(checked_id in assets, f"Unknown {asset_type}: {checked_id}")
    asset = assets[checked_id]
    require(asset["asset_type"] == asset_type, f"{checked_id} is not a {asset_type}")
    if sex is not None:
        require(asset["sex_compatibility"] in (sex, "unisex"), f"{checked_id} is incompatible with {sex}")
    return asset


def validate_look_contract(
    source: dict[str, Any], assets: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    looks = source.get("looks")
    require(isinstance(looks, list) and len(looks) == 16, "Exactly 16 sparse FullReference looks are required")
    look_ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    by_sex: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized: list[dict[str, Any]] = []
    for raw in looks:
        require(isinstance(raw, dict), "Every look must be an object")
        look = dict(raw)
        look_id = require_id(look.get("look_id"), "look_id")
        require(look_id not in look_ids, f"Duplicate look_id: {look_id}")
        look_ids.add(look_id)
        sex = look.get("sex")
        require(sex in ("female", "male"), f"Invalid look sex: {look_id}")
        require_asset(assets, look.get("bodyfit_id"), "bodyfit", sex)
        require_asset(assets, look.get("identity_id"), "identity", sex)
        require_asset(assets, look.get("outfit_id"), "outfit", sex)
        pair = (str(look["identity_id"]), str(look["outfit_id"]))
        require(pair not in pairs, f"Duplicate identity/outfit pair: {pair}")
        pairs.add(pair)
        by_sex[sex].append(look)
        normalized.append(look)

    for sex in ("female", "male"):
        sex_looks = by_sex[sex]
        require(len(sex_looks) == 8, f"{sex} must have exactly 8 looks")
        identity_counts = Counter(item["identity_id"] for item in sex_looks)
        outfit_counts = Counter(item["outfit_id"] for item in sex_looks)
        require(len(identity_counts) == 4 and set(identity_counts.values()) == {2}, f"{sex} identities must each appear in two looks")
        require(len(outfit_counts) == 4 and set(outfit_counts.values()) == {2}, f"{sex} outfits must each appear in two looks")
        bodyfits = {item["bodyfit_id"] for item in sex_looks}
        require(len(bodyfits) == 1, f"{sex} must use exactly one BodyFit")
        adjacency: dict[str, set[str]] = defaultdict(set)
        for item in sex_looks:
            identity = f"i:{item['identity_id']}"
            outfit = f"o:{item['outfit_id']}"
            adjacency[identity].add(outfit)
            adjacency[outfit].add(identity)
        seen = set()
        queue = deque([next(iter(adjacency))])
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(adjacency[current] - seen)
        require(seen == set(adjacency), f"{sex} sparse look graph is disconnected")
    return sorted(normalized, key=lambda item: item["look_id"])


def validate_runtime_contract(
    source: dict[str, Any], assets: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    action_sets = source.get("actions_by_sex")
    require(isinstance(action_sets, dict), "actions_by_sex is required")
    normalized_actions: dict[str, list[str]] = {}
    for sex in ("female", "male"):
        action_ids = action_sets.get(sex)
        require(isinstance(action_ids, list) and len(action_ids) == 6, f"{sex} requires exactly 6 actions")
        require(len(set(action_ids)) == 6, f"{sex} action IDs must be unique")
        for action_id in action_ids:
            require_asset(assets, action_id, "action", sex)
        normalized_actions[sex] = sorted(action_ids)

    expressions = source.get("expression_roles")
    require(isinstance(expressions, dict) and set(expressions) == {"happy", "angry", "sad"}, "expression_roles must define happy, angry, and sad")
    require(len(set(expressions.values())) == 3, "Expression assets must be distinct")
    for expression_id in expressions.values():
        require_asset(assets, expression_id, "expression")

    scene = source.get("scene_binding")
    require(isinstance(scene, dict), "scene_binding is required")
    require_asset(assets, scene.get("scene_id"), "scene")
    require_asset(assets, scene.get("lighting_id"), "lighting")
    require_asset(assets, scene.get("anchor_id"), "anchor")
    cameras = scene.get("camera_ids")
    require(isinstance(cameras, dict) and set(cameras) == {"medium", "full_body"}, "camera_ids must define medium and full_body")
    for camera_id in cameras.values():
        require_asset(assets, camera_id, "camera")

    profile = source.get("render_profile")
    require(isinstance(profile, dict), "render_profile is required")
    require_id(profile.get("render_profile_id"), "render_profile_id")
    require(profile.get("fps") == 24, "First-batch fps must be 24")
    require(profile.get("duration_frames") in (48, 72), "duration_frames must be 48 or 72")
    resolution = profile.get("resolution")
    require(isinstance(resolution, dict), "render resolution is required")
    require(resolution.get("width") in (960, 1280), "Unsupported render width")
    require(resolution.get("height") in (540, 720), "Unsupported render height")
    require(isinstance(profile.get("sequence_asset"), str) and profile["sequence_asset"].startswith("/Game/"), "sequence_asset must be a UE soft object path")
    return {
        "actions_by_sex": normalized_actions,
        "expression_roles": dict(expressions),
        "scene_binding": dict(scene),
        "render_profile": dict(profile),
    }


def build_nodes(
    looks: list[dict[str, Any]], runtime: dict[str, Any]
) -> list[dict[str, Any]]:
    profile = runtime["render_profile"]
    scene = runtime["scene_binding"]
    expression_roles = runtime["expression_roles"]
    states = (
        ("medium", "happy"),
        ("medium", "angry"),
        ("medium", "sad"),
        ("full_body", "happy"),
    )
    nodes: list[dict[str, Any]] = []
    seen: dict[str, bytes] = {}
    for look in looks:
        for action_id in runtime["actions_by_sex"][look["sex"]]:
            for camera_role, expression_role in states:
                config = {
                    "sex": look["sex"],
                    "bodyfit_id": look["bodyfit_id"],
                    "identity_id": look["identity_id"],
                    "outfit_id": look["outfit_id"],
                    "action_id": action_id,
                    "expression_id": expression_roles[expression_role],
                    "scene_id": scene["scene_id"],
                    "camera_id": scene["camera_ids"][camera_role],
                    "lighting_id": scene["lighting_id"],
                    "anchor_id": scene["anchor_id"],
                    "duration_frames": profile["duration_frames"],
                    "fps": profile["fps"],
                    "resolution": dict(profile["resolution"]),
                    "seed": int(profile.get("seed", 0)),
                }
                identity_payload = {
                    "schema_version": SCHEMA_VERSION,
                    "config": config,
                    "render_profile_id": profile["render_profile_id"],
                }
                node_id = stable_id("n", identity_payload)
                encoded = canonical_bytes(identity_payload)
                if node_id in seen and seen[node_id] != encoded:
                    raise ConfigGraphError(f"Node hash collision: {node_id}")
                seen[node_id] = encoded
                nodes.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "node_id": node_id,
                        "config": config,
                        "render_profile_id": profile["render_profile_id"],
                        "expected_media_uri": f"media/nodes/{node_id}/video.mp4",
                        "look_id": look["look_id"],
                        "camera_role": camera_role,
                        "expression_role": expression_role,
                    }
                )
    require(len(nodes) == 384, f"First-batch node cardinality drifted: {len(nodes)}")
    require(len({item["node_id"] for item in nodes}) == 384, "Node IDs are not unique")
    return sorted(nodes, key=lambda item: item["node_id"])


def build_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    node_by_id = {item["node_id"]: item for item in nodes}
    edges: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for axis, field in EDIT_FIELDS.items():
        groups: dict[bytes, list[dict[str, Any]]] = defaultdict(list)
        for node in nodes:
            reduced = dict(node["config"])
            reduced.pop(field)
            groups[canonical_bytes(reduced)].append(node)
        for group in groups.values():
            if len(group) < 2:
                continue
            for source in group:
                for target in group:
                    if source["node_id"] == target["node_id"]:
                        continue
                    before = source["config"][field]
                    after = target["config"][field]
                    if before == after:
                        continue
                    payload = {
                        "source_node_id": source["node_id"],
                        "target_node_id": target["node_id"],
                        "edit_axis": axis,
                    }
                    edge_id = stable_id("e", payload)
                    if edge_id in edge_ids:
                        continue
                    edge_ids.add(edge_id)
                    edges.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "edge_id": edge_id,
                            **payload,
                            "before_value": before,
                            "after_value": after,
                            "changed_fields": [f"config.{field}"],
                            "inverse_edge_id": None,
                            "instruction_templates": [f"{axis.lower()}_set_v1"],
                        }
                    )
    by_triplet = {
        (item["source_node_id"], item["target_node_id"], item["edit_axis"]): item
        for item in edges
    }
    for edge in edges:
        inverse = by_triplet.get(
            (edge["target_node_id"], edge["source_node_id"], edge["edit_axis"])
        )
        require(inverse is not None, f"Missing inverse for {edge['edge_id']}")
        edge["inverse_edge_id"] = inverse["edge_id"]
        validate_atomic_edge(edge, node_by_id)
    return sorted(edges, key=lambda item: item["edge_id"])


def validate_atomic_edge(
    edge: dict[str, Any], node_by_id: dict[str, dict[str, Any]]
) -> None:
    source = node_by_id[edge["source_node_id"]]["config"]
    target = node_by_id[edge["target_node_id"]]["config"]
    differences = sorted(key for key in source if source[key] != target[key])
    expected = EDIT_FIELDS[edge["edit_axis"]]
    require(differences == [expected], f"Non-atomic edge {edge['edge_id']}: {differences}")
    require(edge["before_value"] == source[expected], f"Incorrect before_value: {edge['edge_id']}")
    require(edge["after_value"] == target[expected], f"Incorrect after_value: {edge['edge_id']}")


def allocate_class_counts(total: int, ratios: dict[str, float]) -> dict[str, int]:
    require(set(ratios) == set(CHAIN_CLASSES), "class_ratios must define all chain classes")
    require(abs(sum(float(value) for value in ratios.values()) - 1.0) < 1e-9, "class_ratios must sum to 1")
    raw = {key: total * float(ratios[key]) for key in CHAIN_CLASSES}
    counts = {key: math.floor(raw[key]) for key in CHAIN_CLASSES}
    remaining = total - sum(counts.values())
    order = sorted(CHAIN_CLASSES, key=lambda key: (raw[key] - counts[key], key), reverse=True)
    for key in order[:remaining]:
        counts[key] += 1
    return counts


def weighted_edge(
    candidates: list[dict[str, Any]], rng: random.Random
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in candidates:
        grouped[edge["edit_axis"]].append(edge)
    axes = sorted(grouped)
    weights = [AXIS_WEIGHTS[axis] for axis in axes]
    axis = rng.choices(axes, weights=weights, k=1)[0]
    return rng.choice(grouped[axis])


def progressive_path(
    start: str,
    length: int,
    adjacency: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> list[dict[str, Any]] | None:
    node_ids = [start]
    path: list[dict[str, Any]] = []
    for _ in range(length):
        candidates = [
            edge
            for edge in adjacency[node_ids[-1]]
            if edge["target_node_id"] not in node_ids
        ]
        if not candidates:
            return None
        edge = weighted_edge(candidates, rng)
        path.append(edge)
        node_ids.append(edge["target_node_id"])
    return path


def rollback_path(
    start: str,
    length: int,
    adjacency: dict[str, list[dict[str, Any]]],
    edge_by_id: dict[str, dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]] | None:
    first = weighted_edge(adjacency[start], rng)
    inverse = edge_by_id[first["inverse_edge_id"]]
    path = [first, inverse]
    current = start
    used = {first["edge_id"], inverse["edge_id"]}
    while len(path) < length:
        candidates = [
            edge
            for edge in adjacency[current]
            if edge["edge_id"] not in used
        ]
        if not candidates:
            return None
        edge = weighted_edge(candidates, rng)
        path.append(edge)
        used.add(edge["edge_id"])
        current = edge["target_node_id"]
    if current == start:
        return None
    return path


def closed_cycle_path(
    start: str,
    length: int,
    adjacency: dict[str, list[dict[str, Any]]],
    rng: random.Random,
) -> list[dict[str, Any]] | None:
    def search(
        current: str,
        depth: int,
        visited: set[str],
        used_edges: set[str],
    ) -> list[dict[str, Any]] | None:
        remaining = length - depth
        if remaining == 1:
            closing = [
                edge
                for edge in adjacency[current]
                if edge["target_node_id"] == start
                and edge["edge_id"] not in used_edges
            ]
            return [weighted_edge(closing, rng)] if closing else None
        candidates = [
            edge
            for edge in adjacency[current]
            if edge["target_node_id"] != start
            and edge["target_node_id"] not in visited
            and edge["edge_id"] not in used_edges
        ]
        rng.shuffle(candidates)
        candidates.sort(key=lambda edge: AXIS_WEIGHTS[edge["edit_axis"]], reverse=True)
        for edge in candidates[:24]:
            tail = search(
                edge["target_node_id"],
                depth + 1,
                visited | {edge["target_node_id"]},
                used_edges | {edge["edge_id"]},
            )
            if tail is not None:
                return [edge, *tail]
        return None

    return search(start, 0, {start}, set())


def instruction_for_edge(
    edge: dict[str, Any],
    target_node_id: str,
    prior_nodes: list[str],
) -> str:
    labels = {
        "E1": "人物身份",
        "E2": "服装",
        "E3": "身体动作",
        "E7": "镜头",
        "E11": "面部表情",
    }
    if target_node_id in prior_nodes:
        prior_index = max(index for index, value in enumerate(prior_nodes) if value == target_node_id)
        if prior_index == 0:
            return f"将{labels[edge['edit_axis']]}恢复到初始状态。"
        return f"将{labels[edge['edit_axis']]}恢复到第 {prior_index} 轮后的状态。"
    return f"将{labels[edge['edit_axis']]}切换为 {edge['after_value']}。"


def build_chains(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    length_counts_raw = plan.get("length_counts") or {"3": 1000, "4": 2000, "5": 1000}
    length_counts = {int(key): int(value) for key, value in length_counts_raw.items()}
    require(set(length_counts) == {3, 4, 5}, "length_counts must define 3, 4, and 5")
    require(all(value > 0 for value in length_counts.values()), "length_counts must be positive")
    ratios = plan.get("class_ratios") or {
        "progressive": 0.70,
        "rollback": 0.20,
        "closed_cycle": 0.10,
    }
    seed = int(plan.get("sampling_seed", 20260820))
    rng = random.Random(seed)
    node_ids = [item["node_id"] for item in nodes]
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edge_by_id = {item["edge_id"]: item for item in edges}
    for edge in edges:
        adjacency[edge["source_node_id"]].append(edge)

    chains: list[dict[str, Any]] = []
    path_keys: set[tuple[str, ...]] = set()
    matrix: dict[int, dict[str, int]] = {}
    for length, count in sorted(length_counts.items()):
        matrix[length] = allocate_class_counts(count, ratios)

    for length, classes in matrix.items():
        for chain_class in CHAIN_CLASSES:
            required = classes[chain_class]
            accepted = 0
            attempts = 0
            max_attempts = max(required * 500, 10000)
            while accepted < required and attempts < max_attempts:
                attempts += 1
                start = rng.choice(node_ids)
                if chain_class == "progressive":
                    path = progressive_path(start, length, adjacency, rng)
                elif chain_class == "rollback":
                    path = rollback_path(start, length, adjacency, edge_by_id, rng)
                else:
                    path = closed_cycle_path(start, length, adjacency, rng)
                if path is None:
                    continue
                edge_ids = tuple(edge["edge_id"] for edge in path)
                path_key = (start, *edge_ids)
                if path_key in path_keys:
                    continue
                chain_nodes = [start]
                instructions: list[dict[str, Any]] = []
                for round_index, edge in enumerate(path, 1):
                    target = edge["target_node_id"]
                    instructions.append(
                        {
                            "round": round_index,
                            "language": "zh-CN",
                            "text": instruction_for_edge(edge, target, chain_nodes),
                        }
                    )
                    chain_nodes.append(target)
                if chain_class == "progressive" and len(set(chain_nodes)) != len(chain_nodes):
                    continue
                if chain_class == "rollback" and (
                    len(set(chain_nodes)) == len(chain_nodes)
                    or chain_nodes[-1] == chain_nodes[0]
                ):
                    continue
                if chain_class == "closed_cycle" and chain_nodes[-1] != chain_nodes[0]:
                    continue
                chain_payload = {
                    "start_node_id": start,
                    "edge_ids": list(edge_ids),
                    "sampler_version": SAMPLER_VERSION,
                }
                chain_id = stable_id("c", chain_payload)
                chains.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "chain_id": chain_id,
                        "start_node_id": start,
                        "edge_ids": list(edge_ids),
                        "node_ids": chain_nodes,
                        "edit_axes": [edge["edit_axis"] for edge in path],
                        "chain_class": chain_class,
                        "sampling_seed": seed,
                        "sampler_version": SAMPLER_VERSION,
                        "instructions": instructions,
                    }
                )
                path_keys.add(path_key)
                accepted += 1
            require(accepted == required, f"Could not sample {required} unique {length}-step {chain_class} chains")

    chains.sort(key=lambda item: item["chain_id"])
    axis_counts = Counter(axis for chain in chains for axis in chain["edit_axes"])
    total_edges = sum(axis_counts.values())
    axis_shares = {axis: axis_counts[axis] / total_edges for axis in EDIT_FIELDS}
    require(all(axis_shares[axis] >= 0.10 for axis in EDIT_FIELDS), f"Edit-axis minimum coverage failed: {axis_shares}")
    require(axis_shares["E1"] >= 0.15 and axis_shares["E2"] >= 0.15, f"Identity/outfit coverage failed: {axis_shares}")
    report = {
        "chain_count": len(chains),
        "length_counts": dict(sorted(Counter(len(item["edge_ids"]) for item in chains).items())),
        "class_counts": dict(sorted(Counter(item["chain_class"] for item in chains).items())),
        "axis_counts": dict(sorted(axis_counts.items())),
        "axis_shares": {key: round(value, 6) for key, value in sorted(axis_shares.items())},
        "unique_path_count": len(path_keys),
        "sampling_seed": seed,
        "sampler_version": SAMPLER_VERSION,
    }
    return chains, report


def build_required_exports(
    source: dict[str, Any],
    looks: list[dict[str, Any]],
    runtime: dict[str, Any],
    assets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    action_ids = [
        action_id
        for sex in ("female", "male")
        for action_id in runtime["actions_by_sex"][sex]
    ]
    return {
        "schema_version": "required_exports_v1",
        "batch_id": source["batch_id"],
        "generated_at": now(),
        "production_status": "frozen_inputs_pending_runtime_validation",
        "counts": {
            "full_reference_looks": len(looks),
            "action_assets": len(action_ids),
            "female_actions": len(runtime["actions_by_sex"]["female"]),
            "male_actions": len(runtime["actions_by_sex"]["male"]),
            "expression_assets": 3,
        },
        "full_reference_looks": looks,
        "actions": [
            {
                "action_id": action_id,
                "sex_compatibility": assets[action_id]["sex_compatibility"],
                "source_ref": assets[action_id]["source_ref"],
                "content_sha256": assets[action_id]["content_sha256"],
                "root_motion_policy": assets[action_id]["constraints"].get("root_motion_policy"),
                "face_policy": assets[action_id]["constraints"].get("face_policy"),
            }
            for action_id in action_ids
        ],
        "expressions": [
            {
                "role": role,
                "expression_id": expression_id,
                "source_ref": assets[expression_id]["source_ref"],
                "content_sha256": assets[expression_id]["content_sha256"],
            }
            for role, expression_id in sorted(runtime["expression_roles"].items())
        ],
        "scene_binding": runtime["scene_binding"],
        "render_profile": runtime["render_profile"],
    }


def build_render_jobs(
    nodes: list[dict[str, Any]], runtime: dict[str, Any]
) -> list[dict[str, Any]]:
    sequence = runtime["render_profile"]["sequence_asset"]
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "job_id": f"rj_{node['node_id'][2:]}",
            "node_id": node["node_id"],
            "status": "pending",
            "attempt": 0,
            "sequence_asset": sequence,
            "temporary_output_uri": f"staging/render/{node['node_id']}",
            "expected_media_uri": node["expected_media_uri"],
            "log_uri": f"logs/render/{node['node_id']}/attempt_000.jsonl",
        }
        for node in nodes
    ]


def build_graph(source_path: Path, output_dir: Path) -> dict[str, Any]:
    source = read_json(source_path)
    require(source.get("schema_version") == SOURCE_SCHEMA_VERSION, "Unsupported source schema")
    require_id(source.get("batch_id"), "batch_id")
    require(source.get("status") == "frozen", "Source manifest status must be frozen")
    assets = index_assets(source)
    looks = validate_look_contract(source, assets)
    runtime = validate_runtime_contract(source, assets)
    nodes = build_nodes(looks, runtime)
    edges = build_edges(nodes)
    chains, chain_report = build_chains(nodes, edges, source.get("chain_plan") or {})
    jobs = build_render_jobs(nodes, runtime)
    required_exports = build_required_exports(source, looks, runtime, assets)

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_lock = {
        "schema_version": "asset_lock_v1",
        "batch_id": source["batch_id"],
        "generated_at": now(),
        "source_manifest": source_path.name,
        "source_manifest_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "assets": [assets[key] for key in sorted(assets)],
        "looks": looks,
        "runtime_contract": runtime,
    }
    write_json(output_dir / "assets.json", asset_lock)
    write_json(output_dir / "required_exports.json", required_exports)
    write_jsonl(output_dir / "nodes.jsonl", nodes)
    write_jsonl(output_dir / "edges.jsonl", edges)
    write_jsonl(output_dir / "chains.jsonl", chains)
    write_jsonl(output_dir / "render_jobs.jsonl", jobs)

    report = {
        "schema_version": "config_graph_build_report_v1",
        "batch_id": source["batch_id"],
        "generated_at": now(),
        "status": "passed",
        "counts": {
            "assets": len(assets),
            "looks": len(looks),
            "nodes": len(nodes),
            "edges": len(edges),
            "chains": len(chains),
            "render_jobs": len(jobs),
        },
        "chain_report": chain_report,
        "files": {},
    }
    for name in (
        "assets.json",
        "required_exports.json",
        "nodes.jsonl",
        "edges.jsonl",
        "chains.jsonl",
        "render_jobs.jsonl",
    ):
        path = output_dir / name
        report["files"][name] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    write_json(output_dir / "build_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_graph(args.source.resolve(), args.output_dir.resolve())
    except ConfigGraphError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
