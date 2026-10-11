import subprocess
import sys
import unittest
from pathlib import Path

from scripts.build_nuitka import run_cmd


class RunCmdTests(unittest.TestCase):
    def test_failure_does_not_expose_secrets(self):
        command = [sys.executable, "-c", "import sys; sys.exit(3)", "/p", "SuperSecret123"]

        with self.assertRaises(RuntimeError) as context:
            run_cmd(command, Path.cwd(), secrets=("SuperSecret123",))

        self.assertNotIn("SuperSecret123", str(context.exception))
        self.assertIn("exit code 3", str(context.exception))
        self.assertIsNone(context.exception.__cause__)
        self.assertTrue(context.exception.__suppress_context__)

    def test_failure_without_secrets_keeps_original_error(self):
        command = [sys.executable, "-c", "import sys; sys.exit(4)"]

        with self.assertRaises(subprocess.CalledProcessError) as context:
            run_cmd(command, Path.cwd())

        self.assertEqual(context.exception.returncode, 4)


if __name__ == "__main__":
    unittest.main()
