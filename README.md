<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**An OSINT tool to find people by username, e-mail, phone number, and full name.**

Clean links. Playwright-powered. DuckDuckGo dorking built in. Multilingual.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()

</div>

---

## 🔍 What is it

`scratrace` is a console OSINT scanner that walks through a catalog of sites and
finds user profiles by a given identifier. Unlike most alternatives, we **never
report a hit at random**: every link in the catalog is verified for honesty, and
sites that lie are flagged and dropped.

### Supported search types

| Type               | Description                                          |
| ------------------ | ---------------------------------------------------- |
| 🧑 `username`      | Search by nickname across socials, forums, dev, etc. |
| 📧 `email`         | Search by e-mail · _coming soon_                       |
| 📱 `number_phone`  | Search by phone number · _coming soon_                |
| 👤 `full_name`     | Search by first and last name · _coming soon_         |

---

## ⚡ Why scratrace?

> Inspired by [Maigret](https://github.com/soxoj/maigret) — a mature OSINT tool with
> 3000+ sites and a clever double-check mechanism (claimed vs unclaimed username).
> We share the same goal but took a different path.

### 1. SQLite instead of JSON — lean & typed

Maigret stores its 3200+ sites in a **44k-line JSON file** (`~/.maigret/data.json`, 1.4MB).
That works, but:

- no schema — every field is a string, no validation
- the entire JSON must be loaded into memory at once
- diffs are massive even for tiny changes
- no indexing — finding a site means scanning the whole dict

We use **SQLite** (`SiteRegistry.db`, 536KB). Every column is typed
(`int`, `str`, `JSON`, `bool`), we can `SELECT`, `UPDATE`, `DELETE` with precision,
and the DB stays fast regardless of size.

### 2. Playwright for SPA & antibot sites

Maigret relies on raw HTTP and misses anything that requires JavaScript.
We run **real browser scripts** via Playwright for TikTok, Replit, Weebly,
Wix, Fiverr, LiveJournal and more.

### 3. DuckDuckGo dorking built in

Beyond the site catalog, we automatically run a **DuckDuckGo search** for the
username and show fresh web results under "Other Info". No API key, no captcha.

### 4. Beautiful, friendly interface

A gradient menu, live progress bar with percentage, growing results feed
with color-coded categories. Built on [`rich`](https://github.com/Textualize/rich).

<div align="center">

![How scratrace looks in the terminal](assets/terminal.png)

</div>

### 5. Multilingual

Built-in i18n. Switch languages on the fly in Settings:

| Language   | Code |
| ---------- | ---- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

### 6. Always fresh — dead sites get pruned automatically

A regular `pytest` run catches dead and lying sites and removes them from the
catalog. The database stays honest without manual effort.

---

## 🚀 Installation

The fastest way is to install straight from GitHub:

```bash
pip install git+https://github.com/0xScodyx/scratrace.git
```

Or a specific tagged version:

```bash
pip install git+https://github.com/0xScodyx/scratrace.git@v0.1.0
```

For development (editable mode):

```bash
git clone https://github.com/0xScodyx/scratrace.git
cd scratrace
pip install -e .
```

Dependencies: `aiohttp`, `rich`, `pytest`, `pytest-xdist`.

## 💻 Usage

```bash
pyscratrace          # interactive menu
```

Pick a search type (`username` / `email` / `phone` / `full_name`), enter a value,
and watch the live progress. Press `Enter` when done.

### Programmatic use

```python
from scratrace.osint import UserName

results = UserName("scodyx").check_all()
# -> {'social': [...], 'forums': [...], 'gaming': [...], ...}
```

---

## 🧪 Testing and catalog cleanup

```bash
pytest tests/ -n auto       # reachability + OSINT behavioural checks
```

---

## 🗂 Structure

```
src/scratrace/
├── app.py               # interactive menu (rich)
├── ui.py                # gradients, tables, progress
├── i18n.py / lang.json  # translations
├── banner.py
├── log_view.py          # CLI viewer for scratrace.log
└── osint/
    ├── sites.py         # site registry + DB-backed catalog
    ├── username.py      # username check (all strategies)
    ├── pw_scripts.py    # Playwright profile & dork scripts
    ├── log.py           # ANSI-colored logging
    ├── email.py
    ├── number_phone.py
    └── full_name.py
tests/
├── test_sites.py        # reachability (do not touch!)
├── test_username.py     # OSINT behavioural checks
└── conftest.py
```

---

## 👥 Contributors

Thanks to everyone making `scratrace` cleaner and more accurate:

<!-- contrib.rocks: contributor avatars are pulled from the GitHub API automatically -->
<a href="https://github.com/0xScodyx/scratrace/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=0xScodyx/scratrace" />
</a>

> Want to show up here? Add a site to `sites.py` or improve the check — PRs welcome!

---

## 📜 License

MIT © scratrace contributors
