from src.modules.knowledge.follow_up import expand_follow_up, queries_for_turn


def test_follow_up_appends_previous_topic_for_search() -> None:
    query = expand_follow_up(
        "А для патента?",
        previous_question="Как вести учёт на УСН?",
        previous_material="Учёт на УСН",
    )

    assert query.startswith("А для патента?")
    assert "Как вести учёт на УСН?" in query
    assert "Учёт на УСН" in query


def test_ordinary_question_is_not_expanded() -> None:
    question = "Как вести учёт доходов на УСН?"
    assert (
        expand_follow_up(
            question,
            previous_question="старый вопрос",
            previous_material="Старый материал",
        )
        == question
    )


def test_follow_up_without_memory_stays_as_written() -> None:
    assert expand_follow_up("Подробнее", previous_question=None, previous_material=None) == (
        "Подробнее"
    )


def test_long_message_is_not_treated_as_follow_up() -> None:
    text = "А для патента? " + ("подробности " * 20)
    assert expand_follow_up(text, previous_question="учёт", previous_material=None) == text.strip()


def test_llm_question_stays_literal_when_search_is_expanded() -> None:
    question, search_query = queries_for_turn(
        "А для патента?",
        previous_question="Как вести учёт на УСН?",
        previous_material="Учёт на УСН",
    )

    assert question == "А для патента?"
    assert "Как вести учёт на УСН?" in search_query
    assert question != search_query
