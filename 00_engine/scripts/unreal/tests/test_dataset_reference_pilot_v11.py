"""Offline fake checks for reference semantics and owned-copy ordering."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

PATH = Path(__file__).resolve().parents[1] / "ue_dataset_reference_pilot_v11.py"
SPEC = importlib.util.spec_from_file_location("tested_reference_pilot_v11", PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Key:
    def __init__(self, value, frame=0): self.value, self.frame = value, frame
    def get_time(self, **kw): return NS(frame_number=NS(value=self.frame), sub_frame=0.0)
    def get_value(self): return self.value


class Channel:
    def __init__(self, name, value): self.name, self.value = name, value
    def get_editor_property(self, key): return self.name
    def get_keys(self): return [Key(self.value), Key(999, 1)]


class Transform:
    def __init__(self, channels): self.channels = channels
    def get_sections(self): return [NS(get_all_channels=lambda: self.channels)]


class Float(Transform): pass


class Tests(unittest.TestCase):
    def test_source_camera_reads_frame_zero_actual_keys(self):
        channels = [Channel(n, v) for n, v in zip(
            ["Location.X", "Location.Y", "Location.Z", "Rotation.X", "Rotation.Y", "Rotation.Z", "Scale.X", "Scale.Y", "Scale.Z"],
            [10, 20, 30, 3, 1, 2, 1, 1, 1])]
        tracks = [Transform(channels), Float([Channel("FieldOfView", 45)])]
        binding = NS(get_tracks=lambda: tracks, get_display_name=lambda: "Camera pilot baked trajectory")
        sequence = NS(get_display_rate=lambda: NS(numerator=30, denominator=1), get_playback_start=lambda: 0,
                      get_bindings=lambda: [binding])
        u = NS(MovieScene3DTransformTrack=Transform, MovieSceneFloatTrack=Float,
               MovieSceneTimeUnit=NS(DISPLAY_RATE=0))
        # Float is a distinct UE class; mimic its separate type for this fake.
        u.MovieScene3DTransformTrack = type("OnlyTransform", (), {})
        tracks[0].__class__ = u.MovieScene3DTransformTrack
        tracks[0].get_sections = lambda: [NS(get_all_channels=lambda: channels)]
        prepared = {"position": [10, 20, 30], "rotation_pitch_yaw_roll": [1, 2, 3], "horizontal_fov_degrees": 45}
        self.assertEqual(M.first_camera(u, sequence, prepared)["rotation_pitch_yaw_roll"], [1, 2, 3])
        prepared["position"][0] = 11
        with self.assertRaisesRegex(ValueError, "differs"):
            M.first_camera(u, sequence, prepared)

    def test_map_copy_loads_source_then_saves_then_loads_owned_copy(self):
        calls, current = [], {"path": "/Game/Initial.Initial"}
        world = NS(get_path_name=lambda: current["path"])
        def load(path):
            calls.append(("load", path)); current["path"] = path + "." + path.rsplit("/", 1)[1]; return True
        def save(world_arg, path):
            calls.append(("save", path)); return True  # Deliberately does not switch the world.
        levels = NS(load_level=load)
        u = NS(LevelEditorSubsystem="levels", UnrealEditorSubsystem="world",
               LevelSequenceEditorBlueprintLibrary=NS(close_level_sequence=lambda: None),
               EditorLoadingAndSavingUtils=NS(save_map=save),
               get_editor_subsystem=lambda name: levels if name == "levels" else NS(get_editor_world=lambda: world))
        destination = M.ROOT + "/Maps/L_fake"
        self.assertIs(M.copy_main_map(u, "/Game/Main/L_source.L_source", destination), world)
        self.assertEqual(calls, [("load", "/Game/Main/L_source"), ("save", destination), ("load", destination)])

    def test_garment_only_uses_whole_one_item_and_framing(self):
        asset = {"asset_id": "garment", "slot": "full_body", "mesh_paths": ["/Game/A.A", "/Game/B.B"]}
        source = {"appearance": {"wardrobe_assets": [asset]}}
        self.assertEqual(M.garment_target(source, "garment")["mesh_paths"], asset["mesh_paths"])
        with self.assertRaisesRegex(ValueError, "actual asset"):
            M.garment_target(source, "body")
        bounds = [{"center": [0, 0, 100], "extent": [30, 50, 80]}]
        pose = M.garment_framing(bounds, 1024, 1024)
        self.assertEqual(pose["rotation_pitch_yaw_roll"], [0, -90, 0])
        self.assertGreater(pose["position"][1], 300)
        self.assertEqual(pose["position"][0], 0)
        self.assertEqual(pose["position"][2], 100)

    def test_head_identity_and_complete_long_hair_front_back(self):
        head = [0, 0, 165]
        long_hair = [{"center": [0, -5, 135], "extent": [25, 18, 50]}]
        face = M.head_framing(head, long_hair, "identity", "front", 1024, 1024)
        front = M.head_framing(head, long_hair, "hair", "front", 1024, 1024)
        back = M.head_framing(head, long_hair, "hair", "back", 1024, 1024)
        self.assertEqual(face["bounds_center"][2], 172)
        self.assertGreater(front["bounds_extent"][2], face["bounds_extent"][2])
        self.assertGreater(front["position"][1], front["bounds_center"][1])
        self.assertLess(back["position"][1], back["bounds_center"][1])
        self.assertEqual(front["rotation_pitch_yaw_roll"], [0, -90, 0])
        self.assertEqual(back["rotation_pitch_yaw_roll"], [0, 90, 0])
        self.assertEqual(front["bounds_center"], back["bounds_center"])
        with self.assertRaisesRegex(ValueError, "requires actual"):
            M.head_framing(head, [], "hair", "front", 1024, 1024)

    def test_hair_bounds_use_mesh_reference_box_not_inherited_body_bounds(self):
        vector = lambda x, y, z: NS(x=x, y=y, z=z)
        mesh = NS(get_bounds=lambda: NS(origin=vector(10, 20, 30), box_extent=vector(1, 2, 3)),
                  get_path_name=lambda: "/Game/Hair.Hair")
        component = NS(get_skeletal_mesh_asset=lambda: mesh, get_world_transform=lambda: "transform")
        u = NS(Vector=vector, MathLibrary=NS(transform_location=lambda t, p: vector(p.y, -p.x, p.z + 100)))
        bounds = M.hair_asset_bounds(u, {"HairPart01": component, "Body": component})
        self.assertEqual(len(bounds), 1)
        self.assertEqual(bounds[0]["center"], [20, -10, 130])
        self.assertEqual(bounds[0]["extent"], [2, 1, 3])


if __name__ == "__main__": unittest.main()
