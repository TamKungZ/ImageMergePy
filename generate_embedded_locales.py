import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    locales_dir = root / "locales"
    output_file = root / "embedded_locales.py"

    embedded_locales: dict[str, dict[str, str]] = {}
    for locale_file in sorted(locales_dir.glob("*.json")):
        lang = locale_file.stem
        with open(locale_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid locale format in {locale_file}")

        embedded_locales[lang] = {str(key): str(value) for key, value in data.items()}

    output = "# Auto-generated from locales/*.json\nEMBEDDED_LOCALES = "
    output += json.dumps(embedded_locales, ensure_ascii=False, indent=4)
    output += "\n"

    output_file.write_text(output, encoding="utf-8")
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    main()
