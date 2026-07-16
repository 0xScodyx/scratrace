<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**An OSINT tool to find people by username, e-mail, phone number, and full name.**

Clean links. Zero false positives. A beautiful interface. Multilingual.

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
| 📧 `email`         | Search by e-mail                                      |
| 📱 `number_phone`  | Search by phone number                               |
| 👤 `full_name`     | Search by first and last name                        |

---

## ⚡ Our advantages

> Why `scratrace` instead of yet another `sherlock` fork?

### 1. Clean links with no false positives

Most OSINT tools (including popular ones) consider a site "found" if it returns
**any** response — even a `404` or a "user does not exist" page. We verify every
site with a double request:

- we substitute a **popular** username (`news`, `user`, `admin`);
- we substitute a **deliberately random** `kljwwdlkjadkljakdl`.

If the response codes **match** — the site lies (always returns `200`) →
`type_url=None`, the link is not considered working. If the codes **differ** — the
site is honest → we record the real code (`type_url=200`) and only then use it.

```
username=news      → 200
username=kljwwd... → 404   ✅ honest, type_url=200

username=news      → 200
username=kljwwd... → 200   ❌ lies, type_url=None (dropped)
```

The catalog isn't the largest yet, but **every link in it is current and verified**.

### 2. A beautiful, friendly interface

A gradient menu, a live progress bar with a percentage and a growing results feed,
categories with accent colors. Everything is built on
[`rich`](https://github.com/Textualize/rich).

<div align="center">

![How scratrace looks in the terminal](assets/terminal.png)

</div>

### 3. Translations into multiple languages

A built-in i18n system. Currently supported:

| Language   | Code |
| ---------- | ---- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

Switch via the **Settings** menu → choose language.

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

Dead sites are detected via `pytest` and automatically pruned:

```bash
pytest tests/test_sites.py -n auto     # writes dead sites to .dead_sites.json
python tests/cut_sites.py              # removes them from sites.py
```

---

## 🗂 Structure

```
src/scratrace/
├── app.py            # interactive menu (rich)
├── ui.py             # gradients, tables, progress
├── i18n.py / lang.json
├── banner.py
└── osint/
    ├── sites.py      # site registry (Sites objects)
    ├── username.py   # username check
    ├── email.py
    ├── number_phone.py
    └── full_name.py
tests/
├── test_sites.py     # reachability check (do not touch!)
├── conftest.py       # dead-site collection
└── cut_sites.py      # auto-removal
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
