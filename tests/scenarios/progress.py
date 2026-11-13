"""Построчный отчёт прогона сценариев вместо точек pytest -q."""

from __future__ import annotations

from pathlib import Path

import pytest

SECTIONS = {
    "test_commands.py": "Команды",
    "test_knowledge_dialog.py": "База знаний",
    "test_profile_dialog.py": "Профиль",
    "test_recommend_dialog.py": "Подбор материалов",
    "test_reminders_dialog.py": "Напоминания",
    "test_tax_dialog.py": "Налоги",
    "test_jury.py": "Приёмка жюри",
    "test_edge.py": "Нестандартные случаи",
}

TITLES = {
    "test_commands.py::test_start_and_mention": (
        "/start и /start@бот показывают приветствие и три кнопки"
    ),
    "test_commands.py::test_help_unknown_sticker_and_too_long": (
        "/help, неизвестная команда, стикер и слишком длинный текст"
    ),
    "test_commands.py::test_blank_and_greeting_go_to_knowledge": (
        "пустое сообщение и «привет» идут в базу знаний"
    ),
    "test_commands.py::test_start_buttons_ask_recommend_and_remind": (
        "кнопки «вопрос», «материалы» и «напоминание» запускают свои сценарии"
    ),
    "test_commands.py::test_handler_exception_returns_error_general": (
        "сбой обработчика отвечает общей ошибкой, затем /help снова работает"
    ),
    "test_knowledge_dialog.py::test_answer_shows_source_feedback_and_business_prompt": (
        "ответ со источником, оценкой и вопросом про бизнес"
    ),
    "test_knowledge_dialog.py::test_feedback_yes_and_no": "оценка «да» и «нет»",
    "test_knowledge_dialog.py::test_no_business_prompt_when_sphere_known": (
        "сфера уже известна — анкету не предлагают"
    ),
    "test_knowledge_dialog.py::test_visa_question_is_not_found": (
        "виза в Китай — ответа нет, бот не выдумывает"
    ),
    "test_knowledge_dialog.py::test_related_material_when_answer_is_weak": (
        "слабый ответ предлагает близкий материал"
    ),
    "test_knowledge_dialog.py::test_clarify_with_variants_and_free_form": (
        "уточнение: варианты и свой текст"
    ),
    "test_knowledge_dialog.py::test_llm_error_has_no_feedback_and_no_profile_prompt": (
        "ошибка модели без оценки и без анкеты"
    ),
    "test_knowledge_dialog.py::test_answered_question_steers_next_recommendation": (
        "тема вопроса задаёт следующую подборку"
    ),
    "test_profile_dialog.py::test_coffee_half_year_saves_sphere_and_stage": (
        "«Кофейня, полгода» сохраняет сферу и стадию"
    ),
    "test_profile_dialog.py::test_sphere_without_stage_asks_for_buttons": (
        "сфера без стадии — бот просит выбрать стадию"
    ),
    "test_profile_dialog.py::test_blank_business_line_repeats_the_question": (
        "пустая строка повторяет вопрос про бизнес"
    ),
    "test_profile_dialog.py::test_skip_on_business_then_stage_without_a_saved_profile": (
        "пропуск бизнеса и стадии без сохранённого профиля"
    ),
    "test_profile_dialog.py::test_skip_on_stage_without_mode_asks_tax_then_stops": (
        "пропуск стадии спрашивает налог и останавливается"
    ),
    "test_profile_dialog.py::test_skip_on_tax_keeps_existing_mode": (
        "пропуск налога сохраняет уже выбранный режим"
    ),
    "test_profile_dialog.py::test_stage_buttons": "кнопка стадии сохраняет этап",
    "test_profile_dialog.py::test_tax_mode_buttons": "кнопка режима сохраняет налог",
    "test_profile_dialog.py::test_profile_card_and_edits": "карточка профиля и правки полей",
    "test_profile_dialog.py::test_profile_and_reminders_commands_leave_the_questionnaire": (
        "/profile и /reminders выходят из анкеты"
    ),
    "test_profile_dialog.py::test_remind_phrase_inside_profile_does_not_start_reminder": (
        "«напомни про налог» внутри анкеты не создаёт напоминание"
    ),
    "test_profile_dialog.py::test_reminder_text_is_not_saved_as_business": (
        "текст напоминания не сохраняется как бизнес"
    ),
    "test_recommend_dialog.py::test_empty_profile_gets_cold_start": (
        "пустой профиль получает холодный старт"
    ),
    "test_recommend_dialog.py::test_newbie_gets_learning_route": "новичок получает учебный маршрут",
    "test_recommend_dialog.py::test_coffee_usn_route_and_paid_line_stay_short": (
        "кофейня на УСН — маршрут и короткая платная строка"
    ),
    "test_recommend_dialog.py::test_marketing_profile_gets_its_route": (
        "маркетинг получает свой маршрут"
    ),
    "test_reminders_dialog.py::test_custom_reminder_confirms_before_create": (
        "своё напоминание подтверждается до создания"
    ),
    "test_reminders_dialog.py::test_edit_restarts_the_flow": "«изменить» начинает сценарий заново",
    "test_reminders_dialog.py::test_quick_phrase_keeps_text_and_asks_when": (
        "фраза «в пятницу» оставляет текст и спрашивает время"
    ),
    "test_reminders_dialog.py::test_time_phrases_land_on_different_instants": (
        "разные фразы времени дают разные моменты"
    ),
    "test_reminders_dialog.py::test_bad_and_past_time_stay_on_the_when_step": (
        "неверное и прошедшее время остаются на шаге «когда»"
    ),
    "test_reminders_dialog.py::test_list_empty_then_change_frequency": (
        "пустой список, затем смена частоты"
    ),
    "test_reminders_dialog.py::test_fire_custom_course_and_buttons": (
        "срабатывание своего и курса, кнопки готово / позже / выкл"
    ),
    "test_reminders_dialog.py::test_one_minute_reminder_is_sent_without_sleep": (
        "напоминание через минуту уходит без реального ожидания"
    ),
    "test_tax_dialog.py::test_usn_tax_reminder_can_be_quarterly_or_once": (
        "налог УСН — ежеквартально или один раз"
    ),
    "test_tax_dialog.py::test_patent_offer_uses_seeded_deadline": (
        "патент предлагает срок из справочника"
    ),
    "test_tax_dialog.py::test_npd_has_no_deadline": "у самозанятости нет срока в справочнике",
    "test_tax_dialog.py::test_known_mode_skips_the_questionnaire": (
        "известный режим пропускает анкету"
    ),
    "test_tax_dialog.py::test_saving_mode_without_tax_flag_does_not_offer_tax": (
        "сохранение режима без флага не предлагает налог"
    ),
    "test_tax_dialog.py::test_tax_fire_with_material_and_without": (
        "срабатывание налога с материалом и без него"
    ),
    "test_jury.py::test_jury_question_profile_and_recommendation": (
        "вопрос про УСН, профиль кофейни, шаблон и платный курс"
    ),
    "test_jury.py::test_jury_tax_reminder": "«напомни про налог»: подтверждение и отправка",
    "test_jury.py::test_jury_unclear_question_and_missing_answer": (
        "размытый вопрос про кредит и виза без ответа"
    ),
    "test_edge.py::test_reset_commands_leave_reminder_text_step": (
        "команда сбрасывает шаг «о чём напомнить»"
    ),
    "test_edge.py::test_profile_and_reminders_commands_drop_the_when_step": (
        "/profile и /reminders сбрасывают шаг «когда»"
    ),
    "test_edge.py::test_help_on_when_step_is_help_not_a_time_error": (
        "/help на шаге «когда» показывает справку, а не ошибку времени"
    ),
    "test_edge.py::test_question_on_confirm_stays_in_reminder_until_reset": (
        "вопрос на подтверждении не создаёт напоминание, пока нет сброса"
    ),
    "test_edge.py::test_start_and_help_reset_business_prompt": (
        "/start и /help сбрасывают вопрос про бизнес"
    ),
    "test_edge.py::test_command_shapes_and_polite_reminder_phrase": (
        "варианты команд и вежливое «пожалуйста напомни»"
    ),
    "test_edge.py::test_tax_intent_ignores_case_and_spaces": (
        "намерение «налог» не зависит от регистра и пробелов"
    ),
    "test_edge.py::test_bare_remind_asks_what_to_remember": "голое «напомни» спрашивает, о чём",
    "test_edge.py::test_odd_time_phrases": "кривые фразы времени: вчера, 25:00, ноль минут, завтра",
    "test_edge.py::test_business_line_does_not_read_tax_mode_from_the_tail": (
        "хвост строки про бизнес не читается как режим налога"
    ),
    "test_edge.py::test_emoji_sphere_is_stored": "сфера из эмодзи сохраняется",
    "test_edge.py::test_blank_sphere_edit_offers_profile_again": (
        "пустая правка сферы снова открывает профиль"
    ),
    "test_edge.py::test_markup_question_is_passed_through": (
        "вопрос с HTML-разметкой уходит в базу очищенным"
    ),
    "test_edge.py::test_feedback_buttons_work_without_a_prior_answer": (
        "кнопки оценки без предыдущего ответа не ломают диалог"
    ),
    "test_edge.py::test_unknown_callback_sends_no_message": "неизвестная кнопка ничего не пишет",
    "test_edge.py::test_stale_stage_and_mode_buttons_overwrite_profile": (
        "устаревшие кнопки стадии и режима перезаписывают профиль"
    ),
    "test_edge.py::test_skip_while_idle_answers_smalltalk": (
        "«пропустить» в покое отвечает короткой подсказкой"
    ),
    "test_edge.py::test_confirm_and_repeat_without_payload_do_not_create": (
        "подтверждение и повтор без черновика ничего не создают"
    ),
    "test_edge.py::test_tax_button_without_draft_is_an_error": (
        "кнопка налога без черновика отвечает ошибкой"
    ),
    "test_edge.py::test_missing_reminder_buttons_do_not_crash": (
        "кнопки чужого или пропавшего напоминания не роняют бота"
    ),
    "test_edge.py::test_second_tax_yes_does_not_duplicate": (
        "второй «да» по налогу не дублирует запись"
    ),
    "test_edge.py::test_second_confirm_does_not_duplicate": (
        "второе подтверждение не создаёт второе напоминание"
    ),
    "test_edge.py::test_callback_without_message_or_user_is_silent": (
        "кнопка без сообщения или пользователя молчит"
    ),
    "test_edge.py::test_dialogs_of_two_users_stay_apart": (
        "диалоги двух пользователей не смешиваются"
    ),
    "test_edge.py::test_foreign_reminder_id_can_pause_it": (
        "кнопка «выкл» с чужим id ставит напоминание на паузу"
    ),
    "test_edge.py::test_failed_send_is_retried_on_the_next_tick": (
        "неудачная отправка повторяется на следующем тике"
    ),
    "test_edge.py::test_missing_user_is_not_sent_and_stays_active": (
        "пропавший пользователь не получает сообщение, напоминание остаётся"
    ),
    "test_edge.py::test_quarterly_fire_moves_the_next_date": (
        "ежеквартальное срабатывание сдвигает дату на 91 день"
    ),
    "test_edge.py::test_partial_profiles_pick_different_routes": (
        "неполные профили получают разные маршруты"
    ),
    "test_edge.py::test_tax_and_marketing_in_one_question_keep_usn_topic": (
        "«налог и маркетинг» в одном вопросе оставляет тему УСН"
    ),
}

