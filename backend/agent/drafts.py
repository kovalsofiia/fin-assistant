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
