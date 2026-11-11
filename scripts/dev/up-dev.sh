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

docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --wait
