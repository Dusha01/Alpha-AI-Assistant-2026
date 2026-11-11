# Контракт данных кейса

Схема приложения — `app` (`app.users`, `app.profiles`, `app.dialog_states`). Её создаёт Alembic.
`public` принадлежит кейсу: мы не меняем его таблицы, колонки и данные.

## Каталог материалов

| Материал | Таблица | Строк |
|---|---|---:|
| Статьи | `public."Articles"` | 855 |
| Курсы | `public."Courses"` | 37 |
| Уроки | `public."Lessons"` | 508 |
| Документы и шаблоны | `public."Documents"` | 247 |
| Вебинары | `public."Webinars"` | 19 |
| Подкасты | `public."Podcasts"` | 8 |
| Глоссарий | `public."Glossary"` | 351 |
| Калькуляторы | `public."Calculators"` | 7 |
| Лендинги | `public."Landings"` | 33 |

Имена таблиц и колонок в `public` регистрозависимые, в SQL их нужно брать в кавычки:
`"Articles"`, `"Url"`, `"StatusId"` и т.д.

## Ссылка на материал

- `Url` во всех таблицах материалов — **slug**, а не полный URL.
  Примеры: `gde-vzyat-dengi-na-biznes`, `azy-finansovoj-gramotnosti`.
  Домена платформы в базе нет; его нужно задавать конфигом приложения.
- У `public."Lessons"` поля `Url` нет. Урок связан с курсом через
  `public."CourseLessonBindings"` (`"CourseId"`, `"LessonId"`, `"Order"`, `"IsTrial"`),
  ссылку строим от `public."Courses"."Url"`.
- `public."Webinars"."Url"` nullable.
- `public."Files"."Url"` — относительный путь к файлу, например
  `/3442d095-29b7-4e12-bd70-cff37e019ca2_File_133934210628242051.pdf`.
- У `public."Documents"` поля `"FileId"` и `"FileIdNew"` существуют, но **все значения NULL**.
  Использовать их как ссылку на файл нельзя. Для документа доступен `"Url"` (slug страницы)
  и блоки `public."DocumentEmbedItems"`.

## Платность

Единого признака платности у материалов нет. Фактические данные такие:

- Для курсов признак задаёт `public."Courses"."TypeId"` → `public."CourseTypes"."Id"`:

  | `CourseTypes."Title"` | `CourseTypes."Id"` | Курсов |
  |---|---|---:|
  | `Открытый` | `ed085df2-b9bf-43fc-9a29-e2140346e333` | 32 |
  | `По подписке` | `1069fd62-8920-417b-b6c1-1bfb7c3f57fb` | 4 |
  | `Платный` | `9cda1148-8db6-4d29-98fc-6d67ea538fff` | 1 |
  | `Закрытый` | `50c186e6-14c2-4446-81c5-5263fd5b3362` | 0 |

- `public."Courses"."Cost"` заполнен у 1 строки, `public."Podcasts"."Cost"` — у 0 строк.
  Как надёжный признак платности они не подходят.
- `public."CourseUserBindings"."IsPaid"` — факт покупки конкретным пользователем,
  а не свойство каталога.
- `public."CourseLessonBindings"."IsTrial"` — признак пробного урока.
- `public."LessonEmbedItems"` содержит полные тексты уроков, включая платные.
  Для платных материалов в ответ нельзя отдавать тело урока: только название,
  краткую пользу и ссылку.
- `public."Articles"."IsPublic"` и `public."Topics"."IsPublic"` — не платность.
- `public."Topics"."PaidCount" / "PrivateCount" / "PublicCount" / "SubscriptionCount"` —
  агрегаты по теме, а не признак конкретного материала.

## Embed-блоки

Контент материалов лежит в embed-таблицах, а не в родительских `Content`:

