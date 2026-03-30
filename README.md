# iMAS Mini-Complex OSINT v5

Обновлённый демо-проект под презентацию:
- модуль 1: Выявление событий
- модуль 2: Анализ изображений и геолокации
- модуль 3: Username / Email Intelligence
- единый UI в стиле iMAS
- подключаемый Yandex reverse image search через `.env`
- поддержка внешнего инструмента `user-scanner` для OSINT-поиска по email и username

## Быстрый старт (Ubuntu)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn app.main:app --reload
```

Открыть:
- `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## Где вставить API ключ Yandex

В корне проекта создай или отредактируй `.env`:

```env
YANDEX_SEARCH_ENABLED=true
YANDEX_FOLDER_ID=your_folder_id
YANDEX_API_KEY=your_api_key
```

## Как включить user-scanner

По желанию в активированном окружении:

```bash
pip install user-scanner
```

По умолчанию модуль цифрового профиля умеет работать и без пакета — в demo fallback-режиме.

## Структура

- `/modules/event-detection` — выявление событий
- `/modules/image-geo` — анализ изображений
- `/modules/digital-profile` — разведка по email и username
