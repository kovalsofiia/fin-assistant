from pydantic import BaseModel, Field
from typing import Optional
from models.common import FopGroup, TaxSystem, ActivityType, ReportingPeriod
from core.constants import (
    MIN_TAX_PERCENT, 
    MAX_TAX_PERCENT, 
    MAX_ESV_VALUE,
    MIN_ESV_VALUE
)

class FopSettingsBase(BaseModel):
    # Валідація: Група тільки 1, 2, 3 або 4
    fop_group: Optional[FopGroup] = None
    # ЗЕД: True/False
    is_zed: Optional[bool] = None
    # Податок: від 0% до 100%
    income_tax_percent: Optional[float] = Field(None, ge=MIN_TAX_PERCENT, le=MAX_TAX_PERCENT)
    # ЄСВ: не може бути від'ємним
    esv_value: Optional[float] = Field(None, ge=MIN_ESV_VALUE, le=MAX_ESV_VALUE)
    # Військовий збір: від 0% до 100%
    military_tax_percent: Optional[float] = Field(None, ge=MIN_TAX_PERCENT, le=MAX_TAX_PERCENT)
    
    # НОВІ ПОЛЯ 2025
    tax_system: Optional[TaxSystem] = Field(TaxSystem.SIMPLIFIED)
    activity_type: Optional[ActivityType] = Field(ActivityType.SERVICES)
    has_employees: bool = Field(False)
    employees_count: int = Field(0, ge=0)
    is_vat_payer: bool = Field(False)
    land_area_ha: Optional[float] = Field(None, ge=0)
    normative_land_value: Optional[float] = Field(None, ge=0)

class FopSettingsUpdate(FopSettingsBase):
    pass # Використовуємо ту ж структуру для оновлення

class FopSettingsResponse(FopSettingsBase):
    setting_id: str
    user_id: str
