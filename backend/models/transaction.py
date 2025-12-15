from pydantic import BaseModel
from typing import Optional
from datetime import date as date_type
from models.common_type import CommonType

class TransactionCreate(BaseModel):
    user_id: str
    category_id: Optional[str] = None
    type: CommonType
    amount: float
    currency: str = "UAH" 
    description: Optional[str] = None
    date: date_type
    manual_rate: Optional[float] = None

class TransactionPatch(BaseModel):
    category_id: Optional[str] = None
    type: Optional[CommonType] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date_type] = None
    currency: Optional[str] = None
    manual_rate: Optional[float] = None