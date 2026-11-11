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

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --wait
