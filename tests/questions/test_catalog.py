from tests.questions.catalog import CASES


def test_catalog_lists_every_question_once() -> None:
    assert [case.number for case in CASES] == list(range(1, 57))
