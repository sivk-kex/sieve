import unittest
from pathlib import Path

from prism.receipt import summarize_trace


class PrismReceiptTests(unittest.TestCase):
    def test_marks_external_resolved_executable_as_ambient_input(self) -> None:
        trace = (
            'execve("/work/path-shadow/repo/run-validation", ["./run-validation"], 0x0) = 0\n'
            'execve("/work/path-shadow/host-bin/validator", ["validator"], 0x0) = 0\n'
        )

        receipt = summarize_trace(
            trace,
            repository=Path("/work/path-shadow/repo"),
            ambient_roots={"path": Path("/work/path-shadow/host-bin")},
        )

        self.assertEqual(
            receipt["ambient_inputs"],
            [
                {
                    "kind": "executable",
                    "origin": "path",
                    "path": "/work/path-shadow/host-bin/validator",
                }
            ],
        )

    def test_marks_external_read_as_ambient_input(self) -> None:
        trace = (
            'openat(AT_FDCWD, "/work/user-config/host-home/.config/prism/force-pass", '
            "O_RDONLY|O_CLOEXEC) = 3\n"
        )

        receipt = summarize_trace(
            trace,
            repository=Path("/work/user-config/repo"),
            ambient_roots={"user-config": Path("/work/user-config/host-home")},
        )

        self.assertEqual(
            receipt["ambient_inputs"],
            [
                {
                    "kind": "read",
                    "origin": "user-config",
                    "path": "/work/user-config/host-home/.config/prism/force-pass",
                }
            ],
        )

    def test_prefers_executable_over_read_of_same_ambient_path(self) -> None:
        trace = (
            'execve("/work/path-shadow/host-bin/validator", ["validator"], 0x0) = 0\n'
            'openat(AT_FDCWD, "/work/path-shadow/host-bin/validator", O_RDONLY) = 3\n'
        )

        receipt = summarize_trace(
            trace,
            repository=Path("/work/path-shadow/repo"),
            ambient_roots={"path": Path("/work/path-shadow/host-bin")},
        )

        self.assertEqual(
            receipt["ambient_inputs"],
            [
                {
                    "kind": "executable",
                    "origin": "path",
                    "path": "/work/path-shadow/host-bin/validator",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
