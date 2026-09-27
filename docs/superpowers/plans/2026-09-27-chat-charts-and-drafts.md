# Chat Charts & Transaction Drafts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Асистент малює графіки за структурованим запитом (дані рахує сервер) і готує чернетки транзакцій, які користувач перевіряє та додає сам.

**Architecture:** Два нові tools в `backend/agent/tools.py`: `build_chart` і `propose_transaction`. Вони спираються на чисті модулі `agent/charts.py` (валідація й агрегація) та `agent/drafts.py` (валідація чернетки) і повертають `WithAttachment`: коротке зведення йде в LLM, повні дані йдуть у вкладення. `run_tool` віддає вкладення, runner збирає їх (до 3 на відповідь), `ChatResponse.attachments` передає їх у віджет. Віджет малює `ChatChart.vue` (vue-chartjs) і `TransactionDraftCard.vue`. Картка записує транзакцію наявним `POST /transactions` лише після натискання «Додати». Агент не має інструменту запису.

**Tech Stack:** Python 3 / FastAPI / pytest (backend `.venv`, Python 3.14); Vue 3 (JS) + Tailwind 4 + chart.js 4 + vue-chartjs 5 + lucide-vue-next + Pinia.

**Spec:** `docs/superpowers/specs/2026-09-27-chat-charts-and-drafts-design.md`

> Код у цьому плані вже прогнано на копії бекенду та фронтенду: повний набір тестів — 125 passed, покриття 98.6%, `vite build` проходить. Переносьте його дослівно.

## Global Constraints

