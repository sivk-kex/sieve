import unittest
from pathlib import Path

from sieve.fixture import load_fixture, run_target


ROOT = Path(__file__).resolve().parents[1]


class SieveFixtureTests(unittest.TestCase):
    def test_clean_target_passes_only_the_clean_control(self) -> None:
        outcomes = {
            name: run_target(load_fixture(ROOT / "tasks" / "sieve" / name)).exit_code
            for name in ("clean_control", "env_marker", "config_marker")
        }

        self.assertEqual(outcomes["clean_control"], 0)
        self.assertNotEqual(outcomes["env_marker"], 0)
        self.assertNotEqual(outcomes["config_marker"], 0)


if __name__ == "__main__":
    unittest.main()
