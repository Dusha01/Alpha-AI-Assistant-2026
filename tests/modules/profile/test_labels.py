from src.data.models import Profile
from src.data.models.enums import BusinessStage, TaxMode
from src.modules.profile.labels import format_profile_show, is_profile_empty


def test_profile_empty_detection() -> None:
    assert is_profile_empty(None) is True
    assert is_profile_empty(Profile(user_id=None)) is True  # type: ignore[arg-type]


def test_profile_show_renders_fields() -> None:
    import uuid

    text = format_profile_show(
        Profile(
            user_id=uuid.uuid4(),
            sphere="Кофейня",
            stage=BusinessStage.LT_YEAR,
            mode=TaxMode.USN,
        )
    )
    assert "Кофейня" in text
    assert "УСН" in text
