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

docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --wait postgres
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --no-deps bot

bot_id="$(docker compose --env-file .env.dev -f docker-compose.dev.yml ps -aq bot)"
bot_status="created"
for _ in 1 2 3 4 5 6 7 8; do
  bot_status="$(docker inspect -f '{{.State.Status}}' "${bot_id}")"
  if [[ "${bot_status}" == "exited" ]]; then
    break
  fi
  sleep 0.5
done

bot_code="$(docker inspect -f '{{.State.ExitCode}}' "${bot_id}")"
if [[ "${bot_status}" != "running" && "${bot_code}" != "0" ]]; then
  docker compose --env-file .env.dev -f docker-compose.dev.yml logs bot --tail 40
  exit "${bot_code}"
fi
if [[ "${bot_status}" != "running" ]]; then
  docker compose --env-file .env.dev -f docker-compose.dev.yml logs bot --tail 20
fi
