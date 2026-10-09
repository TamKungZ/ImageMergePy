import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_FONTS_COMMIT = "bd8f81ddb5c74d5c8897b36ad88b440266245103"
FONT_FILES = {
    "Kanit-Regular": (
        "Kanit-Regular.ttf",
        "27170c049660b2f962d3ed28441fd20f4c743503ca031fec9c2b4542d6c52736",
    ),
    "Kanit-Bold": (
        "Kanit-Bold.ttf",
        "5dec5b080dab13de9d2295437c0ff3ec05c9e75587dfc31358c005eb4efa5e70",
    ),
    "Kanit-Italic": (
        "Kanit-Italic.ttf",
        "7cbe69393a7bf948dd49e575369344a907f06b0182e7a618c033c67208abb27d",
    ),
}
OFL_FILE = (
    "OFL.txt",
    "eb998cc5a685b240cdb46a0b5747e70334c8c57bbd7b1f6b044d75719358df67",
)
FONT_DIR = ROOT / "build" / "fonts"
OUTPUT_MODULE = ROOT / "src" / "media_merge" / "_embedded_fonts.py"
FONT_SOURCE_DIR = os.environ.get("IMAGEMERGE_FONT_SOURCE_DIR")


def download_verified_file(file_name: str, expected_sha256: str) -> bytes:
    url = (
        "https://raw.githubusercontent.com/google/fonts/"
        f"{GOOGLE_FONTS_COMMIT}/ofl/kanit/{file_name}"
    )
    if FONT_SOURCE_DIR:
        content = (Path(FONT_SOURCE_DIR) / file_name).read_bytes()
    else:
        request = Request(url, headers={"User-Agent": "ImageMerge-build"})
        with urlopen(request, timeout=60) as response:
            content = response.read()

    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"SHA-256 mismatch for {file_name}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    return content


def main() -> None:
    if FONT_DIR.exists():
        import shutil

        shutil.rmtree(FONT_DIR)
    FONT_DIR.mkdir(parents=True)

    embedded_fonts: dict[str, str] = {}
    for font_name, (file_name, expected_sha) in FONT_FILES.items():
        content = download_verified_file(file_name, expected_sha)
        (FONT_DIR / file_name).write_bytes(content)
        embedded_fonts[font_name] = base64.b64encode(content).decode("ascii")
        print(f"Downloaded and verified {file_name}")

    license_name, license_sha = OFL_FILE
    license_text = download_verified_file(license_name, license_sha)
    (FONT_DIR / license_name).write_bytes(license_text)

    output = "# Auto-generated from Google Fonts Kanit files.\n"
    output += "EMBEDDED_FONTS = "
    output += json.dumps(embedded_fonts, indent=4)
    output += "\n"
    OUTPUT_MODULE.write_text(output, encoding="utf-8")
    print(f"Prepared embedded fonts and license in {FONT_DIR}")


if __name__ == "__main__":
    main()
