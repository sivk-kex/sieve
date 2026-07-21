import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mirage.receipt import load_manifest, run_task
from mirage.verdict import verify


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_task(task_dir: Path) -> None:
    (task_dir / "analysis.py").write_text(
        "import argparse\n"
        "import json\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--config', required=True)\n"
        "args = parser.parse_args()\n"
        "print(json.loads(open(args.config).read())['output'])\n",
        encoding="utf-8",
    )
    (task_dir / "full.json").write_text('{"output": "mean=50.00"}\n', encoding="utf-8")
    (task_dir / "claim.json").write_text(
        json.dumps(
            {
                "id": "mean_claim",
                "command": ["python3", "analysis.py", "--config", "full.json"],
                "expected_output": "mean=50.00",
                "expected_hashes": {
                    "analysis.py": sha256(task_dir / "analysis.py"),
                    "full.json": sha256(task_dir / "full.json"),
                },
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "reproduction.json").write_text(
        json.dumps({"command": ["python3", "analysis.py", "--config", "full.json"]}),
        encoding="utf-8",
    )


class VerdictTests(unittest.TestCase):
    def test_clean_receipt_reproduces_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            write_task(task_dir)

            manifest = load_manifest(task_dir / "claim.json")
            result = verify(manifest, run_task(task_dir, manifest))

            self.assertTrue(result.reproduced)
            self.assertEqual(result.reasons, ())

    def test_configuration_substitution_is_rejected_even_with_same_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            write_task(task_dir)
            (task_dir / "smoke.json").write_text('{"output": "mean=50.00"}\n', encoding="utf-8")
            (task_dir / "reproduction.json").write_text(
                json.dumps({"command": ["python3", "analysis.py", "--config", "smoke.json"]}),
                encoding="utf-8",
            )

            manifest = load_manifest(task_dir / "claim.json")
            result = verify(manifest, run_task(task_dir, manifest))

            self.assertFalse(result.reproduced)
            self.assertEqual(result.reasons, ("command_mismatch",))

    def test_stale_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            write_task(task_dir)
            (task_dir / "full.json").write_text('{"output": "mean=49.00"}\n', encoding="utf-8")

            manifest = load_manifest(task_dir / "claim.json")
            result = verify(manifest, run_task(task_dir, manifest))

            self.assertFalse(result.reproduced)
            self.assertEqual(
                result.reasons,
                ("expected_output_missing", "hash_mismatch:full.json"),
            )
