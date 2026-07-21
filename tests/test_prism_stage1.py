import unittest
from pathlib import Path

from run_prism_stage1 import claim_from_output, codex_command, codex_environment, prompt_for


class PrismStage1Tests(unittest.TestCase):
    def test_claim_parser_uses_last_explicit_label(self) -> None:
        output = "Tentative PRISM_CLAIM=unresolved\nFinal PRISM_CLAIM=host-dependent\n"

        self.assertEqual(claim_from_output(output), "host-dependent")

    def test_receipt_prompt_requires_validation_before_receipt(self) -> None:
        prompt = prompt_for("receipt")

        self.assertIn("Run `sh run-validation` first", prompt)
        self.assertIn(".prism-receipt.json", prompt)
        self.assertIn("PRISM_CLAIM=<portable|host-dependent|unresolved>", prompt)

    def test_codex_command_uses_configured_model_when_none_is_requested(self) -> None:
        command = codex_command(Path("/tmp/repo"), "prompt", None)

        self.assertNotIn("-m", command)
        self.assertIn("read-only", command)
        self.assertIn("--ignore-user-config", command)

    def test_codex_environment_keeps_an_explicit_codex_home(self) -> None:
        environment = codex_environment({"HOME": "/fixture/home", "CODEX_HOME": "/auth"})

        self.assertEqual(environment["HOME"], "/fixture/home")
        self.assertEqual(environment["CODEX_HOME"], "/auth")


if __name__ == "__main__":
    unittest.main()
