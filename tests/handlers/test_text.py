from src.handlers.errors import handler_failure_key
from src.handlers.text import COPY, FEEDBACK_BUTTONS, START_BUTTONS


def test_handler_texts_match_spec() -> None:
    assert COPY["start"] == (
        "👋 Здравствуйте! Я помощник «Альфа-Курса». Отвечаю на вопросы о запуске "
        "и ведении бизнеса по материалам платформы, подбираю полезные курсы "
        "и шаблоны и могу напомнить о важных датах. О чём хотите спросить?"
    )
    assert COPY["help"] == (
        "👋 Вот что я умею:\n"
        "— отвечать на вопросы по материалам «Альфа-Курса»;\n"
        "— подбирать материалы под ваш бизнес;\n"
        "— напоминать о налогах и обучении.\n"
        "Команды: /profile — что я знаю о вашем бизнесе, /reminders — ваши напоминания."
    )
    assert COPY["unknown_command"] == (
        "Такой команды я не знаю. Напишите вопрос обычным сообщением или отправьте /help."
    )
    assert COPY["non_text"] == (
        "Пока я понимаю только текст. Напишите, пожалуйста, вопрос словами."
    )
    assert COPY["smalltalk"] == (
        "Рад помочь! Спросите о любом вопросе бизнеса: налоги, учёт, маркетинг, продажи."
    )
    assert COPY["error_general"] == (
        "Что-то пошло не так. Попробуйте ещё раз или отправьте /start."
    )
    assert COPY["too_long"] == (
        "Сообщение получилось длинным. Сформулируйте, пожалуйста, "
        "главный вопрос в одном-двух предложениях."
    )
    assert COPY["answer_source"] == "Подробнее в материале «{material_name}»: {url}"
    assert COPY["clarify"] == (
        "Уточните, пожалуйста, что именно вас интересует: {variant_1} или {variant_2}?"
    )
    assert COPY["clarify_free"] == (
        "Чтобы ответить точнее, расскажите чуть подробнее: о какой ситуации речь?"
    )
    assert COPY["not_found"] == (
        "В материалах «Альфа-Курса» нет ответа на этот вопрос, поэтому не буду гадать. "
        "Напишите, какую задачу по запуску, учёту, налогам или продажам разобрать."
    )
    assert "консульства" in COPY["not_found_visa"]
    assert "курс" in COPY["not_found_fx"]
    assert "рецепт" in COPY["not_found_recipe"].lower() or "Рецепта" in COPY["not_found_recipe"]
    assert "код" in COPY["not_found_code"]
    assert "VIN" in COPY["not_found_vin"]
    assert "кофемашин" in COPY["not_found_device"]
    assert "банк" in COPY["not_found_banks"]
    assert "инструкц" in COPY["not_found_prompt"]
    assert COPY["not_found_related"] == (
        "Точного ответа в материалах нет, но вот что может быть полезно: "
        "«{material_name}» — {benefit}. {url}"
    )
    assert COPY["feedback"] == "Ответ помог?"
    assert COPY["feedback_no"] == (
        "Спасибо, что сказали. Попробуйте переформулировать вопрос, и я поищу ещё раз."
    )
    assert COPY["error_llm"] == (
        "Не получилось подготовить ответ, это техническая заминка. "
        "Попробуйте, пожалуйста, ещё раз через минуту."
    )
    assert START_BUTTONS == (
        "Задать вопрос",
        "Подобрать материалы",
        "Поставить напоминание",
    )
    assert FEEDBACK_BUTTONS == (("Да", "feedback_yes"), ("Нет", "feedback_no"))
    assert handler_failure_key() == "error_general"
    assert COPY[handler_failure_key()].strip()


def test_friendly_lines_keep_one_emoji_and_spec_wording() -> None:
    assert COPY["profile_saved"] == "✅ Запомнил: {что_запомнил}. Поменять можно в /profile."
    assert COPY["reminder_created"].startswith("✅ Готово!")
    assert COPY["tax_created"].startswith("✅ Готово:")
    assert COPY["recommend_free"].startswith("📚 Советую")
    assert COPY["recommend_paid"].startswith("📚 Если хотите")
    assert COPY["recommend_route"].startswith("📚 Предлагаю")
    assert COPY["recommend_cold"].startswith("📚 Вот с чего")
    assert COPY["reminder_fire_course"].startswith("⏰ Напоминаю:")
    assert COPY["reminder_fire_custom"].startswith("⏰ Напоминание:")
    assert COPY["tax_fire"].startswith("⏰ Через")
    assert COPY["clarify"].startswith("Уточните")
    assert COPY["not_found"].startswith("В материалах")
    assert COPY["error_llm"].startswith("Не получилось")
    assert COPY["error_general"].startswith("Что-то пошло")
    assert COPY["too_long"].startswith("Сообщение получилось")
    assert START_BUTTONS == (
        "Задать вопрос",
        "Подобрать материалы",
        "Поставить напоминание",
    )
