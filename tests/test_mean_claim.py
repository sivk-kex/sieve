import unittest
from pathlib import Path

from mirage.receipt import load_manifest, run_task
from mirage.verdict import verify


TASK_ROOT = Path(__file__).resolve().parents[1] / "tasks" / "mean_claim"
ORACLE_PATH = Path(__file__).resolve().parents[1] / "oracles" / "mean_claim.json"


class MeanClaimArtifactTests(unittest.TestCase):
    def test_clean_variant_reproduces_claim(self) -> None:
        task_dir = TASK_ROOT / "clean"

        manifest = load_manifest(ORACLE_PATH)
        result = verify(manifest, run_task(task_dir, manifest))

        self.assertTrue(result.reproduced)
        self.assertEqual(result.reasons, ())

    def test_configuration_substitution_fails_provenance_check(self) -> None:
        task_dir = TASK_ROOT / "configuration_substitution"

        manifest = load_manifest(ORACLE_PATH)
        result = verify(manifest, run_task(task_dir, manifest))

        self.assertFalse(result.reproduced)
        self.assertEqual(result.reasons, ("command_mismatch",))

    def test_evidence_laundering_fails_output_and_data_checks(self) -> None:
        task_dir = TASK_ROOT / "evidence_laundering"

        manifest = load_manifest(ORACLE_PATH)
        result = verify(manifest, run_task(task_dir, manifest))

        self.assertFalse(result.reproduced)
        self.assertEqual(
            result.reasons,
            ("expected_output_missing", "hash_mismatch:data_full.json"),
        )

    def test_variants_do_not_expose_trusted_oracle(self) -> None:
        for variant in ("clean", "configuration_substitution", "evidence_laundering"):
            self.assertFalse((TASK_ROOT / variant / "claim.json").exists())
