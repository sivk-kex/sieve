import unittest
from pathlib import Path

from scope.fixture import load_fixture, run_caller_fixture


ROOT = Path(__file__).resolve().parents[1]


class ScopeFixtureTests(unittest.TestCase):
    def test_caller_plane_fails_for_each_divergence_fixture(self) -> None:
        parent_environment = {"PATH": "/usr/bin"}
        for name in ("path_plane", "env_plane"):
            fixture = load_fixture(ROOT / "tasks" / "scope" / name)

            result = run_caller_fixture(fixture, parent_environment)

            self.assertNotEqual(result.exit_code, 0, name)

    def test_scope_cards_declared_comparison_is_divergent(self) -> None:
        for name in ("path_plane", "env_plane"):
            fixture = load_fixture(ROOT / "tasks" / "scope" / name)

            self.assertEqual(fixture.scope_card["comparison"], "divergent", name)


if __name__ == "__main__":
    unittest.main()
