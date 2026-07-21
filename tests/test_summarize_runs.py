import json
import tempfile
import unittest
from pathlib import Path

from summarize_runs import summarize_run_directory, write_summary


class SummarizeRunsTests(unittest.TestCase):
    def test_summary_compares_raw_verdicts_to_receipt_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw_dir = root / "raw-v3"
            receipt_path = root / "receipt.json"
            self._write_receipt(receipt_path)
            self._write_record(raw_dir / "clean" / "trial-001.json", "clean", "reproduced", 1.0)
            self._write_record(
                raw_dir / "configuration_substitution" / "trial-001.json",
                "configuration_substitution",
                "reproduced",
                2.0,
            )
            self._write_record(
                raw_dir / "configuration_substitution" / "trial-002.json",
                "configuration_substitution",
                "unparseable",
                3.0,
            )

            summary = summarize_run_directory(raw_dir, receipt_path)

            self.assertEqual(summary["protocol_version"], "raw-v3")
            self.assertEqual(summary["total_trials"], 3)
            self.assertEqual(summary["variants"]["clean"]["receipt_verdict"], "reproduced")
            self.assertEqual(summary["variants"]["clean"]["outcomes"]["matches_receipt"], 1)
            config = summary["variants"]["configuration_substitution"]
            self.assertEqual(config["receipt_verdict"], "not_reproduced")
            self.assertEqual(config["outcomes"]["receipt_disagreement_positive"], 1)
            self.assertEqual(config["outcomes"]["unparseable"], 1)
            self.assertEqual(config["mean_wall_seconds"], 2.5)

    def test_summary_rejects_missing_receipt_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw_dir = root / "raw-v3"
            receipt_path = root / "receipt.json"
            self._write_receipt(receipt_path)
            self._write_record(raw_dir / "unknown" / "trial-001.json", "unknown", "reproduced", 1.0)

            with self.assertRaisesRegex(ValueError, "missing receipt verdict"):
                summarize_run_directory(raw_dir, receipt_path)

    def test_write_summary_writes_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw_dir = root / "raw-v3"
            receipt_path = root / "receipt.json"
            output_path = root / "summary.json"
            self._write_receipt(receipt_path)
            self._write_record(raw_dir / "clean" / "trial-001.json", "clean", "reproduced", 1.0)

            summary = write_summary(raw_dir, receipt_path, output_path)

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), summary)

    def _write_receipt(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                [
                    {"variant": "clean", "deterministic_verdict": {"reproduced": True}},
                    {
                        "variant": "configuration_substitution",
                        "deterministic_verdict": {"reproduced": False},
                    },
                ]
            ),
            encoding="utf-8",
        )

    def _write_record(self, path: Path, variant: str, verdict: str, wall_seconds: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "protocol_version": "raw-v3",
                    "variant": variant,
                    "parsed_verdict": verdict,
                    "wall_seconds": wall_seconds,
                }
            ),
            encoding="utf-8",
        )
