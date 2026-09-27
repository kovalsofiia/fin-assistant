from datetime import date

import pytest

from agent.drafts import DraftError, build_draft, draft_model_result

TODAY = date(2026, 9, 27)
EXPENSE_CATEGORIES = [{"id": "c1", "name": "Таксі"}, {"id": "c2", "name": "Кава"}]


def draft(**overrides):
    args = {
        "type": "expense",
        "amount": 300,
        "transaction_date": "2026-09-26",
        "categories": EXPENSE_CATEGORIES,
        "is_fop": False,
        "today": TODAY,
    }
    args.update(overrides)
    return build_draft(**args)


def test_builds_draft_with_matched_category():
    assert draft(category="таксі", description="  Uber  ") == {
        "type": "expense",
        "amount": 300.0,
        "currency": "UAH",
        "date": "2026-09-26",
        "category_id": "c1",
        "category_name": "Таксі",
        "category_hint": None,
        "description": "Uber",
        "is_fop": False,
    }


def test_unknown_category_becomes_hint():
    result = draft(category="Ресторан")

    assert (result["category_id"], result["category_name"], result["category_hint"]) == (None, None, "Ресторан")


def test_no_category_and_blank_description():
    result = draft(description="   ")

    assert (result["category_id"], result["category_hint"], result["description"]) == (None, None, None)


def test_amount_is_rounded_and_description_truncated():
    result = draft(amount="12.345", description="x" * 300)

    assert result["amount"] == 12.35
    assert len(result["description"]) == 255


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"type": "transfer"}, "type"),
        ({"amount": "багато"}, "amount"),
        ({"amount": True}, "amount"),
        ({"amount": 0}, "amount"),
        ({"amount": 0.01}, "amount"),
        ({"amount": 10_000_001}, "amount"),
        ({"transaction_date": "26.09.2026"}, "transaction_date"),
        ({"transaction_date": "2026-09-28"}, "майбутньому"),
        ({"transaction_date": "2021-09-01"}, "5 років"),
    ],
)
def test_rejects_invalid(overrides, message):
    with pytest.raises(DraftError, match=message):
        draft(**overrides)


def test_today_is_allowed():
    assert draft(transaction_date="2026-09-27")["date"] == "2026-09-27"


def test_model_result_warns_not_to_claim_saved():
    result = draft_model_result(draft(category="Таксі"))

    assert result["status"] == "draft_shown"
    assert "не кажи, що її вже додано" in result["note"]
    assert result["draft"] == {"type": "expense", "amount": 300.0, "date": "2026-09-26", "category_name": "Таксі", "description": None}


def test_model_result_mentions_unknown_category():
    assert "«Ресторан» не знайдено" in draft_model_result(draft(category="Ресторан"))["note"]
