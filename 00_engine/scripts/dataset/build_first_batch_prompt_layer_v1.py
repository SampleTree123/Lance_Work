"""Build the bilingual text layer for first-batch multi-round video edits.

The config graph remains the semantic authority. This builder never changes
nodes, edges, chains, or rendered media; it derives deterministic model-facing
prompts and materializes one ``video_in + prompt + video_out`` record per turn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROMPT_SCHEMA_VERSION = "multi_round_video_edit_prompt_v1"
TURN_SCHEMA_VERSION = "multi_round_video_edit_turn_v1"
DIALOG_SCHEMA_VERSION = "multi_round_video_edit_dialog_v1"
EXPECTED_CHAINS = 4000
EXPECTED_TURNS = 15000
EDIT_FIELDS = {
    "E1": ("identity_id", "identity"),
    "E2": ("outfit_id", "outfit"),
    "E3": ("action_id", "action"),
    "E7": ("camera_id", "camera"),
}
INTERNAL_ID_PATTERN = re.compile(
    r"(?:[fm]_id\d{2}|[fm]_o\d{2}|act_[a-z0-9_]+|[fm]02_average|"
    r"tokyo_stylized_v1|first_batch_actor_anchor_v1)",
    re.IGNORECASE,
)


class PromptLayerError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PromptLayerError(message)


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromptLayerError(f"Could not read JSON: {path}") from exc
    require(isinstance(value, dict), f"Expected a JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise PromptLayerError(f"Could not read JSONL: {path}") from exc
    require(all(isinstance(value, dict) for value in values), f"Invalid JSONL: {path}")
    return values


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


def validate_catalog(catalog: dict[str, Any]) -> tuple[str, list[str], str]:
    require(
        catalog.get("schema_version") == "video_edit_prompt_catalog_v1",
        "Unsupported prompt catalog schema",
    )
    version = catalog.get("prompt_layer_version")
    require(isinstance(version, str) and version, "Missing prompt_layer_version")
    languages = catalog.get("languages")
    require(
        isinstance(languages, list)
        and len(languages) >= 1
        and len(languages) == len(set(languages)),
        "languages must be a unique non-empty list",
    )
    primary = catalog.get("primary_language")
    require(primary in languages, "primary_language must be present in languages")
    labels = catalog.get("labels")
    templates = catalog.get("templates")
    require(isinstance(labels, dict), "Missing labels")
    require(isinstance(templates, dict), "Missing templates")
    for category in ("identity", "outfit", "action", "camera", "axis"):
        require(isinstance(labels.get(category), dict), f"Missing {category} labels")
    identity_catalog = catalog.get("identity_description_catalog")
    require(isinstance(identity_catalog, dict), "Missing identity_description_catalog")
    require(
        identity_catalog.get("schema_version")
        == "first_batch_identity_description_catalog_v1",
        "Unsupported identity description catalog schema",
    )
    identity_catalog_version = identity_catalog.get("catalog_version")
    require(
        isinstance(identity_catalog_version, str) and identity_catalog_version,
        "Missing identity description catalog version",
    )
    require(
        identity_catalog_version
        == catalog.get("identity_grounding", {}).get("description_catalog_version"),
        "Identity grounding and description catalog versions disagree",
    )
    identities = identity_catalog.get("identities")
    require(isinstance(identities, dict) and identities, "Missing identity descriptions")
    require(
        set(identities) == set(labels["identity"]),
        "Identity labels and descriptions must cover the same IDs",
    )
    prompt_targets: dict[str, set[str]] = {language: set() for language in languages}
    for identity_id, identity in identities.items():
        require(isinstance(identity, dict), f"Invalid identity description: {identity_id}")
        require(identity.get("sex") in {"female", "male"}, f"Invalid sex: {identity_id}")
        reference_images = identity.get("reference_images")
        require(
            isinstance(reference_images, list)
            and len(reference_images) == 3
            and all(isinstance(uri, str) and uri for uri in reference_images),
            f"Identity requires front and two 45-degree references: {identity_id}",
        )
        attributes = identity.get("visible_attributes")
        require(isinstance(attributes, dict) and attributes, f"Missing visible attributes: {identity_id}")
        for field in ("prompt_target", "full_description"):
            values = identity.get(field)
            require(isinstance(values, dict), f"Missing {field}: {identity_id}")
            for language in languages:
                value = values.get(language)
                require(
                    isinstance(value, str) and value.strip(),
                    f"Missing {field}.{language}: {identity_id}",
                )
        for language in languages:
            target = identity["prompt_target"][language].strip()
            require(
                labels["identity"][identity_id].get(language) == target,
                f"Identity prompt label drift: {identity_id}/{language}",
            )
            prompt_targets[language].add(target)
    for language in languages:
        require(
            len(prompt_targets[language]) == len(identities),
            f"Identity prompt targets must be unique in {language}",
        )
    for edge_type in EDIT_FIELDS:
        direct = templates.get(edge_type, {}).get("direct")
        require(isinstance(direct, dict), f"Missing direct templates for {edge_type}")
        for language in languages:
            require(
                isinstance(direct.get(language), list) and direct[language],
                f"Missing {language} direct templates for {edge_type}",
            )
    history = templates.get("history")
    require(isinstance(history, dict), "Missing history templates")
    for mode in ("restore_initial", "restore_round"):
        for language in languages:
            require(
                isinstance(history.get(mode, {}).get(language), list)
                and history[mode][language],
                f"Missing {language} templates for {mode}",
            )
    return version, list(languages), str(primary)


def deterministic_choice(
    values: list[str],
    *,
    version: str,
    chain_id: str,
    round_index: int,
    mode: str,
    language: str,
) -> tuple[str, int]:
    payload = f"{version}|{chain_id}|{round_index}|{mode}|{language}".encode("utf-8")
    index = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % len(values)
    return values[index], index


def get_label(
    catalog: dict[str, Any], category: str, value: str, language: str
) -> str:
    labels = catalog["labels"].get(category, {})
    require(value in labels, f"Missing {category} prompt label: {value}")
    label = labels[value].get(language)
    require(isinstance(label, str) and label.strip(), f"Missing {language} label for {value}")
    return label.strip()


def history_reference(target_node_id: str, prior_node_ids: list[str]) -> dict[str, Any]:
    if target_node_id not in prior_node_ids:
        return {"kind": "new_target", "round": None}
    prior_index = max(
        index for index, node_id in enumerate(prior_node_ids) if node_id == target_node_id
    )
    if prior_index == 0:
        return {"kind": "initial_state", "round": 0}
    return {"kind": "prior_round", "round": prior_index}


def render_prompt_texts(
    *,
    catalog: dict[str, Any],
    version: str,
    languages: list[str],
    chain_id: str,
    round_index: int,
    edge: dict[str, Any],
    target_config: dict[str, Any],
    reference: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    edge_type = edge["edge_type"]
    field, category = EDIT_FIELDS[edge_type]
    dialogue: dict[str, str] = {}
    standalone: dict[str, str] = {}
    template_ids: dict[str, str] = {}
    for language in languages:
        target = get_label(catalog, category, target_config[field], language)
        axis = get_label(catalog, "axis", field, language)

        direct_values = catalog["templates"][edge_type]["direct"][language]
        direct_template, direct_index = deterministic_choice(
            direct_values,
            version=version,
            chain_id=chain_id,
            round_index=round_index,
            mode="standalone_direct",
            language=language,
        )
        standalone[language] = direct_template.format(
            target=target, axis=axis, round=reference.get("round")
        )
        standalone_template_id = f"{edge_type.lower()}_direct_{language}_{direct_index + 1}"

        if reference["kind"] == "new_target":
            dialogue_values = direct_values
            dialogue_mode = "dialogue_direct"
            dialogue_category = f"{edge_type.lower()}_direct"
        elif reference["kind"] == "initial_state":
            dialogue_values = catalog["templates"]["history"]["restore_initial"][language]
            dialogue_mode = "dialogue_restore_initial"
            dialogue_category = "restore_initial"
        else:
            dialogue_values = catalog["templates"]["history"]["restore_round"][language]
            dialogue_mode = "dialogue_restore_round"
            dialogue_category = "restore_round"
        dialogue_template, dialogue_index = deterministic_choice(
            dialogue_values,
            version=version,
            chain_id=chain_id,
            round_index=round_index,
            mode=dialogue_mode,
            language=language,
        )
        dialogue[language] = dialogue_template.format(
            target=target, axis=axis, round=reference.get("round")
        )
        template_ids[f"dialogue.{language}"] = (
            f"{dialogue_category}_{language}_{dialogue_index + 1}"
        )
        template_ids[f"standalone.{language}"] = standalone_template_id
    return dialogue, standalone, template_ids


def validate_model_facing_text(text: str, label: str) -> None:
    require(text == text.strip(), f"Prompt has surrounding whitespace: {label}")
    require(bool(text), f"Empty prompt: {label}")
    require("{" not in text and "}" not in text, f"Unresolved placeholder: {label}")
    require(
        INTERNAL_ID_PATTERN.search(text) is None,
        f"Internal asset ID leaked into model-facing text: {label}: {text}",
    )


def build_prompt_review(
    dialogs: list[dict[str, Any]], turns: list[dict[str, Any]]
) -> tuple[dict[str, Any], str]:
    turn_by_id = {turn["turn_id"]: turn for turn in turns}
    ordered = sorted(dialogs, key=lambda item: item["dialog_id"])
    selectors = (
        ("progressive_shortest", lambda item: item["chain_policy"] == "progressive_shortest"),
        ("rollback", lambda item: item["semantic_facts"]["has_rollback"]),
        ("return_to_start", lambda item: item["semantic_facts"]["returns_to_start"]),
    )
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for reason, predicate in selectors:
        match = next(
            (item for item in ordered if item["dialog_id"] not in selected_ids and predicate(item)),
            None,
        )
        if match is None:
            continue
        selected_ids.add(match["dialog_id"])
        selected.append({"selection_reason": reason, "dialog": match})

    review = {
        "schema_version": "multi_round_video_edit_prompt_review_v1",
        "selection_count": len(selected),
        "selection_policy": "deterministic progressive, rollback, and return-to-start dialogs",
        "dialogs": [],
    }
    lines = [
        "# First-Batch Prompt Review",
        "",
        "This file reviews model-facing text only. Internal asset IDs shown in metadata are not part of the prompts.",
        "",
    ]
    for item in selected:
        dialog = item["dialog"]
        review_turns = [turn_by_id[turn_id] for turn_id in dialog["turn_ids"]]
        review["dialogs"].append(
            {
                "selection_reason": item["selection_reason"],
                "dialog_id": dialog["dialog_id"],
                "chain_policy": dialog["chain_policy"],
                "semantic_facts": dialog["semantic_facts"],
                "turns": review_turns,
            }
        )
        lines.extend(
            [
                f"## {item['selection_reason']}: `{dialog['dialog_id']}`",
                "",
                f"- Policy: `{dialog['chain_policy']}`",
                f"- Turns: `{dialog['edit_length']}`",
                "",
            ]
        )
        for turn in review_turns:
            lines.extend(
                [
                    f"### Round {turn['round']} / {turn['edge_type']}",
                    "",
                    f"- 中文对话指令：{turn['prompt']['dialogue']['zh-CN']}",
                    f"- English dialogue prompt: {turn['prompt']['dialogue']['en']}",
                    f"- 中文独立指令：{turn['prompt']['standalone']['zh-CN']}",
                    f"- English standalone prompt: {turn['prompt']['standalone']['en']}",
                    f"- History reference: `{turn['history_reference']['kind']}`",
                    "",
                ]
            )
    return review, "\n".join(lines).rstrip() + "\n"


def build_identity_description_review(catalog: dict[str, Any]) -> str:
    description_catalog = catalog["identity_description_catalog"]
    canonical_templates = {
        language: catalog["templates"]["E1"]["direct"][language][0]
        for language in ("zh-CN", "en")
    }
    lines = [
        "# First-Batch Identity Description Review",
        "",
        "This is a human-review artifact, not direct model input. Internal identity IDs are shown only to map descriptions to frozen reference images.",
        "",
        f"- Catalog version: `{description_catalog['catalog_version']}`",
        f"- Review status: `{description_catalog['description_policy']['review_status']}`",
        "- Policy: describe visible appearance only; do not infer ethnicity, nationality, personality, occupation, or health.",
        "",
    ]
    for identity_id, identity in sorted(description_catalog["identities"].items()):
        lines.extend(
            [
                f"## `{identity_id}`",
                "",
                f"- 中文目标描述：{identity['prompt_target']['zh-CN']}",
                f"- English target description: {identity['prompt_target']['en']}",
                f"- 中文完整描述：{identity['full_description']['zh-CN']}",
                f"- English full description: {identity['full_description']['en']}",
                "",
                "### Canonical E1 instructions",
                "",
                "- 中文："
                + canonical_templates["zh-CN"].format(
                    target=identity["prompt_target"]["zh-CN"]
                ),
                "- English: "
                + canonical_templates["en"].format(
                    target=identity["prompt_target"]["en"]
                ),
                "",
                "### Reference images",
                "",
            ]
        )
        lines.extend(f"- `{uri}`" for uri in identity["reference_images"])
        lines.extend(["", "### Visible attributes", ""])
        for field, values in identity["visible_attributes"].items():
            lines.append(
                f"- `{field}`: {values['zh-CN']} / {values['en']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_prompt_layer(
    graph_dir: Path,
    catalog_path: Path,
    output_dir: Path,
    *,
    strict_first_batch: bool = True,
) -> dict[str, Any]:
    graph_dir = graph_dir.resolve()
    catalog_path = catalog_path.resolve()
    output_dir = output_dir.resolve()
    catalog = read_json(catalog_path)
    version, languages, primary_language = validate_catalog(catalog)

    source_manifest = read_json(graph_dir / "source_manifest.json")
    nodes = read_jsonl(graph_dir / "nodes.jsonl")
    edges = read_jsonl(graph_dir / "edges.jsonl")
    chains = read_jsonl(graph_dir / "chains.jsonl")
    source_manifest_id = source_manifest.get("source_manifest_id")
    require(isinstance(source_manifest_id, str) and source_manifest_id, "Missing source_manifest_id")

    node_by_id = {node["node_id"]: node for node in nodes}
    edge_by_id = {edge["edge_id"]: edge for edge in edges}
    require(len(node_by_id) == len(nodes), "Duplicate node IDs")
    require(len(edge_by_id) == len(edges), "Duplicate edge IDs")

    turns: list[dict[str, Any]] = []
    dialogs: list[dict[str, Any]] = []
    axis_counts: Counter[str] = Counter()
    history_counts: Counter[str] = Counter()
    template_counts: Counter[str] = Counter()
    primary_texts: set[str] = set()

    for chain in chains:
        chain_id = chain.get("chain_id")
        require(isinstance(chain_id, str) and chain_id, "Chain is missing chain_id")
        node_ids = chain.get("node_ids")
        edge_ids = chain.get("edge_ids")
        require(
            isinstance(node_ids, list)
            and isinstance(edge_ids, list)
            and len(node_ids) == len(edge_ids) + 1,
            f"Invalid chain cardinality: {chain_id}",
        )
        turn_ids: list[str] = []
        dialog_turns: list[dict[str, Any]] = []
        for round_index, edge_id in enumerate(edge_ids, 1):
            require(edge_id in edge_by_id, f"Unknown edge {edge_id} in {chain_id}")
            source_node_id = node_ids[round_index - 1]
            target_node_id = node_ids[round_index]
            require(source_node_id in node_by_id, f"Unknown source node in {chain_id}")
            require(target_node_id in node_by_id, f"Unknown target node in {chain_id}")
            edge = edge_by_id[edge_id]
            require(
                edge["source_node_id"] == source_node_id
                and edge["target_node_id"] == target_node_id,
                f"Edge endpoints do not match chain path: {chain_id}/{round_index}",
            )
            edge_type = edge.get("edge_type")
            require(edge_type in EDIT_FIELDS, f"Unsupported edge type: {edge_type}")
            field, _ = EDIT_FIELDS[edge_type]
            source_node = node_by_id[source_node_id]
            target_node = node_by_id[target_node_id]
            differences = sorted(
                key
                for key in source_node["config"]
                if source_node["config"][key] != target_node["config"][key]
            )
            require(
                differences == [field],
                f"Prompt turn is not atomic: {chain_id}/{round_index}: {differences}",
            )
            reference = history_reference(target_node_id, node_ids[:round_index])
            dialogue_text, standalone_text, template_ids = render_prompt_texts(
                catalog=catalog,
                version=version,
                languages=languages,
                chain_id=chain_id,
                round_index=round_index,
                edge=edge,
                target_config=target_node["config"],
                reference=reference,
            )
            for mode, texts in (
                ("dialogue", dialogue_text),
                ("standalone", standalone_text),
            ):
                require(set(texts) == set(languages), f"Language coverage drift: {chain_id}")
                for language, text in texts.items():
                    validate_model_facing_text(
                        text, f"{chain_id}/{round_index}/{mode}/{language}"
                    )
            prompt_id = stable_id(
                "p",
                {
                    "prompt_layer_version": version,
                    "chain_id": chain_id,
                    "round": round_index,
                    "edge_id": edge_id,
                    "dialogue": dialogue_text,
                    "standalone": standalone_text,
                },
            )
            turn_id = stable_id(
                "t",
                {
                    "prompt_layer_version": version,
                    "chain_id": chain_id,
                    "round": round_index,
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "prompt_id": prompt_id,
                },
            )
            target_value = target_node["config"][field]
            grounding_mode = (
                catalog["identity_grounding"]["mode"]
                if edge_type == "E1"
                else "text_semantic_label"
            )
            target_specificity = (
                catalog["identity_grounding"]["target_specificity"]
                if edge_type == "E1"
                else "asset_specific"
            )
            identity_description = None
            if edge_type == "E1":
                identity_description = catalog["identity_description_catalog"][
                    "identities"
                ][target_value]
            preservation_fields = sorted(
                {edit_field for edit_field, _ in EDIT_FIELDS.values()} - {field}
            )
            turn = {
                "schema_version": TURN_SCHEMA_VERSION,
                "prompt_schema_version": PROMPT_SCHEMA_VERSION,
                "prompt_layer_version": version,
                "turn_id": turn_id,
                "prompt_id": prompt_id,
                "chain_id": chain_id,
                "round": round_index,
                "compatibility_domain_id": chain["compatibility_domain_id"],
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "edge_id": edge_id,
                "edge_type": edge_type,
                "edit_axis": field,
                "before_value": edge["before_value"],
                "after_value": edge["after_value"],
                "video_in_uri": source_node["expected_media_uri"],
                "video_out_uri": target_node["expected_media_uri"],
                "history_turn_ids": list(turn_ids),
                "history_reference": reference,
                "prompt": {
                    "primary_language": primary_language,
                    "dialogue": dialogue_text,
                    "standalone": standalone_text,
                    "template_ids": template_ids,
                },
                "grounding": {
                    "mode": grounding_mode,
                    "target_specificity": target_specificity,
                    "target_asset_id": target_value,
                    "paired_target_node_id": target_node_id,
                    **(
                        {
                            "description_catalog_version": catalog[
                                "identity_description_catalog"
                            ]["catalog_version"],
                            "reference_image_uris": identity_description[
                                "reference_images"
                            ],
                        }
                        if identity_description is not None
                        else {}
                    ),
                },
                "atomic_edit_contract": {
                    "changed_fields": [f"config.{field}"],
                    "preserved_edit_axes": preservation_fields,
                    "fixed_fields": [
                        "expression_id",
                        "scene_id",
                        "lighting_id",
                        "anchor_id",
                        "frame_start",
                        "duration_frames",
                        "fps",
                        "resolution",
                    ],
                },
                "quality_flags": {
                    "atomic": True,
                    "language_complete": True,
                    "contains_internal_id": False,
                    "paired_media_required": True,
                },
            }
            turns.append(turn)
            turn_ids.append(turn_id)
            dialog_turns.append(
                {
                    "turn_id": turn_id,
                    "round": round_index,
                    "video_in_uri": turn["video_in_uri"],
                    "user_prompt": dialogue_text,
                    "standalone_prompt": standalone_text,
                    "video_out_uri": turn["video_out_uri"],
                }
            )
            axis_counts[edge_type] += 1
            history_counts[reference["kind"]] += 1
            template_counts.update(template_ids.values())
            primary_texts.add(dialogue_text[primary_language])

        dialogs.append(
            {
                "schema_version": DIALOG_SCHEMA_VERSION,
                "prompt_layer_version": version,
                "dialog_id": chain_id,
                "chain_id": chain_id,
                "chain_policy": chain["chain_policy"],
                "compatibility_domain_id": chain["compatibility_domain_id"],
                "edit_length": chain["edit_length"],
                "initial_node_id": node_ids[0],
                "initial_video_uri": node_by_id[node_ids[0]]["expected_media_uri"],
                "final_node_id": node_ids[-1],
                "final_video_uri": node_by_id[node_ids[-1]]["expected_media_uri"],
                "turn_ids": turn_ids,
                "turns": dialog_turns,
                "semantic_facts": {
                    key: chain[key]
                    for key in (
                        "is_semantic_shortest",
                        "has_repeated_axis",
                        "has_consecutive_same_axis",
                        "has_rollback",
                        "returns_to_start",
                    )
                },
            }
        )

    if strict_first_batch:
        require(len(chains) == EXPECTED_CHAINS, "First batch requires exactly 4,000 dialogs")
        require(len(turns) == EXPECTED_TURNS, "First batch requires exactly 15,000 turns")
        require(axis_counts == Counter({key: 3750 for key in EDIT_FIELDS}), "Edit-axis prompt counts drifted")
    require(len({turn["turn_id"] for turn in turns}) == len(turns), "Duplicate turn IDs")
    require(len({turn["prompt_id"] for turn in turns}) == len(turns), "Duplicate prompt IDs")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "prompt_catalog.json", catalog)
    write_json(
        output_dir / "identity_descriptions.json",
        catalog["identity_description_catalog"],
    )
    (output_dir / "IDENTITY_DESCRIPTION_REVIEW.md").write_text(
        build_identity_description_review(catalog),
        encoding="utf-8",
        newline="\n",
    )
    write_jsonl(output_dir / "turns.jsonl", turns)
    write_jsonl(output_dir / "dialogs.jsonl", dialogs)
    prompt_review, prompt_review_markdown = build_prompt_review(dialogs, turns)
    write_json(output_dir / "prompt_review.json", prompt_review)
    (output_dir / "PROMPT_REVIEW.md").write_text(
        prompt_review_markdown, encoding="utf-8", newline="\n"
    )

    report = {
        "schema_version": "multi_round_video_edit_prompt_report_v1",
        "status": "passed",
        "generated_at": now(),
        "source_manifest_id": source_manifest_id,
        "prompt_layer_version": version,
        "primary_language": primary_language,
        "languages": languages,
        "counts": {
            "dialogs": len(dialogs),
            "turns": len(turns),
            "unique_prompt_ids": len({turn["prompt_id"] for turn in turns}),
            "unique_primary_dialogue_texts": len(primary_texts),
            "identity_descriptions": len(
                catalog["identity_description_catalog"]["identities"]
            ),
        },
        "axis_counts": dict(sorted(axis_counts.items())),
        "history_reference_counts": dict(sorted(history_counts.items())),
        "template_usage_counts": dict(sorted(template_counts.items())),
        "quality_gates": {
            "all_turns_atomic": True,
            "all_languages_present": True,
            "internal_id_leaks": 0,
            "all_video_pairs_present_as_uris": True,
            "identity_grounding_mode": catalog["identity_grounding"]["mode"],
            "all_identity_descriptions_present": True,
            "identity_prompt_targets_unique": True,
        },
    }
    write_json(output_dir / "prompt_report.json", report)

    manifest = {
        "schema_version": "multi_round_video_edit_prompt_manifest_v1",
        "status": "passed",
        "generated_at": now(),
        "source_manifest_id": source_manifest_id,
        "prompt_layer_version": version,
        "primary_language": primary_language,
        "languages": languages,
        "graph_source": {
            "graph_dir": graph_dir.name,
            "source_manifest_sha256": sha256_file(graph_dir / "source_manifest.json"),
            "nodes_sha256": sha256_file(graph_dir / "nodes.jsonl"),
            "edges_sha256": sha256_file(graph_dir / "edges.jsonl"),
            "chains_sha256": sha256_file(graph_dir / "chains.jsonl"),
        },
        "catalog_source_sha256": sha256_file(catalog_path),
        "counts": report["counts"],
        "files": {},
        "known_limitations": [
            "Identity descriptions are human-authored from frozen front and 45-degree CC reference renders and remain pending explicit user visual approval.",
            "Visible text descriptions improve semantic grounding, while the paired target video remains the pixel-level authority.",
            "Hair and facial hair are treated as part of the current identity presentation; no ethnicity, nationality, personality, occupation, or health is inferred.",
        ],
    }
    for name in (
        "prompt_catalog.json",
        "identity_descriptions.json",
        "IDENTITY_DESCRIPTION_REVIEW.md",
        "turns.jsonl",
        "dialogs.jsonl",
        "prompt_report.json",
        "prompt_review.json",
        "PROMPT_REVIEW.md",
    ):
        path = output_dir / name
        manifest["files"][name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    write_json(output_dir / "prompt_manifest.json", manifest)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).with_name("prompt_catalog_first_batch_v1.json"),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--allow-nonproduction-counts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_prompt_layer(
            args.graph_dir,
            args.catalog,
            args.output_dir,
            strict_first_batch=not args.allow_nonproduction_counts,
        )
    except PromptLayerError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
