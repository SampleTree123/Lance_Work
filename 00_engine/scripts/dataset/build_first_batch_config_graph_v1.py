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
import random
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "config_graph_v1"
SOURCE_MANIFEST_TYPE = "first_batch_source_manifest"
SAMPLING_SPEC_VERSION = "multi_round_v1_20260824"
SAMPLER_VERSION = "first_batch_chain_sampler_v2_20260824"
EDIT_FIELDS = {
    "E1": "identity_id",
    "E2": "outfit_id",
    "E3": "action_id",
    "E7": "camera_id",
}
CHAIN_POLICIES = ("progressive_shortest", "freeform_walk")
EXPECTED_LOOKS = 32
EXPECTED_LOOKS_PER_SEX = 16
EXPECTED_IDENTITIES_PER_SEX = 4
EXPECTED_OUTFITS_PER_SEX = 4
EXPECTED_ACTIONS_PER_SEX = 5
EXPECTED_CAMERAS = ("near", "far", "high", "side")
EXPECTED_EXPRESSION = "happy"
EXPECTED_DOMAINS = ("female_v1", "male_v1")
EXPECTED_NODES_PER_DOMAIN = 320
EXPECTED_NODES = 640
EXPECTED_CHAINS = 4000
AXIS_TARGET_SHARES = {axis: 0.25 for axis in EDIT_FIELDS}
AXIS_SHARE_TOLERANCE = 0.02
DEFAULT_CHAIN_QUOTAS = {
    "female_v1": {
        "progressive_shortest": {3: 500, 4: 500, 5: 0},
        "freeform_walk": {3: 334, 4: 333, 5: 333},
    },
    "male_v1": {
        "progressive_shortest": {3: 500, 4: 500, 5: 0},
        "freeform_walk": {3: 333, 4: 333, 5: 334},
    },
}
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
        "render_profile",
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
    require(
        isinstance(looks, list) and len(looks) == EXPECTED_LOOKS,
        f"Exactly {EXPECTED_LOOKS} FullReference looks are required",
    )
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
        require(
            len(sex_looks) == EXPECTED_LOOKS_PER_SEX,
            f"{sex} must have exactly {EXPECTED_LOOKS_PER_SEX} looks",
        )
        identity_counts = Counter(item["identity_id"] for item in sex_looks)
        outfit_counts = Counter(item["outfit_id"] for item in sex_looks)
        require(
            len(identity_counts) == EXPECTED_IDENTITIES_PER_SEX
            and set(identity_counts.values()) == {EXPECTED_OUTFITS_PER_SEX},
            f"{sex} identities must each appear with all four outfits",
        )
        require(
            len(outfit_counts) == EXPECTED_OUTFITS_PER_SEX
            and set(outfit_counts.values()) == {EXPECTED_IDENTITIES_PER_SEX},
            f"{sex} outfits must each appear with all four identities",
        )
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
        require(seen == set(adjacency), f"{sex} FullReference look graph is disconnected")
    return sorted(normalized, key=lambda item: item["look_id"])


