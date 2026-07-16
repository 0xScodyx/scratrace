import os

from rich.box import ROUNDED
from rich.console import Console, RenderableType
from rich.table import Table

console = Console()


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")

# Blue -> cyan -> green gradient stops (no white).
_GRADIENT = [
    (30, 144, 255),   # dodger blue
    (0, 206, 209),    # dark turquoise
    (0, 220, 200),    # aqua
    (46, 196, 110),   # green
]


def _color(pos: float) -> str:
    seg = len(_GRADIENT) - 1
    p = max(0.0, min(1.0, pos)) * seg
    lo = min(int(p), seg - 1)
    hi = lo + 1
    f = p - lo
    c1, c2 = _GRADIENT[lo], _GRADIENT[hi]
    r = round(c1[0] + (c2[0] - c1[0]) * f)
    g = round(c1[1] + (c2[1] - c1[1]) * f)
    b = round(c1[2] + (c2[2] - c1[2]) * f)
    return f"#{r:02X}{g:02X}{b:02X}"


def _gradient_text(text: str, start: float, span: float) -> str:
    if not text:
        return text
    out = []
    for i, ch in enumerate(text):
        pos = start + span * (i / max(1, len(text) - 1))
        out.append(f"[{_color(pos)}]{ch}[/]")
    return "".join(out)


def solid_text(text: str, color: str) -> str:
    """Wrap ``text`` in a single solid color. No per-char tags, so brackets,
    digits and spaces never break the markup."""
    return f"[{color}]{text}[/]"


def plain_text(text: str) -> str:
    """Return ``text`` unchanged (no color tags). Used for the live username
    search feed so colors never show up mid-search."""
    return text


def plain_table(title: str, rows: list[str]) -> "Table":
    """Like :func:`gradient_table` but without any color markup — for the
    username search live feed."""
    table = Table(
        title=title,
        title_justify="center",
        expand=True,
        show_lines=False,
        show_header=False,
        box=ROUNDED,
    )
    table.add_column("")
    for row in rows:
        table.add_row(row)
    return table


# Per-category accent colors (rich-compatible hex). Used for result headings.
CATEGORY_COLORS = {
    "social": "#1E90FF",
    "forums": "#00CED1",
    "blogs": "#00DCC8",
    "gaming": "#2EC46E",
    "dev": "#1FCC8C",
    "creative": "#0FB3A0",
    "misc": "#46C46E",
    "professional": "#14A5F0",
    "people_search": "#0AB9E0",
    "links": "#3AA0D8",
}


def gradient_table(title: str, rows: list[str]) -> Table:
    # Один сплошной блок: без линий между строками, градиент течёт
    # непрерывно сквозь весь блок (заголовок + все пункты).
    title_len = len(title)
    total_chars = title_len + sum(len(r) for r in rows)
    cursor = 0.0

    def flow(text: str) -> str:
        nonlocal cursor
        span = len(text) / max(1, total_chars)
        colored = _gradient_text(text, cursor, span)
        cursor += span
        return colored

    table = Table(
        title=flow(title),
        title_justify="center",
        expand=True,
        show_lines=False,
        show_header=False,
        box=ROUNDED,
        border_style=_color(0.0),
    )
    table.add_column("")
    for row in rows:
        table.add_row(flow(row))
    return table


def render(renderable: RenderableType) -> None:
    console.print(renderable)


def gradient_text(text: str) -> str:
    return _gradient_text(text, 0.0, 1.0)


def prompt(text: str) -> str:
    return console.input(text)


def pause(text: str) -> None:
    console.input(text)


def progress_bar(total: int):
    """Return a rich Progress with a spinner column and a percentage bar.

    The spinner keeps moving (feels alive) while the percentage reflects the
    real ``completed/total`` ratio updated by the caller.
    """
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TextColumn,
        TaskProgressColumn, TimeElapsedColumn,
    )
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