- Робота йде в гілці `feature/chat-agent` (уже checkout). Гілку не перемикати, не пушити.
- **Ніколи `git add -A` / `git add .` / `git commit -a`.** У робочому дереві є незакомічені зміни користувача: `.gitignore`, `README.md`, `frontend/src/views/DashboardView.vue`, `CLAUDE.md`, pnpm-файли, `scripts/`, `docs/superpowers/plans/2026-09-27-chat-agent.md`. Додавати лише файли, названі в кроці commit.
- Не читати й не друкувати `backend/.env` і `frontend/.env`: там реальні ключі.
- Агент **не записує** дані: у tools немає й не має з'явитися виклику `create_transaction` чи інших хендлерів запису.
- `user_id` для tools береться лише з токена (позиційний перший аргумент handler), ніколи з аргументів моделі.
- Нових запитів до Supabase в агенті немає, лише наявні хендлери роутерів.
- Тести не ходять у мережу: усе мокається через `monkeypatch`.
- Команди бекенду запускаються з `backend/` через `.venv/bin/python`.
- Фронтенд перевіряється командою `cd frontend && node_modules/.bin/vite build`. `pnpm build` може падати на pnpm-гейті `ERR_PNPM_IGNORED_BUILDS`, що не пов'язано з цією роботою.
- Коментарі та тексти для користувача пишуться українською.
- Кожен commit message закінчується порожнім рядком і `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Ліміти (з spec): період графіка ≤ 731 день; ≤ 12 категорій у запиті; ≤ 11 міток категорій плюс «Інше»; ≤ 500 транзакцій на графік; ≤ 3 вкладення на відповідь; сума чернетки > 0.01 і ≤ 10 000 000; дата чернетки не в майбутньому і не давніша за 5 років; опис ≤ 255 символів.

## File Structure

```
backend/agent/charts.py              # create — ChartSpec, parse_chart_spec, build_chart_data, summarize_chart
backend/agent/drafts.py              # create — build_draft, draft_model_result
backend/agent/tools.py               # modify — WithAttachment, build_chart, propose_transaction, UI_TOOLS, run_tool
backend/agent/runner.py              # modify — run_tool, attachments, MAX_ATTACHMENTS
backend/agent/prompts.py             # modify — правила 6 і 9
backend/routers/chat.py              # modify — ChatResponse.attachments
backend/agent/README.md              # modify — нові tools і вкладення
backend/tests/test_charts.py         # create
backend/tests/test_drafts.py         # create
backend/tests/test_tools_ui.py       # create
backend/tests/test_tools_extension.py# modify — 13 tools
backend/tests/test_runner.py         # modify — run_tool замість execute_tool + 2 тести
backend/tests/test_chat_router.py    # modify — attachments у відповіді
frontend/src/components/chat/ChatChart.vue            # create
frontend/src/components/chat/TransactionDraftCard.vue # create
frontend/src/components/chat/ChatWidget.vue           # modify — payload, attachments, рендер
```

---

### Task 1: Модуль графіків `agent/charts.py`

**Files:**
- Create: `backend/agent/charts.py`
- Test: `backend/tests/test_charts.py`

**Interfaces:**
- Consumes: —
- Produces:
  - константи `CHART_KINDS`, `GROUP_BY`, `TYPES`, `METRICS`, `MAX_PERIOD_DAYS = 731`, `MAX_CATEGORIES = 12`, `MAX_CATEGORY_LABELS = 11`, `MAX_TITLE_CHARS = 80`, `OTHER_LABEL = "Інше"`
  - `ChartSpecError(ValueError)`
  - `ChartSpec(chart, group_by, start: date, end: date, type="expense", metric="sum", categories: tuple = (), search=None, title=None)` (frozen dataclass)
  - `parse_chart_spec(chart, group_by, start_date, end_date, type="expense", metric="sum", categories=None, search=None, title=None) -> ChartSpec`
  - `time_labels(start: date, end: date, group_by: str) -> list[str]`
  - `build_chart_data(spec, transactions: list[dict], category_names: dict, selected: Optional[dict] = None) -> dict` → `{"chart", "title", "labels", "datasets": [{"label", "data"}], "unit", "start_date", "end_date"}`
  - `summarize_chart(data: dict) -> dict` → `{"status": "chart_shown", "labels": int, "unit", "series": [{"label", "total"}]}`

- [ ] **Step 1: Написати тести**

Створити `backend/tests/test_charts.py`:

```python
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
```

- [ ] **Step 2: Запустити — має впасти**

Run (з `backend/`): `.venv/bin/python -m pytest tests/test_charts.py -v`
Expected: FAIL — `ImportError: cannot import name 'charts' from 'agent'`

- [ ] **Step 3: Реалізувати `backend/agent/charts.py`**

```python
"""Графіки для чату: валідація структурованого запиту моделі та агрегація транзакцій.

Чисті функції без доступу до БД: дані передає tool build_chart (agent/tools.py).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

CHART_KINDS = ("bar", "line", "doughnut")
GROUP_BY = ("category", "day", "week", "month")
TYPES = ("expense", "income", "both")
METRICS = ("sum", "count")
MAX_PERIOD_DAYS = 731
MAX_CATEGORIES = 12
MAX_CATEGORY_LABELS = 11  # решта категорій згортається в «Інше»
MAX_TITLE_CHARS = 80
OTHER_LABEL = "Інше"
TYPE_LABELS = {"income": "Доходи", "expense": "Витрати"}

_METRIC_TITLES = {"sum": "Сума", "count": "Кількість"}
_TYPE_TITLES = {"expense": "витрат", "income": "доходів", "both": "доходів і витрат"}
_GROUP_TITLES = {"category": "за категоріями", "day": "по днях", "week": "по тижнях", "month": "по місяцях"}


class ChartSpecError(ValueError):
    """Некоректний запит на графік — пояснення повертається моделі."""


@dataclass(frozen=True)
class ChartSpec:
    chart: str
    group_by: str
    start: date
    end: date
    type: str = "expense"
    metric: str = "sum"
    categories: tuple = ()
    search: Optional[str] = None
    title: Optional[str] = None


def _parse_iso(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ChartSpecError(f"{field} має бути датою у форматі YYYY-MM-DD, отримано: {value!r}")


def _require_choice(value, field: str, choices: tuple) -> None:
    if value not in choices:
        raise ChartSpecError(f"{field} має бути одним із: {', '.join(choices)}")


def parse_chart_spec(
    chart,
    group_by,
    start_date,
    end_date,
    type="expense",  # назва збігається з аргументом моделі
    metric="sum",
    categories=None,
    search=None,
    title=None,
) -> ChartSpec:
    _require_choice(chart, "chart", CHART_KINDS)
    _require_choice(group_by, "group_by", GROUP_BY)
    _require_choice(type, "type", TYPES)
    _require_choice(metric, "metric", METRICS)
    start = _parse_iso(start_date, "start_date")
    end = _parse_iso(end_date, "end_date")
    if start > end:
        raise ChartSpecError("start_date не може бути пізніше за end_date")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        raise ChartSpecError(f"Період графіка не може перевищувати {MAX_PERIOD_DAYS} днів")
    if chart == "doughnut" and (group_by != "category" or type == "both"):
        raise ChartSpecError("doughnut можливий лише з group_by='category' і type 'expense' або 'income'")

    categories = [] if categories is None else categories
    if not isinstance(categories, list) or not all(isinstance(c, str) and c.strip() for c in categories):
        raise ChartSpecError("categories має бути списком назв категорій")
    if len(categories) > MAX_CATEGORIES:
        raise ChartSpecError(f"Не більше {MAX_CATEGORIES} категорій в одному графіку")

    return ChartSpec(
        chart=chart,
        group_by=group_by,
        start=start,
        end=end,
        type=type,
        metric=metric,
        categories=tuple(dict.fromkeys(c.strip() for c in categories)),
        search=(str(search).strip() or None) if search is not None else None,
        title=(str(title).strip()[:MAX_TITLE_CHARS] or None) if title is not None else None,
    )


def _bucket_key(day: date, group_by: str) -> str:
    if group_by == "day":
        return day.isoformat()
    if group_by == "week":
        return (day - timedelta(days=day.weekday())).isoformat()  # понеділок тижня
    return f"{day.year:04d}-{day.month:02d}"


def time_labels(start: date, end: date, group_by: str) -> list:
    """Безперервні мітки від start до end, щоб на графіку не було «дірок»."""
    labels = []
    day = start
    while day <= end:
        key = _bucket_key(day, group_by)
        if not labels or labels[-1] != key:
            labels.append(key)
        day += timedelta(days=1)
    return labels


def _tx_date(tx: dict) -> Optional[date]:
    try:
        return date.fromisoformat(str(tx.get("transaction_date"))[:10])
    except ValueError:
        return None


def _value(tx: dict, metric: str) -> float:
    return 1 if metric == "count" else float(tx.get("transaction_amount") or 0)


def _series_types(spec: ChartSpec) -> list:
    return ["income", "expense"] if spec.type == "both" else [spec.type]


def _by_category(spec: ChartSpec, rows: list, category_names: dict) -> tuple:
    types = _series_types(spec)
    totals = {t: {} for t in types}
    for tx in rows:
        bucket = totals.get(tx.get("transaction_type"))
        if bucket is None:
            continue
        name = category_names.get(tx.get("category_id"), OTHER_LABEL)
        bucket[name] = bucket.get(name, 0) + _value(tx, spec.metric)

    overall = {}
    for bucket in totals.values():
        for name, value in bucket.items():
            overall[name] = overall.get(name, 0) + value
    ranked = sorted((n for n in overall if n != OTHER_LABEL), key=lambda n: (-overall[n], n))
    top = ranked[:MAX_CATEGORY_LABELS]
    folded = ranked[MAX_CATEGORY_LABELS:] + ([OTHER_LABEL] if OTHER_LABEL in overall else [])

    labels = top + ([OTHER_LABEL] if folded else [])
    datasets = []
    for t in types:
        data = [round(totals[t].get(n, 0), 2) for n in top]
        if folded:
            data.append(round(sum(totals[t].get(n, 0) for n in folded), 2))
        datasets.append({"label": TYPE_LABELS[t], "data": data})
    return labels, datasets


def _by_time(spec: ChartSpec, rows: list, selected: Optional[dict]) -> tuple:
    labels = time_labels(spec.start, spec.end, spec.group_by)
    index = {label: i for i, label in enumerate(labels)}
    if selected:
        series = list(selected.items())  # [(category_id, назва)]
        key_field = "category_id"
    else:
        series = [(t, TYPE_LABELS[t]) for t in _series_types(spec)]
        key_field = "transaction_type"

    values = {key: [0] * len(labels) for key, _ in series}
    for tx in rows:
        day = _tx_date(tx)
        key = tx.get(key_field)
        if day is None or not (spec.start <= day <= spec.end) or key not in values:
            continue
        values[key][index[_bucket_key(day, spec.group_by)]] += _value(tx, spec.metric)

    datasets = [{"label": name, "data": [round(v, 2) for v in values[key]]} for key, name in series]
    return labels, datasets


def build_chart_data(spec: ChartSpec, transactions: list, category_names: dict, selected: Optional[dict] = None) -> dict:
    """Дані для Chart.js.

    transactions — рядки таблиці transactions (transaction_type, transaction_amount у грн,
    transaction_date, category_id); category_names — {category_id: назва};
    selected — {category_id: назва} для категорій із запиту або None.
    """
    rows = [tx for tx in transactions if spec.type == "both" or tx.get("transaction_type") == spec.type]
    if selected:
        rows = [tx for tx in rows if tx.get("category_id") in selected]

    if spec.group_by == "category":
        labels, datasets = _by_category(spec, rows, category_names)
    else:
        labels, datasets = _by_time(spec, rows, selected)

    default_title = f"{_METRIC_TITLES[spec.metric]} {_TYPE_TITLES[spec.type]} {_GROUP_TITLES[spec.group_by]}"
    return {
        "chart": spec.chart,
        "title": spec.title or default_title,
        "labels": labels,
        "datasets": datasets,
        "unit": "шт" if spec.metric == "count" else "грн",
        "start_date": spec.start.isoformat(),
        "end_date": spec.end.isoformat(),
    }


def summarize_chart(data: dict) -> dict:
    """Коротке зведення для моделі: сам графік вона не бачить."""
    return {
        "status": "chart_shown",
        "labels": len(data["labels"]),
        "unit": data["unit"],
        "series": [{"label": d["label"], "total": round(sum(d["data"]), 2)} for d in data["datasets"]],
    }
```

- [ ] **Step 4: Запустити — має пройти**

Run: `.venv/bin/python -m pytest tests/test_charts.py -v`
Expected: 25 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agent/charts.py backend/tests/test_charts.py
git commit -m "feat(agent): add chart spec validation and aggregation"
```

---

### Task 2: Модуль чернеток `agent/drafts.py`

**Files:**
- Create: `backend/agent/drafts.py`
- Test: `backend/tests/test_drafts.py`

**Interfaces:**
- Consumes: `core.constants.MIN_TRANSACTION_AMOUNT` (= 0.01, наявна константа)
- Produces:
  - `TYPES = ("income", "expense")`, `MAX_AMOUNT`, `MAX_DESCRIPTION_CHARS = 255`, `MAX_PAST_DAYS`
  - `DraftError(ValueError)`
  - `build_draft(type, amount, transaction_date, categories: list[{"id","name"}], is_fop: bool, today: date, category=None, description=None) -> dict` → `{"type", "amount", "currency": "UAH", "date", "category_id", "category_name", "category_hint", "description", "is_fop"}`
  - `draft_model_result(draft) -> dict` → `{"status": "draft_shown", "note", "draft": {...}}`

- [ ] **Step 1: Написати тести**

Створити `backend/tests/test_drafts.py`:

```python
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
```

- [ ] **Step 2: Запустити — має впасти**

Run: `.venv/bin/python -m pytest tests/test_drafts.py -v`
Expected: FAIL — `ImportError: cannot import name 'drafts' from 'agent'` (або `ModuleNotFoundError: No module named 'agent.drafts'`)

- [ ] **Step 3: Реалізувати `backend/agent/drafts.py`**

```python
"""Чернетки транзакцій, які агент пропонує користувачу.

