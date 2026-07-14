import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from run_sieve_stage1 import FIXTURE_NAMES, copy_workspace, stage1_environment
from run_sieve_stage1_v2 import (
    claude_command,
    codex_trace_commands,
    complete_wrapper_trace,
    create_validator_wrapper,
    trace_commands,
)


class SieveStage1V2Tests(unittest.TestCase):
    def test_wrapper_runs_only_declared_candidates(self) -> None:
        with TemporaryDirectory(prefix="sieve-stage1-v2-test-") as temporary:
            workspace = Path(temporary) / "candidates"
            workspace.mkdir()
            copy_workspace(workspace)
            create_validator_wrapper(workspace)
            environment = stage1_environment({}, workspace)

            clean = subprocess.run(
                ("./sieve-validate", "clean_control"),
                cwd=workspace,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            rejected = subprocess.run(
                ("./sieve-validate", "not-a-fixture"),
                cwd=workspace,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )

        self.assertEqual(clean.returncode, 0)
        self.assertNotEqual(rejected.returncode, 0)

    def test_claude_command_allows_only_wrapper_prefix_and_streams_events(self) -> None:
        command = claude_command(Path("/tmp/sieve-workspace"), "review")

        allowed = command[command.index("--allowed-tools") + 1]
        self.assertEqual(allowed, "Bash(./sieve-validate:*)")
        self.assertEqual(command[command.index("--output-format") + 1], "stream-json")
        self.assertIn("--bare", command)
        self.assertIn("--verbose", command)

    def test_trace_commands_reads_bash_tool_events(self) -> None:
        stream = "\n".join(
            [
                '{"type":"assistant","message":{"content":[{"name":"Bash","input":{"command":"./sieve-validate clean_control"}}]}}',
                '{"type":"assistant","message":{"content":[{"name":"Bash","input":{"command":"./sieve-validate env_marker"}}]}}',
            ]
        )

        self.assertEqual(
            trace_commands(stream),
            ("./sieve-validate clean_control", "./sieve-validate env_marker"),
        )

    def test_codex_trace_requires_execution_entries_not_prompt_text(self) -> None:
        transcript = """user
- `./sieve-validate failure_control`
exec
/bin/bash -lc './sieve-validate clean_control' in /tmp/workspace
 succeeded in 0ms:
Validation passed.
exec
/bin/bash -lc './sieve-validate failure_control' in /tmp/workspace
 exited 1 in 0ms:
Validation failed.
"""

        commands = codex_trace_commands(transcript)

        self.assertEqual(
            commands,
            ("./sieve-validate clean_control", "./sieve-validate failure_control"),
        )
        self.assertFalse(complete_wrapper_trace(commands))


if __name__ == "__main__":
    unittest.main()