| Таблица | Родительская колонка | Колонки |
|---|---|---|
| `public."ArticleEmbedItems"` | `"ArticleId"` | `"Id"`, `"Type"`, `"HtmlContent"`, `"Params"`, `"Order"` |
| `public."LessonEmbedItems"` | `"LessonId"` | `"Id"`, `"Type"`, `"HtmlContent"`, `"Params"`, `"Order"` |
| `public."DocumentEmbedItems"` | `"DocumentId"` | `"Id"`, `"Type"`, `"HtmlContent"`, `"Params"`, `"Order"` |
| `public."GlossaryEmbedItems"` | `"GlossaryId"` | `"Id"`, `"Type"`, `"HtmlContent"`, `"Params"`, `"Order"` |
| `public."CalculatorPageEmbedItems"` | `"CalculatorPageId"` | `"Id"`, `"Type"`, `"HtmlContent"`, `"Params"`, `"Order"` |

- `"Type"` — integer-дискриминатор. Фактически встречаются значения `0–9`, `13`, `14`.
  Семантику конкретного значения по базе не восстановить, её нельзя додумывать.
- `"HtmlContent"` и `"Params"` имеют тип `citext`. У большинства просмотренных блоков
  `"Params"` — `{}`; текст лежит в `"HtmlContent"`.
- `public."Articles"."Content"` и `public."Lessons"."Content"` существуют, но
  **все значения пустые**. Использовать их как источник текста нельзя.
- Количество блоков: `ArticleEmbedItems` — 32 475, `LessonEmbedItems` — 2 892,
  `DocumentEmbedItems` — 274, `GlossaryEmbedItems` — 5 756.

## Публикация и удаление

- `public."Statuses"."Id" = '61f12dbc-3cd4-4c14-b64b-1709548b904e'` — `Опубликовано`.
- Для `Articles`, `Courses`, `Documents`, `Glossary`, `Landings`, `Podcasts`
  фильтр публикации: `"StatusId" = '61f12dbc-3cd4-4c14-b64b-1709548b904e'`
  и `"IsDeleted" = false`.
- У `Articles`, `Courses`, `Documents`, `Glossary`, `Landings`, `Podcasts`
  есть `"Published"`. У `Webinars` его нет — используем `"StartsAt"`, `"EndsAt"`, `"StatusId"`.
- У `Calculators` нет `"StatusId"` — фильтруем только по `"IsDeleted" = false`.
- `Lessons` не имеет собственного статуса публикации; доступность определяется
  связью `CourseLessonBindings` и курсом.

## Связи и навигация

- `public."ContentSettings"` связывает материал с типом и статусом:
  `"EntityId"` → id материала, `"EntityTypeId"` → тип сущности, `"TypeId"` → тип курса,
  `"StatusId"` → статус. Связи с темами и отраслями лежат в
  `ContentSettingsTopics` и `ContentSettingsIndustries`.
- Фактические `EntityTypeId` в `ContentSettings`:

  | Сущность | `EntityTypeId` | Строк |
  |---|---|---:|
  | Статья | `8ede4179-0faf-407d-a4fc-1d94f9a63089` | 855 |
  | Документ | `da1ad865-8605-4ab1-9f6c-4489a26fbc35` | 247 |
  | Курс | `8b440b1a-00c3-423a-9bae-3376475eb203` | 37 |
  | Вебинар | `ece4acf3-5dd3-47b9-9f08-99c0d6203cc7` | 19 |
  | Подкаст | `142c23e2-bf71-4a73-b12e-6b1b5e4d47cc` | 8 |

- `public."vw_SubscriptionCatalog"` — представление каталога над `Landings`, `Podcasts`,
  `Articles`. Это не таблица и не замена `Courses`.
- `public."RecommendedItems"` — связи материалов (`"ItemId"`, `"ItemTypeId"`, `"CourseId"`, `"Order"`).
- `public."__EFMigrationsHistory"` — история миграций EF Core платформы. К нашему Alembic
  отношения не имеет, трогать её нельзя.

## Расширения

В восстановленной базе установлены `citext`, `btree_gin`, `pg_trgm`.
Расширения `vector` нет — его добавление будет отдельной задачей RAG, не частью
первой миграции `app`.
