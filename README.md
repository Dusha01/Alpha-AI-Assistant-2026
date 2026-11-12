# Alpha-AI-Assistant-2026

ИИ-помощник «Альфа-Курса» в Telegram: PostgreSQL + pgvector, RAG по бесплатному контенту кейса.

## Что нужно заранее

- Docker и Docker Compose v2
- Дамп каталога кейса — **один файл** (формат `pg_restore`, не каталог):
  `src/data/backups/alfa_course_hackathon.backup`
- Токен Telegram-бота, при необходимости `TELEGRAM_PROXY_URL`
- Для ответов с LLM — `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` в env

Дамп в git обычно не хранится: получите у команды / из материалов хакатона и положите по пути выше.
Проверка: `file src/data/backups/alfa_course_hackathon.backup` → `PostgreSQL custom database dump`.

---

## Dev: первый запуск

1. Секреты и настройки:

```bash
cp .env.dev.example .env.dev
# заполнить POSTGRES_PASSWORD, TELEGRAM_BOT_TOKEN, LLM_*, TELEGRAM_PROXY_URL при необходимости
```

2. Положить дамп:

```bash
# должен быть файл, ~19M+, не папка с таким именем
ls -lh src/data/backups/alfa_course_hackathon.backup
```

3. Поднять весь стек одной командой (Postgres → restore дампа → migrate → ingest при пустых чанках → bot):

```bash
./scripts/dev/up-dev.sh
```

Скрипт **не стартует** compose, если дампа нет, он пустой или это каталог.

4. Проверка:

```bash
curl -s http://127.0.0.1:8000/health
docker compose --env-file .env.dev -f docker-compose.dev.yml logs -f bot
```

В логах бота ожидайте `Start polling` и ответ в Telegram на `/start`.

### Повторный запуск и ingest

- **migrate** выполняется при каждом `./scripts/dev/up-dev.sh` (идемпотентно).
- **ingest** пропускается, если в `content.chunks` уже есть строки с эмбеддингами.
- Принудительный ingest: `FORCE_INGEST=1 ./scripts/dev/up-dev.sh`
- Без ingest (быстрый старт): `./scripts/dev/up-dev.sh --no-ingest`
- Пробный ingest: `INGEST_ARGS="--dry-run --limit 10" ./scripts/dev/up-dev.sh`

Остановка:

```bash
./scripts/dev/down-dev.sh          # контейнеры
./scripts/dev/down-dev.sh -purge   # контейнеры + тома Postgres (следующий up снова накатит дамп)
```

Порт Postgres на хосте по умолчанию **5432** (`.env.dev` → `POSTGRES_HOST_PORT`).

### Локально без Docker-бота

Можно поднять только БД и data pipeline, бота гонять через venv:

```bash
./scripts/dev/up-dev.sh --no-ingest   # или остановить сервис bot после up
# в .env.dev задать DATABASE_URL_HOST на localhost:5432
uvicorn src.core.app:app --reload
```

---

## Prod (VPS / стенд)

1. `cp .env.prod.example .env.prod` — пароль Postgres, токен, LLM, `DEBUG=false`, `LOG_LEVEL=INFO`.
2. Тот же дамп в `src/data/backups/alfa_course_hackathon.backup`.
3. `./scripts/prod/up-prod.sh` — тот же порядок: postgres → migrate → ingest (если нужно) → bot.
4. Порт Postgres на хосте по умолчанию **5433**, API бота **8000** (`API_PORT`).

```bash
./scripts/prod/down-prod.sh
./scripts/prod/down-prod.sh -purge
```

Переменные для скриптов (опционально):

| Переменная | Смысл |
|------------|--------|
| `BACKUP_REL` | путь к дампу от корня репо (по умолчанию `src/data/backups/alfa_course_hackathon.backup`) |
| `FORCE_INGEST=1` | всегда запускать ingest |
| `INGEST_ARGS` | аргументы, напр. `--dry-run --limit 10` |

Подробнее про compose и ручные команды: [scripts/README.md](scripts/README.md).

---

## Стек в compose

| Сервис | Dev | Prod |
|--------|-----|------|
| `postgres` | pgvector 17, restore дампа при пустом томе | то же |
| `migrate` | профиль `tools`, Alembic | то же |
| `ingest` | профиль `tools`, чанки в pgvector | то же |
| `bot` | gunicorn + aiogram | то же |

Схема `public.*` — из дампа платформы; `app.*` и `content.chunks` — Alembic и ingest.
