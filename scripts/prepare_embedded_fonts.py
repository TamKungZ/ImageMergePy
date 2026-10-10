import hashlib
import os
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_FONTS_COMMIT = "bd8f81ddb5c74d5c8897b36ad88b440266245103"
FONT_FILES = {
    "Noto Sans": (
        "notosans",
        "NotoSans[wdth,wght].ttf",
        "bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d",
    ),
    "Noto Sans Thai": (
        "notosansthai",
        "NotoSansThai[wdth,wght].ttf",
        "5a1c559bb539583c8a1fd99d1c5b9491e5e14478c9cd2bd0970d5c3096cc9ef8",
    ),
    "Noto Sans JP": (
        "notosansjp",
        "NotoSansJP[wght].ttf",
        "c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f",
    ),
    "Noto Sans KR": (
        "notosanskr",
        "NotoSansKR[wght].ttf",
        "194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252",
    ),
    "Noto Sans SC": (
        "notosanssc",
        "NotoSansSC[wght].ttf",
        "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
    ),
    "Noto Sans Arabic": (
        "notosansarabic",
        "NotoSansArabic[wdth,wght].ttf",
        "63111b5b2e074dd48cc67692e0a2726d86ee94c1c37fe8598257b7b4e87e869e",
    ),
}
LICENSE_FILES = {
    "NotoSans-OFL.txt": (
        "notosans",
        "cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a",
    ),
    "NotoSansThai-OFL.txt": (
        "notosansthai",
        "2e98fd23a52d253db8612cd5942c8f2ff4111b21d2367050fdca91d8ccc374a0",
    ),
    "NotoSansJP-OFL.txt": (
        "notosansjp",
        "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9",
    ),
    "NotoSansKR-OFL.txt": (
        "notosanskr",
        "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9",
    ),
    "NotoSansSC-OFL.txt": (
        "notosanssc",
        "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9",
    ),
    "NotoSansArabic-OFL.txt": (
        "notosansarabic",
        "07fc70bfeb985cc1a87a8587d0a0c80bab11c86c9dc3fd95b6f0cb332f983e96",
    ),
}
FONT_DIR = ROOT / "build" / "fonts"
FONT_SOURCE_DIR = os.environ.get("IMAGEMERGE_FONT_SOURCE_DIR")


def download_verified_file(directory: str, file_name: str, expected_sha256: str) -> bytes:
    if FONT_SOURCE_DIR:
        content = (Path(FONT_SOURCE_DIR) / directory / file_name).read_bytes()
    else:
        url = (
            "https://raw.githubusercontent.com/google/fonts/"
            f"{GOOGLE_FONTS_COMMIT}/ofl/{directory}/{file_name}"
        )
        request = Request(url, headers={"User-Agent": "ImageMerge-build"})
        with urlopen(request, timeout=60) as response:
            content = response.read()

    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"SHA-256 mismatch for {directory}/{file_name}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    return content


def main() -> None:
    if FONT_DIR.exists():
        shutil.rmtree(FONT_DIR)
    FONT_DIR.mkdir(parents=True)

    for family, (directory, file_name, expected_sha) in FONT_FILES.items():
        content = download_verified_file(directory, file_name, expected_sha)
        (FONT_DIR / file_name).write_bytes(content)
        print(f"Downloaded and verified {family}")

    for license_name, (directory, expected_sha) in LICENSE_FILES.items():
        content = download_verified_file(directory, "OFL.txt", expected_sha)
        (FONT_DIR / license_name).write_bytes(content)

    print(f"Prepared Noto Sans fonts and licenses in {FONT_DIR}")


if __name__ == "__main__":
    main()
