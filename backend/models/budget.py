from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type
from enum import Enum

class BudgetPeriod(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"
    custom = "custom"

class BudgetCreate(BaseModel):
    user_id: str
    category_id: Optional[str] = None
    amount: float = Field(..., gt=0, description="Ліміт бюджету має бути більше 0")
    period: BudgetPeriod = Field(default=BudgetPeriod.monthly)
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None

class BudgetUpdate(BaseModel):
    category_id: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None