Агент нічого не записує: чернетка йде у вкладення відповіді /chat/, а запис робить
фронтенд через наявний POST /transactions лише після підтвердження користувачем.
"""
from datetime import date, timedelta
from typing import Optional

from core.constants import MIN_TRANSACTION_AMOUNT

TYPES = ("income", "expense")
MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_CHARS = 255
MAX_PAST_DAYS = 5 * 366


class DraftError(ValueError):
    """Некоректні дані чернетки — пояснення повертається моделі."""


def _match_category(name: Optional[str], categories: list) -> tuple:
    """(category_id, category_name, category_hint): hint — назва, яку не знайдено."""
    if name is None or not str(name).strip():
        return None, None, None
    wanted = str(name).strip()
    for category in categories:
        if str(category.get("name", "")).casefold() == wanted.casefold():
            return category["id"], category["name"], None
    return None, None, wanted


def build_draft(
    type: str,  # назва збігається з аргументом моделі
    amount,
    transaction_date,
    categories: list,
    is_fop: bool,
    today: date,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """categories — категорії користувача потрібного типу: [{"id", "name"}, ...]."""
    if type not in TYPES:
        raise DraftError("type має бути 'income' або 'expense'")
    if isinstance(amount, bool):
        raise DraftError("amount має бути числом")
    try:
        value = round(float(amount), 2)
    except (TypeError, ValueError):
        raise DraftError("amount має бути числом")
    if not (MIN_TRANSACTION_AMOUNT < value <= MAX_AMOUNT):
        raise DraftError(f"amount має бути більше {MIN_TRANSACTION_AMOUNT} і не більше {MAX_AMOUNT}")
    try:
        day = date.fromisoformat(transaction_date)
    except (TypeError, ValueError):
        raise DraftError(f"transaction_date має бути датою у форматі YYYY-MM-DD, отримано: {transaction_date!r}")
    if day > today:
        raise DraftError("Дата транзакції не може бути в майбутньому")
    if day < today - timedelta(days=MAX_PAST_DAYS):
        raise DraftError("Дата транзакції не може бути давнішою за 5 років")

    category_id, category_name, category_hint = _match_category(category, categories)
    text = str(description).strip()[:MAX_DESCRIPTION_CHARS] if description is not None else ""
    return {
        "type": type,
        "amount": value,
        "currency": "UAH",
        "date": day.isoformat(),
        "category_id": category_id,
        "category_name": category_name,
        "category_hint": category_hint,
        "description": text or None,
        "is_fop": bool(is_fop),
    }


def draft_model_result(draft: dict) -> dict:
    """Що бачить модель після propose_transaction."""
    note = (
        "Чернетку показано користувачу в картці. Транзакцію буде додано лише після його "
        "підтвердження — не кажи, що її вже додано."
    )
    if draft["category_hint"]:
        note += f" Категорію «{draft['category_hint']}» не знайдено — користувач обере її в картці."
    summary = {k: draft[k] for k in ("type", "amount", "date", "category_name", "description")}
    return {"status": "draft_shown", "note": note, "draft": summary}
```

- [ ] **Step 4: Запустити — має пройти**

Run: `.venv/bin/python -m pytest tests/test_drafts.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agent/drafts.py backend/tests/test_drafts.py
git commit -m "feat(agent): add transaction draft validation"
```

---

### Task 3: Tools `build_chart` і `propose_transaction`, `run_tool` з вкладеннями

**Files:**
- Modify: `backend/agent/tools.py`
- Modify: `backend/tests/test_tools_extension.py:17`
- Test: `backend/tests/test_tools_ui.py`

**Interfaces:**
- Consumes: Task 1 (`charts.*`), Task 2 (`drafts.*`); наявні в `tools.py`: `Tool`, `ToolArgumentError`, `_category_names(user_id)`, `_DATE`, `_dump`, `CORE_TOOLS`, `EXTENSION_TOOLS`, `logger`; хендлери `transactions_router.get_transactions(current_user_id, limit, offset, start_date: date, end_date: date, type, category_id, search)` і `categories_router.get_categories(current_user_id)` → `{"all": [{"id","name","type",...}], "income": [...], "expense": [...], "user_is_fop": bool}`
- Produces:
  - `tools.WithAttachment(model_result: Any, attachment: dict)` (frozen dataclass)
  - `tools.MAX_CHART_TRANSACTIONS = 500`, `tools.MAX_LISTED_CATEGORIES = 30`
  - `tools.UI_TOOLS: list[Tool]` — `build_chart`, `propose_transaction`; `TOOLS` містить 13 tools
  - `tools.run_tool(name, arguments, user_id) -> tuple[str, Optional[dict]]` — ніколи не кидає
  - `tools.execute_tool(name, arguments, user_id) -> str` — лишається, повертає `run_tool(...)[0]`
  - вкладення: `{"type": "chart", "chart": <build_chart_data>}` і `{"type": "transaction_draft", "draft": <build_draft>}`

- [ ] **Step 1: Написати тести**

Створити `backend/tests/test_tools_ui.py`:

```python
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
```

У `backend/tests/test_tools_extension.py` замінити:

```python
    assert len(tools.TOOLS) == 11
```

на:

```python
    assert len(tools.TOOLS) == 13
```

- [ ] **Step 2: Запустити — має впасти**

Run: `.venv/bin/python -m pytest tests/test_tools_ui.py tests/test_tools_extension.py -v`
Expected: FAIL — `AttributeError: module 'agent.tools' has no attribute 'run_tool'` та `assert 11 == 13`

- [ ] **Step 3: Імпорт модулів**

У `backend/agent/tools.py` замінити рядок:

```python
from models.common import ReportingPeriod
```

на:

```python
from agent import charts, drafts
from models.common import ReportingPeriod
```

- [ ] **Step 4: Обробники UI tools**

У `backend/agent/tools.py` безпосередньо **перед** рядком `# --- Реєстр ---` вставити:

```python
# --- UI tools: графіки та чернетки транзакцій (дані для клієнта йдуть у вкладення) ---

MAX_CHART_TRANSACTIONS = 500
MAX_LISTED_CATEGORIES = 30


@dataclass(frozen=True)
class WithAttachment:
    """Результат tool: model_result іде в LLM, attachment — лише клієнту у відповіді /chat/."""

    model_result: Any
    attachment: dict


def _resolve_categories(user_id: str, names: list) -> dict:
    """{category_id: назва} для назв із запиту (без урахування регістру)."""
    if not names:
        return {}
    all_categories = categories_router.get_categories(current_user_id=user_id).get("all", [])
    by_name = {}
    for category in all_categories:
        by_name.setdefault(category["name"].casefold(), []).append(category)

    selected, unknown = {}, []
    for name in names:
        matches = by_name.get(name.casefold())
        if not matches:
            unknown.append(name)
            continue
        for category in matches:
            selected[category["id"]] = category["name"]
    if unknown:
        available = ", ".join(sorted({c["name"] for c in all_categories})[:MAX_LISTED_CATEGORIES])
        raise ToolArgumentError(f"Невідомі категорії: {', '.join(unknown)}. Доступні: {available}")
    return selected


def _build_chart(
    user_id: str,
    chart: str,
    group_by: str,
    start_date: str,
    end_date: str,
    type: str = "expense",  # назва збігається з аргументом моделі
    metric: str = "sum",
    categories: Optional[list] = None,
    search: Optional[str] = None,
    title: Optional[str] = None,
) -> Any:
    try:
        spec = charts.parse_chart_spec(
            chart=chart,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            type=type,
            metric=metric,
            categories=categories,
            search=search,
            title=title,
        )
    except charts.ChartSpecError as exc:
        raise ToolArgumentError(str(exc))

    selected = _resolve_categories(user_id, list(spec.categories))
    rows = transactions_router.get_transactions(
        current_user_id=user_id,
        limit=MAX_CHART_TRANSACTIONS + 1,
        offset=0,
        start_date=spec.start,
        end_date=spec.end,
        type=None if spec.type == "both" else spec.type,
        category_id=next(iter(selected)) if len(selected) == 1 else None,
        search=spec.search,
    )
    if len(rows) > MAX_CHART_TRANSACTIONS:
        raise ToolArgumentError(
            f"Забагато транзакцій для графіка (понад {MAX_CHART_TRANSACTIONS}). Звузьте період або фільтри."
        )
    names = _category_names(user_id) if spec.group_by == "category" else {}
    data = charts.build_chart_data(spec, rows, names, selected or None)
    return WithAttachment(model_result=charts.summarize_chart(data), attachment={"type": "chart", "chart": data})


def _propose_transaction(
    user_id: str,
    type: str,  # назва збігається з аргументом моделі
    amount: Any,
    transaction_date: str,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    categories = categories_router.get_categories(current_user_id=user_id)
    try:
        draft = drafts.build_draft(
            type=type,
            amount=amount,
            transaction_date=transaction_date,
            categories=categories.get(type, []) if isinstance(type, str) else [],
            is_fop=categories.get("user_is_fop", True),
            today=date.today(),
            category=category,
            description=description,
        )
    except drafts.DraftError as exc:
        raise ToolArgumentError(str(exc))
    return WithAttachment(
        model_result=drafts.draft_model_result(draft),
        attachment={"type": "transaction_draft", "draft": draft},
    )
```

- [ ] **Step 5: Реєстрація в TOOLS**

У `backend/agent/tools.py` замінити рядок:

```python
TOOLS = {tool.name: tool for tool in CORE_TOOLS + EXTENSION_TOOLS}
```

на:

```python
UI_TOOLS = [
    Tool(
        name="build_chart",
        description=(
            "Показати користувачу графік за його транзакціями. Дані рахує сервер — ти обираєш лише тип, "
            "групування, період і фільтри. Графік з'явиться в чаті автоматично; у тексті дай 1–2 речення висновку."
        ),
        parameters={
            "type": "object",
            "properties": {
                "chart": {"type": "string", "enum": list(charts.CHART_KINDS), "description": "doughnut — лише з group_by=category"},
                "group_by": {"type": "string", "enum": list(charts.GROUP_BY)},
                "start_date": _DATE,
                "end_date": _DATE,
                "type": {"type": "string", "enum": list(charts.TYPES), "description": "Типово expense"},
                "metric": {"type": "string", "enum": list(charts.METRICS), "description": "sum — сума в грн, count — кількість"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": charts.MAX_CATEGORIES,
                    "description": "Назви категорій для порівняння (по одній серії на категорію)",
                },
                "search": {"type": "string", "description": "Текст для пошуку в описі транзакцій"},
                "title": {"type": "string", "description": f"Заголовок графіка, до {charts.MAX_TITLE_CHARS} символів"},
            },
            "required": ["chart", "group_by", "start_date", "end_date"],
        },
        handler=_build_chart,
    ),
    Tool(
        name="propose_transaction",
        description=(
            "Підготувати чернетку нової транзакції з повідомлення користувача. Нічого не записує: "
            "користувач перевірить поля в картці й сам натисне «Додати»."
        ),
        parameters={
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": list(drafts.TYPES)},
                "amount": {"type": "number", "description": "Сума в грн, більше 0.01"},
                "transaction_date": {**_DATE, "description": "Дата транзакції (YYYY-MM-DD), не в майбутньому"},
                "category": {"type": "string", "description": "Назва категорії користувача (див. list_categories)"},
                "description": {"type": "string", "description": "Короткий опис, до 255 символів"},
            },
            "required": ["type", "amount", "transaction_date"],
        },
        handler=_propose_transaction,
    ),
]
TOOLS = {tool.name: tool for tool in CORE_TOOLS + EXTENSION_TOOLS + UI_TOOLS}
```

- [ ] **Step 6: `run_tool` замість тіла `execute_tool`**

У `backend/agent/tools.py` функція `execute_tool` стоїть останньою у файлі. Замінити **всю** функцію `def execute_tool(...)` (від рядка `def execute_tool(` до кінця файлу) на:

```python
def run_tool(name: str, arguments: dict, user_id: str) -> tuple:
    """Виконує tool. Повертає (JSON-рядок для моделі, вкладення для клієнта або None). Ніколи не кидає."""
    tool = TOOLS.get(name)
    if tool is None:
        return _dump({"error": f"Невідомий інструмент: {name}"}), None
    try:
        # Перевірка аргументів до виклику: TypeError від bind — некоректні аргументи моделі,
        # TypeError всередині handler — внутрішня помилка (не плутати ці два випадки).
        # user_id передається позиційно: спроба моделі передати свій user_id дасть TypeError.
        inspect.signature(tool.handler).bind(user_id, **arguments)
    except TypeError as exc:
        return _dump({"error": f"Некоректні аргументи для {name}: {exc}"}), None
    attachment = None
    try:
        result = tool.handler(user_id, **arguments)
    except HTTPException as exc:
        if exc.status_code >= 500:
            logger.error("Tool %s failed with HTTP %s", name, exc.status_code)
            result = {"error": "Внутрішня помилка інструменту"}
        else:
            result = {"error": exc.detail}
    except ToolArgumentError as exc:
        result = {"error": str(exc)}
    except Exception:
        logger.exception("Tool %s failed", name)
        result = {"error": "Внутрішня помилка інструменту"}
    if isinstance(result, WithAttachment):
        result, attachment = result.model_result, result.attachment
    return _dump(result), attachment


def execute_tool(name: str, arguments: dict, user_id: str) -> str:
    """Виконує tool і повертає лише JSON-рядок для моделі (без вкладення). Ніколи не кидає винятків."""
    return run_tool(name, arguments, user_id)[0]
```

- [ ] **Step 7: Запустити — має пройти**

Run: `.venv/bin/python -m pytest tests/test_tools_ui.py tests/test_tools_extension.py tests/test_tools.py -v`
Expected: усі passed (11 у `test_tools_ui.py`)

- [ ] **Step 8: Commit**

```bash
git add backend/agent/tools.py backend/tests/test_tools_ui.py backend/tests/test_tools_extension.py
git commit -m "feat(agent): add build_chart and propose_transaction tools with attachments"
```

---

### Task 4: Вкладення в runner і `/chat/`, промпт, README

**Files:**
- Modify: `backend/agent/runner.py`, `backend/routers/chat.py`, `backend/agent/prompts.py`, `backend/agent/README.md`
- Modify: `backend/tests/test_runner.py`, `backend/tests/test_chat_router.py`

**Interfaces:**
- Consumes: `tools.run_tool` (Task 3)
- Produces:
  - `runner.MAX_ATTACHMENTS = 3`, `runner.TOO_MANY_ATTACHMENTS_REPLY`
  - `runner.AgentResult(reply, tools_used=[], attachments=[])`
  - `POST /chat/` → `{"reply", "tools_used", "model", "attachments": [ ... ]}` (типово `[]`)

- [ ] **Step 1: Оновити наявні тести runner під `run_tool`**

У `backend/tests/test_runner.py`:

(a) замінити:

```python
    def fake_execute(name, arguments, user_id):
        executed.append((name, arguments, user_id))
        return '{"balance": 5}'

    monkeypatch.setattr(runner, "execute_tool", fake_execute)
```

на:

```python
    def fake_run(name, arguments, user_id):
        executed.append((name, arguments, user_id))
        return '{"balance": 5}', None

    monkeypatch.setattr(runner, "run_tool", fake_run)
```

(b) замінити:

```python
    monkeypatch.setattr(runner, "execute_tool", lambda name, arguments, user_id: executed.append(name) or "{}")
```

на:

```python
    monkeypatch.setattr(runner, "run_tool", lambda name, arguments, user_id: (executed.append(name) or "{}", None))
```

(c) **обидва** входження рядка:

```python
    monkeypatch.setattr(runner, "execute_tool", lambda name, arguments, user_id: "{}")
```

замінити на:

```python
    monkeypatch.setattr(runner, "run_tool", lambda name, arguments, user_id: ("{}", None))
```

(d) додати в кінець файлу:

```python
def test_collects_attachments(monkeypatch):
    monkeypatch.setattr(
        runner, "run_tool", lambda name, arguments, user_id: ('{"status": "chart_shown"}', {"type": "chart", "chart": {}})
    )
    llm = ScriptedLLM(
        [
            AssistantTurn(content=None, tool_calls=[ToolCall(id="c1", name="build_chart", arguments={})]),
            AssistantTurn(content="Ось графік."),
        ]
    )

    result = run(llm)

    assert result.attachments == [{"type": "chart", "chart": {}}]
    assert llm.calls[1]["messages"][-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"status": "chart_shown"}'}


def test_limits_attachments_per_reply(monkeypatch):
    monkeypatch.setattr(runner, "run_tool", lambda name, arguments, user_id: ("{}", {"type": "chart", "chart": {}}))
    calls = [ToolCall(id=str(i), name="build_chart", arguments={}) for i in range(runner.MAX_ATTACHMENTS + 1)]
    llm = ScriptedLLM([AssistantTurn(content=None, tool_calls=calls), AssistantTurn(content="Готово")])

    result = run(llm)

    assert len(result.attachments) == runner.MAX_ATTACHMENTS
    tool_messages = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"]
    assert "Забагато графіків" in tool_messages[-1]["content"]
    assert all(m["content"] == "{}" for m in tool_messages[:-1])
```

- [ ] **Step 2: Оновити тести роутера**

У `backend/tests/test_chat_router.py`:

(a) після рядка `from agent.llm_client import AssistantTurn` додати:

```python
from agent.runner import AgentResult
```

(b) замінити:

```python
    assert response.json() == {"reply": "Вітаю!", "tools_used": [], "model": "test-model"}
```

на:

```python
    assert response.json() == {"reply": "Вітаю!", "tools_used": [], "model": "test-model", "attachments": []}
```

(c) додати в кінець файлу:

```python
def test_chat_returns_attachments(client, monkeypatch):
    use_llm(ScriptedLLM([]))
    attachment = {"type": "chart", "chart": {"labels": ["2026-09"]}}
    monkeypatch.setattr(
        chat_router,
        "run_agent",
        lambda history, user_id, llm: AgentResult(reply="Ось графік.", tools_used=["build_chart"], attachments=[attachment]),
    )

    response = client.post("/chat/", json={"messages": [user_message()]})

    assert response.status_code == 200
    assert response.json()["attachments"] == [attachment]
```

- [ ] **Step 3: Запустити — має впасти**

Run: `.venv/bin/python -m pytest tests/test_runner.py tests/test_chat_router.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'run_tool'` (monkeypatch runner), `attachments` відсутні у відповіді

- [ ] **Step 4: Runner**

У `backend/agent/runner.py`:

(a) замінити `from agent.tools import execute_tool, tool_schemas` на:

```python
from agent.tools import run_tool, tool_schemas
```

(b) після рядка `TOO_MANY_TOOL_CALLS_REPLY = {"error": "Забагато викликів інструментів за раз"}` додати:

```python
MAX_ATTACHMENTS = 3
TOO_MANY_ATTACHMENTS_REPLY = {"error": "Забагато графіків або чернеток в одній відповіді"}
```

(c) у `AgentResult` після `tools_used: list = field(default_factory=list)` додати:

```python
    attachments: list = field(default_factory=list)
```

(d) у `run_agent` після рядка `    tools_used = []` додати:

```python
    attachments = []
```

(e) замінити:

```python
            return AgentResult(reply=(turn.content or "").strip() or FALLBACK_REPLY, tools_used=tools_used)
```

на:

```python
            reply = (turn.content or "").strip() or FALLBACK_REPLY
            return AgentResult(reply=reply, tools_used=tools_used, attachments=attachments)
```

(f) замінити:

```python
            tools_used.append(call.name)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": execute_tool(call.name, call.arguments, user_id)}
            )
```

на:

```python
            tools_used.append(call.name)
            content, attachment = run_tool(call.name, call.arguments, user_id)
            if attachment is not None:
                if len(attachments) < MAX_ATTACHMENTS:
                    attachments.append(attachment)
                else:
                    content = json.dumps(TOO_MANY_ATTACHMENTS_REPLY, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
```

(g) замінити:

```python
    return AgentResult(reply=ITERATION_LIMIT_REPLY, tools_used=tools_used)
```

на:

```python
    return AgentResult(reply=ITERATION_LIMIT_REPLY, tools_used=tools_used, attachments=attachments)
```

- [ ] **Step 5: Роутер `/chat/`**

У `backend/routers/chat.py`:

(a) у класі `ChatResponse` після рядка `    model: str` додати:

```python
    # Графіки та чернетки транзакцій для віджета; у LLM вони не повертаються
    attachments: List[dict] = Field(default_factory=list)
```

(b) замінити:

```python
    return ChatResponse(reply=result.reply, tools_used=result.tools_used, model=model)
```

на:

```python
    return ChatResponse(
        reply=result.reply, tools_used=result.tools_used, model=model, attachments=result.attachments
    )
```

- [ ] **Step 6: Системний промпт**

У `backend/agent/prompts.py` в `SYSTEM_PROMPT_TEMPLATE`:

(a) замінити рядок правила 6:

```
6. Ти лише читаєш дані: не можеш створювати, змінювати чи видаляти транзакції, бюджети або налаштування. Якщо про це просять — поясни, де це зробити в застосунку.
```

на:

```
6. Ти не змінюєш дані сам. Щоб додати транзакцію, виклич propose_transaction: користувач перевірить чернетку й підтвердить її в картці. Ніколи не кажи, що транзакцію вже додано. Редагувати чи видаляти транзакції, бюджети або налаштування ти не можеш — поясни, де це зробити в застосунку.
```

(b) замінити останній рядок шаблону:

```
8. Не відповідай на запитання, не пов'язані з фінансами користувача, податками ФОП чи роботою застосунку."""
```

на:

```
8. Не відповідай на запитання, не пов'язані з фінансами користувача, податками ФОП чи роботою застосунку.
9. Якщо користувач просить показати, намалювати чи наочно порівняти дані — виклич build_chart. Графік з'явиться в чаті автоматично: у тексті дай 1–2 речення висновку і не перелічуй усі значення."""
```

- [ ] **Step 7: README модуля**

У `backend/agent/README.md` в кінці розділу `## Архітектура` (перед `## Налаштування`) додати:

