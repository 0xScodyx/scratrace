"""Миграция строковых маркеров type_url в JSON.

Старые записи Redirect в колонке type_url хранились как текст:
  Redirect("https://...", "marker")

Парсим обёртку, вызываем РЕАЛЬНЫЙ дата-класс Redirect (из osint.sites)
и перезаписываем ячейку в tagged JSON.

Сложные страницы (playwright) маркируются числом PLAYWRIGHT (-999) в type_url,
никакой миграции не требуют — скрипт берётся из pw_scripts по link сайта.
"""

import json
import sqlite3

from .osint.sites import Redirect, SiteRegistry


class TypeUrlConverter:
    CATEGORIES = [
        "SOCIAL", "FORUMS", "BLOGS", "GAMING", "DEV",
        "CREATIVE", "MISC", "PROFESSIONAL", "PEOPLE_SEARCH", "LINKS",
    ]

    def __init__(self) -> None:
        self.con = SiteRegistry._connect()
        self.cur = self.con.cursor()

    # ------------------------------------------------------------------ #
    # вспомогательные (по ролям, имена говорят сами за себя)
    # ------------------------------------------------------------------ #
    def is_redirect(self, cell: str) -> bool:
        return cell.startswith("Redirect(") and cell.endswith(")")

    def redirect_to_json(self, cell: str) -> str | None:
        if not self.is_redirect(cell):
            return None
        inner = cell[len("Redirect(") : -1].strip()
        args = [a.strip() for a in inner.split(",", 1) if a.strip()]
        r = Redirect(final_url=args[0], marker=args[1] if len(args) > 1 else None)
        return json.dumps({"__redirect__": True, **vars(r)}, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # публичный
    # ------------------------------------------------------------------ #
    def convert_redirects(self) -> int:
        updated = 0
        for cat in self.CATEGORIES:
            for link, cell in self.cur.execute(
                f"SELECT link, type_url FROM {cat} WHERE type_url LIKE 'Redirect(%'"
            ).fetchall():
                new = self.redirect_to_json(cell)
                if new is not None:
                    self.cur.execute(
                        f"UPDATE {cat} SET type_url = ? WHERE link = ?", (new, link)
                    )
                    updated += 1
        self.con.commit()
        return updated


def redirects_to_json_db() -> None:
    """Точка входа для app.py: мигрируем Redirect-маркеры в JSON."""
    TypeUrlConverter().convert_redirects()
