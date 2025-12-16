from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type
from models.common import CommonType
from core.constants import(
    MIN_TRANSACTION_AMOUNT,
    CURRENCY_REGEX,
    MAX_DESCRIPTION_LENGTH,
    MIN_MANUAL_RATE
)

class TransactionCreate(BaseModel):
    user_id: str
    category_id: Optional[str] = None
    type: CommonType
    # 1. Забороняємо 0 і мінус. Сума має бути строго більше 0
    amount: float = Field(..., gt=MIN_TRANSACTION_AMOUNT, description="Сума має бути більше 0.01") 
    # 2. Валідація валюти: Рівно 3 символи, тільки великі літери (A-Z)
    currency: str = Field("UAH", pattern=CURRENCY_REGEX) 
    # 3. Обмеження довжини опису
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH) 
    date: date_type
    # 4. Курс теж має бути більше 0, якщо він заданий
    manual_rate: Optional[float] = Field(None, gt=MIN_MANUAL_RATE) 

class TransactionPatch(BaseModel):
    category_id: Optional[str] = None
    type: Optional[CommonType] = None
    amount: Optional[float] = Field(None, gt=MIN_TRANSACTION_AMOUNT)
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    date: Optional[date_type] = None
    currency: Optional[str] = Field(None, pattern=CURRENCY_REGEX)
    manual_rate: Optional[float] = Field(None, gt=MIN_MANUAL_RATE)