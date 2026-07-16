import json
from pathlib import Path

import platformdirs

# settings.json живёт в user config dir — пользователю не нужно думать о путях.
_SETTINGS_DIR = Path(platformdirs.user_config_dir("scratrace", "scratrace"))
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"

_DEFAULTS = {"language": "en"}


class Settings:
    """Persistence for user settings, stored as settings.json in the user config dir."""

    def __init__(self) -> None:
        self._data = dict(_DEFAULTS)
        self._load()

    @property
    def language(self) -> str:
        return self._data["language"]

    @language.setter
    def language(self, value: str) -> None:
        self._data["language"] = value
        self._save()

    def _load(self) -> None:
        if not _SETTINGS_PATH.exists():
            return
        loaded = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        # Сливаем с дефолтами, чтобы новые ключи не ломали старый файл.
        self._data.update({k: loaded[k] for k in _DEFAULTS if k in loaded})

    def _save(self) -> None:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(json.dumps(self._data, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