_TOPIC = {
    "usn": "УСН",
    "marketing": "маркетинг",
    "startup": "старт",
    "finance": "финансы",
}
_REPEAT = {
    "once": "один раз",
    "weekly": "каждую неделю",
    "monthly": "каждый месяц",
    "quarterly": "каждый квартал",
}
_STATUS = {
    "passed": ("ок", {"green": True}),
    "failed": ("сбой", {"red": True}),
    "skipped": ("пропуск", {"yellow": True}),
}

_section: str | None = None
_titles: dict[str, str] = {}


def scenario_title(nodeid: str) -> str:
    normalized = nodeid.replace("\\", "/")
    relative = normalized.split("tests/scenarios/", 1)[-1]
    path, _, rest = relative.partition("::")
    name = rest.partition("[")[0]
    title = TITLES.get(f"{path}::{name}")
    if title is None:
        title = name.removeprefix("test_").replace("_", " ")
    case = _titles.get(nodeid)
    if case:
        return f"{title} — {case}"
    return title


def remember(item: pytest.Item) -> None:
    nodeid = item.nodeid.replace("\\", "/")
    if "tests/scenarios/" not in nodeid:
        return
    case = _case(item)
    if case:
        _titles[item.nodeid] = case


def report_status(
    report: pytest.TestReport,
    config: pytest.Config,
) -> tuple[str, str, str] | None:
    if report.when != "call" or config.getoption("verbose") > 0:
        return None
    nodeid = str(report.nodeid).replace("\\", "/")
    if "tests/scenarios/" not in nodeid:
        return None
    _write(report, config)
    outcome = report.outcome
    if outcome in _STATUS:
        return outcome, "", outcome.upper()
    return None


def _case(item: pytest.Item) -> str | None:
    spec = getattr(item, "callspec", None)
    if spec is None:
        return None
    params: dict[str, object] = spec.params
    label = params.get("label")
    if label:
        return str(label)
    if "topic" in params:
        topic = str(params["topic"])
        return _TOPIC.get(topic, topic)
    if "repeat" in params:
        repeat = str(params["repeat"])
        return _REPEAT.get(repeat, repeat)
    for key in ("command", "phrase"):
        if key in params:
            return str(params[key])
    return None


def _write(report: pytest.TestReport, config: pytest.Config) -> None:
    global _section
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    filename = Path(str(report.nodeid).split("::", 1)[0]).name
    section = SECTIONS.get(filename, filename)
    if section != _section:
        _section = section
        reporter.write_line("")
        reporter.write_line(section, bold=True)
    status, markup = _STATUS.get(report.outcome, (report.outcome, {}))
    reporter.write_line(f"  {status:<7} {scenario_title(str(report.nodeid))}", **markup)
    reporter.flush()
