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
