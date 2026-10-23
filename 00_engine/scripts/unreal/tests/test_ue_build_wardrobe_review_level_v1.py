from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock


SCRIPT = Path(__file__).resolve().parents[1] / "ue_build_wardrobe_review_level_v1.py"
sys.modules.setdefault("unreal", types.ModuleType("unreal"))
SPEC = importlib.util.spec_from_file_location("wardrobe_review_under_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReloadInspectionTests(unittest.TestCase):
    def setUp(self):
        self.body = Mock()
        self.body.get_skeletal_mesh_asset.return_value = "/Body"
        self.body.get_editor_property.return_value.get_editor_property.return_value = "/Motion"
        self.actor = Mock()
        self.actor.get_path_name.return_value = "/Review/Actor"
        self.properties = {
            "visible": True, "hidden_in_game": False,
            "leader_pose_component": self.body,
        }
        self.follower = Mock()
        self.follower.get_name.return_value = "UpperInner"
        self.follower.get_skeletal_mesh_asset.return_value = "/Top"
        self.follower.get_editor_property.side_effect = self.properties.__getitem__
        self.follower.get_collision_enabled.return_value = "CollisionEnabled.NO_COLLISION"
        self.runtime = Mock()
        self.runtime.actor_components.return_value = (self.body, [self.follower])
        self.runtime.object_path.side_effect = lambda obj: obj
        self.bodyfit = {"bodyfit_id": "F02_Average", "body_mesh_path": "/Body"}
        self.variant = {"assignments": [{"target_component": "UpperInner", "mesh_path": "/Top"}]}

    def inspect(self):
        return MODULE.inspect_actor(self.runtime, self.actor, self.bodyfit, self.variant)

    def test_valid_saved_assignment(self):
        result = self.inspect()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["animation"], "/Motion")

    def test_missing_saved_mesh(self):
        self.follower.get_skeletal_mesh_asset.return_value = None
        self.assertIn("UpperInner: persisted mesh differs", self.inspect()["errors"])

    def test_disabled_slot_cannot_retain_mesh(self):
        self.variant["assignments"] = []
        self.properties.update(visible=False, hidden_in_game=True)
        self.assertIn("UpperInner: persisted mesh differs", self.inspect()["errors"])

    def test_visibility_must_match_assignment(self):
        self.properties["hidden_in_game"] = True
        self.assertIn("UpperInner: persisted visibility differs", self.inspect()["errors"])

    def test_leader_must_be_body(self):
        self.properties["leader_pose_component"] = None
        self.assertIn("UpperInner: leader or collision differs", self.inspect()["errors"])

    def test_body_identity_must_not_change(self):
        self.body.get_skeletal_mesh_asset.return_value = "/OtherBody"
        self.assertIn("Body identity differs after reload", self.inspect()["errors"])

    def test_no_collision_required(self):
        self.follower.get_collision_enabled.return_value = "CollisionEnabled.QUERY_AND_PHYSICS"
        self.assertIn("UpperInner: leader or collision differs", self.inspect()["errors"])


if __name__ == "__main__":
    unittest.main()
