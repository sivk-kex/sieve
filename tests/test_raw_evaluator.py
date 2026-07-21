import unittest
from pathlib import Path

from mirage.raw_evaluator import EVALUATOR_PROMPT, PROTOCOLS, build_command, parse_verdict


class RawEvaluatorTests(unittest.TestCase):
    def test_parser_accepts_one_terminal_verdict(self) -> None:
        response = "Evidence reviewed.\nMIRAGE_VERDICT: reproduced\n"

        self.assertEqual(parse_verdict(response), "reproduced")

    def test_parser_rejects_missing_or_multiple_verdicts(self) -> None:
        self.assertEqual(parse_verdict("No final label."), "unparseable")
        self.assertEqual(
            parse_verdict("MIRAGE_VERDICT: reproduced\nMIRAGE_VERDICT: not_reproduced"),
            "unparseable",
        )

    def test_command_uses_ephemeral_read_only_isolation(self) -> None:
        command = build_command("codex", Path("/tmp/task"), Path("/tmp/response.txt"))

        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("read-only", command)
        self.assertEqual(command[-1], EVALUATOR_PROMPT)

    def test_raw_v3_keeps_generic_evaluator_prompt(self) -> None:
        self.assertNotIn("Do not repair", PROTOCOLS["raw-v3"])
        self.assertIn("Determine whether this stated claim is reproduced", PROTOCOLS["raw-v3"])
