import argparse
from pathlib import Path

from .config import APP_FALLBACK_TITLE, SUPPORTED_LANGS, detect_language
from .i18n import I18n
from .media_ops import (
    Logger,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
    normalize_prefix,
    process_media,
)

def parse_cli_input(entry: str) -> dict:
    raw = (entry or "").strip()
    if not raw:
        raise ValueError("Input entry cannot be empty")

    if "::" in raw:
        path_text, prefix_text = raw.rsplit("::", 1)
    else:
        path_text, prefix_text = raw, ""

    path = Path(path_text).expanduser().resolve()
    prefix = normalize_prefix(prefix_text)
    return {"path": path, "prefix": prefix}


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
                        choices=[MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE, MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER], help="Process mode")
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

    run_cli_mode = args.cli or bool(args.input) or bool(args.output)
    if not run_cli_mode:
        parser.print_help()
        return 0

    if not args.input and args.mode not in {MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER}:
        parser.error("--input is required in CLI mode")
    if not args.output:
        parser.error("--output is required in CLI mode")

    input_configs = [parse_cli_input(entry) for entry in args.input]
    lang = args.lang or detect_language()
    tr = I18n(lang).t
    output_dir = Path(args.output).expanduser().resolve()
    logger = Logger(lambda text: print(text, flush=True))

    process_media(
        input_dir_configs=input_configs,
        output_dir=output_dir,
        mode=args.mode,
        clear_output_first=args.clear_output,
        remove_duplicates_in_place=args.remove_duplicates,
        allow_duplicate_files=args.allow_duplicates,
        use_safe_temp_workspace=(not args.no_safe_temp),
        logger=logger,
        tr=tr,
    )
    return 0


