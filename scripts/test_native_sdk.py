import argparse
import ctypes
import json
import platform
import sys
import tempfile
from pathlib import Path


def locate_build_outputs(root: Path) -> tuple[Path, Path]:
    if sys.platform == "win32":
        library = root / "native" / "imagemerge-sdk" / "target" / "release" / "imagemerge.dll"
        executable_candidates = [
            root / "dist" / "windows" / "MainApp.dist" / "ImageMerge.exe",
            root / "dist" / "windows" / "ImageMerge.dist" / "ImageMerge.exe",
        ]
    elif sys.platform == "darwin":
        library = (
            root
            / "native"
            / "imagemerge-sdk"
            / "target"
            / "release"
            / "libimagemerge.dylib"
        )
        executable_candidates = [
            root / "dist" / "macos-binary" / "MainApp.dist" / "ImageMerge",
            root / "dist" / "macos-binary" / "ImageMerge.dist" / "ImageMerge",
        ]
    else:
        library = (
            root
            / "native"
            / "imagemerge-sdk"
            / "target"
            / "release"
            / "libimagemerge.so"
        )
        executable_candidates = [
            root / "dist" / "linux" / "MainApp.dist" / "ImageMerge",
            root / "dist" / "linux" / "ImageMerge.dist" / "ImageMerge",
        ]

    executable = next((path for path in executable_candidates if path.is_file()), None)
    if not library.is_file():
        raise FileNotFoundError(f"Native SDK library not found: {library}")
    if executable is None:
        raise FileNotFoundError(
            f"ImageMerge executable not found in: {', '.join(map(str, executable_candidates))}"
        )
    return library, executable


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the Native SDK against a standalone build.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    library_path, executable_path = locate_build_outputs(root)
    library = ctypes.CDLL(str(library_path))
    library.imagemerge_sdk_version.argtypes = []
    library.imagemerge_sdk_version.restype = ctypes.c_char_p
    library.imagemerge_sdk_run.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    library.imagemerge_sdk_run.restype = ctypes.c_void_p
    library.imagemerge_sdk_free_string.argtypes = [ctypes.c_void_p]
    library.imagemerge_sdk_free_string.restype = None

    version = library.imagemerge_sdk_version().decode("ascii")
    if not version:
        raise RuntimeError("Native SDK returned an empty version")

    with tempfile.TemporaryDirectory(prefix="imagemerge-sdk-test-") as temp_dir:
        request = json.dumps(
            {
                "output": temp_dir,
                "mode": "main_folder",
                "safe_temp": False,
                "lang": "en",
            }
        )
        result_pointer = library.imagemerge_sdk_run(
            str(executable_path).encode("utf-8"),
            request.encode("utf-8"),
        )
        if not result_pointer:
            raise RuntimeError("Native SDK returned a null result")
        try:
            result = json.loads(ctypes.string_at(result_pointer).decode("utf-8"))
        finally:
            library.imagemerge_sdk_free_string(result_pointer)

    if not result.get("ok"):
        raise RuntimeError(
            f"Native SDK invocation failed (version {version}): "
            f"{result.get('error') or result.get('stderr') or result}"
        )
    if result.get("exit_code") != 0:
        raise RuntimeError(f"ImageMerge returned an unexpected status: {result}")

    print(f"Native SDK {version} launched {executable_path.name} successfully on {platform.platform()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
