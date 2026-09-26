"""Системний промпт асистента і контекст профілю ФОП."""
from datetime import date

from routers import settings as settings_router

TAX_DISCLAIMER = (
    "Це довідковий розрахунок, а не податкова консультація. "
    "Остаточні суми звіряйте з бухгалтером або ДПС."
)

PROFILE_UNAVAILABLE = "Дані профілю ФОП недоступні."

SYSTEM_PROMPT_TEMPLATE = """Ти — фінансовий асистент застосунку «FOP Assistant» для фізичних осіб-підприємців (ФОП) в Україні.

Сьогодні: {today}.

Профіль користувача:
{profile_context}

Правила:
1. Відповідай українською мовою, стисло і по суті.
2. Будь-які суми, дати та факти про фінанси користувача бери ЛИШЕ з результатів інструментів. Ніколи не вигадуй і не оцінюй цифри «на око».
3. Якщо для відповіді потрібні дані — спершу виклич відповідний інструмент. Якщо даних немає або інструмент повернув помилку — чесно скажи про це.
4. Дати в аргументах інструментів передавай у форматі YYYY-MM-DD. «Цей місяць», «минулий квартал» тощо рахуй відносно сьогоднішньої дати.
5. Суми вказуй у гривнях (грн), якщо не сказано інше.
6. Ти лише читаєш дані: не можеш створювати, змінювати чи видаляти транзакції, бюджети або налаштування. Якщо про це просять — поясни, де це зробити в застосунку.
7. Якщо відповідь стосується податків, наприкінці додай: «{disclaimer}»
8. Не відповідай на запитання, не пов'язані з фінансами користувача, податками ФОП чи роботою застосунку."""

_PROFILE_FIELDS = [
    ("fop_group", "Група ФОП"),
    ("tax_system", "Система оподаткування"),
    ("activity_type", "Вид діяльності"),
    ("is_vat_payer", "Платник ПДВ"),
    ("has_employees", "Має найманих працівників"),
]


def build_system_prompt(today: date, profile_context: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=today.isoformat(), profile_context=profile_context, disclaimer=TAX_DISCLAIMER
    )


def format_profile_context(fop_settings: dict) -> str:
    lines = []
    for key, label in _PROFILE_FIELDS:
        value = fop_settings.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            value = "так" if value else "ні"
        lines.append(f"- {label}: {value}")
    return "\n".join(lines) or PROFILE_UNAVAILABLE


def load_profile_context(user_id: str) -> str:
    """Короткий опис налаштувань ФОП для системного промпту. Ніколи не кидає винятків."""
    try:
        raw = settings_router.get_fop_settings(user_id=user_id, current_user_id=user_id)
    except Exception:
        return PROFILE_UNAVAILABLE
    data = raw.model_dump(mode="json") if hasattr(raw, "model_dump") else dict(raw or {})
    return format_profile_context(data)
