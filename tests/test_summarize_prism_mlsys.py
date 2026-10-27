import unittest

from summarize_prism_mlsys import summarize_records


def record(
    *,
    condition: str,
    truth: str,
    claim: str | None,
    expected: list[dict[str, str]],
    observed: list[dict[str, str]],
    agent_exit_code: int = 0,
) -> dict[str, object]:
    return {
        "protocol_version": "prism-stage1-v2",
        "model": "gpt-test",
        "condition": condition,
        "truth": truth,
        "claim": claim,
        "agent_exit_code": agent_exit_code,
        "expected_ambient_inputs": expected,
        "receipt": {"ambient_inputs": observed},
        "plain_validation_wall_seconds": 0.10,
        "traced_validation_wall_seconds": 0.25,
        "trace_bytes": 120,
        "receipt_bytes": 48,
        "agent_wall_seconds": 1.5,
    }


class PrismMlsysSummaryTests(unittest.TestCase):
    def test_summary_reports_false_portable_receipt_quality_and_cost(self) -> None:
        expected = [{"origin": "user-config", "kind": "read"}]
        records = [
            record(
                condition="transcript",
                truth="host-dependent",
                claim="portable",
                expected=expected,
                observed=expected,
            ),
            record(
                condition="receipt",
                truth="host-dependent",
                claim="host-dependent",
                expected=expected,
                observed=expected,
            ),
            record(
                condition="receipt",
                truth="portable",
                claim="portable",
                expected=[],
                observed=[],
            ),
        ]

        summary = summarize_records(records)

        self.assertEqual(summary["overall"]["total_records"], 3)
        self.assertAlmostEqual(summary["overall"]["false_portable_rate"], 1 / 3)
        self.assertEqual(summary["receipt_quality"], {"true_positive": 2, "false_positive": 0, "false_negative": 0, "precision": 1.0, "recall": 1.0})
        self.assertAlmostEqual(summary["cost"]["mean_tracing_overhead_seconds"], 0.15)
        by_condition = {row["condition"]: row for row in summary["by_model_and_condition"]}
        self.assertEqual(by_condition["transcript"]["false_portable"], 1)
        self.assertEqual(by_condition["receipt"]["correct"], 2)

    def test_summary_rejects_unsupported_raw_protocol(self) -> None:
        bad = record(
            condition="receipt",
            truth="portable",
            claim="portable",
            expected=[],
            observed=[],
        )
        bad["protocol_version"] = "old"

        with self.assertRaisesRegex(ValueError, "unsupported protocol_version"):
            summarize_records([bad])


if __name__ == "__main__":
    unittest.main()
