import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "build_first_batch_chain_render_matrix_v1.py"
SPEC = importlib.util.spec_from_file_location("chain_render_matrix", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture(root):
    graph = root / "graph"
    review = graph / "review_10"
    source_id = "fixture_source"
    cameras = ("near", "far", "high", "side")
    assets = [
        {
            "asset_id": camera_id,
            "asset_type": "camera",
            "constraints": {"section_index": index},
        }
        for index, camera_id in enumerate(cameras)
    ]
    for sex, action_id, source_action_id in (
        ("female", "act_f01", "ACT_F01"),
        ("male", "act_m01", "ACT_M01"),
    ):
        assets.append(
            {
                "asset_id": action_id,
                "asset_type": "action",
                "constraints": {
                    "source_action_id": source_action_id,
                    "happy_composite_animation": f"/Game/Fixture/{sex}/Happy",
                },
            }
        )
    looks = [
        {
            "look_id": "f_look",
            "source_look_id": "F_LOOK",
            "bodyfit_id": "f02_average",
            "identity_id": "f_id01",
            "outfit_id": "f_o01",
            "character_blueprint": "/Game/Fixture/F/BP_F",
            "character_blueprint_class": "/Game/Fixture/F/BP_F.BP_F_C",
        },
        {
            "look_id": "m_look",
            "source_look_id": "M_LOOK",
            "bodyfit_id": "m02_average",
            "identity_id": "m_id01",
            "outfit_id": "m_o01",
            "character_blueprint": "/Game/Fixture/M/BP_M",
            "character_blueprint_class": "/Game/Fixture/M/BP_M.BP_M_C",
        },
    ]
    write_json(
        graph / "source_manifest.json",
        {
            "source_manifest_id": source_id,
            "sampling_spec_version": "fixture_sampling",
            "assets": assets,
            "looks": looks,
        },
    )
    write_json(
        graph / "build_report.json",
        {"status": "passed", "source_manifest_id": source_id},
    )

    female_ids = [f"f{index}" for index in range(5)]
    male_ids = [f"m{index}" for index in range(4)]
    candidates = [
        {
            "chain_id": "chain_f",
            "selection_reason": "female_progressive",
            "node_ids": female_ids,
        },
        {
            "chain_id": "chain_m",
            "selection_reason": "male_return",
            "node_ids": [male_ids[0], male_ids[1], male_ids[2], male_ids[1], male_ids[0], male_ids[3]],
        },
    ]
    write_json(
        review / "ue_render_candidates.json",
        {
            "source_manifest_id": source_id,
            "candidates": candidates,
        },
    )
    nodes = []
    for sex, node_ids, look_id, action_id, domain in (
        ("female", female_ids, "f_look", "act_f01", "female_v1"),
        ("male", male_ids, "m_look", "act_m01", "male_v1"),
    ):
        for index, node_id in enumerate(node_ids):
            nodes.append(
                {
                    "node_id": node_id,
                    "look_id": look_id,
                    "compatibility_domain_id": domain,
                    "expected_media_uri": f"media/{node_id}.mp4",
                    "config": {
                        "sex": sex,
                        "identity_id": f"{sex[0]}_id01",
                        "outfit_id": f"{sex[0]}_o01",
                        "action_id": action_id,
                        "camera_id": cameras[index % 4],
                        "expression_id": "happy",
                    },
                }
            )
    (graph / "nodes.jsonl").write_text(
        "\n".join(json.dumps(node) for node in nodes) + "\n",
        encoding="utf-8",
    )
    base = root / "base.json"
    write_json(
        base,
        {
            "unreal": {
                "source_sequence_package": "/Game/Fixture/SourceSequence",
                "workspace_sequence_package": "/Game/Fixture/WorkspaceSequence",
            },
            "render": {
                "resolution": [2560, 1440],
                "fps": 30,
                "frame_count": 150,
            },
        },
    )
    return graph, base


class ChainRenderMatrixTests(unittest.TestCase):
    def test_builds_two_chain_unique_node_matrix(self):
        with tempfile.TemporaryDirectory() as raw:
            graph, base = fixture(Path(raw))
            matrix = SUBJECT.build_chain_render_matrix(graph, base)
            self.assertEqual(2, matrix["coverage"]["chain_count"])
            self.assertEqual(11, matrix["coverage"]["path_node_reference_count"])
            self.assertEqual(9, matrix["coverage"]["unique_node_count"])
            self.assertEqual(9, len(matrix["samples"]))
            self.assertTrue(all(matrix["coverage"]["checks"].values()))
            self.assertEqual(
                {0, 150, 300, 450},
                {sample["start_frame_inclusive"] for sample in matrix["samples"]},
            )
            self.assertEqual(
                {"ACT_F01", "ACT_M01"},
                {sample["action_id"] for sample in matrix["samples"]},
            )

    def test_rejects_non_happy_node(self):
        with tempfile.TemporaryDirectory() as raw:
            graph, base = fixture(Path(raw))
            nodes_path = graph / "nodes.jsonl"
            nodes = [json.loads(line) for line in nodes_path.read_text().splitlines()]
            nodes[0]["config"]["expression_id"] = "sad"
            nodes_path.write_text(
                "\n".join(json.dumps(node) for node in nodes) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(SUBJECT.ChainRenderMatrixError):
                SUBJECT.build_chain_render_matrix(graph, base)


if __name__ == "__main__":
    unittest.main()
