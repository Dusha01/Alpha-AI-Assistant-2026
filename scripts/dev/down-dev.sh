#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [[ ! -f .env.dev ]]; then
  echo "Нет файла .env.dev. Скопируйте .env.dev.example и заполните его." >&2
  exit 1
fi
if ! grep -Eq '^POSTGRES_PASSWORD=.+$' .env.dev; then
  echo "В .env.dev пустой POSTGRES_PASSWORD." >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  docker compose --env-file .env.dev -f docker-compose.dev.yml down
elif [[ "$1" == "-purge" ]]; then
  docker compose --env-file .env.dev -f docker-compose.dev.yml down -v --remove-orphans
else
  echo "Неизвестный аргумент: $1. Для удаления томов используйте -purge." >&2
  exit 2
fi
