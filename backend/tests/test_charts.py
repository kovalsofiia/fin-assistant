from datetime import date

import pytest

from agent import charts
from agent.charts import ChartSpecError, build_chart_data, parse_chart_spec, summarize_chart, time_labels


def spec(**overrides):
    args = {"chart": "bar", "group_by": "month", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    args.update(overrides)
    return parse_chart_spec(**args)


def tx(amount, day, type="expense", category_id="c1"):
    return {"transaction_amount": amount, "transaction_date": day, "transaction_type": type, "category_id": category_id}


def test_parse_defaults():
    parsed = spec()

    assert parsed == charts.ChartSpec(
        chart="bar", group_by="month", start=date(2026, 7, 1), end=date(2026, 9, 30), type="expense", metric="sum"
    )


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"chart": "pie"}, "chart"),
        ({"group_by": "year"}, "group_by"),
        ({"type": "refund"}, "type"),
        ({"metric": "avg"}, "metric"),
        ({"start_date": "01.07.2026"}, "start_date"),
        ({"start_date": "2026-10-01"}, "start_date не може"),
        ({"start_date": "2024-01-01", "end_date": "2026-01-02"}, "731"),
        ({"chart": "doughnut", "group_by": "month"}, "doughnut"),
        ({"chart": "doughnut", "group_by": "category", "type": "both"}, "doughnut"),
        ({"categories": "Таксі"}, "categories"),
        ({"categories": ["Таксі", " "]}, "categories"),
        ({"categories": [f"c{i}" for i in range(13)]}, "12"),
    ],
)
def test_parse_rejects_invalid(overrides, message):
    with pytest.raises(ChartSpecError, match=message):
        spec(**overrides)


def test_parse_cleans_categories_search_and_title():
    parsed = spec(categories=[" Таксі", "Таксі", "Кава"], search="  uber ", title="x" * 100)

    assert parsed.categories == ("Таксі", "Кава")
    assert parsed.search == "uber"
    assert parsed.title == "x" * charts.MAX_TITLE_CHARS


def test_time_labels():
    assert time_labels(date(2026, 9, 29), date(2026, 10, 1), "day") == ["2026-09-29", "2026-09-30", "2026-10-01"]
    # 2026-09-02 — середа, тож перший тиждень починається з понеділка 2026-08-31
    assert time_labels(date(2026, 9, 2), date(2026, 9, 15), "week") == ["2026-08-31", "2026-09-07", "2026-09-14"]
    assert time_labels(date(2026, 7, 15), date(2026, 9, 1), "month") == ["2026-07", "2026-08", "2026-09"]


def test_expenses_by_month_fill_zeros_and_ignore_income():
    rows = [tx(100, "2026-07-03"), tx(50.556, "2026-09-10"), tx(999, "2026-08-01", type="income")]

    data = build_chart_data(spec(), rows, {})

    assert data == {
        "chart": "bar",
        "title": "Сума витрат по місяцях",
        "labels": ["2026-07", "2026-08", "2026-09"],
        "datasets": [{"label": "Витрати", "data": [100.0, 0, 50.56]}],
        "unit": "грн",
        "start_date": "2026-07-01",
        "end_date": "2026-09-30",
    }


def test_both_types_by_month():
    rows = [tx(100, "2026-07-03"), tx(1000, "2026-07-05", type="income")]

    data = build_chart_data(spec(type="both", start_date="2026-07-01", end_date="2026-07-31"), rows, {})

    assert data["datasets"] == [{"label": "Доходи", "data": [1000.0]}, {"label": "Витрати", "data": [100.0]}]
    assert data["title"] == "Сума доходів і витрат по місяцях"


def test_selected_categories_make_one_series_each():
    rows = [tx(100, "2026-07-03", category_id="c1"), tx(40, "2026-08-03", category_id="c2"), tx(7, "2026-08-04", category_id="c3")]

    data = build_chart_data(spec(categories=["Таксі", "Кава"]), rows, {}, selected={"c1": "Таксі", "c2": "Кава"})

    assert data["datasets"] == [
        {"label": "Таксі", "data": [100.0, 0, 0]},
        {"label": "Кава", "data": [0, 40.0, 0]},
    ]


def test_by_category_sorted_with_names_and_unknown_as_other():
    rows = [tx(10, "2026-07-01", category_id="c1"), tx(30, "2026-07-02", category_id="c2"), tx(5, "2026-07-03", category_id=None)]

    data = build_chart_data(spec(chart="doughnut", group_by="category"), rows, {"c1": "Кава", "c2": "Таксі"})

    assert data["labels"] == ["Таксі", "Кава", "Інше"]
    assert data["datasets"] == [{"label": "Витрати", "data": [30.0, 10.0, 5.0]}]


def test_by_category_folds_tail_into_other():
    names = {f"c{i}": f"Категорія {i:02d}" for i in range(13)}
    rows = [tx(100 - i, "2026-07-01", category_id=f"c{i}") for i in range(13)]

    data = build_chart_data(spec(group_by="category"), rows, names)

    assert len(data["labels"]) == charts.MAX_CATEGORY_LABELS + 1
    assert data["labels"][-1] == "Інше"
    assert data["datasets"][0]["data"][-1] == 89.0 + 88.0


def test_by_category_both_types():
    rows = [tx(10, "2026-07-01", category_id="c1"), tx(500, "2026-07-02", type="income", category_id="c9")]

    data = build_chart_data(spec(group_by="category", type="both"), rows, {"c1": "Кава", "c9": "Зарплата"})

    assert data["labels"] == ["Зарплата", "Кава"]
    assert data["datasets"] == [{"label": "Доходи", "data": [500.0, 0]}, {"label": "Витрати", "data": [0, 10.0]}]


def test_count_metric():
    rows = [tx(100, "2026-07-03"), tx(50, "2026-07-04")]

    data = build_chart_data(spec(metric="count", start_date="2026-07-01", end_date="2026-07-31"), rows, {})

    assert data["datasets"][0]["data"] == [2]
    assert data["unit"] == "шт"


def test_rows_outside_period_or_with_bad_date_are_ignored():
    rows = [tx(100, "2026-06-30"), tx(5, "not-a-date"), tx(7, "2026-07-10T12:00:00")]

    data = build_chart_data(spec(start_date="2026-07-01", end_date="2026-07-31"), rows, {})

    assert data["datasets"][0]["data"] == [7.0]


def test_custom_title_is_used():
    assert build_chart_data(spec(title="Мої витрати"), [], {})["title"] == "Мої витрати"


def test_summarize_chart():
    data = build_chart_data(spec(type="both"), [tx(100, "2026-07-03"), tx(50, "2026-08-03")], {})

    assert summarize_chart(data) == {
        "status": "chart_shown",
        "labels": 3,
        "unit": "грн",
        "series": [{"label": "Доходи", "total": 0}, {"label": "Витрати", "total": 150.0}],
    }
