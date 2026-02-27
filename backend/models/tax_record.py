from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaxRecordBase(BaseModel):
    user_id: str
    year: int
    month: int
    fop_income: float = 0.0
    esv: float = 0.0
    income_tax: float = 0.0
    military_tax: float = 0.0
    is_paid: bool = False

class TaxRecordCreate(TaxRecordBase):
    pass

class TaxRecordResponse(TaxRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
