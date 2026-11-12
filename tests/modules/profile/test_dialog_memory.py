from src.modules.profile.dialog_memory import payload_after_reset, payload_with_follow_up


def test_reset_drops_flow_and_keeps_topic_memory() -> None:
    payload = payload_after_reset(
        {
            "reminder_text": "налог",
            "tax_reminder_pending": True,
            "last_topic": "usn",
            "follow_question": "Как вести учёт на УСН?",
            "follow_material": "Учёт на УСН",
        }
    )

    assert payload == {
        "last_topic": "usn",
        "follow_question": "Как вести учёт на УСН?",
        "follow_material": "Учёт на УСН",
    }


def test_follow_up_memory_keeps_existing_topic() -> None:
    payload = payload_with_follow_up(
        {"last_topic": "usn", "reminder_text": "черновик"},
        question="Как вести учёт на УСН?",
        material_title="Учёт на УСН",
    )

    assert payload["last_topic"] == "usn"
    assert payload["follow_question"] == "Как вести учёт на УСН?"
    assert payload["follow_material"] == "Учёт на УСН"
    assert payload["reminder_text"] == "черновик"