def validate_runtime_contract(
    source: dict[str, Any], assets: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    action_sets = source.get("actions_by_sex")
    require(isinstance(action_sets, dict), "actions_by_sex is required")
    normalized_actions: dict[str, list[str]] = {}
    for sex in ("female", "male"):
        action_ids = action_sets.get(sex)
        require(
            isinstance(action_ids, list)
            and len(action_ids) == EXPECTED_ACTIONS_PER_SEX,
            f"{sex} requires exactly {EXPECTED_ACTIONS_PER_SEX} actions",
        )
        require(
            len(set(action_ids)) == EXPECTED_ACTIONS_PER_SEX,
            f"{sex} action IDs must be unique",
        )
        for action_id in action_ids:
            require_asset(assets, action_id, "action", sex)
        normalized_actions[sex] = sorted(action_ids)

    expression_ids = source.get("expression_ids")
    require(
        expression_ids == [EXPECTED_EXPRESSION],
        "expression_ids must be exactly ['happy']",
    )
    require_asset(assets, EXPECTED_EXPRESSION, "expression")

    expression_policy = source.get("expression_policy")
    require(isinstance(expression_policy, dict), "expression_policy is required")
    require(
        expression_policy.get("fixed_expression_id") == EXPECTED_EXPRESSION,
        "The first batch must freeze the Happy expression",
    )
    require(
        expression_policy.get("editable_feature") is False,
        "Expressions must not be editable in the first batch",
    )
    require(
        expression_policy.get("edit_axis") is None,
        "Expression edit_axis must be null",
    )

    scene = source.get("scene_binding")
    require(isinstance(scene, dict), "scene_binding is required")
    require_asset(assets, scene.get("scene_id"), "scene")
    require_asset(assets, scene.get("lighting_id"), "lighting")
    require_asset(assets, scene.get("anchor_id"), "anchor")
    cameras = scene.get("camera_ids")
    require(
        isinstance(cameras, dict) and tuple(cameras) == EXPECTED_CAMERAS,
        "camera_ids must define near, far, high, and side in canonical order",
    )
    require(
        tuple(cameras.values()) == EXPECTED_CAMERAS,
        "Camera asset IDs must use the canonical near/far/high/side IDs",
    )
    for camera_id in EXPECTED_CAMERAS:
        require_asset(assets, camera_id, "camera")

    profile = source.get("render_profile")
    require(isinstance(profile, dict), "render_profile is required")
    render_profile_id = require_id(
        profile.get("render_profile_id"), "render_profile_id"
    )
    require_asset(assets, render_profile_id, "render_profile")
    require(profile.get("fps") == 30, "First-batch fps must be 30")
    require(profile.get("frame_start") == 0, "First-batch frame_start must be 0")
    require(profile.get("duration_frames") == 150, "First-batch duration must be 150 frames")
    resolution = profile.get("resolution")
    require(isinstance(resolution, dict), "render resolution is required")
    require(
        resolution == {"width": 2560, "height": 1440},
        "First-batch resolution must be 2560x1440",
    )
    require(isinstance(profile.get("sequence_asset"), str) and profile["sequence_asset"].startswith("/Game/"), "sequence_asset must be a UE soft object path")
    return {
        "actions_by_sex": normalized_actions,
        "expression_ids": [EXPECTED_EXPRESSION],
        "expression_policy": dict(expression_policy),
        "scene_binding": dict(scene),
        "render_profile": dict(profile),
    }


def build_compatibility_domains(
    looks: list[dict[str, Any]], runtime: dict[str, Any]
) -> list[dict[str, Any]]:
    domains: list[dict[str, Any]] = []
    for sex in ("female", "male"):
        domain_id = f"{sex}_v1"
        sex_looks = [look for look in looks if look["sex"] == sex]
        bodyfit_ids = sorted({look["bodyfit_id"] for look in sex_looks})
        require(len(bodyfit_ids) == 1, f"{domain_id} must use one BodyFit")
        domains.append(
            {
                "schema_version": SCHEMA_VERSION,
                "compatibility_domain_id": domain_id,
                "sex": sex,
                "bodyfit_id": bodyfit_ids[0],
                "identity_ids": sorted({look["identity_id"] for look in sex_looks}),
                "outfit_ids": sorted({look["outfit_id"] for look in sex_looks}),
                "action_ids": list(runtime["actions_by_sex"][sex]),
                "camera_ids": list(EXPECTED_CAMERAS),
                "expression_ids": [EXPECTED_EXPRESSION],
                "expected_node_count": EXPECTED_NODES_PER_DOMAIN,
                "hard_constraints": {
                    "full_reference_look_matrix_required": True,
                    "same_sex_actions_only": True,
                    "cross_domain_edges_allowed": False,
                    "root_motion_policy_source": "action_asset.constraints",
                },
            }
        )
    require(
        tuple(item["compatibility_domain_id"] for item in domains)
        == EXPECTED_DOMAINS,
        "Compatibility-domain IDs drifted",
    )
    return domains


def build_nodes(
    looks: list[dict[str, Any]], runtime: dict[str, Any]
) -> list[dict[str, Any]]:
    profile = runtime["render_profile"]
    scene = runtime["scene_binding"]
    nodes: list[dict[str, Any]] = []
    seen: dict[str, bytes] = {}
    for look in looks:
        domain_id = f"{look['sex']}_v1"
        for action_id in runtime["actions_by_sex"][look["sex"]]:
            for camera_id in EXPECTED_CAMERAS:
                config = {
                    "sex": look["sex"],
                    "bodyfit_id": look["bodyfit_id"],
                    "identity_id": look["identity_id"],
                    "outfit_id": look["outfit_id"],
                    "action_id": action_id,
                    "expression_id": EXPECTED_EXPRESSION,
                    "scene_id": scene["scene_id"],
                    "camera_id": scene["camera_ids"][camera_id],
                    "lighting_id": scene["lighting_id"],
                    "anchor_id": scene["anchor_id"],
                    "frame_start": profile["frame_start"],
                    "duration_frames": profile["duration_frames"],
                    "fps": profile["fps"],
                    "resolution": dict(profile["resolution"]),
                    "seed": int(profile.get("seed", 0)),
                }
                identity_payload = {
                    "schema_version": SCHEMA_VERSION,
                    "compatibility_domain_id": domain_id,
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
                        "compatibility_domain_id": domain_id,
                        "node_role": "chain_node",
                        "config": config,
                        "render_profile_id": profile["render_profile_id"],
                        "expected_media_uri": f"media/nodes/{node_id}/video.mp4",
                        "config_sha256": hashlib.sha256(
                            canonical_bytes(config)
                        ).hexdigest(),
                        "look_id": look["look_id"],
                        "character_blueprint": look.get("character_blueprint"),
                    }
                )
    require(
        len(nodes) == EXPECTED_NODES,
        f"First-batch node cardinality drifted: {len(nodes)}",
    )
    require(
        len({item["node_id"] for item in nodes}) == EXPECTED_NODES,
        "Node IDs are not unique",
    )
    domain_counts = Counter(item["compatibility_domain_id"] for item in nodes)
    require(
        domain_counts
        == Counter({domain: EXPECTED_NODES_PER_DOMAIN for domain in EXPECTED_DOMAINS}),
        f"Node domain counts drifted: {dict(domain_counts)}",
    )
    return sorted(nodes, key=lambda item: item["node_id"])


