#!/bin/bash
# Восстанавливает дамп кейса в пустой volume. Official entrypoint вызывает
# скрипт один раз, пока каталог данных ещё не инициализирован.
set -euo pipefail

backup=/backup/alfa_course_hackathon.backup

if [ ! -f "${backup}" ]; then
  echo "Backup not found: ${backup}" >&2
  exit 1
fi

echo "Restoring ${backup} into database ${POSTGRES_DB}"

set +e
pg_restore \
  --username "${POSTGRES_USER}" \
  --no-owner \
  --no-acl \
  --exit-on-error \
  --dbname "${POSTGRES_DB}" \
  "${backup}"
status=$?
set -e

table_count="$(
  psql \
    --username "${POSTGRES_USER}" \
    --dbname "${POSTGRES_DB}" \
    --tuples-only \
    --no-align \
    --command "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
)"
table_count="$(echo "${table_count}" | tr -d '[:space:]')"

if [ "${status}" -eq 0 ]; then
  echo "pg_restore finished cleanly; public tables: ${table_count}"
  exit 0
fi

if [ "${status}" -ge 2 ]; then
  echo "pg_restore failed with status ${status}" >&2
  exit "${status}"
fi

if [ "${table_count}" -lt 1 ]; then
  echo "pg_restore exited ${status} and public schema has no tables" >&2
  exit 1
fi

echo "pg_restore exited ${status}; public tables: ${table_count}. Treating warnings as success."