```markdown
### Графіки й чернетки транзакцій

- `build_chart` — модель заповнює структурований запит (`chart`, `group_by`, період, `type`, `metric`, `categories`, `search`, `title`); `charts.py` валідує його й агрегує транзакції користувача (≤ 500, період ≤ 731 день). SQL модель не пише.
- `propose_transaction` — `drafts.py` валідує чернетку; **нічого не записується**. Запис робить віджет через `POST /transactions` після натискання «Додати».
- Обидва tools повертають `WithAttachment`: зведення йде в LLM, повні дані — у `attachments` відповіді `/chat/` (≤ 3 на відповідь). Назад у LLM вкладення не надсилаються.
```

- [ ] **Step 8: Повний набір тестів**

Run: `.venv/bin/python -m pytest --cov=agent --cov=routers.chat --cov-report=term-missing --cov-fail-under=80`
Expected: 125 passed, coverage ≈ 98%

- [ ] **Step 9: Commit**

```bash
git add backend/agent/runner.py backend/routers/chat.py backend/agent/prompts.py backend/agent/README.md backend/tests/test_runner.py backend/tests/test_chat_router.py
git commit -m "feat(chat): return chart and draft attachments from the agent"
```

---

### Task 5: Фронтенд — графік і картка чернетки у віджеті

