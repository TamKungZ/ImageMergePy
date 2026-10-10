import argparse
import os
import sys
from pathlib import Path

from .config import APP_FALLBACK_TITLE, APP_METADATA, SUPPORTED_LANGS, detect_language
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

EXIT_OK = 0
EXIT_COMPLETED_WITH_ERRORS = 3

_EPILOG = """\
examples:
  ImageMerge --input /photos/trip::trip --input /photos/phone --output /library
  ImageMerge --mode move --input ~/Downloads --output ~/Pictures/all --dry-run
  ImageMerge --mode inside_folder --output /library --remove-duplicates

exit codes:
  0    finished successfully
  1    error (set IMAGEMERGE_DEBUG=1 for a traceback)
  2    invalid arguments
  3    finished, but some files could not be processed
  130  interrupted (Ctrl+C); nothing is applied in safe mode
"""


def _warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr, flush=True)


def _configure_streams() -> None:
    """Never crash on characters the console encoding cannot represent.

    On Windows (legacy code pages) and when output is piped, a localized log line
    would otherwise raise UnicodeEncodeError halfway through a run.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                pass


def _version_text() -> str:
    version = APP_METADATA.get("product_version") or APP_METADATA.get("file_version") or "unknown"
    return f"{APP_FALLBACK_TITLE} {version}"


def _split_entry(entry: str) -> tuple[str, str]:
    raw = entry.strip()
    if "::" in raw:
        path_text, prefix_text = raw.rsplit("::", 1)
    else:
        path_text, prefix_text = raw, ""
    return path_text.strip().strip('"').strip(), prefix_text.strip()


def parse_cli_input(entry: str) -> SourceFolder:
    if not entry.strip():
        raise ValueError("Input entry cannot be empty")

    path_text, prefix_text = _split_entry(entry)
    if not path_text:
        raise ValueError("Input path cannot be empty")

    return SourceFolder(
        path=Path(path_text).expanduser().resolve(),
        prefix=normalize_prefix(prefix_text),
    )


def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_FALLBACK_TITLE,
        description="ImageMerge CLI mode",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=_version_text())
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
    parser.add_argument("--dry-run", action="store_true",
                        help="Do everything in the temp workspace and report the result, "
                             "but change no files (needs extra disk space for staging)")
    parser.add_argument("--lang", default="", choices=sorted(SUPPORTED_LANGS), help="CLI log language")
    return parser


def run_cli(argv: list[str]) -> int:
    _configure_streams()
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
    if args.dry_run and args.no_safe_temp:
        parser.error("--dry-run cannot be used with --no-safe-temp")

    output_dir = Path(args.output).expanduser().resolve()
    if output_dir.exists() and not output_dir.is_dir():
        parser.error(f"Output path exists and is not a directory: {output_dir}")

    try:
        inputs = [parse_cli_input(entry) for entry in args.input]
    except ValueError as exc:
        parser.error(str(exc))
    for folder in inputs:
        if not folder.path.is_dir():
            parser.error(f"Input path is not an existing directory: {folder.path}")

    if args.mode == MODE_INSIDE_FOLDER and inputs:
        _warn("--input is ignored in inside_folder mode (only --output is organized).")
        inputs = []

    # Tell the user when a prefix was changed or dropped by normalization.
    for entry, folder in zip(args.input, inputs):
        raw_prefix = _split_entry(entry)[1]
        if raw_prefix and raw_prefix != folder.prefix:
            if folder.prefix:
                _warn(f"Prefix '{raw_prefix}' was normalized to '{folder.prefix}'.")
            else:
                _warn(f"Prefix '{raw_prefix}' has no usable characters (a-z, 0-9, _, -) and was ignored.")

    # The same folder listed twice would only be scanned twice.
    unique_inputs: list[SourceFolder] = []
    seen: set[str] = set()
    for folder in inputs:
        key = os.path.normcase(str(folder.path))
        if key in seen:
            _warn(f"Duplicate input ignored: {folder.path}")
            continue
        seen.add(key)
        unique_inputs.append(folder)

    options = ProcessOptions(
        mode=args.mode,
        output_dir=output_dir,
        inputs=unique_inputs,
        clear_output_first=args.clear_output,
        remove_duplicates_in_place=args.remove_duplicates,
        allow_duplicate_files=args.allow_duplicates,
        use_safe_temp_workspace=not args.no_safe_temp,
        dry_run=args.dry_run,
    )
    tr = I18n(args.lang or detect_language()).t
    stats = process_media(options, Logger(lambda text: print(text, flush=True)), tr)
    return EXIT_COMPLETED_WITH_ERRORS if stats.failed else EXIT_OK