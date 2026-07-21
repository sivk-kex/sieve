import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mirage.receipt import ManifestError, load_manifest, run_task


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_clean_task(task_dir: Path) -> None:
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
    manifest = {
        "id": "mean_claim",
        "command": ["python3", "analysis.py", "--config", "full.json"],
        "expected_output": "mean=50.00",
        "expected_hashes": {
            "analysis.py": sha256(task_dir / "analysis.py"),
            "full.json": sha256(task_dir / "full.json"),
        },
    }
    (task_dir / "claim.json").write_text(json.dumps(manifest), encoding="utf-8")
    (task_dir / "reproduction.json").write_text(
        json.dumps({"command": manifest["command"]}), encoding="utf-8"
    )


class ReceiptTests(unittest.TestCase):
    def test_run_task_records_manifest_command_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            write_clean_task(task_dir)

            receipt = run_task(task_dir, load_manifest(task_dir / "claim.json"))

            self.assertEqual(receipt.command, ("python3", "analysis.py", "--config", "full.json"))
            self.assertEqual(receipt.exit_code, 0)
            self.assertEqual(receipt.stdout.strip(), "mean=50.00")
            self.assertEqual(receipt.file_hashes["analysis.py"], sha256(task_dir / "analysis.py"))
            self.assertGreaterEqual(receipt.elapsed_seconds, 0)

    def test_manifest_rejects_parent_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            (task_dir / "claim.json").write_text(
                json.dumps(
                    {
                        "id": "unsafe",
                        "command": ["python3", "../outside.py"],
                        "expected_output": "ok",
                        "expected_hashes": {},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "parent path"):
                load_manifest(task_dir / "claim.json")

    def test_manifest_rejects_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            (task_dir / "claim.json").write_text(
                json.dumps(
                    {
                        "id": "unsafe",
                        "command": ["python3", "/tmp/outside.py"],
                        "expected_output": "ok",
                        "expected_hashes": {},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ManifestError, "absolute path"):
                load_manifest(task_dir / "claim.json")