**Files:**
- Create: `frontend/src/components/chat/ChatChart.vue`, `frontend/src/components/chat/TransactionDraftCard.vue`
- Modify: `frontend/src/components/chat/ChatWidget.vue`

**Interfaces:**
- Consumes: `attachments` з `POST /chat/` (Task 4); `api.createTransaction(data)` (`frontend/src/services/api/transactions.js`, `POST /transactions`, тіло `TransactionCreate`: `type, amount, date, category_id, description, currency, is_fop`); `useTransactionStore()` — `categories: {income, expense, all}`, `fetchCategories()`, `fetchTransactions()`
- Produces: компоненти `<ChatChart :chart>` і `<TransactionDraftCard :draft>`

- [ ] **Step 1: `frontend/src/components/chat/ChatChart.vue`**

```vue
<script setup>
import { computed } from 'vue';
import { Bar, Doughnut, Line } from 'vue-chartjs';
import {
    ArcElement,
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip);

const props = defineProps({
    // {chart, title, labels, datasets: [{label, data}], unit} — з backend/agent/charts.py
    chart: { type: Object, required: true },
});

const PALETTE = ['#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#65a30d', '#ea580c', '#4f46e5', '#0d9488', '#9ca3af'];
const COMPONENTS = { bar: Bar, line: Line, doughnut: Doughnut };

const isDoughnut = computed(() => props.chart.chart === 'doughnut');
const chartComponent = computed(() => COMPONENTS[props.chart.chart] || Bar);

const data = computed(() => ({
    labels: props.chart.labels,
    datasets: props.chart.datasets.map((dataset, index) => {
        const color = PALETTE[index % PALETTE.length];
        return {
            label: dataset.label,
            data: dataset.data,
            backgroundColor: isDoughnut.value ? props.chart.labels.map((_, i) => PALETTE[i % PALETTE.length]) : color,
            borderColor: isDoughnut.value ? '#ffffff' : color,
            borderWidth: 2,
            tension: 0.3,
            pointRadius: props.chart.labels.length > 40 ? 0 : 2,
        };
    }),
}));

function formatValue(value) {
    return `${Number(value).toLocaleString('uk-UA', { maximumFractionDigits: 2 })} ${props.chart.unit}`;
}

const options = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        title: { display: Boolean(props.chart.title), text: props.chart.title, font: { size: 13 } },
        legend: {
            display: isDoughnut.value || props.chart.datasets.length > 1,
            position: 'bottom',
            labels: { boxWidth: 10, font: { size: 11 } },
        },
        tooltip: {
            callbacks: {
                label: (ctx) =>
                    isDoughnut.value
                        ? `${ctx.label}: ${formatValue(ctx.parsed)}`
                        : `${ctx.dataset.label}: ${formatValue(ctx.parsed.y)}`,
            },
        },
    },
    scales: isDoughnut.value
        ? {}
        : {
              x: { ticks: { font: { size: 10 }, maxRotation: 45 } },
              y: { beginAtZero: true, ticks: { font: { size: 10 } } },
          },
}));
</script>

<template>
  <div class="h-56 w-full rounded-xl bg-white p-2 ring-1 ring-gray-100">
    <component :is="chartComponent" :data="data" :options="options" />
  </div>
</template>
```

