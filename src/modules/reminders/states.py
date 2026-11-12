IDLE = "idle"

REMINDER_TEXT = "reminder_text"
REMINDER_WHEN = "reminder_when"
REMINDER_REPEAT = "reminder_repeat"
REMINDER_CONFIRM = "reminder_confirm"

ACTIVE_STATES = frozenset(
    {
        REMINDER_TEXT,
        REMINDER_WHEN,
        REMINDER_REPEAT,
        REMINDER_CONFIRM,
    }
)
