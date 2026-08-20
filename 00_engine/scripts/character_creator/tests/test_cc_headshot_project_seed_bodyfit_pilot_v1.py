import ast
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_module(
    "cc_build_headshot_project_seed_bodyfit_pilot_v1",
    "cc_build_headshot_project_seed_bodyfit_pilot_v1.py",
)


class HeadshotProjectSeedBodyFitPilotTests(unittest.TestCase):
    def test_pilot_is_minimal_sex_matched_and_hash_locked(self):
        library = BUILDER.build_library()
        self.assertEqual(
            "headshot_project_seed_bodyfit_pilot",
            library["diagnostic_mode"],
        )
        self.assertTrue(library["save_character_projects"])
        self.assertEqual(2, library["pilot_policy"]["case_count"])
        self.assertFalse(library["pilot_policy"]["production_approved"])
        self.assertEqual(2, len(library["presets"]))

        by_sex = {item["sex"]: item for item in library["presets"]}
        self.assertEqual({"female", "male"}, set(by_sex))
        self.assertEqual("F02_Average", by_sex["female"]["bodyfit_id"])
        self.assertEqual("M02_Average", by_sex["male"]["bodyfit_id"])
        for preset in library["presets"]:
            self.assertEqual("H00_BASELINE", preset["head_profile_id"])
            self.assertEqual(
                "headshot_project_seed_then_bodyfit_v1",
                preset["project_seed_assembly"]["pipeline"],
            )
            self.assertEqual(
                7,
                len(preset["project_seed_assembly"]["head_shape_targets"]),
            )
            self.assertEqual(
                [-600.0, 8.0, 75.0],
                preset["full_body_position"],
            )
            for key in (
                "source_project",
                "bodyfit_reference_project",
                "source_facial_profile",
                "prototype_manifest",
            ):
                record = preset[key]
                self.assertTrue(pathlib.Path(record["path"]).is_file())
                self.assertEqual(64, len(record["sha256"]))

    def test_average_bodyfit_proportions_are_explicit(self):
        library = BUILDER.build_library()
        by_sex = {item["sex"]: item for item in library["presets"]}
        female_targets = by_sex["female"]["bodyfit_proportion_adjustment"][
            "targets"
        ]
        male_targets = by_sex["male"]["bodyfit_proportion_adjustment"][
            "targets"
        ]
        self.assertEqual(
            ["head_scale", "neck_height"],
            [item["role"] for item in female_targets],
        )
        self.assertEqual(0.1, female_targets[0]["target"])
        self.assertEqual(0.0, female_targets[1]["target"])
        self.assertEqual("implicit_neutral", female_targets[1]["selection_status"])
        self.assertEqual(
            ["head_scale", "neck_height"],
            [item["role"] for item in male_targets],
        )
        self.assertEqual(0.0, male_targets[0]["target"])
        self.assertEqual(0.0, male_targets[1]["target"])
        self.assertEqual("implicit_neutral", male_targets[1]["selection_status"])

    def test_executor_initializes_subset_mode_in_the_pilot_scope(self):
        source = (ROOT / "cc_validate_body_reconstruction.py").read_text(
            encoding="utf-8"
        )
        module = ast.parse(source)
        functions = {
            node.name: node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
        }
        pilot = functions["run_headshot_project_seed_bodyfit_pilot"]
        probe = functions["probe_direct_skin_age_matrix"]
        pilot_assignments = {
            target.id
            for node in ast.walk(pilot)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        probe_assignments = {
            target.id
            for node in ast.walk(probe)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertIn("selection_mode", pilot_assignments)
        self.assertNotIn("selection_mode", probe_assignments)
        selected_assignment = next(
            node
            for node in ast.walk(pilot)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "selected_ids"
                for target in node.targets
            )
        )
        self.assertFalse(
            any(isinstance(node, ast.BoolOp) for node in ast.walk(selected_assignment))
        )


if __name__ == "__main__":
    unittest.main()
