from src.data.models import BusinessStage, TaxMode


def test_business_stage_values() -> None:
    assert {stage.value for stage in BusinessStage} == {
        "planning",
        "lt_year",
        "gt_year",
    }


def test_tax_mode_values() -> None:
    assert {mode.value for mode in TaxMode} == {
        "usn",
        "patent",
        "npd",
        "other",
        "unknown",
    }
