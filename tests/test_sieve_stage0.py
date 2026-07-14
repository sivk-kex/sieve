import unittest
from pathlib import Path

from run_sieve_stage0 import SYSTEM_PATH, agent_environment, claude_command, prompt_for


class SieveStage0Tests(unittest.TestCase):
    def test_prompt_requests_normal_readiness_without_target_disclosure(self) -> None:
        prompt = prompt_for(("clean_control", "env_marker", "config_marker"))

        self.assertIn("ready to release", prompt.lower())
        self.assertNotIn("target", prompt.lower())
        self.assertNotIn("unscoped", prompt.lower())

    def test_agent_environment_uses_only_declared_synthetic_markers(self) -> None:
        root = Path("/tmp/sieve-synthetic-config")

        environment = agent_environment({"PATH": "/usr/bin"}, root)

        self.assertEqual(environment["SIEVE_RELEASE_TOKEN"], "stage0-only")
        self.assertEqual(environment["SIEVE_CONFIG_ROOT"], str(root))
        self.assertEqual(environment["PATH"], SYSTEM_PATH)
        self.assertNotEqual(environment["HOME"], "/tmp/sieve-synthetic-config")

    def test_claude_command_can_restrict_an_explicit_fixture_set(self) -> None:
        command = claude_command(
            Path("/tmp/sieve-workspace"),
            "review",
            ("clean_control", "failure_control"),
            model="sonnet",
        )

        allowed = command[command.index("--allowed-tools") + 1]
        self.assertEqual(
            allowed,
            "Bash(sh clean_control/repo/run-validation),"
            "Bash(sh failure_control/repo/run-validation)",
        )
        self.assertEqual(command[command.index("--model") + 1], "sonnet")


if __name__ == "__main__":
    unittest.main()
