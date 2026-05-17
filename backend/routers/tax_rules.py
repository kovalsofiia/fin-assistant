from fastapi import APIRouter, Depends, HTTPException
from datetime import date as date_type, timedelta
from typing import Optional
from services.tax_service import TaxService
from models.setting import FopSettingsBase
from models.common import ReportingPeriod
from core.database import supabase
from core.auth import get_current_user_id

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

@router.get("/calculate")
def calculate_tax(
    current_user_id: str = Depends(get_current_user_id),
    annual_income: float = 0.0,
    monthly_income: float = 0.0,
    period: ReportingPeriod = ReportingPeriod.MONTH,
    calc_date: Optional[date_type] = None
):
    """
    Розрахунок податків на основі налаштувань користувача та доходу.
    """
    try:
        effective_calc_date = calc_date or date_type.today()

        # 1. Отримуємо налаштування ФОП
        settings_res = supabase.table("fop_settings").select("*").eq("user_id", current_user_id).execute()
        if not settings_res.data:
            raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")
        
        settings_data = settings_res.data[0]
        settings = FopSettingsBase(**settings_data)
        
        # 2. Рахуємо дохід за обраний період напряму з транзакцій (джерело істини для історичних ставок).
        period_income_total, income_by_month = _collect_period_income(current_user_id, period, effective_calc_date)
        annual_income_value = _collect_annual_income(current_user_id, effective_calc_date.year)

        # Legacy fallback, якщо історичні транзакції відсутні.
        if period_income_total <= 0 and monthly_income > 0:
            months_to_calc = _period_months(period)
            period_income_total = monthly_income if months_to_calc == 1 else (monthly_income * months_to_calc)
            if months_to_calc == 1:
                income_by_month = {f"{effective_calc_date.year}-{effective_calc_date.month:02d}": period_income_total}

        if annual_income_value <= 0 and annual_income > 0:
            annual_income_value = annual_income

        # 3. Перевіряємо ліміти та обмеження
        errors = TaxService.verify_group_restrictions(settings, annual_income_value)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})
            
        # 4. Отримуємо попередження
        warnings = TaxService.get_warnings(settings, annual_income_value)
        
        # 5. Рахуємо податки.
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
        if isinstance(e, HTTPException): raise e
        print(f"Tax Calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules")
def get_tax_rules(year: int, month: int):
    """
    Повертає глобальні правила оподаткування для вказаного періоду.
    """
    try:
        rules = TaxService.get_tax_rules(year, month)
        return rules
    except Exception as e:
        print(f"Error in /tax/rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
