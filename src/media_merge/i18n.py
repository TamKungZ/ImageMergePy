import json

from .config import DEFAULT_LANG, LOCALES_DIR, SUPPORTED_LANGS
from embedded_locales import EMBEDDED_LOCALES as FILE_EMBEDDED_LOCALES

class I18n:
    def __init__(self, lang: str):
        self.catalogs: dict[str, dict[str, str]] = {}
        for code in sorted(SUPPORTED_LANGS):
            self._load_catalog(code)
        if not self.catalogs.get(DEFAULT_LANG):
            self.catalogs[DEFAULT_LANG] = {}
        self.lang = lang if lang in self.catalogs else DEFAULT_LANG

    def _load_catalog(self, lang: str):
        catalog: dict[str, str] = {}
        locale_file = LOCALES_DIR / f"{lang}.json"
        if locale_file.exists():
            try:
                parsed = json.loads(locale_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    catalog = {str(key): str(value) for key, value in parsed.items()}
            except Exception:
                catalog = {}
        if not catalog:
            embedded = FILE_EMBEDDED_LOCALES.get(lang, {})
            catalog = {str(key): str(value) for key, value in embedded.items()}
        self.catalogs[lang] = catalog

    def t(self, key: str, **kwargs) -> str:
        text = self.catalogs.get(self.lang, {}).get(key)
        if text is None:
            text = self.catalogs.get(DEFAULT_LANG, {}).get(key, key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text


def t_identity(key: str, **kwargs) -> str:
    if not kwargs:
        return key
    try:
        return key.format(**kwargs)
    except Exception:
        return key


