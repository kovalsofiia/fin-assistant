import json
from datetime import date

from fastapi import HTTPException

from agent import tools

EXTENSION_NAMES = {"get_tax_history", "get_exchange_rate", "get_financial_report", "get_profile", "list_categories"}


def run(name, arguments, user_id="user-1"):
    return json.loads(tools.execute_tool(name, arguments, user_id))


def test_all_eleven_tools_registered():
    assert EXTENSION_NAMES <= set(tools.TOOLS)
    assert len(tools.TOOLS) == 13


def test_tax_history(monkeypatch):
    monkeypatch.setattr(
        tools.analytics_router, "get_tax_history", lambda current_user_id: [{"year": 2026, "user": current_user_id}]
    )

    assert run("get_tax_history", {}) == [{"year": 2026, "user": "user-1"}]


def test_exchange_rate(monkeypatch):
    calls = {}

    def fake(currency_code, date_val):
        calls.update(code=currency_code, date=date_val)
        return 41.25

    monkeypatch.setattr(tools.nbu_service, "get_nbu_rate", fake)

    result = run("get_exchange_rate", {"currency": "usd", "rate_date": "2026-09-01"})

    assert result == {"currency": "USD", "date": "2026-09-01", "rate_uah": 41.25}
    assert calls == {"code": "USD", "date": date(2026, 9, 1)}


def test_exchange_rate_not_found(monkeypatch):
    monkeypatch.setattr(tools.nbu_service, "get_nbu_rate", lambda currency_code, date_val: 0.0)

    assert "error" in run("get_exchange_rate", {"currency": "EUR", "rate_date": "2026-09-01"})


def test_exchange_rate_rejects_bad_currency():
    assert "currency" in run("get_exchange_rate", {"currency": "долар"})["error"]


def test_financial_report_names_categories(monkeypatch):
    def fake_reports(period, start_date, end_date, current_user_id):
        assert (period, start_date, end_date) == ("weekly", None, None)
        return {"period": "weekly", "total_expenses": 30.0, "categories_spent": {"c1": 30.0}, "tips": []}

    monkeypatch.setattr(tools.analytics_router, "get_reports", fake_reports)
    monkeypatch.setattr(
        tools.categories_router, "get_categories", lambda current_user_id: {"all": [{"id": "c1", "name": "Кава"}]}
    )

    result = run("get_financial_report", {"period": "weekly"})

    assert result["categories_spent"] == [{"category": "Кава", "amount": 30.0}]
    assert result["total_expenses"] == 30.0


def test_financial_report_rejects_bad_period():
    assert "period" in run("get_financial_report", {"period": "decade"})["error"]


def test_profile_combines_profile_and_settings(monkeypatch):
    monkeypatch.setattr(
        tools.profiles_router, "get_profile", lambda user_id, current_user_id: {"full_name": "Тест", "id": user_id}
    )

    def no_settings(user_id, current_user_id):
        raise HTTPException(status_code=404, detail="нема")

    monkeypatch.setattr(tools.settings_router, "get_fop_settings", no_settings)

    assert run("get_profile", {}) == {"profile": {"full_name": "Тест", "id": "user-1"}, "fop_settings": None}


def test_list_categories(monkeypatch):
    monkeypatch.setattr(
        tools.categories_router,
        "get_categories",
        lambda current_user_id: {"all": [{"id": "c1", "name": "Їжа", "type": "expense", "user_id": None}]},
    )

    assert run("list_categories", {}) == {"categories": [{"id": "c1", "name": "Їжа", "type": "expense"}]}
