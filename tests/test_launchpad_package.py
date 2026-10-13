import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_launchpad_source import build_source_package, extract_runtime


def write_runtime_zip(archive: Path, entries: dict[str, int]) -> None:
    with zipfile.ZipFile(archive, "w") as zip_file:
        for name, mode in entries.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | mode) << 16
            zip_file.writestr(info, "data")


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

    def test_extract_runtime_restores_permissions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "runtime.zip"
            write_runtime_zip(
                archive,
                {"ImageMerge/ImageMerge": 0o644, "ImageMerge/_opcode.so": 0o755},
            )

            runtime_dir = extract_runtime(archive, root / "extract")

            self.assertEqual((runtime_dir / "ImageMerge").stat().st_mode & 0o777, 0o755)
            self.assertEqual((runtime_dir / "_opcode.so").stat().st_mode & 0o777, 0o755)

    def run_build(self, keep_in_tarball, check_result=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "runtime.zip"
            write_runtime_zip(
                archive,
                {"ImageMerge/ImageMerge": 0o755, "ImageMerge/_opcode.so": 0o644},
            )
            output_dir = root / "out"
            package_root = Path(__file__).resolve().parents[1]

            def fake_build(command, cwd, check):
                self.assertEqual(command[0], "dpkg-buildpackage")
                self.assertIn("-S", command)
                self.assertIn("-sa", command)
                self.assertIn("-I.imagemerge-keep-everything", command)
                self.assertIn("-kABCDEF", command)
                self.assertIn("-pC:\\signer", command)
                changelog = (cwd / "debian" / "changelog").read_text(encoding="utf-8")
                self.assertIn("imagemerge (2.0.3ubuntu24.04.1) noble;", changelog)
                control = (cwd / "debian" / "control").read_text(encoding="utf-8")
                self.assertIn("Maintainer: TamKungZ_ <maintainer@example.org>", control)
                self.assertTrue((cwd / "runtime" / "ImageMerge" / "ImageMerge").is_file())
                self.assertTrue((cwd / "runtime" / "ImageMerge" / "_opcode.so").is_file())
                self.assertTrue((cwd / "packaging" / "imagemerge").is_file())
                self.assertNotIn(b"\r", (cwd / "debian" / "rules").read_bytes())
                (cwd.parent / "imagemerge_2.0.3ubuntu24.04.1_source.changes").write_text(
                    "signed source changes",
                    encoding="utf-8",
                )
                (cwd.parent / "imagemerge_2.0.3ubuntu24.04.1.dsc").write_text(
                    "source descriptor",
                    encoding="utf-8",
                )
                with tarfile.open(
                    cwd.parent / "imagemerge_2.0.3ubuntu24.04.1.tar.xz", "w:xz"
                ) as tar_file:
                    for path in sorted((cwd / "runtime").rglob("*")):
                        if path.is_file() and keep_in_tarball(path):
                            tar_file.add(
                                path,
                                arcname=f"{cwd.name}/{path.relative_to(cwd).as_posix()}",
                            )

            with patch("scripts.build_launchpad_source.subprocess.run", side_effect=fake_build):
                changes = build_source_package(
                    package_root,
                    archive,
                    "v2.0.3",
                    "noble",
                    output_dir,
                    "ABCDEF",
                    Path("C:\\signer"),
                    "maintainer@example.org",
                )
            if check_result is not None:
                check_result(changes, output_dir)

    def test_build_source_package_stages_matching_suite_and_signing_args(self):
        def check_result(changes, output_dir):
            self.assertEqual(changes.name, "imagemerge_2.0.3ubuntu24.04.1_source.changes")
            self.assertTrue(changes.is_file())
            self.assertTrue((output_dir / "imagemerge_2.0.3ubuntu24.04.1.dsc").is_file())
            self.assertTrue((output_dir / "imagemerge_2.0.3ubuntu24.04.1.tar.xz").is_file())

        self.run_build(lambda path: True, check_result)

    def test_build_source_package_refuses_tarball_missing_runtime_files(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete package"):
            self.run_build(lambda path: path.suffix != ".so")


if __name__ == "__main__":
    unittest.main()
