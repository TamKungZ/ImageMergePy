import json

from .config import DEFAULT_LANG, LOCALES_DIR, SUPPORTED_LANGS


class I18n:
    """Translator with lazily loaded catalogs (only the active + default language)."""

    def __init__(self, lang: str):
        self._catalogs: dict[str, dict[str, str]] = {}
        self.lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG

    def _catalog(self, code: str) -> dict[str, str]:
        catalog = self._catalogs.get(code)
        if catalog is None:
            catalog = self._load_catalog(code)
            self._catalogs[code] = catalog
        return catalog

    @staticmethod
    def _load_catalog(code: str) -> dict[str, str]:
        catalog: dict[str, str] = {}
        locale_file = LOCALES_DIR / f"{code}.json"
        if locale_file.is_file():
            try:
                parsed = json.loads(locale_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    catalog = {str(key): str(value) for key, value in parsed.items()}
            except (OSError, ValueError):
                catalog = {}
        if not catalog:
            from ._embedded_locales import EMBEDDED_LOCALES

            catalog = {str(k): str(v) for k, v in EMBEDDED_LOCALES.get(code, {}).items()}
        return catalog

    def t(self, key: str, **kwargs) -> str:
        text = self._catalog(self.lang).get(key)
        if text is None:
            text = self._catalog(DEFAULT_LANG).get(key, key)
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text


def t_identity(key: str, **kwargs) -> str:
    if not kwargs:
        return key
    try:
        return key.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return key
