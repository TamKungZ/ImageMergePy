import argparse
from pathlib import Path

from .config import APP_FALLBACK_TITLE, SUPPORTED_LANGS, detect_language
from .constants import (
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
)
from .i18n import I18n
from .media_ordering import normalize_prefix
from .models import Logger, ProcessOptions, SourceFolder
from .pipeline import process_media


def parse_cli_input(entry: str) -> SourceFolder:
    raw = entry.strip()
    if not raw:
        raise ValueError("Input entry cannot be empty")

    if "::" in raw:
        path_text, prefix_text = raw.rsplit("::", 1)
    else:
        path_text, prefix_text = raw, ""

    if not path_text.strip():
        raise ValueError("Input path cannot be empty")

    return SourceFolder(
        path=Path(path_text).expanduser().resolve(),
        prefix=normalize_prefix(prefix_text),
    )


def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_FALLBACK_TITLE,
        description="ImageMerge CLI mode",
    )
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode without opening GUI")
    parser.add_argument("--input", action="append", default=[], metavar="PATH[::PREFIX]",
                        help="Input folder entry, repeatable.")
    parser.add_argument("--output", default="", metavar="PATH", help="Output folder path")
    parser.add_argument("--mode", default=MODE_COPY_KEEP,
                        choices=[MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE, MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER],
                        help="Process mode")
    parser.add_argument("--clear-output", action="store_true",
                        help="Clear media files in output before processing")
    parser.add_argument("--remove-duplicates", action="store_true",
                        help="Inside organizer: remove duplicate files by content hash + extension")
    parser.add_argument("--allow-duplicates", action="store_true",
                        help="Import duplicate files instead of skipping matching content")
    parser.add_argument("--no-safe-temp", action="store_true",
                        help="Disable safe temp workspace staging and write directly to output")
    parser.add_argument("--lang", default="", choices=sorted(SUPPORTED_LANGS), help="CLI log language")
    return parser


def run_cli(argv: list[str]) -> int:
    parser = create_cli_parser()
    args = parser.parse_args(argv)

    if not (args.cli or args.input or args.output):
        parser.print_help()
        return 0

    is_organizer = args.mode in {MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER}
    if not args.input and not is_organizer:
        parser.error("--input is required in CLI mode")
    if not args.output:
        parser.error("--output is required in CLI mode")
    if args.remove_duplicates and args.mode != MODE_INSIDE_FOLDER:
        parser.error("--remove-duplicates can only be used with --mode inside_folder")
    if args.remove_duplicates and args.allow_duplicates:
        parser.error("--remove-duplicates cannot be used with --allow-duplicates")
    if args.clear_output and args.mode == MODE_INSIDE_FOLDER:
        parser.error("--clear-output cannot be used with --mode inside_folder")

    try:
        inputs = [parse_cli_input(entry) for entry in args.input]
    except ValueError as exc:
        parser.error(str(exc))
    for folder in inputs:
        if not folder.path.is_dir():
            parser.error(f"Input path is not an existing directory: {folder.path}")

    options = ProcessOptions(
        mode=args.mode,
        output_dir=Path(args.output).expanduser().resolve(),
        inputs=inputs,
        clear_output_first=args.clear_output,
        remove_duplicates_in_place=args.remove_duplicates,
        allow_duplicate_files=args.allow_duplicates,
        use_safe_temp_workspace=not args.no_safe_temp,
    )
    tr = I18n(args.lang or detect_language()).t
    process_media(options, Logger(lambda text: print(text, flush=True)), tr)
    return 0
