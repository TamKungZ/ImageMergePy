"""Start the compiled GUI for a couple of seconds and fail if it crashes.

The Native SDK smoke test and the CLI never open a window, so a Qt/Nuitka crash on
GUI start-up (e.g. a native style plugin segfault) would otherwise reach a release.
"""
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_executable() -> Path:
    system = platform.system().lower()
    if system == "windows":
        out, name = "windows", "ImageMerge.exe"
    elif system == "darwin":
        out, name = "macos-binary", "ImageMerge"
    else:
        out, name = "linux", "ImageMerge"
    for folder in ("MainApp.dist", "ImageMerge.dist"):
        candidate = ROOT / "dist" / out / folder / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"ImageMerge executable not found under dist/{out}")


def main() -> int:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else find_executable()
    state_dir = tempfile.mkdtemp(prefix="imagemerge-gui-smoke-")
    env = dict(os.environ, IMAGEMERGE_GUI_SMOKE="1", LOCALAPPDATA=state_dir, XDG_STATE_HOME=state_dir)
    if platform.system().lower() != "windows":
        env.setdefault("QT_QPA_PLATFORM", "offscreen")  # no display on CI; Windows uses the real platform

    print(f"Starting GUI: {exe}")
    try:
        result = subprocess.run([str(exe)], env=env, timeout=90, capture_output=True, text=True)
        code = result.returncode
        print(result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        print("GUI did not exit within 90 seconds")
        code = -1

    log = Path(state_dir) / "ImageMerge" / "error.log"
    if log.is_file():
        print("---- error.log ----")
        print(log.read_text(encoding="utf-8", errors="replace"))
    if code != 0:
        print(f"GUI smoke test FAILED (exit code {code})")
        return 1
    print("GUI smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
