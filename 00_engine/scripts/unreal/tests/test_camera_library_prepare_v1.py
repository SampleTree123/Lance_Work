"""Safety gates for the root-owned camera expansion preparation helper."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

PATH = Path(__file__).resolve().parents[1]/'ue_camera_library_prepare_v1.py'
spec = importlib.util.spec_from_file_location('camera_library_prepare_under_test', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PrepareSafetyTests(unittest.TestCase):
    def test_dirty_content_is_not_silently_discarded(self):
        package = SimpleNamespace(get_name=lambda: '/Game/UserUnsavedMaterial')
        u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(
            get_dirty_map_packages=lambda: [], get_dirty_content_packages=lambda: [package]))
        with self.assertRaisesRegex(RuntimeError, 'UserUnsavedMaterial'):
            m.clean(u)

    def test_dirty_map_is_not_silently_saved(self):
        package = SimpleNamespace(get_name=lambda: '/Game/UserMap')
        u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(
            get_dirty_map_packages=lambda: [package], get_dirty_content_packages=lambda: []))
        with self.assertRaisesRegex(RuntimeError, 'UserMap'):
            m.clean(u)

    def test_wrong_project_fails_before_accessing_editor(self):
        u = SimpleNamespace(Paths=SimpleNamespace(project_dir=lambda: 'D:/UE/projects/other'))
        with self.assertRaisesRegex(ValueError, 'Wrong UE project'):
            m.prepare(u)

    def test_path_rejects_traversal(self):
        for path in ['/Game/../Outside', '/Engine/Character', '/Game/Bad-Name']:
            with self.assertRaises(ValueError):
                m.package(path)

    def test_world_normalization_preserves_component_relationship_difference(self):
        before = {'component': '/Game/A.A:Actor.Hair', 'leader': '/Game/A.A:Actor.Body'}
        copied = {'component': '/Game/B.B:Actor.Hair', 'leader': '/Game/B.B:Actor.Body'}
        wrong = dict(copied, leader='/Game/B.B:OtherActor.Body')
        self.assertEqual(m.normalized(before, '/Game/A.A'), m.normalized(copied, '/Game/B.B'))
        self.assertNotEqual(m.normalized(before, '/Game/A.A'), m.normalized(wrong, '/Game/B.B'))


if __name__ == '__main__':
    unittest.main()
