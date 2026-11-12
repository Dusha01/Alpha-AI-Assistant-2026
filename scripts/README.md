# Скрипты стека

Запускать из любой директории — скрипт переходит в корень репозитория.

## Dev

- Env: `.env.dev`, compose: `docker-compose.dev.yml`
- Порт Postgres на хосте: **5432** (`POSTGRES_HOST_PORT`)

```bash
./scripts/dev/up-dev.sh              # postgres + migrate + ingest (если пусто) + bot
./scripts/dev/up-dev.sh --no-ingest  # без ingest
./scripts/dev/down-dev.sh
./scripts/dev/down-dev.sh -purge     # + тома (следующий up снова восстановит дамп)
```

## Prod

- Env: `.env.prod`, compose: `docker-compose.prod.yml`
- Порт Postgres на хосте: **5433** по умолчанию (чтобы не конфликтовать с dev)

```bash
./scripts/prod/up-prod.sh
./scripts/prod/up-prod.sh --no-ingest
./scripts/prod/down-prod.sh
./scripts/prod/down-prod.sh -purge
```

## Что делает `up-*.sh`

Вся последовательность прописана в `scripts/dev/up-dev.sh` и `scripts/prod/up-prod.sh`:

1. Проверка `.env.*` и непустого `POSTGRES_PASSWORD`
2. Проверка дампа `src/data/backups/alfa_course_hackathon.backup` (файл, непустой, не каталог) — при ошибке **выход без запуска** compose
3. `postgres` до статуса healthy (в т.ч. таблицы в `public` из дампа)
4. `migrate` (one-off)
5. `ingest` (one-off), если нет чанков с эмбеддингами, иначе пропуск
6. `bot` до healthy (`/health`)

Дамп накатывается только в **пустой** volume Postgres (`scripts/postgres/init-restore.sh`). После смены дампа или неудачного init: `down -purge` и снова `up`.

## Переменные

```bash
FORCE_INGEST=1 ./scripts/dev/up-dev.sh
INGEST_ARGS="--dry-run --limit 10" ./scripts/dev/up-dev.sh
BACKUP_REL=path/to/backup ./scripts/prod/up-prod.sh
```

## Ручные команды (без скрипта)

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml --profile tools run --rm migrate
docker compose --env-file .env.dev -f docker-compose.dev.yml --profile tools run --rm ingest
docker compose --env-file .env.dev -f docker-compose.dev.yml --profile tools run --rm ingest \
  python -m src.modules.knowledge.ingest --dry-run --limit 10
```

Аналогично с `.env.prod` и `docker-compose.prod.yml`.

`down` снимает контейнеры и сеть; тома остаются. `-purge` удаляет тома.
