#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

ENV_FILE=".env.prod"
COMPOSE_FILE="${ROOT}/docker-compose.prod.yml"
BACKUP_REL="${BACKUP_REL:-src/data/backups/alfa_course_hackathon.backup}"
BACKUP="${ROOT}/${BACKUP_REL}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Нет файла ${ENV_FILE}. Скопируйте .env.prod.example и заполните его." >&2
  exit 1
fi
if ! grep -Eq '^POSTGRES_PASSWORD=.+$' "${ENV_FILE}"; then
  echo "В ${ENV_FILE} пустой POSTGRES_PASSWORD." >&2
  exit 1
fi

if [[ -d "${BACKUP}" ]]; then
  echo "Ошибка: путь дампа — каталог, нужен один файл:" >&2
  echo "  ${BACKUP}" >&2
  echo "Удалите каталог и положите pg_dump -Fc (см. README)." >&2
  exit 1
fi
if [[ ! -f "${BACKUP}" ]]; then
  echo "Нет файла дампа кейса (обязателен для Postgres и ingest):" >&2
  echo "  ${BACKUP}" >&2
  echo "Скопируйте alfa_course_hackathon.backup в этот путь до запуска стека." >&2
  exit 1
fi
if [[ ! -s "${BACKUP}" ]]; then
  echo "Файл дампа пустой: ${BACKUP}" >&2
  exit 1
fi

SKIP_INGEST=0
if [[ "${1:-}" == "--no-ingest" ]]; then
  SKIP_INGEST=1
fi

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

echo "==> Postgres (ожидание healthy и дампа в public)..."
compose up -d --build postgres
compose up -d --wait postgres

echo "==> Alembic migrate..."
compose --profile tools build migrate
compose --profile tools run --rm --no-deps migrate

if [[ "${SKIP_INGEST}" == "1" ]]; then
  echo "==> Ingest пропущен (--no-ingest)."
else
  PG_USER="$(grep -E '^POSTGRES_USER=' "${ENV_FILE}" | head -1 | cut -d= -f2-)"
  PG_DB="$(grep -E '^POSTGRES_DB=' "${ENV_FILE}" | head -1 | cut -d= -f2-)"
  CHUNK_COUNT="$(compose exec -T postgres \
    psql -U "${PG_USER}" -d "${PG_DB}" -tAc \
    "SELECT count(*) FROM content.chunks WHERE embedding IS NOT NULL" 2>/dev/null \
    | tr -d '[:space:]' || true)"
  CHUNK_COUNT="${CHUNK_COUNT:-0}"

  FORCE_INGEST="${FORCE_INGEST:-0}"
  if [[ "${FORCE_INGEST}" != "1" && "${CHUNK_COUNT}" =~ ^[0-9]+$ && "${CHUNK_COUNT}" -gt 0 ]]; then
    echo "==> Ingest пропущен: в content.chunks уже ${CHUNK_COUNT} чанков с эмбеддингами."
    echo "    Повторный ingest: FORCE_INGEST=1 ./scripts/prod/up-prod.sh"
  else
    echo "==> Ingest (может занять много времени, качается модель)..."
    compose --profile tools build ingest
    if [[ -n "${INGEST_ARGS:-}" ]]; then
      # shellcheck disable=SC2086
      compose --profile tools run --rm --no-deps ingest \
        python -m src.modules.knowledge.ingest ${INGEST_ARGS}
    else
      compose --profile tools run --rm --no-deps ingest
    fi
  fi
fi

echo "==> Бот..."
compose up -d --build --no-deps bot
compose up -d --wait bot

echo ""
echo "Готово (prod)."
echo "  health: curl -s http://127.0.0.1:\${API_PORT:-8000}/health"
echo "  логи:   docker compose --env-file ${ENV_FILE} -f docker-compose.prod.yml logs -f bot"