- [ ] **Step 2: `frontend/src/components/chat/TransactionDraftCard.vue`**

```vue
<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { Check, X } from 'lucide-vue-next';
import api from '@/services/api';
import { useTransactionStore } from '@/stores/transactionStore';

const props = defineProps({
    // {type, amount, currency, date, category_id, category_name, category_hint, description, is_fop} — з backend/agent/drafts.py
    draft: { type: Object, required: true },
});

const txStore = useTransactionStore();
const form = reactive({
    type: props.draft.type,
    amount: props.draft.amount,
    date: props.draft.date,
    category_id: props.draft.category_id || '',
    description: props.draft.description || '',
});
const status = ref('editing'); // editing | saving | saved | cancelled
const error = ref('');
const today = new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD у локальному часовому поясі

const categories = computed(() => txStore.categories?.[form.type] || []);
const isEditable = computed(() => status.value === 'editing');
const canSave = computed(() => isEditable.value && Number(form.amount) > 0 && Boolean(form.date) && Boolean(form.type));

onMounted(async () => {
    if (!txStore.categories?.all?.length) {
        try {
            await txStore.fetchCategories();
        } catch {
            // Без категорій транзакцію все одно можна додати «Без категорії»
        }
    }
});

function onTypeChange() {
    // Категорії доходів і витрат різні — скидаємо вибір, якщо він не підходить до нового типу
    if (!categories.value.some((c) => c.id === form.category_id)) form.category_id = '';
}

async function save() {
    if (!canSave.value) return;
    status.value = 'saving';
    error.value = '';
    try {
        await api.createTransaction({
            type: form.type,
            amount: Number(form.amount),
            date: form.date,
            category_id: form.category_id || null,
            description: form.description.trim() || null,
            currency: 'UAH',
            is_fop: props.draft.is_fop,
        });
    } catch (e) {
        status.value = 'editing';
        const detail = e?.response?.data?.detail;
        error.value = typeof detail === 'string' ? detail : 'Не вдалося додати транзакцію.';
        return;
    }
    status.value = 'saved';
    // Оновлюємо дашборд окремо: помилка оновлення не означає, що запис не додано
    txStore.fetchTransactions().catch(() => {});
}

function cancel() {
    status.value = 'cancelled';
}
</script>

<template>
  <div class="rounded-xl bg-white p-3 text-sm ring-1 ring-gray-200">
    <p class="mb-2 font-medium text-gray-900">Нова транзакція</p>

    <div class="grid grid-cols-2 gap-2">
      <select
        v-model="form.type"
        :disabled="!isEditable"
        aria-label="Тип"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
        @change="onTypeChange"
      >
        <option value="expense">Витрата</option>
        <option value="income">Дохід</option>
      </select>
      <input
        v-model="form.amount"
        type="number"
        min="0.01"
        step="0.01"
        :disabled="!isEditable"
        aria-label="Сума, грн"
        placeholder="Сума, грн"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
      <input
        v-model="form.date"
        type="date"
        :max="today"
        :disabled="!isEditable"
        aria-label="Дата"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
      <select
        v-model="form.category_id"
        :disabled="!isEditable"
        aria-label="Категорія"
        class="rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      >
        <option value="">Без категорії</option>
        <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
      </select>
      <input
        v-model="form.description"
        maxlength="255"
        :disabled="!isEditable"
        aria-label="Опис"
        placeholder="Опис"
        class="col-span-2 rounded-lg border border-gray-200 px-2 py-1.5 disabled:bg-gray-50"
      />
    </div>

    <p v-if="draft.category_hint && !form.category_id" class="mt-1 text-xs text-amber-700">
      Категорію «{{ draft.category_hint }}» не знайдено — оберіть її зі списку.
    </p>
    <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>

    <div v-if="status === 'editing' || status === 'saving'" class="mt-3 flex justify-end gap-2">
      <button
        type="button"
        :disabled="status === 'saving'"
        class="rounded-lg px-3 py-1.5 text-gray-600 hover:bg-gray-100 disabled:opacity-40"
        @click="cancel"
      >
        Скасувати
      </button>
      <button
        type="button"
        :disabled="!canSave"
        class="rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white disabled:opacity-40"
        @click="save"
      >
        {{ status === 'saving' ? 'Додаю…' : 'Додати' }}
      </button>
    </div>
    <p v-else-if="status === 'saved'" class="mt-3 flex items-center gap-1 text-green-700">
      <Check class="h-4 w-4" aria-hidden="true" /> Додано
    </p>
    <p v-else class="mt-3 flex items-center gap-1 text-gray-500">
      <X class="h-4 w-4" aria-hidden="true" /> Скасовано
    </p>
  </div>
</template>
```

