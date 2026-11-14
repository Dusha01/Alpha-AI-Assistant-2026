# Alpha-AI-Assistant-2026

ИИ-помощник «Альфа-Курса» в Telegram: PostgreSQL + pgvector, ответы по бесплатному контенту кейса.

Инструкция ниже — для проверки проекта. Все команды вводятся в терминале из **корня репозитория** (папка, в которой лежат этот `README.md`, файл `.env.dev.example` и каталог `scripts`).

Есть два способа запустить dev-версию. Оба начинают с одного и того же файла секретов `.env.dev` и одного и того же дампа базы.

| Способ | Что делает | Когда выбирать |
|--------|------------|----------------|
| [Виртуальное окружение](#запуск-бота-из-виртуального-окружения) | База в Docker, сам бот — программой Python на компьютере | Обычная проверка: бот отвечает в Telegram |
| [Docker-скрипт](#запуск-через-docker-скрипт) | `./scripts/dev/up-dev.sh` поднимает базу, миграции и загрузку знаний | Проверка, что стек собирается скриптом |

Сервис `bot` в `docker-compose.dev.yml` сейчас закомментирован. Скрипт доводит базу, миграции и загрузку знаний, а на шаге запуска контейнера `bot` останавливается с ошибкой. После этого бота запускают из виртуального окружения — это ожидаемый порядок для dev.

---

## Что установить заранее

1. **Docker** с Compose V2. Проверка: `docker compose version` печатает версию, а не «команда не найдена».
2. **Python 3.12** — нужен для запуска бота на компьютере. Проверка: `python3.12 --version`.
3. **Дамп каталога кейса** — один файл формата `pg_restore`, не папка:
   `src/data/backups/alfa_course_hackathon.backup`.
   В git его нет: файл выдаёт команда или он лежит в материалах хакатона.
4. **Токен Telegram-бота** (выдаёт [@BotFather](https://t.me/BotFather)).
5. **Доступ к LLM** с API, совместимым с OpenAI: адрес, ключ и имя модели. Организаторы передают их отдельно. Эти три значения бот читает из `.env.dev`.

Интернет нужен при первом запуске: Docker скачает образы, Python скачает библиотеки, загрузка знаний скачает модель эмбеддингов `intfloat/multilingual-e5-small` (сотни мегабайт, несколько минут).

---

## Секреты: файл `.env.dev`

Рабочий файл с паролями и ключами — `.env.dev` в корне репозитория. В git он не попадает. Образец без ваших ключей — `.env.dev.example`.

Скопируйте образец один раз:

```bash
cp .env.dev.example .env.dev
```

Откройте `.env.dev` в любом текстовом редакторе. Каждая настройка — отдельная строка `ИМЯ=значение`. Значение пишется сразу после `=`, без кавычек и без пробелов вокруг `=`. Пустая строка после `=` значит «значение не задано».

### Что заполнить своими данными

Эти четыре строки без ваших значений бот либо не подключится к Telegram, либо не сможет отвечать через модель.

| Строка | Откуда взять | Как выглядит значение |
|--------|----------------|------------------------|
| `TELEGRAM_BOT_TOKEN` | @BotFather, команда `/newbot` или уже созданный бот | Целиком, вида `7123456789:AAH...` |
| `LLM_BASE_URL` | Адрес API, который дали организаторы | Адрес **без** хвоста `/v1`. Программа сама дописывает `/v1/chat/completions`. Пример: `https://api.openai.com` |
| `LLM_API_KEY` | Ключ того же провайдера | Длинная строка ключа, как её выдали |
| `LLM_MODEL` | Имя модели у этого провайдера | Точное имя, например `gpt-4o-mini` |

Пример заполненного блока (подставьте свои значения):

```bash
############# APP #############
APP_ENV=dev
DEBUG=true
LOG_LEVEL=DEBUG

############# DB #############
POSTGRES_USER=alfa
POSTGRES_PASSWORD=change_me_db_pass
POSTGRES_DB=alfa_course
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=5432

DATABASE_URL=postgresql+asyncpg://alfa:change_me_db_pass@localhost:5432/alfa_course
DATABASE_URL_HOST=postgresql+asyncpg://alfa:change_me_db_pass@localhost:5432/alfa_course

############# TG bot #############
TELEGRAM_BOT_TOKEN=change_me_tg_bot_token
#TELEGRAM_PROXY_URL=

############# LLM #############
LLM_BASE_URL=change_me_ai_base_url
LLM_API_KEY=change_me_ai_token
LLM_MODEL=deepseek/deepseek-v4.1-flash-1017
LLM_FALLBACK_MODEL=
LLM_TIMEOUT_SECONDS=30

############# RAG #############
EMBEDDING_MODEL=intfloat/multilingual-e5-small
PLATFORM_BASE_URL=https://example.alfacourse.local
INGEST_CHUNK_SIZE=800
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.35
RAG_RELATED_SCORE_THRESHOLD=0.27
RAG_CLARIFY_SCORE_GAP=0.06
APP_ENV=dev
DEBUG=true
LOG_LEVEL=DEBUG


```

`LLM_FALLBACK_MODEL` можно оставить пустым. Если указать второе имя модели, бот попробует её, когда первая не ответит.

### Прокси Telegram — только если без него бот не достучится до Telegram

`TELEGRAM_PROXY_URL` оставьте пустым, если компьютер и так открывает Telegram. Тогда в логе будет «прямое подключение».

Если у вас есть прокси, вставьте один URL. Подходят схемы `http`, `https`, `socks4`, `socks5`, `socks5h`:

```bash
TELEGRAM_PROXY_URL=socks5://user:password@127.0.0.1:1080
```

Слова `none`, `off`, `false`, `-` программа считает пустым значением.

### Пароль базы

В образце уже стоит пароль `dev_only_change_me`. Для локальной проверки его можно не менять: скрипт требует только чтобы строка `POSTGRES_PASSWORD` была непустой.

Пароль записан в трёх строках и во всех трёх должен совпадать:

- `POSTGRES_PASSWORD=dev_only_change_me`
- `DATABASE_URL=...://alfa:dev_only_change_me@postgres:5432/alfa_course` — этим адресом пользуются контейнеры. Хост в адресе — слово `postgres`.
- `DATABASE_URL_HOST=...://alfa:dev_only_change_me@localhost:5432/alfa_course` — этим адресом пользуется бот, запущенный на компьютере. Хост — `localhost`, порт `5432`.

Если меняете пароль, замените `dev_only_change_me` во всех трёх строках на одно и то же новое значение. Имена `alfa` и `alfa_course` оставьте как в образце.

### Что оставить как в образце

Эти строки уже заполнены. Для проверки их не меняют.

| Строка | Зачем она |
|--------|-----------|
| `POSTGRES_USER=alfa` | Имя пользователя базы |
| `POSTGRES_DB=alfa_course` | Имя базы |
| `POSTGRES_HOST=postgres` | Имя сервиса базы внутри Docker |
| `POSTGRES_PORT=5432` | Порт базы внутри Docker |
| `POSTGRES_HOST_PORT=5432` | Порт базы на вашем компьютере |
| `EMBEDDING_MODEL=intfloat/multilingual-e5-small` | Модель, которая превращает тексты в векторы. При первой загрузке знаний скачивается сама |
| `PLATFORM_BASE_URL=https://example.alfacourse.local` | Начало ссылок на материалы курса в ответах бота. Если организаторы дали адрес площадки — подставьте его. Иначе оставьте пример |
| `INGEST_CHUNK_SIZE=800` | Длина куска текста при загрузке знаний |
| `RAG_TOP_K`, `RAG_SCORE_THRESHOLD`, `RAG_RELATED_SCORE_THRESHOLD`, `RAG_CLARIFY_SCORE_GAP` | Сколько фрагментов искать и какие пороги похожести считать достаточными |
| `LLM_TIMEOUT_SECONDS=30` | Сколько секунд ждать ответ модели |
| `APP_ENV=dev` | Режим. Для этой инструкции всегда `dev`: программа читает именно `.env.dev` |
| `API_PORT=8000` | Порт проверки здоровья бота в браузере |
| `DEBUG=true` | Подробные сообщения об ошибках |
| `LOG_LEVEL=DEBUG` | Подробные логи |

Файл сохраните. Имя должно остаться `.env.dev` (с точкой в начале), место — корень репозитория.

---

## Куда положить дамп

Один файл, не папка с таким же именем:

```text
src/data/backups/alfa_course_hackathon.backup
```

Проверка из корня репозитория:

```bash
ls -lh src/data/backups/alfa_course_hackathon.backup
file src/data/backups/alfa_course_hackathon.backup
```

Ожидается файл размером около 19 МБ и больше, а `file` пишет `PostgreSQL custom database dump`. Пустой файл и каталог скрипт запуска отклоняет и контейнеры не стартует.

Дамп попадает в базу только когда том Postgres ещё пустой (первый запуск или запуск после очистки томов). Повторный `up` уже существующую базу заново не перезаписывает.

---

## Запуск через Docker-скрипт


Из корня репозитория:

```bash
./scripts/dev/up-dev.sh
```

Скрипт сам переходит в корень, даже если его вызвали из другой папки. Порядок такой:

1. Проверяет, что `.env.dev` есть и `POSTGRES_PASSWORD` не пустой.
2. Проверяет файл дампа.
3. Поднимает Postgres и ждёт, пока в схеме `public` появятся таблицы из дампа.
4. Применяет миграции (схема `app` и таблица `content.chunks`). Повторный запуск миграций безопасен.
5. Загружает знания в `content.chunks`, если таблица ещё пустая. Первый раз это долго: качается модель эмбеддингов. Если чанки уже есть, шаг пропускается.
6. Пытается запустить контейнер `bot`.

На шаге 6 команда завершится ошибкой вида «no such service: bot»: в `docker-compose.dev.yml` этот сервис закомментирован. База, миграции и загрузка знаний к этому моменту уже выполнены. Дальше запустите бота из виртуального окружения — следующий раздел. Повторять загрузку знаний для этого не нужно.

Полезные варианты той же команды:

```bash
./scripts/dev/up-dev.sh --no-ingest          # не загружать знания
FORCE_INGEST=1 ./scripts/dev/up-dev.sh       # загрузить знания ещё раз
INGEST_ARGS="--dry-run --limit 10" ./scripts/dev/up-dev.sh   # пробный прогон 10 материалов
```

Остановка:

```bash
./scripts/dev/down-dev.sh          # остановить контейнеры, данные базы сохранить
./scripts/dev/down-dev.sh -purge   # остановить и удалить данные базы; следующий up снова накатит дамп
```

Логи того, что успело подняться:

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml logs -f postgres
```

---

## Запуск бота из виртуального окружения

База при этом остаётся в Docker. Бот читает `.env.dev` и ходит в неё по `DATABASE_URL_HOST` (`localhost:5432`).

### 1. База уже должна работать

Если вы уже запускали `./scripts/dev/up-dev.sh` и он остановился только на сервисе `bot`, этот шаг пропустите: Postgres запущен, миграции применены, знания загружены.

Если скрипт ещё не запускали, поднимите всю подготовку одной командой (она снова остановится на `bot` — это нормально для текущего compose):

```bash
./scripts/dev/up-dev.sh
```

### 2. Создать окружение и поставить библиотеки

Нужен Python 3.12. Команды из корня репозитория:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Строка с `torch` ставит версию для процессора. Без неё `pip` может начать качать сборку под видеокарту NVIDIA на несколько гигабайт.

Приглашение терминала после `activate` начинается с `(.venv)`. Все следующие команды этого раздела выполняйте в том же окне терминала. В новом окне активацию повторяют: `source .venv/bin/activate`.

### 3. Запустить бота

```bash
uvicorn src.core.app:app --reload --host 127.0.0.1 --port 8000
```

Окно терминала остаётся занятым — это и есть работающий бот. Остановка: `Ctrl+C`.

В логе ожидайте строки `Альфа-Курс бот`, `telegram token=задан` и `Telegram API: прямое подключение` (или строку про прокси, если `TELEGRAM_PROXY_URL` заполнен). Затем в Telegram откройте своего бота и отправьте `/start`.

---

## Как понять, что всё поднялось

Проверка HTTP (пока бот запущен):

```bash
curl -s http://127.0.0.1:8000/health
```

Тело ответа — текст `ok`. Порт берётся из `API_PORT` (в образце это `8000`).

В Telegram:

1. Найдите бота по имени, которое задавали в BotFather.
2. Отправьте `/start`.
3. Задайте вопрос по материалам курса. Ответ с моделью появляется, когда заполнены `LLM_BASE_URL`, `LLM_API_KEY` и `LLM_MODEL`, а загрузка знаний уже прошла.

Если бот молчит, смотрите лог в том терминале, где запущен `uvicorn`. Частые причины: пустой `TELEGRAM_BOT_TOKEN`, неверный токен, пустые поля LLM, база не запущена (`docker compose ... ps` не показывает `postgres` в состоянии running).

---

## Prod (стенд, не для первой проверки)

Для стенда используется другой файл и другие скрипты. Проверяющим на локальной машине этот раздел не нужен.

1. `cp .env.prod.example .env.prod`
2. Заполнить те же секреты: `POSTGRES_PASSWORD` (в образце он пустой — задайте его и тот же пароль в `DATABASE_URL` и `DATABASE_URL_HOST`), `TELEGRAM_BOT_TOKEN`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Оставьте `APP_ENV=prod`, `DEBUG=false`, `LOG_LEVEL=INFO`.
3. Тот же файл дампа: `src/data/backups/alfa_course_hackathon.backup`.
4. `./scripts/prod/up-prod.sh` — Postgres, миграции, загрузка знаний при необходимости, затем контейнер бота. В prod-compose сервис `bot` включён.
5. Порт Postgres на компьютере по умолчанию **5433**, HTTP бота — **8000**.

```bash
./scripts/prod/down-prod.sh
./scripts/prod/down-prod.sh -purge
```

Дополнительные переменные скриптов `up-dev.sh` и `up-prod.sh`:

| Переменная | Смысл |
|------------|--------|
| `BACKUP_REL` | путь к дампу от корня репозитория (по умолчанию `src/data/backups/alfa_course_hackathon.backup`) |
| `FORCE_INGEST=1` | загрузить знания, даже если чанки уже есть |
| `INGEST_ARGS` | аргументы загрузчика, например `--dry-run --limit 10` |

Ручные команды compose и устройство скриптов: [scripts/README.md](scripts/README.md).

---

## Стек в compose

| Сервис | Dev | Prod |
|--------|-----|------|
| `postgres` | pgvector 17, дамп при пустом томе | то же, порт на компьютере 5433 |
| `migrate` | профиль `tools`, Alembic, разовый запуск | то же |
| `ingest` | профиль `tools`, чанки в pgvector, разовый запуск | то же |
| `bot` | в `docker-compose.dev.yml` закомментирован, бот запускается из venv | gunicorn + aiogram в контейнере |

Схема `public.*` приходит из дампа платформы. Схемы `app.*` и таблица `content.chunks` создаются миграциями; строки чанков пишет загрузка знаний.

## Таблица фактов

> На своем железе запускать строго с лимитом записей, иначе - токены (1800+ записе.й)

```
python -m src.modules.knowledge.facts --limit 20
```

## Tests
```python
pytest -q tests/scenarios -m integration
pytest -q tests/questions -m questions
```