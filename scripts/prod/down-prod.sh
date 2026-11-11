#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [[ ! -f .env.prod ]]; then
  echo "Нет файла .env.prod. Скопируйте .env.prod.example и заполните его." >&2
  exit 1
fi
if ! grep -Eq '^POSTGRES_PASSWORD=.+$' .env.prod; then
  echo "В .env.prod пустой POSTGRES_PASSWORD." >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  docker compose --env-file .env.prod -f docker-compose.prod.yml down
elif [[ "$1" == "-purge" ]]; then
  docker compose --env-file .env.prod -f docker-compose.prod.yml down -v --remove-orphans
else
  echo "Неизвестный аргумент: $1. Для удаления томов используйте -purge." >&2
  exit 2
fi