def build_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    node_by_id = {item["node_id"]: item for item in nodes}
    edges: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for edge_type, field in EDIT_FIELDS.items():
        groups: dict[tuple[str, bytes], list[dict[str, Any]]] = defaultdict(list)
        for node in nodes:
            reduced = dict(node["config"])
            reduced.pop(field)
            groups[
                (node["compatibility_domain_id"], canonical_bytes(reduced))
            ].append(node)
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
                        "compatibility_domain_id": source[
                            "compatibility_domain_id"
                        ],
                        "edge_type": edge_type,
                        "edit_axis": field,
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
                            "instruction_template_ids": [
                                f"{edge_type.lower()}_set_v1"
                            ],
                        }
                    )
    by_triplet = {
        (item["source_node_id"], item["target_node_id"], item["edge_type"]): item
        for item in edges
    }
    for edge in edges:
        inverse = by_triplet.get(
            (edge["target_node_id"], edge["source_node_id"], edge["edge_type"])
        )
        require(inverse is not None, f"Missing inverse for {edge['edge_id']}")
        edge["inverse_edge_id"] = inverse["edge_id"]
        validate_atomic_edge(edge, node_by_id)
    return sorted(edges, key=lambda item: item["edge_id"])


def validate_atomic_edge(
    edge: dict[str, Any], node_by_id: dict[str, dict[str, Any]]
) -> None:
    source_node = node_by_id[edge["source_node_id"]]
    target_node = node_by_id[edge["target_node_id"]]
    require(
        source_node["compatibility_domain_id"]
        == target_node["compatibility_domain_id"]
        == edge["compatibility_domain_id"],
        f"Cross-domain edge: {edge['edge_id']}",
    )
    source = source_node["config"]
    target = target_node["config"]
    differences = sorted(key for key in source if source[key] != target[key])
    require(edge.get("edge_type") in EDIT_FIELDS, f"Unknown edge type: {edge}")
    expected = EDIT_FIELDS[edge["edge_type"]]
    require(edge.get("edit_axis") == expected, f"Incorrect edit_axis: {edge['edge_id']}")
    require(differences == [expected], f"Non-atomic edge {edge['edge_id']}: {differences}")
    require(edge["before_value"] == source[expected], f"Incorrect before_value: {edge['edge_id']}")
    require(edge["after_value"] == target[expected], f"Incorrect after_value: {edge['edge_id']}")


