import importlib.util
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "inspect_datamake_multiturn_training_data.py"
)
SPEC = importlib.util.spec_from_file_location("inspect_datamake_multiturn", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
locate_parquet_row = MODULE.locate_parquet_row


class LocateParquetRowTests(unittest.TestCase):
    def test_locates_global_index_across_files_and_row_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "part-00000.parquet"
            second = root / "part-00001.parquet"
            pq.write_table(
                pa.table({"value": ["a", "b"]}), first, row_group_size=1
            )
            pq.write_table(
                pa.table({"value": ["c", "d", "e"]}), second, row_group_size=2
            )

            location = locate_parquet_row([first, second], 4)

            self.assertEqual(location["row"], {"value": "e"})
            self.assertEqual(location["parquet_idx"], 1)
            self.assertEqual(location["row_group_id"], 1)
            self.assertEqual(location["row_idx"], 0)
            self.assertEqual(location["total_rows"], 5)

    def test_rejects_out_of_range_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "part.parquet"
            pq.write_table(pa.table({"value": ["a"]}), path)

            with self.assertRaisesRegex(IndexError, "outside 0..0"):
                locate_parquet_row([path], 1)


if __name__ == "__main__":
    unittest.main()
