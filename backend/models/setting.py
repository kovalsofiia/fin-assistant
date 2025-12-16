from pydantic import BaseModel, Field
from typing import Optional
from models.common import FopGroup
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

class FopSettingsUpdate(FopSettingsBase):
    pass # Використовуємо ту ж структуру для оновлення

class FopSettingsResponse(FopSettingsBase):
    setting_id: str
    user_id: str
