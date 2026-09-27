import json
from datetime import date, timedelta

from agent import tools

CATEGORIES = {
    "all": [
        {"id": "c1", "name": "Таксі", "type": "expense"},
        {"id": "c2", "name": "Кава", "type": "expense"},
        {"id": "c3", "name": "Зарплата", "type": "income"},
    ],
    "expense": [{"id": "c1", "name": "Таксі"}, {"id": "c2", "name": "Кава"}],
    "income": [{"id": "c3", "name": "Зарплата"}],
    "user_is_fop": False,
}


def run(name, arguments, user_id="user-1"):
    content, attachment = tools.run_tool(name, arguments, user_id)
    return json.loads(content), attachment


def use_categories(monkeypatch):
    monkeypatch.setattr(tools.categories_router, "get_categories", lambda current_user_id: CATEGORIES)


def forbid(monkeypatch, handler_name):
    def boom(**kwargs):
        raise AssertionError(f"{handler_name} must not be called")

    monkeypatch.setattr(tools.transactions_router, handler_name, boom)


def chart_args(**overrides):
    args = {"chart": "bar", "group_by": "month", "start_date": "2026-08-01", "end_date": "2026-09-30"}
    args.update(overrides)
    return args


def test_ui_tools_registered():
    assert {"build_chart", "propose_transaction"} <= set(tools.TOOLS)


def test_build_chart_passes_user_filters_and_returns_attachment(monkeypatch):
    calls = {}

    def fake_get(current_user_id, limit, offset, start_date, end_date, type, category_id, search):
        calls.update(
            user=current_user_id, limit=limit, start=start_date, end=end_date, type=type, category_id=category_id, search=search
        )
        return [{"transaction_type": "expense", "transaction_amount": 100, "transaction_date": "2026-09-03", "category_id": "c1"}]

    monkeypatch.setattr(tools.transactions_router, "get_transactions", fake_get)
    use_categories(monkeypatch)

    result, attachment = run("build_chart", chart_args(categories=["таксі"]))

    assert calls == {
        "user": "user-1",
        "limit": tools.MAX_CHART_TRANSACTIONS + 1,
        "start": date(2026, 8, 1),
        "end": date(2026, 9, 30),
        "type": "expense",
        "category_id": "c1",
        "search": None,
    }
    assert attachment["type"] == "chart"
    assert attachment["chart"]["labels"] == ["2026-08", "2026-09"]
    assert attachment["chart"]["datasets"] == [{"label": "Таксі", "data": [0, 100.0]}]
    assert result == {"status": "chart_shown", "labels": 2, "unit": "грн", "series": [{"label": "Таксі", "total": 100.0}]}


def test_build_chart_both_types_does_not_filter_by_type(monkeypatch):
    calls = {}

    def fake_get(**kwargs):
        calls.update(kwargs)
        return []

    monkeypatch.setattr(tools.transactions_router, "get_transactions", fake_get)

    _, attachment = run("build_chart", chart_args(type="both"))

    assert calls["type"] is None
    assert calls["category_id"] is None
    assert [d["label"] for d in attachment["chart"]["datasets"]] == ["Доходи", "Витрати"]


def test_build_chart_by_category_uses_names(monkeypatch):
    monkeypatch.setattr(
        tools.transactions_router,
        "get_transactions",
        lambda **kwargs: [{"transaction_type": "expense", "transaction_amount": 30, "transaction_date": "2026-09-01", "category_id": "c2"}],
    )
    use_categories(monkeypatch)

    _, attachment = run("build_chart", chart_args(chart="doughnut", group_by="category"))

    assert attachment["chart"]["labels"] == ["Кава"]


def test_build_chart_unknown_category_lists_available(monkeypatch):
    use_categories(monkeypatch)
    forbid(monkeypatch, "get_transactions")

    result, attachment = run("build_chart", chart_args(categories=["Ресторани"]))

    assert attachment is None
    assert "Невідомі категорії: Ресторани" in result["error"]
    assert "Кава" in result["error"]


def test_build_chart_too_many_transactions(monkeypatch):
    row = {"transaction_type": "expense", "transaction_amount": 1, "transaction_date": "2026-09-01", "category_id": "c1"}
    monkeypatch.setattr(
        tools.transactions_router, "get_transactions", lambda **kwargs: [row] * (tools.MAX_CHART_TRANSACTIONS + 1)
    )

    result, attachment = run("build_chart", chart_args())

    assert attachment is None
    assert "Забагато транзакцій" in result["error"]


def test_build_chart_invalid_spec(monkeypatch):
    forbid(monkeypatch, "get_transactions")

    result, attachment = run("build_chart", chart_args(chart="pie"))

    assert attachment is None
    assert "chart" in result["error"]


def test_propose_transaction_builds_draft_without_writing(monkeypatch):
    use_categories(monkeypatch)
    forbid(monkeypatch, "create_transaction")
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    result, attachment = run(
        "propose_transaction",
        {"type": "expense", "amount": 300, "transaction_date": yesterday, "category": "таксі", "description": "Uber"},
    )

    assert attachment == {
        "type": "transaction_draft",
        "draft": {
            "type": "expense",
            "amount": 300.0,
            "currency": "UAH",
            "date": yesterday,
            "category_id": "c1",
            "category_name": "Таксі",
            "category_hint": None,
            "description": "Uber",
            "is_fop": False,
        },
    }
    assert result["status"] == "draft_shown"
    assert "не кажи, що її вже додано" in result["note"]


def test_propose_transaction_unknown_category(monkeypatch):
    use_categories(monkeypatch)

    result, attachment = run(
        "propose_transaction", {"type": "expense", "amount": 50, "transaction_date": date.today().isoformat(), "category": "Ресторан"}
    )

    assert attachment["draft"]["category_id"] is None
    assert attachment["draft"]["category_hint"] == "Ресторан"
    assert "«Ресторан» не знайдено" in result["note"]


def test_propose_transaction_invalid_amount(monkeypatch):
    use_categories(monkeypatch)

    result, attachment = run("propose_transaction", {"type": "expense", "amount": -5, "transaction_date": "2026-09-01"})

    assert attachment is None
    assert "amount" in result["error"]


def test_execute_tool_returns_only_model_json(monkeypatch):
    use_categories(monkeypatch)

    content = tools.execute_tool(
        "propose_transaction", {"type": "income", "amount": 1000, "transaction_date": date.today().isoformat()}, "user-1"
    )

    assert json.loads(content)["status"] == "draft_shown"
