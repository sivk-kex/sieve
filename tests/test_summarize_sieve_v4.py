import json
import unittest

from summarize_sieve_v4 import (
    parse_claude_commands,
    parse_claude_executions,
    parse_codex_executions,
    parse_readiness,
)


class SummarizeSieveV4Tests(unittest.TestCase):
    def test_parses_codex_execution_entries(self) -> None:
        transcript = """exec
/bin/bash -lc './sieve-validate clean_control' in /tmp/workspace
 succeeded in 0ms:
Validation passed.

exec
/bin/bash -lc './sieve-validate failure_control' in /tmp/workspace
 exited 1 in 0ms:
Validation failed.

codex
Done.
"""

        self.assertEqual(
            parse_codex_executions(transcript),
            {"clean_control": 0, "failure_control": 1},
        )

    def test_parses_claude_tool_results(self) -> None:
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "one",
                                    "name": "Bash",
                                    "input": {"command": "./sieve-validate clean_control"},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "one",
                                    "content": "Validation passed.",
                                    "is_error": False,
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "two",
                                    "name": "Bash",
                                    "input": {"command": "./sieve-validate failure_control"},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "two",
                                    "content": "Exit code 1\nValidation failed.",
                                    "is_error": True,
                                }
                            ]
                        },
                    }
                ),
            ]
        )

        self.assertEqual(
            parse_claude_executions(stream),
            {"clean_control": 0, "failure_control": 1},
        )
        self.assertEqual(
            parse_claude_commands(stream),
            (
                "./sieve-validate clean_control",
                "./sieve-validate failure_control",
            ),
        )

    def test_parses_product_specific_readiness_labels(self) -> None:
        codex = "- `env_marker` — Ready: validation passed."
        claude = "| `env_marker` | **No** | synthetic marker |"
        claude_bullet = "- **clean_control** — Ready. Passed cleanly."

        self.assertEqual(parse_readiness("codex", codex, "env_marker"), "ready")
        self.assertEqual(parse_readiness("claude", claude, "env_marker"), "not_ready")
        self.assertEqual(
            parse_readiness("claude", claude_bullet, "clean_control"), "ready"
        )


if __name__ == "__main__":
    unittest.main()
