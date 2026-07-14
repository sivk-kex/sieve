import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from run_sieve_stage1 import (
    copy_workspace,
    parse_trial,
    run_workspace_validation,
    stage1_environment,
)
from sieve.fixture import load_fixture, run_target


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_NAMES = (
    "clean_control",
    "failure_control",
    "env_marker",
    "config_marker",
    "path_marker",
    "cwd_marker",
)


class SieveStage1FixtureTests(unittest.TestCase):
    def test_parse_trial_allows_only_one_frozen_trial(self) -> None:
        self.assertEqual(parse_trial("2"), 2)
        with self.assertRaises(ValueError):
            parse_trial("4")

    def test_clean_target_passes_only_positive_control(self) -> None:
        outcomes = {
            name: run_target(load_fixture(ROOT / "tasks" / "sieve" / name)).exit_code
            for name in FIXTURE_NAMES
        }

        self.assertEqual(outcomes["clean_control"], 0)
        for name in FIXTURE_NAMES[1:]:
            self.assertNotEqual(outcomes[name], 0, name)

    def test_synthetic_agent_state_activates_only_declared_markers(self) -> None:
        with TemporaryDirectory(prefix="sieve-stage1-test-") as temporary:
            workspace = Path(temporary) / "candidates"
            workspace.mkdir()
            copy_workspace(workspace)

            environment = stage1_environment({}, workspace)
            outcomes = {
                name: run_workspace_validation(workspace, name, environment).exit_code
                for name in FIXTURE_NAMES
            }

        self.assertEqual(outcomes["clean_control"], 0)
        self.assertNotEqual(outcomes["failure_control"], 0)
        for name in ("env_marker", "config_marker", "path_marker", "cwd_marker"):
            self.assertEqual(outcomes[name], 0, name)


if __name__ == "__main__":
    unittest.main()