- [ ] **Step 3: Підключити у `ChatWidget.vue`**

У `frontend/src/components/chat/ChatWidget.vue`:

(a) замінити:

```js
import ChatMarkdown from './ChatMarkdown.vue';
```

на:

```js
import ChatChart from './ChatChart.vue';
import ChatMarkdown from './ChatMarkdown.vue';
import TransactionDraftCard from './TransactionDraftCard.vue';
```

(b) у `send()` замінити:

```js
        const payload = messages.value
        .slice(-MAX_HISTORY)
        .map((m) => (m.role === 'assistant' ? { ...m, content: m.content.slice(0, MAX_ASSISTANT_CHARS) } : m));
    const { data } = await api.sendChatMessage(payload, selectedModel.value);
        messages.value.push({ role: 'assistant', content: data.reply });
```

на:

```js
        // У бекенд ідуть лише role і content: вкладення (графіки, чернетки) в LLM не повертаються
        const payload = messages.value.slice(-MAX_HISTORY).map((m) => ({
            role: m.role,
            content: m.role === 'assistant' ? m.content.slice(0, MAX_ASSISTANT_CHARS) : m.content,
        }));
        const { data } = await api.sendChatMessage(payload, selectedModel.value);
        messages.value.push({ role: 'assistant', content: data.reply, attachments: data.attachments || [] });
```

