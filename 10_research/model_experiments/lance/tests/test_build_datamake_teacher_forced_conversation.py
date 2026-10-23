import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_datamake_teacher_forced_conversation.py"
)
SPEC = importlib.util.spec_from_file_location("build_teacher_forced", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TeacherForcedConversationTest(unittest.TestCase):
    def test_only_final_user_turn_requests_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            videos = []
            for index in range(4):
                path = root / f"{index}.mp4"
                path.write_bytes(b"test")
                videos.append(path.name)
            row = {
                "sample_id": "sample",
                "chain_id": "chain",
                "target_round": 3,
                "prompts": ["one", "two", "three"],
                "video_paths": videos,
            }
            conversation = MODULE.build_conversation(row, root)
        turns = conversation["turns"]
        self.assertEqual([turn["role"] for turn in turns], ["user", "assistant", "user", "assistant", "user"])
        self.assertNotIn("action", turns[0])
        self.assertNotIn("action", turns[2])
        self.assertEqual(turns[4]["action"], "edit_video")
        self.assertEqual(turns[1]["content"][0]["value"], str((root / "1.mp4").resolve()))


if __name__ == "__main__":
    unittest.main()