def validate_domain_connectivity(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> dict[str, Any]:
    nodes_by_domain: dict[str, set[str]] = defaultdict(set)
    adjacency: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        nodes_by_domain[node["compatibility_domain_id"]].add(node["node_id"])
    for edge in edges:
        adjacency[edge["source_node_id"]].add(edge["target_node_id"])

    report: dict[str, Any] = {}
    for domain_id in EXPECTED_DOMAINS:
        domain_nodes = nodes_by_domain[domain_id]
        require(
            len(domain_nodes) == EXPECTED_NODES_PER_DOMAIN,
            f"{domain_id} node count drifted",
        )
        start = min(domain_nodes)
        visited: set[str] = set()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend((adjacency[current] & domain_nodes) - visited)
        require(
            visited == domain_nodes,
            f"Compatibility domain is disconnected: {domain_id}",
        )
        report[domain_id] = {
            "node_count": len(domain_nodes),
            "reachable_node_count": len(visited),
            "connected_component_count": 1,
        }
    return report


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
    }
    edge_type = edge["edge_type"]
    if target_node_id in prior_nodes:
        prior_index = max(index for index, value in enumerate(prior_nodes) if value == target_node_id)
        if prior_index == 0:
            return f"将{labels[edge_type]}恢复到初始状态。"
        return f"将{labels[edge_type]}恢复到第 {prior_index} 轮后的状态。"
    return f"将{labels[edge_type]}切换为 {edge['after_value']}。"


def normalize_chain_quotas(plan: dict[str, Any]) -> dict[str, dict[str, dict[int, int]]]:
    raw = plan.get("quota_matrix") or DEFAULT_CHAIN_QUOTAS
    require(isinstance(raw, dict), "quota_matrix must be an object")
    normalized: dict[str, dict[str, dict[int, int]]] = {}
    for domain_id in EXPECTED_DOMAINS:
        domain_raw = raw.get(domain_id)
        require(isinstance(domain_raw, dict), f"Missing quota domain: {domain_id}")
        normalized[domain_id] = {}
        for policy in CHAIN_POLICIES:
            policy_raw = domain_raw.get(policy)
            require(
                isinstance(policy_raw, dict),
                f"Missing quota bucket: {domain_id}/{policy}",
            )
            lengths = {int(key): int(value) for key, value in policy_raw.items()}
            require(
                set(lengths) == {3, 4, 5} and all(value >= 0 for value in lengths.values()),
                f"Invalid length quotas: {domain_id}/{policy}",
            )
            normalized[domain_id][policy] = lengths
    require(
        normalized == DEFAULT_CHAIN_QUOTAS,
        "The first-batch quota matrix must match the accepted 2026-08-24 contract",
    )
    return normalized


def semantic_facts(
    node_ids: list[str],
    edge_axes: list[str],
    node_by_id: dict[str, dict[str, Any]],
) -> dict[str, bool]:
    start_config = node_by_id[node_ids[0]]["config"]
    end_config = node_by_id[node_ids[-1]]["config"]
    semantic_hamming = sum(
        start_config[field] != end_config[field]
        for field in EDIT_FIELDS.values()
    )
    axis_history = {
        field: [start_config[field]] for field in EDIT_FIELDS.values()
    }
    has_rollback = False
    for index, field in enumerate(edge_axes):
        target_value = node_by_id[node_ids[index + 1]]["config"][field]
        if target_value in axis_history[field]:
            has_rollback = True
        axis_history[field].append(target_value)
    has_repeated_axis = len(set(edge_axes)) != len(edge_axes)
    has_consecutive_same_axis = any(
        first == second for first, second in zip(edge_axes, edge_axes[1:])
    )
    returns_to_start = node_ids[-1] == node_ids[0]
    facts = {
        "is_semantic_shortest": len(edge_axes) == semantic_hamming,
        "has_repeated_axis": has_repeated_axis,
        "has_consecutive_same_axis": has_consecutive_same_axis,
        "has_rollback": has_rollback,
        "returns_to_start": returns_to_start,
    }
    require(
        not facts["has_consecutive_same_axis"] or facts["has_repeated_axis"],
        "Consecutive-axis implication failed",
    )
    require(
        not facts["has_rollback"] or facts["has_repeated_axis"],
        "Rollback implication failed",
    )
    require(
        not facts["returns_to_start"] or facts["has_rollback"],
        "Return-to-start implication failed",
    )
    return facts


def choose_weighted_remaining_axis(
    remaining: dict[str, int], rng: random.Random
) -> str:
    candidates = [axis for axis in EDIT_FIELDS if remaining[axis] > 0]
    require(bool(candidates), "No remaining edit-axis quota")
    total = sum(remaining[axis] for axis in candidates)
    pick = rng.randrange(total)
    for axis in candidates:
        weight = remaining[axis]
        if pick < weight:
            return axis
        pick -= weight
    raise AssertionError("Weighted axis selection fell through")


