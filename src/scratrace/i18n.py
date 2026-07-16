import json
from pathlib import Path


class I18n:
    """Loads translations from lang.json and resolves keys for the active language."""

    def __init__(self, lang: str = "ru") -> None:
        self._data = json.loads(Path(__file__).with_name("lang.json").read_text(encoding="utf-8"))
        self._lang = lang
        if lang not in self._data:
            raise ValueError(f"Unknown language: {lang}")

    @property
    def lang(self) -> str:
        return self._lang

    @lang.setter
    def lang(self, value: str) -> None:
        if value not in self._data:
            raise ValueError(f"Unknown language: {value}")
        self._lang = value

    def t(self, key: str) -> str:
        return self._data[self._lang][key]
