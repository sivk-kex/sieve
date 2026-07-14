import unittest

from run_sieve_stage1_v4 import default_output_path, parse_product


class SieveStage1V4Tests(unittest.TestCase):
    def test_product_gate_allows_one_frozen_product(self) -> None:
        self.assertEqual(parse_product("codex"), "codex")
        self.assertEqual(parse_product("claude"), "claude")
        with self.assertRaises(ValueError):
            parse_product("both")

    def test_default_path_names_trial_and_product(self) -> None:
        self.assertIn("stage1-v4-trial2-claude-", default_output_path(2, "claude").name)


if __name__ == "__main__":
    unittest.main()
