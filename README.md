<div align="center">

![scratrace](assets/scratrace.png)

# scratrace

**OSINT-инструмент для поиска людей по username, e-mail, телефону и полному имени.**

Чистые ссылки. Ноль ложных срабатываний. Красивый интерфейс. Мультиязычность.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
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

> Почему `scratrace`, а не очередной форк `sherlock`?

### 1. Чистые ссылки без ложных срабатываний

Большинство OSINT-тулок (включая популярные) считают сайт «найденным», если он
вернул **любой** ответ, даже `404` или страницу «пользователь не существует».
Мы проверяем каждый сайт двойным запросом:

- подставляем **популярный** username (`news`, `user`, `admin`);
- подставляем **заведомо случайный** `kljwwdlkjadkljakdl`.

Если коды ответов **совпадают** — сайт врёт (всегда отдаёт `200`) → `type_url=None`,
ссылка не считается рабочей. Если коды **различаются** — сайт честный → проставляем
реальный код (`type_url=200`) и только тогда используем.

```
username=news      → 200
username=kljwwd... → 404   ✅ честный, type_url=200

username=news      → 200
username=kljwwd... → 200   ❌ врёт, type_url=None (отброшено)
```

Каталог пока не самый большой, но **каждая ссылка в нём актуальна и проверена**.

### 2. Красивый и дружелюбный интерфейс

Градиентное меню, живой прогресс-бар с процентом и растущей лентой результатов,
категории с акцентными цветами. Всё построено на [`rich`](https://github.com/Textualize/rich).

<div align="center">

![Так выглядит scratrace в терминале](assets/terminal.png)

</div>

### 3. Переводы на разные языки

Встроенная система i18n. Сейчас поддерживаются:

| Язык      | Код |
| --------- | --- |
| 🇷🇺 Русский | `ru` |
| 🇬🇧 English | `en` |
| 🇨🇳 中文    | `cn` |

Переключается в меню **Settings** → выбор языка.

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

Мёртвые сайты выявляются через `pytest` и автоматически вырезаются:

```bash
pytest tests/test_sites.py -n auto     # пишет мертвецов в .dead_sites.json
python tests/cut_sites.py              # удаляет их из sites.py
```

---

## 🗂 Структура

```
src/scratrace/
├── app.py            # интерактивное меню (rich)
├── ui.py             # градиенты, таблицы, прогресс
├── i18n.py / lang.json
├── banner.py
└── osint/
    ├── sites.py      # реестр сайтов (Sites-объекты)
    ├── username.py   # проверка по username
    ├── email.py
    ├── number_phone.py
    └── full_name.py
tests/
├── test_sites.py     # reachability-проверка (не трогать!)
├── conftest.py       # сбор мертвых сайтов
└── cut_sites.py      # авто-удаление
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
