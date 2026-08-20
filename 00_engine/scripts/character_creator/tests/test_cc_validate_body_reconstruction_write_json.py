import ast
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py"


def load_write_json():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "write_json"
    )
    namespace = {"json": json, "os": os, "time": time}
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["write_json"]


class WriteJsonRetryTests(unittest.TestCase):
    def test_retries_transient_permission_error(self):
        write_json = load_write_json()
        real_replace = os.replace
        attempts = []

        def flaky_replace(source, target):
            attempts.append((source, target))
            if len(attempts) < 4:
                raise PermissionError("transient lock")
            return real_replace(source, target)

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "result.json"
            with mock.patch.object(os, "replace", side_effect=flaky_replace):
                with mock.patch.object(time, "sleep") as sleep:
                    write_json({"success": True}, str(target))

            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"success": True})
            self.assertEqual(len(attempts), 4)
            self.assertEqual(sleep.call_count, 3)
            for call, expected in zip(sleep.call_args_list, [0.2, 0.4, 0.6], strict=True):
                self.assertAlmostEqual(call.args[0], expected)

    def test_raises_after_retry_budget(self):
        write_json = load_write_json()

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "result.json"
            with mock.patch.object(os, "replace", side_effect=PermissionError("locked")) as replace:
                with mock.patch.object(time, "sleep") as sleep:
                    with self.assertRaises(PermissionError):
                        write_json({"success": False}, str(target))

            self.assertEqual(replace.call_count, 10)
            self.assertEqual(sleep.call_count, 9)


if __name__ == "__main__":
    unittest.main()
