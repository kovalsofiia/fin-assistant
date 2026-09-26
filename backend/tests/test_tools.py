import json
from datetime import date

from fastapi import HTTPException

from agent import tools
from models.common import ReportingPeriod

CORE_NAMES = {
    "get_transactions_summary",
    "get_expenses_by_category",
    "get_insights",
    "get_tax_estimate",
    "list_transactions",
    "get_budgets_progress",
}


def run(name, arguments, user_id="user-1"):
    return json.loads(tools.execute_tool(name, arguments, user_id))


def test_core_tools_registered():
    assert CORE_NAMES <= set(tools.TOOLS)


def test_schemas_match_registry():
    schemas = tools.tool_schemas()

    assert [s["function"]["name"] for s in schemas] == list(tools.TOOLS)
    for schema in schemas:
        assert schema["type"] == "function"
        assert schema["function"]["description"]
        assert schema["function"]["parameters"]["type"] == "object"


def test_transactions_summary_passes_user_and_parsed_date(monkeypatch):
    calls = {}

    def fake(current_user_id, end_date):
        calls.update(user=current_user_id, end_date=end_date)
        return {"balance": 100}

    monkeypatch.setattr(tools.transactions_router, "get_transaction_summary", fake)

    assert run("get_transactions_summary", {"end_date": "2026-09-30"}) == {"balance": 100}
    assert calls == {"user": "user-1", "end_date": date(2026, 9, 30)}


def test_invalid_date_returns_error():
    result = run("get_transactions_summary", {"end_date": "30.09.2026"})

    assert "YYYY-MM-DD" in result["error"]


def test_expenses_by_category_maps_names_and_sorts(monkeypatch):
    def fake_reports(period, start_date, end_date, current_user_id):
        assert (start_date, end_date, current_user_id) == ("2026-09-01", "2026-09-30", "user-1")
        return {
            "total_expenses": 350.0,
            "total_income": 1000.0,
            "categories_spent": {"c1": 100.0, "c2": 200.0, "gone": 50.0},
        }

    monkeypatch.setattr(tools.analytics_router, "get_reports", fake_reports)
    monkeypatch.setattr(
        tools.categories_router,
        "get_categories",
        lambda current_user_id: {"all": [{"id": "c1", "name": "Їжа"}, {"id": "c2", "name": "Оренда"}]},
    )

    result = run("get_expenses_by_category", {"start_date": "2026-09-01", "end_date": "2026-09-30"})

    assert result == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "total_expenses": 350.0,
        "total_income": 1000.0,
        "categories": [
            {"category": "Оренда", "amount": 200.0},
            {"category": "Їжа", "amount": 100.0},
            {"category": "Інше", "amount": 50.0},
        ],
    }


def test_period_requires_start_before_end():
    result = run("get_insights", {"start_date": "2026-09-30", "end_date": "2026-09-01"})

    assert "start_date" in result["error"]


def test_period_requires_both_dates():
    result = run("get_insights", {"start_date": None, "end_date": "2026-09-01"})

    assert "start_date" in result["error"]


def test_insights_passes_iso_dates(monkeypatch):
    calls = {}

    def fake(start_date, end_date, current_user_id):
        calls.update(start=start_date, end=end_date, user=current_user_id)
        return {"summary": {}}

    monkeypatch.setattr(tools.analytics_router, "get_insights", fake)

    assert run("get_insights", {"start_date": "2026-07-01", "end_date": "2026-09-30"}) == {"summary": {}}
    assert calls == {"start": "2026-07-01", "end": "2026-09-30", "user": "user-1"}


def test_tax_estimate_converts_period(monkeypatch):
    calls = {}

    def fake(current_user_id, annual_income, monthly_income, period, calc_date):
        calls.update(user=current_user_id, period=period, calc_date=calc_date)
        return {"taxes": {"total_period_tax": 1.0}, "warnings": []}

    monkeypatch.setattr(tools.tax_rules_router, "calculate_tax", fake)

    result = run("get_tax_estimate", {"period": "quarter"})

    assert result["taxes"]["total_period_tax"] == 1.0
    assert calls == {"user": "user-1", "period": ReportingPeriod.QUARTER, "calc_date": None}


def test_tax_estimate_rejects_unknown_period():
    assert "period" in run("get_tax_estimate", {"period": "week"})["error"]


def test_list_transactions_caps_limit_and_passes_filters(monkeypatch):
    calls = {}

    def fake(current_user_id, limit, offset, start_date, end_date, type, category_id, search):
        calls.update(limit=limit, offset=offset, start=start_date, type=type, search=search)
        return [{"id": "t1"}]

    monkeypatch.setattr(tools.transactions_router, "get_transactions", fake)

    result = run("list_transactions", {"limit": 500, "type": "expense", "search": "оренда", "start_date": "2026-09-01"})

    assert result == [{"id": "t1"}]
    assert calls == {"limit": 50, "offset": 0, "start": date(2026, 9, 1), "type": "expense", "search": "оренда"}


def test_list_transactions_rejects_bad_type():
    assert "type" in run("list_transactions", {"type": "refund"})["error"]


def test_budgets_progress(monkeypatch):
    monkeypatch.setattr(
        tools.budgets_router, "get_budgets_progress", lambda current_user_id: [{"spent": 10, "user": current_user_id}]
    )

    assert run("get_budgets_progress", {}) == [{"spent": 10, "user": "user-1"}]


def test_http_exception_becomes_error(monkeypatch):
    def fake(**kwargs):
        raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")

    monkeypatch.setattr(tools.tax_rules_router, "calculate_tax", fake)

    assert run("get_tax_estimate", {"period": "month"}) == {"error": "Налаштування ФОП не знайдено"}


def test_unexpected_exception_is_hidden(monkeypatch):
    def fake(current_user_id):
        raise RuntimeError("secret connection string")

    monkeypatch.setattr(tools.budgets_router, "get_budgets_progress", fake)

    assert run("get_budgets_progress", {}) == {"error": "Внутрішня помилка інструменту"}


def test_unknown_tool():
    assert "drop_tables" in run("drop_tables", {})["error"]


def test_unexpected_argument_is_rejected():
    assert "error" in run("get_budgets_progress", {"foo": 1})


def test_model_cannot_override_user_id(monkeypatch):
    called = []
    monkeypatch.setattr(tools.budgets_router, "get_budgets_progress", lambda current_user_id: called.append(current_user_id))

    result = run("get_budgets_progress", {"user_id": "someone-else"})

    assert "error" in result
    assert called == []


def test_large_result_is_truncated(monkeypatch):
    monkeypatch.setattr(
        tools.budgets_router, "get_budgets_progress", lambda current_user_id: ["x" * 1000 for _ in range(20)]
    )

    raw = tools.execute_tool("get_budgets_progress", {}, "user-1")
    result = json.loads(raw)

    assert result["truncated"] is True
    assert len(result["data_preview"]) == tools.MAX_RESULT_CHARS
