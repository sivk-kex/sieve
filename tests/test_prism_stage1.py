import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from prism.fixture import FixtureRun, TracedFixtureRun
from run_prism_stage1 import (
    claim_from_output,
    codex_command,
    codex_environment,
    execution_config,
    ensure_fresh_output,
    experiment_cells,
    prompt_for,
    run_stage1,
    select_names,
)


class PrismStage1Tests(unittest.TestCase):
    def test_claim_parser_uses_last_explicit_label(self) -> None:
        output = "Tentative PRISM_CLAIM=unresolved\nFinal PRISM_CLAIM=host-dependent\n"

        self.assertEqual(claim_from_output(output), "host-dependent")

    def test_receipt_prompt_requires_validation_before_receipt(self) -> None:
        prompt = prompt_for("receipt")

        self.assertIn("Run `sh run-validation` first", prompt)
        self.assertIn(".prism-receipt.json", prompt)
        self.assertIn("PRISM_CLAIM=<portable|host-dependent|unresolved>", prompt)

    def test_codex_command_uses_configured_model_when_none_is_requested(self) -> None:
        command = codex_command(Path("/tmp/repo"), "prompt", None)

        self.assertNotIn("-m", command)
        self.assertIn("read-only", command)
        self.assertIn("--ignore-user-config", command)

    def test_codex_environment_keeps_an_explicit_codex_home(self) -> None:
        environment = codex_environment({"HOME": "/fixture/home", "CODEX_HOME": "/auth"})

        self.assertEqual(environment["HOME"], "/fixture/home")
        self.assertEqual(environment["CODEX_HOME"], "/auth")

    def test_select_names_keeps_requested_order_and_rejects_unknown_value(self) -> None:
        available = ("clean_control", "path_shadow", "user_config")

        selected = select_names("user_config,path_shadow", available)

        self.assertEqual(selected, ("user_config", "path_shadow"))
        with self.assertRaisesRegex(ValueError, "unknown selection: missing"):
            select_names("missing", available)

    def test_experiment_cells_repeat_each_fixture_condition_pair(self) -> None:
        cells = list(experiment_cells(("path_shadow",), ("transcript", "receipt"), 2))

        self.assertEqual(
            cells,
            [
                ("path_shadow", "transcript", 1),
                ("path_shadow", "transcript", 2),
                ("path_shadow", "receipt", 1),
                ("path_shadow", "receipt", 2),
            ],
        )
        with self.assertRaisesRegex(ValueError, "trials must be positive"):
            list(experiment_cells(("path_shadow",), ("transcript",), 0))

    def test_ensure_fresh_output_rejects_existing_raw_record(self) -> None:
        with TemporaryDirectory() as temp:
            output = Path(temp) / "raw.json"
            output.write_text("[]\n", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                ensure_fresh_output(output)

    def test_execution_config_declares_fixed_agent_and_trace_settings(self) -> None:
        config = execution_config(Path("/usr/bin/strace"), "gpt-test")

        self.assertEqual(config["agent_timeout_seconds"], 180)
        self.assertEqual(config["agent_sandbox"], "read-only")
        self.assertEqual(config["reasoning_effort"], "low")
        self.assertEqual(config["strace_path"], "/usr/bin/strace")
        self.assertEqual(config["trace_syscalls"], ["execve", "openat"])

    def test_stage1_record_contains_baseline_trace_and_agent_costs(self) -> None:
        traced = TracedFixtureRun(
            run=FixtureRun(("sh", "run-validation"), 0, "", "", 0.25),
            receipt={"ambient_inputs": []},
            trace="trace-data",
        )
        with TemporaryDirectory() as temp:
            output = Path(temp) / "raw.json"
            with (
                patch("run_prism_stage1.run_traced_fixture", return_value=traced),
                patch(
                    "run_prism_stage1.run_codex",
                    return_value={"agent_exit_code": 0, "claim": "portable"},
                ),
            ):
                records = run_stage1(
                    Path("/usr/bin/strace"),
                    output,
                    "gpt-test",
                    fixtures=("clean_control",),
                    conditions=("transcript",),
                )

        record = records[0]
        self.assertGreaterEqual(record["plain_validation_wall_seconds"], 0.0)
        self.assertEqual(record["traced_validation_wall_seconds"], 0.25)
        self.assertEqual(record["trace_bytes"], len(b"trace-data"))
        self.assertGreaterEqual(record["receipt_bytes"], 1)
        self.assertGreaterEqual(record["agent_wall_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