def choose_axis_sequence(
    policy: str,
    length: int,
    axis_counts: Counter[str],
    axis_targets: dict[str, int],
    rng: random.Random,
) -> list[str]:
    local_counts = Counter(axis_counts)
    if policy == "progressive_shortest":
        axes = list(EDIT_FIELDS)
        rng.shuffle(axes)
        axes.sort(
            key=lambda axis: axis_targets[axis] - local_counts[axis],
            reverse=True,
        )
        selected = axes[:length]
        require(
            len(selected) == length
            and all(axis_targets[axis] > local_counts[axis] for axis in selected),
            "Progressive axis quota exhausted",
        )
        rng.shuffle(selected)
        return selected

    selected: list[str] = []
    for _ in range(length):
        remaining = {
            axis: axis_targets[axis] - local_counts[axis] for axis in EDIT_FIELDS
        }
        axis = choose_weighted_remaining_axis(remaining, rng)
        selected.append(axis)
        local_counts[axis] += 1
    return selected


def build_path_for_axes(
    start_node_id: str,
    edge_types: list[str],
    adjacency: dict[str, dict[str, list[dict[str, Any]]]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []
    current = start_node_id
    for edge_type in edge_types:
        candidates = adjacency[current][edge_type]
        require(bool(candidates), f"No {edge_type} edge from {current}")
        edge = candidates[rng.randrange(len(candidates))]
        path.append(edge)
        current = edge["target_node_id"]
    return path


def chain_identity_payload(chain: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_manifest_id": chain["source_manifest_id"],
        "sampling_spec_version": chain["sampling_spec_version"],
        "sampler_version": chain["sampler_version"],
        "node_ids": chain["node_ids"],
        "edge_ids": chain["edge_ids"],
    }


def make_chain_record(
    start_node_id: str,
    path: list[dict[str, Any]],
    policy: str,
    source_manifest_id: str,
    sampler_seed: int,
    node_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    node_ids = [start_node_id]
    instructions: list[dict[str, Any]] = []
    for round_index, edge in enumerate(path, 1):
        target = edge["target_node_id"]
        instructions.append(
            {
                "round": round_index,
                "language": "zh-CN",
                "text": instruction_for_edge(edge, target, node_ids),
            }
        )
        node_ids.append(target)
    edge_axes = [edge["edit_axis"] for edge in path]
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "sampling_spec_version": SAMPLING_SPEC_VERSION,
        "source_manifest_id": source_manifest_id,
        "compatibility_domain_id": node_by_id[start_node_id][
            "compatibility_domain_id"
        ],
        "chain_policy": policy,
        "edit_length": len(path),
        "start_node_id": start_node_id,
        "end_node_id": node_ids[-1],
        "node_ids": node_ids,
        "edge_ids": [edge["edge_id"] for edge in path],
        "edge_types": [edge["edge_type"] for edge in path],
        "edge_axes": edge_axes,
        "sampler_seed": sampler_seed,
        "sampler_version": SAMPLER_VERSION,
        "instructions": instructions,
        **semantic_facts(node_ids, edge_axes, node_by_id),
    }
    record["chain_id"] = stable_id("c", chain_identity_payload(record))
    return record


def validate_chain_set(
    chains: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    quotas: dict[str, dict[str, dict[int, int]]],
    axis_tolerance: float,
) -> dict[str, Any]:
    node_by_id = {node["node_id"]: node for node in nodes}
    edge_by_id = {edge["edge_id"]: edge for edge in edges}
    path_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    referenced_nodes: set[str] = set()
    quota_counts: Counter[tuple[str, str, int]] = Counter()
    axis_counts: Counter[str] = Counter()
    fact_counts: Counter[str] = Counter()
    freeform_fact_counts: Counter[str] = Counter()

    for chain in chains:
        length = chain["edit_length"]
        require(length in (3, 4, 5), f"Invalid chain length: {chain['chain_id']}")
        require(
            len(chain["node_ids"]) == length + 1
            and len(chain["edge_ids"]) == length
            and len(chain["edge_axes"]) == length
            and len(chain["edge_types"]) == length
            and len(chain["instructions"]) == length,
            f"Chain cardinality mismatch: {chain['chain_id']}",
        )
        require(
            chain["start_node_id"] == chain["node_ids"][0]
            and chain["end_node_id"] == chain["node_ids"][-1],
            f"Chain endpoint mismatch: {chain['chain_id']}",
        )
        require(
            all(node_id in node_by_id for node_id in chain["node_ids"]),
            f"Dangling node reference: {chain['chain_id']}",
        )
        domain_id = chain["compatibility_domain_id"]
        require(
            domain_id in EXPECTED_DOMAINS
            and all(
                node_by_id[node_id]["compatibility_domain_id"] == domain_id
                for node_id in chain["node_ids"]
            ),
            f"Cross-domain chain: {chain['chain_id']}",
        )
        path_edges: list[dict[str, Any]] = []
        for index, edge_id in enumerate(chain["edge_ids"]):
            require(edge_id in edge_by_id, f"Dangling edge reference: {edge_id}")
            edge = edge_by_id[edge_id]
            require(
                edge["source_node_id"] == chain["node_ids"][index]
                and edge["target_node_id"] == chain["node_ids"][index + 1],
                f"Broken chain path: {chain['chain_id']}",
            )
            require(
                edge["compatibility_domain_id"] == domain_id,
                f"Cross-domain edge in chain: {chain['chain_id']}",
            )
            path_edges.append(edge)
        require(
            chain["edge_types"] == [edge["edge_type"] for edge in path_edges]
            and chain["edge_axes"] == [edge["edit_axis"] for edge in path_edges],
            f"Chain axis metadata drifted: {chain['chain_id']}",
        )
        facts = semantic_facts(chain["node_ids"], chain["edge_axes"], node_by_id)
        for key, value in facts.items():
            require(chain.get(key) is value, f"Incorrect {key}: {chain['chain_id']}")
            if value:
                fact_counts[key] += 1
                if chain["chain_policy"] == "freeform_walk":
                    freeform_fact_counts[key] += 1

        policy = chain["chain_policy"]
        require(policy in CHAIN_POLICIES, f"Unknown chain policy: {policy}")
        if policy == "progressive_shortest":
            require(length in (3, 4), f"Progressive length invalid: {chain['chain_id']}")
            require(
                facts
                == {
                    "is_semantic_shortest": True,
                    "has_repeated_axis": False,
                    "has_consecutive_same_axis": False,
                    "has_rollback": False,
                    "returns_to_start": False,
                },
                f"Progressive facts invalid: {chain['chain_id']}",
            )

        require(
            chain["chain_id"] == stable_id("c", chain_identity_payload(chain)),
            f"Chain ID drifted: {chain['chain_id']}",
        )
        path_key = (tuple(chain["node_ids"]), tuple(chain["edge_ids"]))
        require(path_key not in path_keys, f"Duplicate chain path: {chain['chain_id']}")
        path_keys.add(path_key)
        referenced_nodes.update(chain["node_ids"])
        quota_counts[(domain_id, policy, length)] += 1
        axis_counts.update(chain["edge_types"])

    expected_quota_counts = Counter(
        {
            (domain_id, policy, length): count
            for domain_id, domain in quotas.items()
            for policy, lengths in domain.items()
            for length, count in lengths.items()
            if count
        }
    )
    require(quota_counts == expected_quota_counts, f"Chain quota drifted: {quota_counts}")
    require(len(chains) == EXPECTED_CHAINS, f"Expected {EXPECTED_CHAINS} chains")
    require(
        referenced_nodes == set(node_by_id),
        f"Node coverage failed: {len(referenced_nodes)}/{len(node_by_id)}",
    )
    total_edges = sum(axis_counts.values())
    axis_shares = {
        axis: axis_counts[axis] / total_edges for axis in EDIT_FIELDS
    }
    require(
        all(
            abs(axis_shares[axis] - AXIS_TARGET_SHARES[axis]) <= axis_tolerance
            for axis in EDIT_FIELDS
        ),
        f"Edit-axis target tolerance failed: {axis_shares}",
    )
    return {
        "chain_count": len(chains),
        "length_counts": dict(
            sorted(Counter(chain["edit_length"] for chain in chains).items())
        ),
        "policy_counts": dict(
            sorted(Counter(chain["chain_policy"] for chain in chains).items())
        ),
        "domain_counts": dict(
            sorted(
                Counter(chain["compatibility_domain_id"] for chain in chains).items()
            )
        ),
        "quota_counts": {
            f"{domain}/{policy}/length_{length}": count
            for (domain, policy, length), count in sorted(quota_counts.items())
        },
        "axis_counts": dict(sorted(axis_counts.items())),
        "axis_shares": {
            key: round(value, 6) for key, value in sorted(axis_shares.items())
        },
        "fact_true_counts": dict(sorted(fact_counts.items())),
        "freeform_fact_true_counts": dict(sorted(freeform_fact_counts.items())),
        "referenced_node_count": len(referenced_nodes),
        "unique_path_count": len(path_keys),
        "duplicate_path_count": 0,
    }


def build_chains(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    plan: dict[str, Any],
    source_manifest_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quotas = normalize_chain_quotas(plan)
    seed = int(plan.get("sampler_seed", 20260824))
    axis_tolerance = float(plan.get("axis_share_tolerance", AXIS_SHARE_TOLERANCE))
    require(
        0 <= axis_tolerance <= AXIS_SHARE_TOLERANCE,
        "axis_share_tolerance cannot exceed 0.02",
    )
    rng = random.Random(seed)
    node_by_id = {node["node_id"]: node for node in nodes}
    nodes_by_domain: dict[str, list[str]] = defaultdict(list)
    adjacency: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for node in nodes:
        nodes_by_domain[node["compatibility_domain_id"]].append(node["node_id"])
    for edge in edges:
        adjacency[edge["source_node_id"]][edge["edge_type"]].append(edge)
    for node_id in adjacency:
        for edge_type in adjacency[node_id]:
            adjacency[node_id][edge_type].sort(key=lambda edge: edge["edge_id"])
    for domain_id in nodes_by_domain:
        nodes_by_domain[domain_id].sort()

    total_edges = sum(
        length * count
        for domain in quotas.values()
        for lengths in domain.values()
        for length, count in lengths.items()
    )
    require(total_edges % len(EDIT_FIELDS) == 0, "Axis target is not integral")
    axis_targets = {
        axis: total_edges // len(EDIT_FIELDS) for axis in EDIT_FIELDS
    }
    axis_counts: Counter[str] = Counter()
    uncovered = {
        domain_id: set(node_ids) for domain_id, node_ids in nodes_by_domain.items()
    }

    chains: list[dict[str, Any]] = []
    path_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for policy in CHAIN_POLICIES:
        for domain_id in EXPECTED_DOMAINS:
            for length in (3, 4, 5):
                required = quotas[domain_id][policy][length]
                accepted = 0
                attempts = 0
                max_attempts = max(required * 200, 10000)
                while accepted < required and attempts < max_attempts:
                    attempts += 1
                    if uncovered[domain_id]:
                        start_pool = sorted(uncovered[domain_id])
                    else:
                        start_pool = nodes_by_domain[domain_id]
                    start = start_pool[rng.randrange(len(start_pool))]
                    edge_types = choose_axis_sequence(
                        policy, length, axis_counts, axis_targets, rng
                    )
                    path = build_path_for_axes(start, edge_types, adjacency, rng)
                    chain = make_chain_record(
                        start,
                        path,
                        policy,
                        source_manifest_id,
                        seed,
                        node_by_id,
                    )
                    path_key = (
                        tuple(chain["node_ids"]),
                        tuple(chain["edge_ids"]),
                    )
                    if path_key in path_keys:
                        continue
                    if policy == "progressive_shortest" and not chain[
                        "is_semantic_shortest"
                    ]:
                        continue
                    chains.append(chain)
                    path_keys.add(path_key)
                    axis_counts.update(edge_types)
                    uncovered[domain_id].difference_update(chain["node_ids"])
                    accepted += 1
                require(
                    accepted == required,
                    f"Could not sample {required} unique {domain_id}/{policy}/length-{length} chains",
                )

    chains.sort(key=lambda item: item["chain_id"])
    require(axis_counts == Counter(axis_targets), f"Axis quota drifted: {axis_counts}")
    require(
        all(not remaining for remaining in uncovered.values()),
        f"Sampler left uncovered nodes: {uncovered}",
    )
    report = validate_chain_set(chains, nodes, edges, quotas, axis_tolerance)
    report["sampler_seed"] = seed
    report["sampler_version"] = SAMPLER_VERSION
    report["sampling_spec_version"] = SAMPLING_SPEC_VERSION
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
            "expression_assets": 1,
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
                "expression_id": EXPECTED_EXPRESSION,
                "source_ref": assets[EXPECTED_EXPRESSION]["source_ref"],
                "content_sha256": assets[EXPECTED_EXPRESSION]["content_sha256"],
            }
        ],
        "expression_policy": runtime["expression_policy"],
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
            "render_job_id": stable_id(
                "rj",
                {
                    "node_id": node["node_id"],
                    "render_profile_id": node["render_profile_id"],
                    "attempt_policy": "retry_same_config_v1",
                },
            ),
            "node_id": node["node_id"],
            "status": "pending",
            "attempt": 0,
            "max_attempts": 3,
            "attempt_policy": "retry_same_config_v1",
            "sequence_asset": sequence,
            "temporary_output_uri": f"staging/render/{node['node_id']}",
            "expected_media_uri": node["expected_media_uri"],
            "log_uri": f"logs/render/{node['node_id']}/attempt_000.jsonl",
        }
        for node in nodes
    ]


