import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_launchpad_source import build_source_package, extract_runtime


class LaunchpadPackageTests(unittest.TestCase):
    def test_extract_runtime_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("../outside", "not allowed")

            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                extract_runtime(archive, root / "extract")

            self.assertFalse((root / "outside").exists())

    def test_build_source_package_stages_matching_suite_and_signing_args(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "runtime.zip"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("ImageMerge/ImageMerge", "binary")

            (root / "app_metadata.json").write_text(
                '{"product_version":"2.0.0.0"}',
                encoding="utf-8",
            )
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "LICENSE").write_text("license", encoding="utf-8")
            output_dir = root / "out"
            package_root = Path(__file__).resolve().parents[1]

            def fake_build(command, cwd, check):
                self.assertEqual(command[0], "dpkg-buildpackage")
                self.assertIn("-S", command)
                self.assertIn("-sa", command)
                self.assertIn("-kABCDEF", command)
                self.assertIn("-pC:\\signer", command)
                changelog = (cwd / "debian" / "changelog").read_text(encoding="utf-8")
                self.assertIn("imagemerge (2.0.0ubuntu24.04.1) noble;", changelog)
                control = (cwd / "debian" / "control").read_text(encoding="utf-8")
                self.assertIn("Maintainer: TamKungZ_ <maintainer@example.org>", control)
                self.assertTrue((cwd / "runtime" / "ImageMerge" / "ImageMerge").is_file())
                self.assertTrue((cwd / "packaging" / "imagemerge").is_file())
                (cwd.parent / "imagemerge_2.0.0ubuntu24.04.1_source.changes").write_text(
                    "signed source changes",
                    encoding="utf-8",
                )
                (cwd.parent / "imagemerge_2.0.0ubuntu24.04.1.dsc").write_text(
                    "source descriptor",
                    encoding="utf-8",
                )
                (cwd.parent / "imagemerge_2.0.0ubuntu24.04.1.tar.xz").write_text(
                    "source archive",
                    encoding="utf-8",
                )

            with patch("scripts.build_launchpad_source.subprocess.run", side_effect=fake_build):
                changes = build_source_package(
                    package_root,
                    archive,
                    "v2.0.0",
                    "noble",
                    output_dir,
                    "ABCDEF",
                    Path("C:\\signer"),
                    "maintainer@example.org",
                )

            self.assertTrue(changes.is_file())
            self.assertTrue((output_dir / "imagemerge_2.0.0ubuntu24.04.1.dsc").is_file())
            self.assertTrue((output_dir / "imagemerge_2.0.0ubuntu24.04.1.tar.xz").is_file())


if __name__ == "__main__":
    unittest.main()
