<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**OSINT-инструмент для поиска людей по username, e-mail, телефону и полному имени.**

Чистые ссылки. Ноль ложных срабатываний. Красивый интерфейс. Мультиязычность.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()

</div>

---

## 🔍 Что это

`scratrace` — консольный OSINT-сканер, который пробегается по каталогу сайтов и
находит профили пользователя по заданному идентификатору. В отличие от большинства
аналогов, мы **не выдаём найденное наобум**: каждая ссылка в каталоге проверена на
честность, а «врущие» сайты помечаются и отбрасываются.

### Поддерживаемые типы поиска

| Тип                | Описание                                            |
| ------------------ | --------------------------------------------------- |
| 🧑 `username`      | Поиск по никнейму across соцсетей, форумов, dev и т.д. |
| 📧 `email`         | Поиск по e-mail                                      |
| 📱 `number_phone`  | Поиск по номеру телефона                            |
| 👤 `full_name`     | Поиск по имени и фамилии                            |

---

## ⚡ Наши преимущества

> База сайтов построена на основе каталога [Maigret](https://github.com/soxoj/maigret) — самой большой коллекции OSINT-сайтов. Мы взяли лучшее и сделали быстрее, чище и надёжнее.

### 1. Ноль ложных срабатываний — гарантировано

Большинство OSINT-тулов (включая Maigret и форки Sherlock) считают сайт
«найденным», если он вернул **любой** HTTP-ответ, даже стандартную `404`
или страницу «пользователь не существует», отданную с кодом 200. Мы — нет.

Каждый сайт в каталоге проходит **двойную проверку**:

- запрашиваем **заведомо популярный** username (`news`, `admin`, `user`);
- запрашиваем **заведомо случайный** `kljwwdlkjadkljakdl`.

Если коды совпадают — сайт врёт (всегда отдаёт 200) → помечаем его как
ненадёжный (`type_url=None`). Если коды различаются — сайт честный →
запоминаем реальный код детекта и используем его.

```
news      → 200
kljwwd…   → 404   ✅ честный, type_url=200

news      → 200
kljwwd…   → 200   ❌ врёт, отброшен
```

**Каждая ссылка в выдаче — реальный профиль, а не угадайка.**

### 2. Playwright для SPA и антибот-сайтов

Maigret и Sherlock полагаются только на HTTP и не видят то, что требует
JavaScript. Мы запускаем **настоящие браузерные скрипты** через Playwright
для TikTok, Replit, Weebly, Wix, Fiverr, LiveJournal и других — сайтов,
которые прячут контент за логинами, SPA или антибот-проверками.

### 3. Встроенный DuckDuckGo-доркинг

Помимо каталога сайтов, мы автоматически ищем username в DuckDuckGo
и показываем свежие результаты из веба в категории «Other Info».
Никаких API-ключей, никаких капч — через `ddgs`.

### 4. Красивый и дружелюбный интерфейс

Градиентное меню, живой прогресс-бар с процентом и растущей лентой результатов,
категории с акцентными цветами. Всё построено на [`rich`](https://github.com/Textualize/rich).

<div align="center">

![Так выглядит scratrace в терминале](assets/terminal.png)

</div>

### 5. Переводы на разные языки

Встроенная система i18n. Сейчас поддерживаются:

| Язык      | Код |
| --------- | --- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

Переключается в меню **Settings** → выбор языка.

### 6. Автоматическая подчистка мёртвых сайтов

Регулярный прогон `pytest` находит битые и врущие сайты и удаляет их
из каталога. База остаётся честной без ручного труда.

---

## 🚀 Установка

Самый быстрый способ — поставить прямо из GitHub:

```bash
pip install git+https://github.com/0xScodyx/scratrace.git
```

Или конкретную версию по тегу:

```bash
pip install git+https://github.com/0xScodyx/scratrace.git@v0.1.0
```

Для разработки (editable-режим):

```bash
git clone https://github.com/0xScodyx/scratrace.git
cd scratrace
pip install -e .
```

Зависимости: `aiohttp`, `rich`, `pytest`, `pytest-xdist`.

## 💻 Использование

```bash
pyscratrace          # интерактивное меню
```

В меню выбери тип поиска (`username` / `email` / `phone` / `full_name`),
введи значение — и смотри живой прогресс. По завершении нажми `Enter`.

### Программный вызов

```python
from scratrace.osint import UserName

results = UserName("scodyx").check_all()
# -> {'social': [...], 'forums': [...], 'gaming': [...], ...}
```

---

## 🧪 Тестирование и очистка каталога

```bash
pytest tests/ -n auto       # reachability + OSINT behavioural checks
```

---

## 🗂 Структура

```
src/scratrace/
├── app.py               # интерактивное меню (rich)
├── ui.py                # градиенты, таблицы, прогресс
├── i18n.py / lang.json  # переводы
├── banner.py
├── log_view.py          # CLI-просмотрщик scratrace.log
└── osint/
    ├── sites.py         # реестр сайтов (БД)
    ├── username.py      # проверка username (все стратегии)
    ├── pw_scripts.py    # Playwright-скрипты профилей и доркинга
    ├── log.py           # ANSI-цветное логирование
    ├── email.py
    ├── number_phone.py
    └── full_name.py
tests/
├── test_sites.py        # reachability (не трогать!)
├── test_username.py     # OSINT behavioural-проверки
└── conftest.py
```

---

## 👥 Контрибьютеры

Спасибо всем, кто делает `scratrace` чище и точнее:

<!-- contrib.rocks: аватарки всех контрибьютеров подтягиваются с GitHub API автоматически -->
<a href="https://github.com/0xScodyx/scratrace/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=0xScodyx/scratrace" />
</a>

> Хочешь попасть сюда? Добавь сайт в `sites.py` или улучши проверку — PR welcome!

---

## 📜 Лицензия

MIT © scratrace contributors
