from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from build_animation_p0_dynamic_gate_run import (  # noqa: E402
    OutfitPortalError,
    load_visual_decision,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnimationP0DynamicDecisionTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, list[Path], Path, list[str]]:
        case_ids = ["p0_001", "p0_002"]
        gate = root / "gate.json"
        gate.write_text("{}", encoding="utf-8")
        validation = root / "validation.json"
        validation.write_text("{}", encoding="utf-8")
        decision = root / "decision.json"
        decision.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "review_scope": {
                        "gate_manifest": {
                            "path": str(gate),
                            "sha256": sha256_file(gate),
                        },
                        "source_validations": [
                            {
                                "path": str(validation),
                                "sha256": sha256_file(validation),
                            }
                        ],
                        "reviewed_motion_count": 2,
                    },
                    "user_visual_review": {
                        "overall_status": "all_16_visual_quality_accepted",
                        "accepted_case_ids": case_ids,
                    },
                }
            ),
            encoding="utf-8",
        )
        return gate, [validation], decision, case_ids

    def test_accepts_hash_bound_full_set_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            gate, validations, decision, case_ids = self._fixture(Path(temporary))
            loaded = load_visual_decision(
                decision, gate, validations, case_ids
            )
            self.assertEqual(
                loaded["user_visual_review"]["accepted_case_ids"],
                case_ids,
            )

    def test_rejects_partial_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            gate, validations, decision, case_ids = self._fixture(Path(temporary))
            payload = json.loads(decision.read_text(encoding="utf-8"))
            payload["user_visual_review"]["accepted_case_ids"] = case_ids[:1]
            decision.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(OutfitPortalError):
                load_visual_decision(decision, gate, validations, case_ids)


if __name__ == "__main__":
    unittest.main()
