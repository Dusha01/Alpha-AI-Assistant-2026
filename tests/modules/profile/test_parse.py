from src.data.models.enums import BusinessStage
from src.modules.profile.parse import parse_business_line


def test_parses_coffee_and_half_year() -> None:
    parsed = parse_business_line("Кофейня, полгода")
    assert parsed.sphere == "Кофейня"
    assert parsed.stage == BusinessStage.LT_YEAR


def test_detects_planning() -> None:
    parsed = parse_business_line("Маркетплейс, только планирую")
    assert parsed.stage == BusinessStage.PLANNING
