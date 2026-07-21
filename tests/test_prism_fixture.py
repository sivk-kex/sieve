import os
import unittest
from pathlib import Path

from prism.fixture import load_fixture, run_fixture, run_traced_fixture


ROOT = Path(__file__).resolve().parents[1]


class PrismFixtureTests(unittest.TestCase):
    def test_path_shadow_expands_ambient_path_and_root(self) -> None:
        fixture = load_fixture(ROOT / "tasks" / "prism" / "path_shadow")

        environment, roots = fixture.context_for("ambient", {"PATH": "/usr/bin"})

        self.assertEqual(
            environment["PATH"],
            f"{fixture.path / 'host-bin'}:{fixture.repository / 'tools'}:/usr/bin",
        )
        self.assertEqual(roots, {"path": fixture.path / "host-bin"})

    def test_user_config_clean_context_has_no_ambient_roots(self) -> None:
        fixture = load_fixture(ROOT / "tasks" / "prism" / "user_config")

        environment, roots = fixture.context_for("clean", {"HOME": "/home/original"})

        self.assertEqual(environment["HOME"], str(fixture.path / "clean-home"))
        self.assertEqual(roots, {})

    def test_fixtures_pass_only_with_intended_ambient_state(self) -> None:
        parent_environment = {"PATH": "/usr/bin"}
        for name in ("path_shadow", "user_config"):
            fixture = load_fixture(ROOT / "tasks" / "prism" / name)

            ambient = run_fixture(fixture, "ambient", parent_environment)
            clean = run_fixture(fixture, "clean", parent_environment)

            self.assertEqual(ambient.exit_code, 0, name)
            self.assertNotEqual(clean.exit_code, 0, name)

    @unittest.skipUnless(os.environ.get("PRISM_STRACE"), "PRISM_STRACE is required")
    def test_traced_ambient_passes_expose_declared_origin(self) -> None:
        expected_origins = {
            "path_shadow": "path",
            "user_config": "user-config",
        }
        for name, expected_origin in expected_origins.items():
            fixture = load_fixture(ROOT / "tasks" / "prism" / name)
            traced = run_traced_fixture(
                fixture,
                "ambient",
                {"PATH": "/usr/bin"},
                Path(os.environ["PRISM_STRACE"]),
            )

            self.assertEqual(traced.run.exit_code, 0, name)
            self.assertEqual(
                [item["origin"] for item in traced.receipt["ambient_inputs"]],
                [expected_origin],
                name,
            )


if __name__ == "__main__":
    unittest.main()
