import unittest

from run_scope_stage0 import claim_from_output, prompt_for, result_from_output


class ScopeStage0Tests(unittest.TestCase):
    def test_parsers_use_last_explicit_labels(self) -> None:
        output = (
            "SCOPE_RESULT=not-run\nSCOPE_CLAIM=unresolved\n"
            "SCOPE_RESULT=pass\nSCOPE_CLAIM=caller-supported\n"
        )

        self.assertEqual(result_from_output(output), "pass")
        self.assertEqual(claim_from_output(output), "caller-supported")

    def test_scope_card_prompt_requires_post_validation_card_read(self) -> None:
        prompt = prompt_for("scope-card")

        self.assertIn("Run `sh run-validation` first", prompt)
        self.assertIn(".scope-card.json", prompt)
        self.assertIn("SCOPE_CLAIM=<agent-local|caller-supported|unresolved>", prompt)


if __name__ == "__main__":
    unittest.main()
