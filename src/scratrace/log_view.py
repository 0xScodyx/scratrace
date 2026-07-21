#!/usr/bin/env python3
"""Вывод scratrace.log в терминал с ANSI-цветами."""

from __future__ import annotations

import sys

from scratrace.osint.log import LOG_PATH


def main() -> None:
    if not LOG_PATH.exists():
        print(f"scratrace.log не найден: {LOG_PATH}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(LOG_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
