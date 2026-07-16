import sys

from rich.traceback import install as install_rich_traceback

from .banner import print_banner
from .i18n import I18n
from .settings import Settings
from . import ui
from .osint import UserName


# title_key -> (build UserName-like checker, run it).
# The runner returns {category: [urls]}.
def _run_username(value: str, on_progress=None):
    # check_username_sites() is already synchronous (it runs asyncio.run
    # internally) — calling it inside another asyncio.run raises
    # "a coroutine was expected". So invoke it directly.
    return UserName(value).check_username_sites(on_progress)


_SEARCHERS = {
    "search_username_title": _run_username,
}

# category key (from UserName) -> i18n key with the human-readable label
_CATEGORY_KEYS = {
    "social": "category_social",
    "forums": "category_forums",
    "blogs": "category_blogs",
    "gaming": "category_gaming",
    "dev": "category_dev",
    "creative": "category_creative",
    "misc": "category_misc",
    "professional": "category_professional",
    "people_search": "category_people_search",
    "links": "category_links",
}

# Control signals returned by menu loops.
BACK = "back"
EXIT = "exit"


class Menu:
    """Base class for every interactive menu screen."""

    def __init__(self, i18n: I18n, settings: Settings) -> None:
        self.i18n = i18n
        self.settings = settings

    def _render(self) -> None:
        """Render the banner (if this is a top-level screen) and the menu body."""
        raise NotImplementedError

    def run(self) -> str:
        """Run the menu loop until the user backs out (BACK) or quits (EXIT)."""
        raise NotImplementedError

    def _ask(self) -> str:
        return ui.prompt(f"{ui.gradient_text(self.i18n.t('select_option'))}: ").strip()

    def _invalid(self) -> None:
        ui.console.print(f"[bold red]{self.i18n.t('invalid_option')}[/]")
        ui.pause(self.i18n.t("press_continue"))


class MainMenu(Menu):
    def _render(self) -> None:
        ui.clear()
        print_banner()
        rows = [
            self.i18n.t("menu_osint"),
            self.i18n.t("menu_settings"),
            self.i18n.t("menu_faq"),
            self.i18n.t("menu_exit"),
        ]
        ui.render(ui.gradient_table(self.i18n.t("main_menu_title"), rows))

    def run(self) -> str:
        while True:
            self._render()
            choice = self._ask()
            if choice == "1":
                OsintMenu(self.i18n, self.settings).run()
            elif choice == "2":
                SettingsMenu(self.i18n, self.settings).run()
            elif choice == "3":
                FaqMenu(self.i18n, self.settings).run()
            elif choice == "0":
                ui.console.print(self.i18n.t("goodbye"))
                return EXIT
            else:
                self._invalid()


class OsintMenu(Menu):
    def _render(self) -> None:
        ui.clear()
        print_banner()
        rows = [
            self.i18n.t("osint_username"),
            self.i18n.t("osint_email"),
            self.i18n.t("osint_fio"),
            self.i18n.t("osint_phone"),
            self.i18n.t("osint_back"),
        ]
        ui.render(ui.gradient_table(self.i18n.t("osint_title"), rows))

    def run(self) -> str:
        while True:
            self._render()
            choice = self._ask()
            if choice == "1":
                SearchScreen(
                    self.i18n, self.settings, "search_username_title", "enter_username"
                ).run()
            elif choice == "2":
                SearchScreen(
                    self.i18n, self.settings, "search_email_title", "enter_email"
                ).run()
            elif choice == "3":
                SearchScreen(
                    self.i18n, self.settings, "search_fio_title", "enter_fio"
                ).run()
            elif choice == "4":
                SearchScreen(
                    self.i18n, self.settings, "search_phone_title", "enter_phone"
                ).run()
            elif choice == "0":
                return BACK
            else:
                self._invalid()