def build_graph(source_path: Path, output_dir: Path) -> dict[str, Any]:
    source = read_json(source_path)
    require(source.get("schema_version") == SCHEMA_VERSION, "Unsupported source schema")
    require(
        source.get("manifest_type") == SOURCE_MANIFEST_TYPE,
        "Unsupported source manifest type",
    )
    require(
        source.get("sampling_spec_version") == SAMPLING_SPEC_VERSION,
        "Unsupported sampling specification",
    )
    source_manifest_id = require_id(
        source.get("source_manifest_id"), "source_manifest_id"
    )
    require_id(source.get("batch_id"), "batch_id")
    require(source.get("status") == "frozen", "Source manifest status must be frozen")
    require(source.get("production_mode") == "full_pool", "First batch must use full_pool")
    require(source.get("expected_domain_count") == 2, "Expected domain count must be 2")
    require(source.get("expected_nodes") == EXPECTED_NODES, "Expected node count must be 640")
    require(source.get("expected_chains") == EXPECTED_CHAINS, "Expected chain count must be 4000")
    require(source.get("expected_render_jobs") == EXPECTED_NODES, "Expected render-job count must be 640")
    require(
        bool(SHA256.fullmatch(str(source.get("input_manifest_sha256", "")))),
        "input_manifest_sha256 must be a SHA-256 value",
    )
    assets = index_assets(source)
    looks = validate_look_contract(source, assets)
    runtime = validate_runtime_contract(source, assets)
    domains = build_compatibility_domains(looks, runtime)
    nodes = build_nodes(looks, runtime)
    edges = build_edges(nodes)
    domain_report = validate_domain_connectivity(nodes, edges)
    chains, chain_report = build_chains(
        nodes,
        edges,
        source.get("chain_plan") or {},
        source_manifest_id,
    )
    jobs = build_render_jobs(nodes, runtime)
    required_exports = build_required_exports(source, looks, runtime, assets)

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_lock = {
        "schema_version": "asset_lock_v1",
        "batch_id": source["batch_id"],
        "source_manifest_id": source_manifest_id,
        "generated_at": now(),
        "source_manifest": source_path.name,
        "source_manifest_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "assets": [assets[key] for key in sorted(assets)],
        "looks": looks,
        "runtime_contract": runtime,
    }
    write_json(output_dir / "source_manifest.json", source)
    write_json(output_dir / "assets.json", asset_lock)
    write_json(
        output_dir / "compatibility_domains.json",
        {
            "schema_version": SCHEMA_VERSION,
            "source_manifest_id": source_manifest_id,
            "domains": domains,
        },
    )
    write_json(output_dir / "required_exports.json", required_exports)
    write_jsonl(output_dir / "nodes.jsonl", nodes)
    write_jsonl(output_dir / "edges.jsonl", edges)
    write_jsonl(output_dir / "chains.jsonl", chains)
    write_jsonl(output_dir / "render_jobs.jsonl", jobs)

    report = {
        "schema_version": "config_graph_build_report_v1",
        "batch_id": source["batch_id"],
        "source_manifest_id": source_manifest_id,
        "sampling_spec_version": SAMPLING_SPEC_VERSION,
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
        "domain_report": domain_report,
        "chain_report": chain_report,
        "files": {},
    }
    for name in (
        "source_manifest.json",
        "assets.json",
        "compatibility_domains.json",
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
