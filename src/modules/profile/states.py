IDLE = "idle"
ASK_BUSINESS = "ask_business"
ASK_STAGE = "ask_stage"
ASK_TAX = "ask_tax"
EDIT_SPHERE = "edit_sphere"
EDIT_STAGE = "edit_stage"
EDIT_MODE = "edit_mode"

ACTIVE_STATES = frozenset(
    {
        ASK_BUSINESS,
        ASK_STAGE,
        ASK_TAX,
        EDIT_SPHERE,
        EDIT_STAGE,
        EDIT_MODE,
    }
)
