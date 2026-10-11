"""Files that are already organized must stay where they are, in every mode."""
import os
import random
import tempfile
import unittest
from pathlib import Path

from src.media_merge.constants import MODE_COPY_KEEP, MODE_INSIDE_FOLDER, MODE_MAIN_FOLDER
from src.media_merge.media_ordering import organize_output
from src.media_merge.models import Logger, ProcessOptions, SourceFolder
from src.media_merge.pipeline import process_media

BASE_TIME = 1_700_000_000


def make_library(folder: Path, count: int, ext: str = ".jpg", shuffle_mtime: bool = True) -> None:
    """0001.. files whose content identifies them; mtimes are NOT in number order,
    like files copied by a previous Merge (copy2 keeps the source mtime)."""
    rng = random.Random(7)
    for i in range(1, count + 1):
        path = folder / f"{i:04d}{ext}"
        path.write_text(f"file-{i}")
        stamp = BASE_TIME - rng.randint(0, 10**7) if shuffle_mtime else BASE_TIME + i
        os.utime(path, (stamp, stamp))


def snapshot(folder: Path) -> dict[str, str]:
    """content -> file name, ignoring the hidden staging folder."""
    return {p.read_text(): p.name for p in folder.iterdir() if p.is_file()}


def run(mode: str, output: Path, inputs=(), safe: bool = True, **kw):
    options = ProcessOptions(
        mode=mode,
        output_dir=output,
        inputs=[SourceFolder(Path(p), pre) for p, pre in inputs],
        use_safe_temp_workspace=safe,
        **kw,
    )
    return process_media(options, Logger(lambda _text: None))


class OrganizedFolderStaysPut(unittest.TestCase):
    def test_tidy_leaves_an_organized_folder_untouched(self):
        for safe in (True, False):
            with self.subTest(safe=safe), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                make_library(out, 60)
                before = snapshot(out)
                run(MODE_INSIDE_FOLDER, out, safe=safe)
                self.assertEqual(snapshot(out), before)

    def test_library_mode_leaves_an_organized_folder_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            make_library(out, 60)
            before = snapshot(out)
            run(MODE_MAIN_FOLDER, out)
            self.assertEqual(snapshot(out), before)

    def test_tidy_unnumbered_file_goes_to_the_end_not_by_mtime(self):
        """The reported bug: renaming the last file to ``a`` must keep it last."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            make_library(out, 50)
            (out / "0050.jpg").rename(out / "a.jpg")
            before = snapshot(out)
            run(MODE_INSIDE_FOLDER, out)
            after = snapshot(out)
            self.assertEqual(after["file-50"], "0050.jpg")
            for i in range(1, 50):
                self.assertEqual(after[f"file-{i}"], before[f"file-{i}"])

    def test_gap_closes_by_shifting_later_files_up(self):
        for mode in (MODE_INSIDE_FOLDER, MODE_MAIN_FOLDER):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                make_library(out, 10)
                (out / "0004.jpg").unlink()
                run(mode, out)
                after = snapshot(out)
                for i in (1, 2, 3):
                    self.assertEqual(after[f"file-{i}"], f"{i:04d}.jpg")
                for i in range(5, 11):
                    self.assertEqual(after[f"file-{i}"], f"{i - 1:04d}.jpg")

    def test_new_file_in_the_middle_does_not_reorder_existing_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            make_library(out, 5, ext=".png")
            (out / "extra.png").write_text("new")
            run(MODE_INSIDE_FOLDER, out)
            after = snapshot(out)
            for i in range(1, 6):
                self.assertEqual(after[f"file-{i}"], f"{i:04d}.png")
            self.assertEqual(after["new"], "0006.png")

    def test_prefix_is_kept_and_does_not_affect_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name in ("trip-0001.jpg", "0002.jpg", "more-0003.jpg"):
                (out / name).write_text(name)
            run(MODE_INSIDE_FOLDER, out)
            self.assertEqual(
                sorted(p.name for p in out.iterdir() if p.is_file()),
                ["0002.jpg", "more-0003.jpg", "trip-0001.jpg"],
            )

    def test_merge_appends_after_existing_files_even_across_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, src = root / "out", root / "src"
            out.mkdir()
            src.mkdir()
            make_library(out, 5, ext=".jpg")
            (src / "1.png").write_text("new-png")  # .png sorts before .jpg in the extension order
            before = snapshot(out)
            run(MODE_COPY_KEEP, out, inputs=[(src, "")])
            after = snapshot(out)
            for content, name in before.items():
                self.assertEqual(after[content], name)
            self.assertEqual(after["new-png"], "0006.png")

    def test_main_folder_import_appends_and_keeps_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, src = root / "out", root / "src"
            out.mkdir()
            src.mkdir()
            make_library(out, 5)
            (src / "x.mp4").write_text("vid")
            before = snapshot(out)
            run(MODE_MAIN_FOLDER, out, inputs=[(src, "")])
            after = snapshot(out)
            for content, name in before.items():
                self.assertEqual(after[content], name)
            self.assertEqual(after["vid"], "0006.mp4")


class RawNamesKeepTheDocumentedRules(unittest.TestCase):
    def test_images_before_videos_and_numeric_order_for_raw_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name in ("2.mp4", "10.jpg", "2.jpg", "1.png"):
                (out / name).write_text(name)
            organize_output(out)
            self.assertEqual(
                {p.read_text(): p.name for p in out.iterdir()},
                {"1.png": "0001.png", "2.jpg": "0002.jpg", "10.jpg": "0003.jpg", "2.mp4": "0004.mp4"},
            )

    def test_tidy_orders_raw_names_by_mtime_within_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name, offset in (("b.jpg", 1), ("a.jpg", 2), ("c.jpg", 0)):
                path = out / name
                path.write_text(name)
                os.utime(path, (BASE_TIME + offset, BASE_TIME + offset))
            organize_output(out, sort_by_file_mtime=True)
            self.assertEqual(
                {p.read_text(): p.name for p in out.iterdir()},
                {"c.jpg": "0001.jpg", "b.jpg": "0002.jpg", "a.jpg": "0003.jpg"},
            )


if __name__ == "__main__":
    unittest.main()
