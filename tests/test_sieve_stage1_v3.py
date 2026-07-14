import unittest
from pathlib import Path

from run_sieve_stage1_v3 import claude_command


class SieveStage1V3Tests(unittest.TestCase):
    def test_claude_uses_authenticated_wrapper_only_configuration(self) -> None:
        command = claude_command(Path("/tmp/sieve-workspace"), "review")

        self.assertNotIn("--bare", command)
        self.assertIn("--safe-mode", command)
        self.assertEqual(command[command.index("--tools") + 1], "Bash")
        self.assertEqual(
            command[command.index("--allowed-tools") + 1],
            "Bash(./sieve-validate:*)",
        )
        self.assertEqual(command[command.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", command)


if __name__ == "__main__":
    unittest.main()
