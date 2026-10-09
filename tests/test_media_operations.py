import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.media_merge.media_ops import (
    Logger,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    process_media,
)
from src.media_merge.media_ordering import build_output_name, normalize_prefix, organize_output


class MediaOrderingTests(unittest.TestCase):
    def test_output_name_normalizes_prefix_and_extension(self):
        self.assertEqual(normalize_prefix(" Vacation Photos "), "vacation-photos")
        self.assertEqual(
            build_output_name(3, ".JPG", " Vacation Photos "),
            "vacation-photos-0003.jpg",
        )

    def test_organize_output_keeps_images_before_videos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "2.mp4").write_bytes(b"video")
            (output_dir / "10.jpg").write_bytes(b"image")
            (output_dir / "1.png").write_bytes(b"image")

            organized = organize_output(output_dir)

            self.assertEqual(
                [path.name for path in organized],
                ["0001.png", "0002.jpg", "0003.mp4"],
            )


class MediaProcessingTests(unittest.TestCase):
    def test_allowing_duplicates_skips_hashing_existing_and_source_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "source.jpg").write_bytes(b"same content")
            (output_dir / "0001.jpg").write_bytes(b"same content")
            logs: list[str] = []

            with patch(
                "src.media_merge.media_ops.sha256_file",
                side_effect=AssertionError("hashing is unnecessary when duplicates are allowed"),
            ):
                process_media(
                    input_dir_configs=[{"path": input_dir, "prefix": ""}],
                    output_dir=output_dir,
                    mode=MODE_COPY_KEEP,
                    clear_output_first=False,
                    remove_duplicates_in_place=False,
                    allow_duplicate_files=True,
                    use_safe_temp_workspace=False,
                    logger=Logger(logs.append),
                )

            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                ["0001.jpg", "0002.jpg"],
            )
            self.assertIn("log_copied", logs)
            self.assertNotIn("log_duplicate_skip", logs)

    def test_disallowing_duplicates_skips_matching_source_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "source.jpg").write_bytes(b"same content")
            (output_dir / "0001.jpg").write_bytes(b"same content")
            logs: list[str] = []

            process_media(
                input_dir_configs=[{"path": input_dir, "prefix": ""}],
                output_dir=output_dir,
                mode=MODE_COPY_KEEP,
                clear_output_first=False,
                remove_duplicates_in_place=False,
                allow_duplicate_files=False,
                use_safe_temp_workspace=False,
                logger=Logger(logs.append),
            )

            self.assertEqual(
                [path.name for path in output_dir.iterdir()],
                ["0001.jpg"],
            )
            self.assertIn("log_duplicate_skip", logs)

    def test_inside_organizer_only_organizes_once_without_dedupe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "photo.jpg").write_bytes(b"photo")
            logs: list[str] = []

            with patch(
                "src.media_merge.media_ops.organize_output",
                wraps=organize_output,
            ) as organize:
                process_media(
                    input_dir_configs=[],
                    output_dir=output_dir,
                    mode=MODE_INSIDE_FOLDER,
                    clear_output_first=False,
                    remove_duplicates_in_place=False,
                    allow_duplicate_files=False,
                    use_safe_temp_workspace=False,
                    logger=Logger(logs.append),
                )

            organize.assert_called_once()
            self.assertEqual([path.name for path in output_dir.iterdir()], ["0001.jpg"])


if __name__ == "__main__":
    unittest.main()
