from fastapi import APIRouter, Depends, HTTPException
from datetime import date as date_type, timedelta
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

from services.tax_service import TaxService
from models.setting import FopSettingsBase
from models.common import ReportingPeriod
from models.tax_rule import TaxRuleUpdate, TaxRuleResponse
from core.database import supabase
from core.auth import get_current_user_id
from core.admin_auth import require_tax_rules_admin
from core.tax_rules_defaults import default_tax_rules_for_period, TAX_RULES_NUMERIC_KEYS

router = APIRouter(prefix="/tax", tags=["Tax"])


def _period_months(period: ReportingPeriod) -> int:
    if period == ReportingPeriod.QUARTER:
        return 3
    if period == ReportingPeriod.YEAR:
        return 12
    return 1


def _month_start(d: date_type) -> date_type:
    return d.replace(day=1)


def _month_end(d: date_type) -> date_type:
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    return next_month - timedelta(days=1)


def _shift_months(d: date_type, months: int) -> date_type:
    total_month = d.month - 1 + months
    year = d.year + total_month // 12
    month = total_month % 12 + 1
    return d.replace(year=year, month=month, day=1)


def _collect_period_income(current_user_id: str, period: ReportingPeriod, calc_date: date_type):
    months_to_calc = _period_months(period)
    period_start = _month_start(calc_date)
    period_last_month_start = _shift_months(period_start, months_to_calc - 1)
    period_end = _month_end(period_last_month_start)

    tx_res = supabase.table("transactions")\
        .select("transaction_amount, transaction_date")\
        .eq("user_id", current_user_id)\
        .eq("transaction_type", "income")\
        .eq("is_fop", True)\
        .gte("transaction_date", period_start.isoformat())\
        .lte("transaction_date", period_end.isoformat())\
        .execute()

    income_by_month = {}
    period_income_total = 0.0
    for tx in tx_res.data or []:
        amount = float(tx.get("transaction_amount", 0) or 0)
        date_str = str(tx.get("transaction_date", ""))
        month_key = date_str[:7]
        if len(month_key) != 7:
            continue
        income_by_month[month_key] = income_by_month.get(month_key, 0.0) + amount
        period_income_total += amount

    return period_income_total, income_by_month


def _collect_annual_income(current_user_id: str, year: int) -> float:
    start = date_type(year, 1, 1).isoformat()
    end = date_type(year, 12, 31).isoformat()
    tx_res = supabase.table("transactions")\
        .select("transaction_amount")\
        .eq("user_id", current_user_id)\
        .eq("transaction_type", "income")\
        .eq("is_fop", True)\
        .gte("transaction_date", start)\
        .lte("transaction_date", end)\
        .execute()
    return sum(float(tx.get("transaction_amount", 0) or 0) for tx in (tx_res.data or []))


def _invalidate_rules_cache():
    TaxService._rules_cache.clear()


@router.get("/rules")
def get_tax_rules(year: int, month: int):
    """Публічне читання правил для періоду (джерело істини для фронту та квізу)."""
    try:
        return TaxService.get_tax_rules(year, month)
    except Exception as e:
        print(f"Error in /tax/rules: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося завантажити податкові правила")


@router.get("/rules/admin/list")
def list_tax_rules_admin(_admin_id: str = Depends(require_tax_rules_admin)):
    """Усі записи tax_rules для адмін-панелі."""
    try:
        res = (
            supabase.table("tax_rules")
            .select("*")
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Admin list tax rules: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося завантажити список правил")


@router.put("/rules/admin/{rule_id}")
def update_tax_rule_admin(
    rule_id: str,
    payload: TaxRuleUpdate,
    _admin_id: str = Depends(require_tax_rules_admin),
):
    try:
        update_data = jsonable_encoder(payload.dict(exclude_unset=True))
        if not update_data:
            raise HTTPException(status_code=400, detail="Немає полів для оновлення")

        res = (
            supabase.table("tax_rules")
            .update(update_data)
            .eq("id", rule_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Запис не знайдено")

        _invalidate_rules_cache()
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Admin update tax rule: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося оновити правило")


@router.post("/rules/admin/seed/{year}")
def seed_tax_rules_year(
    year: int,
    _admin_id: str = Depends(require_tax_rules_admin),
):
    """Створити/оновити 12 місяців року дефолтними значеннями (2026+ з tax_rules_defaults)."""
    if year < 2020 or year > 2100:
        raise HTTPException(status_code=400, detail="Некоректний рік")

    created = []
    try:
        for month in range(1, 13):
            row = default_tax_rules_for_period(year, month)
            existing = (
                supabase.table("tax_rules")
                .select("id")
                .eq("year", year)
                .eq("month", month)
                .execute()
            )
            if existing.data:
                res = (
                    supabase.table("tax_rules")
                    .update({k: row[k] for k in TAX_RULES_NUMERIC_KEYS})
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                res = supabase.table("tax_rules").insert(row).execute()
            if res.data:
                created.append(res.data[0])

        _invalidate_rules_cache()
        return {"message": f"Оновлено {len(created)} періодів для {year}", "records": created}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Seed tax rules: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося заповнити правила")


@router.get("/rules/admin/me")
def tax_rules_admin_check(current_user_id: str = Depends(get_current_user_id)):
    """Чи має поточний користувач право редагувати tax_rules."""
    from core.admin_auth import _allowed_admin_emails

    allowed = _allowed_admin_emails()
    if not allowed:
        return {"is_admin": False, "reason": "TAX_RULES_ADMIN_EMAILS не налаштовано"}
    try:
        user_res = supabase.auth.admin.get_user_by_id(current_user_id)
        email = (getattr(getattr(user_res, "user", None), "email", None) or "").lower()
        return {"is_admin": email in allowed, "email": email}
    except Exception:
        return {"is_admin": False}


@router.get("/calculate")
def calculate_tax(
    current_user_id: str = Depends(get_current_user_id),
    annual_income: float = 0.0,
    monthly_income: float = 0.0,
    period: ReportingPeriod = ReportingPeriod.MONTH,
    calc_date: Optional[date_type] = None,
):
    """
    Розрахунок податків на основі налаштувань користувача та доходу.
    """
    try:
        effective_calc_date = calc_date or date_type.today()

        settings_res = supabase.table("fop_settings").select("*").eq("user_id", current_user_id).execute()
        if not settings_res.data:
            raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")

        settings_data = settings_res.data[0]
        settings = FopSettingsBase(**settings_data)

        period_income_total, income_by_month = _collect_period_income(
            current_user_id, period, effective_calc_date
        )
        annual_income_value = _collect_annual_income(current_user_id, effective_calc_date.year)

        if period_income_total <= 0 and monthly_income > 0:
            months_to_calc = _period_months(period)
            period_income_total = monthly_income if months_to_calc == 1 else (monthly_income * months_to_calc)
            if months_to_calc == 1:
                income_by_month = {
                    f"{effective_calc_date.year}-{effective_calc_date.month:02d}": period_income_total
                }

        if annual_income_value <= 0 and annual_income > 0:
            annual_income_value = annual_income

        errors = TaxService.verify_group_restrictions(settings, annual_income_value)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        warnings = TaxService.get_warnings(settings, annual_income_value)

        taxes = TaxService.calculate_taxes(
            current_user_id,
            settings,
            period_income_total,
            period,
            effective_calc_date,
            income_by_month=income_by_month,
        )

        return {
            "taxes": taxes,
            "warnings": warnings,
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"Tax Calculation error: {e}")
        raise HTTPException(status_code=500, detail="Помилка розрахунку податків")