(c) у шаблоні замінити:

```vue
            <ChatMarkdown :content="message.content" />
          </div>
        </template>
```

на:

```vue
            <ChatMarkdown :content="message.content" />
            <div v-if="message.attachments?.length" class="mt-2 space-y-2">
              <template v-for="(attachment, attachmentIndex) in message.attachments" :key="attachmentIndex">
                <ChatChart v-if="attachment.type === 'chart'" :chart="attachment.chart" />
                <TransactionDraftCard v-else-if="attachment.type === 'transaction_draft'" :draft="attachment.draft" />
              </template>
            </div>
          </div>
        </template>
```

- [ ] **Step 4: Збірка**

Run: `cd frontend && node_modules/.bin/vite build`
Expected: `✓ built in ...` без помилок

- [ ] **Step 5: Ручна перевірка (користувач)**

`pnpm project:start` (потрібен `LLM_API_KEY` у `backend/.env`), увійти, відкрити чат:
1. «Покажи мої витрати за категоріями за вересень» — doughnut під відповіддю.
2. «Порівняй таксі й каву по місяцях за пів року» — стовпчики з двома серіями.
3. «Запиши, що я вчора витратив 300 грн на таксі» — картка з заповненими полями; змінити суму → «Додати» → «✓ Додано», транзакція з'явилась на дашборді.
4. Друга чернетка → «Скасувати» → «Скасовано», нічого не додано.
5. Сума 0 у картці → кнопка «Додати» неактивна.
6. На ширині 375px графік і картка не виходять за межі.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/ChatChart.vue frontend/src/components/chat/TransactionDraftCard.vue frontend/src/components/chat/ChatWidget.vue
git commit -m "feat(frontend): render chat charts and transaction draft cards"
```

---

## Після виконання

- Push і PR — лише за підтвердженням користувача.
- Для диплому: це розширює об'єкт тестування (`charts.py` і `drafts.py` — детермінована логіка з чіткими межами, зручна для порівняння LLM-згенерованих тестів). Зафіксувати commit SHA після цього плану як нову «заморожену версію».
