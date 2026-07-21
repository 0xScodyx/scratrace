"""Логирование scratrace — пишет в scratrace.log с ANSI-цветами."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from platformdirs import user_log_dir


ERROR = 1
WARNING = 2
INFO = 3

LOG_PATH = Path(user_log_dir("scratrace")) / "scratrace.log"

_LEVEL_STYLES = {
    ERROR: ("\033[38;2;180;40;40m", "\033[38;2;220;60;60m"),
    WARNING: ("\033[38;2;200;160;0m", "\033[38;2;230;200;0m"),
    INFO: ("\033[38;2;50;180;50m", "\033[38;2;130;130;130m"),
}

_LEVEL_LABELS = {
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
}

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_RESET = "\033[0m"


def scratrace_log(msg: str, type: int = INFO) -> None:
    """Запись строки в scratrace.log с ANSI-цветами.

    type — ERROR / WARNING / INFO (константы из этого модуля).
    """
    label_color, msg_color = _LEVEL_STYLES.get(type, ("\033[0m", "\033[0m"))
    label = _LEVEL_LABELS.get(type, "UNKNOWN")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} {label_color}{label}:{_RESET} {msg_color}{msg}{_RESET}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
