<div align="center">

[English](README.md) · [中文](README.zh.md) · [Русский](README.ru.md)

![scratrace](assets/scratrace.png)

# scratrace

**OSINT-инструмент для поиска людей по username, e-mail, телефону и полному имени.**

Чистые ссылки. Playwright. Мультиязычность.

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
| 📧 `email`         | Поиск по e-mail · _скоро_                              |
| 📱 `number_phone`  | Поиск по номеру телефона · _скоро_                   |
| 👤 `full_name`     | Поиск по имени и фамилии · _скоро_                   |

---

## ⚡ Наши преимущества

> Вдохновлён [Maigret](https://github.com/soxoj/maigret) — зрелым OSINT-инструментом
> с 3000+ сайтов и продуманным механизмом двойной проверки (существующий vs несуществующий
> username). У нас общая цель, но разные пути.

### 1. SQLite вместо JSON — компактно и типизированно

Maigret хранит свои 3200+ сайтов в **JSON-файле на 44k строк** (`~/.maigret/data.json`, 1.4MB).
Это работает, но:

- нет схемы — каждое поле просто строка, нет валидации
- весь JSON загружается в память целиком
- диффы огромны даже для крошечных изменений
- нет индексов — поиск сайта означает сканирование всего словаря

Мы используем **SQLite** (`SiteRegistry.db`, 536KB). Каждая колонка типизирована
(`int`, `str`, `JSON`, `bool`), можно делать `SELECT`, `UPDATE`, `DELETE` точечно,
и БД остаётся быстрой независимо от размера.

### 2. Playwright для SPA и антибот-сайтов

Maigret полагается на HTTP и не видит то, что требует JavaScript.
Мы запускаем **настоящие браузерные скрипты** через Playwright для TikTok,
Replit, Weebly, Wix, Fiverr, LiveJournal и других.

### 3. Встроенный доркинг

Помимо каталога сайтов, автоматически ищем username через DuckDuckGo
(Playwright) и показываем свежие результаты в категории «Other Info».
Никаких API-ключей и капч.

### 4. Красивый и дружелюбный интерфейс

Градиентное меню, живой прогресс-бар с процентом, растущая лента результатов
с цветными категориями. Всё на [`rich`](https://github.com/Textualize/rich).

<div align="center">

![Так выглядит scratrace в терминале](assets/terminal.png)

</div>

### 5. Переводы на разные языки

Встроенная i18n. Сейчас поддерживаются:

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

> **Смена лицензии:** scratrace ранее был под GPL v3. Начиная с v0.2.2 лицензия изменена на MIT.

```bash
pip install git+https://github.com/0xScodyx/scratrace.git
```

Или конкретную версию по тегу:

```bash
pip install git+https://github.com/0xScodyx/scratrace.git@v0.2.2
```

### Браузерные проверки (опционально)

Для Playwright-проверок и DuckDuckGo-доркинга доставь браузерную зависимость и сам браузер:

```bash
pip install "scratrace[browser] @ git+https://github.com/0xScodyx/scratrace.git"
playwright install chromium
```

Если сначала поставил базовый пакет, а потом решил добавить браузер:

```bash
pip install playwright playwright-stealth
playwright install chromium
```

### Разработка (editable-режим)

```bash
git clone https://github.com/0xScodyx/scratrace.git
cd scratrace
pip install -e .
```

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

### Просмотр логов

```bash
scratrace-log        # хвост последнего поиска
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

## 🤝 Контрибьюция

Все PR и коммиты отправляются только в ветку `dev`. Ветка `main` — только для стабильных релизов. Не мержите в `main` напрямую — открывайте PR в `dev`.

---

## 📜 Лицензия

MIT © scratrace contributors
