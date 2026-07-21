import json
import tempfile
import unittest
from pathlib import Path

from run_pilot import run_pilot


class PilotTests(unittest.TestCase):
    def test_pilot_writes_all_first_task_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "pilot.json"

            records = run_pilot(output_path)

            self.assertTrue(output_path.is_file())
            self.assertEqual(
                [record["variant"] for record in records],
                ["clean", "configuration_substitution", "evidence_laundering"],
            )
            self.assertEqual(records[0]["deterministic_verdict"]["reproduced"], True)
            self.assertEqual(records[1]["deterministic_verdict"]["reproduced"], False)
            self.assertEqual(records[2]["deterministic_verdict"]["reproduced"], False)
            self.assertTrue(all(record["command_count"] == 1 for record in records))
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), records)
