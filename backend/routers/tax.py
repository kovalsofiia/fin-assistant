from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from services.tax_service import TaxService
from models.setting import FopSettingsBase
from models.common import ReportingPeriod
from core.database import supabase

router = APIRouter(prefix="/tax", tags=["Tax"])

@router.get("/calculate")
def calculate_tax(
    user_id: str,
    annual_income: float = 0.0,
    monthly_income: float = 0.0,
    period: ReportingPeriod = ReportingPeriod.MONTH
):
    """
    Розрахунок податків на основі налаштувань користувача та доходу.
    """
    try:
        # 1. Отримуємо налаштування ФОП
        settings_res = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        if not settings_res.data:
            raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")
        
        settings_data = settings_res.data[0]
        settings = FopSettingsBase(**settings_data)
        
        # 2. Перевіряємо ліміти та обмеження
        errors = TaxService.verify_group_restrictions(settings, annual_income)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})
            
        # 3. Отримуємо попередження
        warnings = TaxService.get_warnings(settings, annual_income)
        
        # 4. Рахуємо податки
        # Для розрахунку використовуємо або місячний дохід, або річний розділений на місяці
        income_for_calc = monthly_income if monthly_income > 0 else (annual_income / 12)
        taxes = TaxService.calculate_taxes(settings, income_for_calc, period)
        
        # 5. Календар
        calendar = TaxService.get_payment_calendar()
        
        return {
            "taxes": taxes,
            "warnings": warnings,
            "calendar": calendar
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Tax Calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
