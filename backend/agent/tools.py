"""Інструменти (tools), які може викликати LLM-агент.

Лише читання даних поточного користувача: кожен tool — тонка обгортка над наявним
хендлером роутера, який сам фільтрує дані за current_user_id.
"""
import inspect
import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional

from fastapi import HTTPException

from models.common import ReportingPeriod
from routers import analytics as analytics_router
from routers import budgets as budgets_router
from routers import categories as categories_router
from routers import profiles as profiles_router
from routers import settings as settings_router
from routers import tax_rules as tax_rules_router
from routers import transactions as transactions_router
from services import nbu_service

logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 8000
MAX_TRANSACTIONS = 50


class ToolArgumentError(ValueError):
    """Модель передала некоректний аргумент — пояснення повертається їй як помилка."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]  # handler(user_id, **arguments)


# --- Хелпери ---

def _parse_date(value: Optional[str], field: str) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ToolArgumentError(f"{field} має бути датою у форматі YYYY-MM-DD, отримано: {value!r}")


def _require_period(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start is None or end is None:
        raise ToolArgumentError("Потрібні обидві дати: start_date і end_date")
    if start > end:
        raise ToolArgumentError("start_date не може бути пізніше за end_date")
    return start.isoformat(), end.isoformat()


def _category_names(user_id: str) -> dict:
    categories = categories_router.get_categories(current_user_id=user_id)
    return {c["id"]: c["name"] for c in categories.get("all", [])}


def _named_categories(categories_spent: dict, names: dict) -> list:
    items = [
        {"category": names.get(category_id, "Інше"), "amount": round(float(amount), 2)}
        for category_id, amount in categories_spent.items()
    ]
    return sorted(items, key=lambda item: item["amount"], reverse=True)


# --- Обробники core tools ---

def _transactions_summary(user_id: str, end_date: Optional[str] = None) -> Any:
    return transactions_router.get_transaction_summary(
        current_user_id=user_id, end_date=_parse_date(end_date, "end_date")
    )


def _expenses_by_category(user_id: str, start_date: str, end_date: str) -> Any:
    start, end = _require_period(start_date, end_date)
    report = analytics_router.get_reports(
        period="custom", start_date=start, end_date=end, current_user_id=user_id
    )
    return {
        "start_date": start,
        "end_date": end,
        "total_expenses": report["total_expenses"],
        "total_income": report["total_income"],
        "categories": _named_categories(report.get("categories_spent", {}), _category_names(user_id)),
    }


def _insights(user_id: str, start_date: str, end_date: str) -> Any:
    start, end = _require_period(start_date, end_date)
    return analytics_router.get_insights(start_date=start, end_date=end, current_user_id=user_id)


def _tax_estimate(user_id: str, period: str = "month", calc_date: Optional[str] = None) -> Any:
    try:
        reporting_period = ReportingPeriod(period)
    except ValueError:
        raise ToolArgumentError("period має бути одним із: month, quarter, year")
    return tax_rules_router.calculate_tax(
        current_user_id=user_id,
        annual_income=0.0,
        monthly_income=0.0,
        period=reporting_period,
        calc_date=_parse_date(calc_date, "calc_date"),
    )


def _list_transactions(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    type: Optional[str] = None,  # назва збігається з аргументом моделі та хендлера
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
) -> Any:
    if type not in (None, "income", "expense"):
        raise ToolArgumentError("type має бути 'income' або 'expense'")
    try:
        limit = max(1, min(int(limit), MAX_TRANSACTIONS))
    except (TypeError, ValueError):
        raise ToolArgumentError("limit має бути цілим числом")
    return transactions_router.get_transactions(
        current_user_id=user_id,
        limit=limit,
        offset=0,
        start_date=_parse_date(start_date, "start_date"),
        end_date=_parse_date(end_date, "end_date"),
        type=type,
        category_id=category_id,
        search=search,
    )


def _budgets_progress(user_id: str) -> Any:
    return budgets_router.get_budgets_progress(current_user_id=user_id)


# --- Обробники extension tools ---

REPORT_PERIODS = ("daily", "weekly", "monthly", "yearly")


def _or_none(handler: Callable[..., Any], **kwargs) -> Any:
    # Відсутній профіль чи налаштування — не помилка всього інструменту.
    try:
        return handler(**kwargs)
    except HTTPException:
        return None


def _tax_history(user_id: str) -> Any:
    return analytics_router.get_tax_history(current_user_id=user_id)


def _exchange_rate(user_id: str, currency: str, rate_date: Optional[str] = None) -> Any:
    code = str(currency).upper()
    if len(code) != 3 or not code.isalpha() or not code.isascii():
        raise ToolArgumentError("currency має бути ISO-кодом валюти, напр. USD або EUR")
    on_date = _parse_date(rate_date, "rate_date") or date.today()
    rate = nbu_service.get_nbu_rate(code, on_date)
    if not rate:
        return {"error": f"Курс {code} на {on_date.isoformat()} не знайдено"}
    return {"currency": code, "date": on_date.isoformat(), "rate_uah": rate}


def _financial_report(user_id: str, period: str = "monthly") -> Any:
    if period not in REPORT_PERIODS:
        raise ToolArgumentError(f"period має бути одним із: {', '.join(REPORT_PERIODS)}")
    report = dict(analytics_router.get_reports(period=period, start_date=None, end_date=None, current_user_id=user_id))
    report["categories_spent"] = _named_categories(report.get("categories_spent", {}), _category_names(user_id))
    return report


def _profile(user_id: str) -> Any:
    return {
        "profile": _or_none(profiles_router.get_profile, user_id=user_id, current_user_id=user_id),
        "fop_settings": _or_none(settings_router.get_fop_settings, user_id=user_id, current_user_id=user_id),
    }


def _categories(user_id: str) -> Any:
    categories = categories_router.get_categories(current_user_id=user_id)
    return {
        "categories": [
            {"id": c["id"], "name": c["name"], "type": c.get("type")} for c in categories.get("all", [])
        ]
    }


# --- Реєстр ---

_DATE = {"type": "string", "description": "Дата у форматі YYYY-MM-DD"}
_PERIOD_PARAMS = {
    "type": "object",
    "properties": {"start_date": _DATE, "end_date": _DATE},
    "required": ["start_date", "end_date"],
}

CORE_TOOLS = [
    Tool(
        name="get_transactions_summary",
        description=(
            "Загальні підсумки користувача від першої транзакції до end_date (або до сьогодні): "
            "сума доходів, витрат, баланс, баланс ФОП, кількість місяців."
        ),
        parameters={"type": "object", "properties": {"end_date": _DATE}},
        handler=_transactions_summary,
    ),
    Tool(
        name="get_expenses_by_category",
        description="Витрати за категоріями (з назвами, від більших до менших) та загальні доходи/витрати за період.",
        parameters=_PERIOD_PARAMS,
        handler=_expenses_by_category,
    ),
    Tool(
        name="get_insights",
        description=(
            "Аналітичні висновки за період: ризикові категорії витрат, зростання порівняно з попереднім "
            "періодом, використання бюджетів і рекомендації."
        ),
        parameters=_PERIOD_PARAMS,
        handler=_insights,
    ),
    Tool(
        name="get_tax_estimate",
        description=(
            "Розрахунок податків ФОП (єдиний податок, ЄСВ, військовий збір) за поточний місяць, квартал "
            "або рік на основі доходів і налаштувань ФОП користувача, а також попередження про ліміти групи."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["month", "quarter", "year"]},
                "calc_date": {**_DATE, "description": "Дата, на яку рахувати (YYYY-MM-DD), типово — сьогодні"},
            },
            "required": ["period"],
        },
        handler=_tax_estimate,
    ),
    Tool(
        name="list_transactions",
        description=(
            "Список транзакцій (новіші першими) з фільтрами: період, тип, категорія, пошук в описі. "
            f"Максимум {MAX_TRANSACTIONS} записів."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_date": _DATE,
                "end_date": _DATE,
                "type": {"type": "string", "enum": ["income", "expense"]},
                "category_id": {"type": "string", "description": "ID категорії"},
                "search": {"type": "string", "description": "Текст для пошуку в описі"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TRANSACTIONS},
            },
        },
        handler=_list_transactions,
    ),
    Tool(
        name="get_budgets_progress",
        description="Бюджети користувача та скільки вже витрачено по кожному.",
        parameters={"type": "object", "properties": {}},
        handler=_budgets_progress,
    ),
]

EXTENSION_TOOLS = [
    Tool(
        name="get_tax_history",
        description="Історія податкових записів по місяцях: дохід ФОП, ЄСВ, єдиний податок, військовий збір, чи сплачено.",
        parameters={"type": "object", "properties": {}},
        handler=_tax_history,
    ),
    Tool(
        name="get_exchange_rate",
        description="Офіційний курс НБУ валюти до гривні на дату (типово — сьогодні).",
        parameters={
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "ISO-код валюти, напр. USD, EUR"},
                "rate_date": _DATE,
            },
            "required": ["currency"],
        },
        handler=_exchange_rate,
    ),
    Tool(
        name="get_financial_report",
        description=(
            "Звіт за поточний день/тиждень/місяць/рік: доходи, витрати, дохід ФОП, витрати за категоріями, "
            "прогноз витрат до кінця місяця і поради."
        ),
        parameters={
            "type": "object",
            "properties": {"period": {"type": "string", "enum": list(REPORT_PERIODS)}},
            "required": ["period"],
        },
        handler=_financial_report,
    ),
    Tool(
        name="get_profile",
        description="Профіль користувача та повні налаштування ФОП (група, система оподаткування, ставки, ЗЕД, ПДВ тощо).",
        parameters={"type": "object", "properties": {}},
        handler=_profile,
    ),
    Tool(
        name="list_categories",
        description="Категорії доходів і витрат користувача з їх ID (для фільтра category_id у list_transactions).",
        parameters={"type": "object", "properties": {}},
        handler=_categories,
    ),
]

TOOLS = {tool.name: tool for tool in CORE_TOOLS + EXTENSION_TOOLS}


def tool_schemas() -> list:
    return [
        {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        }
        for t in TOOLS.values()
    ]


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return str(value)


def _dump(result: Any) -> str:
    raw = json.dumps(result, ensure_ascii=False, default=_json_default)
    if len(raw) <= MAX_RESULT_CHARS:
        return raw
    return json.dumps(
        {
            "truncated": True,
            "note": "Результат завеликий, показано початок. Звузьте період або фільтри.",
            "data_preview": raw[:MAX_RESULT_CHARS],
        },
        ensure_ascii=False,
    )


def execute_tool(name: str, arguments: dict, user_id: str) -> str:
    """Виконує tool і повертає JSON-рядок для моделі. Ніколи не кидає винятків."""
    tool = TOOLS.get(name)
    if tool is None:
        return _dump({"error": f"Невідомий інструмент: {name}"})
    try:
        # Перевірка аргументів до виклику: TypeError від bind — некоректні аргументи моделі,
        # TypeError всередині handler — внутрішня помилка (не плутати ці два випадки).
        # user_id передається позиційно: спроба моделі передати свій user_id дасть TypeError.
        inspect.signature(tool.handler).bind(user_id, **arguments)
    except TypeError as exc:
        return _dump({"error": f"Некоректні аргументи для {name}: {exc}"})
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
    return _dump(result)
