# Скрипты стека

Запускать из любой директории. Скрипт сам переходит в корень репозитория.

Dev использует `.env.dev` и `docker-compose.dev.yml`, порт хоста 5432. Prod использует `.env.prod` и `docker-compose.prod.yml`, порт хоста 5433, чтобы оба стека могли работать рядом. Дамп накатывается скриптом `scripts/postgres/init-restore.sh` только в пустой volume.

```bash
scripts/dev/up-dev.sh
scripts/dev/down-dev.sh
scripts/dev/down-dev.sh -purge

scripts/prod/up-prod.sh
scripts/prod/down-prod.sh
scripts/prod/down-prod.sh -purge
```

`down` останавливает и удаляет контейнеры и сеть. Тома с данными Postgres остаются.

`-purge` делает то же самое и удаляет тома (`docker compose down -v`). Следующий `up` снова восстановит дамп в пустую базу.

Prod поднимает Postgres и бота (`bot`); миграции при старте бота и отдельной командой `migrate`:

```bash
scripts/prod/up-prod.sh
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile tools run --rm migrate
```

Ingest чанков и эмбеддингов (фаза 3) через профиль `tools`, модель кэшируется в volume `hf_cache_prod`:

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml --profile tools run --rm ingest
docker compose --env-file .env.dev -f docker-compose.dev.yml --profile tools run --rm ingest \
  python -m src.modules.knowledge.ingest --dry-run --limit 10

docker compose --env-file .env.prod -f docker-compose.prod.yml --profile tools run --rm ingest
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile tools run --rm ingest \
  python -m src.modules.knowledge.ingest --dry-run --limit 10
```