class SearchScreen(Menu):
    """Экран ввода для одного вида поиска. 'q' в поле ввода возвращает в меню OSINT."""

    def __init__(
        self, i18n: I18n, settings: Settings, title_key: str, prompt_key: str
    ) -> None:
        super().__init__(i18n, settings)
        self.title_key = title_key
        self.prompt_key = prompt_key

    def _render(self) -> None:
        ui.clear()
        print_banner()
        ui.render(
            ui.gradient_table(
                self.i18n.t(self.title_key),
                [self.i18n.t(self.prompt_key), self.i18n.t("input_back_hint")],
            )
        )

    def run(self) -> str:
        while True:
            self._render()
            value = ui.prompt(
                f"{ui.gradient_text(self.i18n.t(self.prompt_key))}: "
            ).strip()
            if value.lower() == "q":
                return BACK
            if not value:
                continue
            self._search(value)

    def _search(self, value: str) -> None:
        search_fn = _SEARCHERS.get(self.title_key)
        if search_fn is None:
            # TODO: implement search for email / full name / phone
            ui.render(
                ui.gradient_table(
                    self.i18n.t(self.title_key),
                    [f"{self.i18n.t('search_todo')}: {value}"],
                )
            )
            ui.pause(self.i18n.t("press_continue"))
            return

        import threading
        import time

        from rich.console import Group
        from rich.live import Live

        checker = UserName(value)
        total = len(checker.targets())

        results: dict[str, list[str]] = {c: [] for c in _CATEGORY_KEYS}
        # Live list: each found url appears immediately under its category.
        live: dict[str, list[str]] = {c: [] for c in _CATEGORY_KEYS}
        done = 0
        lock = threading.Lock()

        def on_progress(cat: str, url: str | None) -> None:
            nonlocal done
            done += 1
            if url:
                with lock:
                    live[cat].append(url)

        def worker() -> None:
            nonlocal results
            results = search_fn(value, on_progress=on_progress)

        def build_table() -> "object":
            with lock:
                found = sum(len(v) for v in live.values())
                rows = [f"{self.i18n.t('search_total')}: {found}"]
                for cat, urls in live.items():
                    if not urls:
                        continue
                    label = self.i18n.t(_CATEGORY_KEYS.get(cat, cat))
                    rows.append("")
                    rows.append(f"{label} ({len(urls)})")
                    rows.extend(
                        [f"  {u}" for u in urls]
                    )  # list of str, not a generator
            return ui.gradient_table(self.i18n.t("search_results_title"), rows)

        ui.clear()
        print_banner()

        progress = ui.progress_bar(total)
        task = progress.add_task(self.i18n.t("search_running"), total=total)

        # One Live frame holds BOTH the progress bar and the growing results
        # table, redrawn in place -- no reprinting, no terminal spam.
        with Live(
            console=ui.console, refresh_per_second=12, transient=False
        ) as live_view:
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            while thread.is_alive() or done < total:
                progress.update(task, completed=done)
                live_view.update(Group(progress, build_table()))
                time.sleep(0.1)
            thread.join()
            progress.update(task, completed=total)
            live_view.update(Group(progress, build_table()))

        # Final render with the authoritative results (reuse the live feed so
        # it matches what was shown during the search), then wait for Enter.
        with lock:
            live = {c: v for c, v in results.items()}
        ui.clear()
        print_banner()
        ui.render(build_table())
        ui.pause(self.i18n.t("press_continue"))
        #     ui.render(build_table())
        # ui.pause(self.i18n.t("press_continue"))


class SettingsMenu(Menu):
    def _render(self) -> None:
        ui.clear()
        print_banner()
        rows = [
            self.i18n.t("settings_language"),
            self.i18n.t("lang_ru"),
            self.i18n.t("lang_en"),
            self.i18n.t("lang_cn"),
            self.i18n.t("settings_back"),
        ]
        ui.render(ui.gradient_table(self.i18n.t("settings_title"), rows))

    def run(self) -> str:
        while True:
            self._render()
            choice = self._ask()
            if choice == "1":
                self._set_language("ru")
            elif choice == "2":
                self._set_language("en")
            elif choice == "3":
                self._set_language("cn")
            elif choice == "0":
                return BACK
            else:
                self._invalid()

    def _set_language(self, lang: str) -> None:
        self.i18n.lang = lang
        self.settings.language = lang
        ui.console.print(f"[green]{self.i18n.t('language_set')}: {lang}[/]")


class FaqMenu(Menu):
    def run(self) -> str:
        ui.clear()
        ui.render(
            ui.gradient_table(
                self.i18n.t("faq_title"),
                [self.i18n.t("faq_text"), self.i18n.t("press_enter")],
            )
        )
        ui.pause("")
        return BACK


def main() -> None:
    install_rich_traceback()
    settings = Settings()
    i18n = I18n(settings.language)
    MainMenu(i18n, settings).run()


if __name__ == "__main__":
    main()
