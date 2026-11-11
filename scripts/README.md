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
