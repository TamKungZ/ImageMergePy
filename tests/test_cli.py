import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.media_merge.cli import parse_cli_input, run_cli
from src.media_merge.config import MODE_INSIDE_FOLDER, MODE_MAIN_FOLDER
from src.media_merge.media_ordering import normalize_prefix


class CliInputTests(unittest.TestCase):
    def test_parse_cli_input_resolves_path_and_normalizes_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = parse_cli_input(f"{temp_dir}:: Vacation Photos ")

        self.assertEqual(config["path"], Path(temp_dir).resolve())
        self.assertEqual(config["prefix"], normalize_prefix("Vacation Photos"))

    def test_parse_cli_input_rejects_empty_path(self):
        with self.assertRaisesRegex(ValueError, "path cannot be empty"):
            parse_cli_input("::prefix")


class CliExecutionTests(unittest.TestCase):
    def test_run_cli_rejects_missing_input_directory_with_usage_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                run_cli(
                    [
                        "--cli",
                        "--input",
                        str(missing_path),
                        "--output",
                        str(Path(temp_dir) / "output"),
                    ]
                )

        self.assertEqual(error.exception.code, 2)
        self.assertIn("Input path is not an existing directory", stderr.getvalue())

    def test_run_cli_rejects_clear_output_for_inside_folder_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                run_cli(
                    [
                        "--cli",
                        "--output",
                        temp_dir,
                        "--mode",
                        MODE_INSIDE_FOLDER,
                        "--clear-output",
                    ]
                )

        self.assertEqual(error.exception.code, 2)
        self.assertIn("cannot be used with --mode inside_folder", stderr.getvalue())

    def test_run_cli_preserves_main_folder_clear_output_option(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.media_merge.cli.process_media") as process_media:
                result = run_cli(
                    [
                        "--cli",
                        "--output",
                        temp_dir,
                        "--mode",
                        MODE_MAIN_FOLDER,
                        "--clear-output",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertTrue(process_media.call_args.kwargs["clear_output_first"])

    def test_run_cli_rejects_duplicate_removal_outside_inside_folder_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                run_cli(
                    [
                        "--cli",
                        "--input",
                        str(input_dir),
                        "--output",
                        str(Path(temp_dir) / "output"),
                        "--remove-duplicates",
                    ]
                )

        self.assertEqual(error.exception.code, 2)
        self.assertIn("only be used with --mode inside_folder", stderr.getvalue())

    def test_run_cli_passes_valid_input_config_to_processor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()

            with patch("src.media_merge.cli.process_media") as process_media:
                result = run_cli(
                    [
                        "--cli",
                        "--input",
                        f"{input_dir}:: Trip ",
                        "--output",
                        str(output_dir),
                    ]
                )

        self.assertEqual(result, 0)
        kwargs = process_media.call_args.kwargs
        self.assertEqual(kwargs["input_dir_configs"], [{"path": input_dir.resolve(), "prefix": "trip"}])
        self.assertEqual(kwargs["output_dir"], output_dir.resolve())
        self.assertTrue(kwargs["use_safe_temp_workspace"])


if __name__ == "__main__":
    unittest.main()
