from pydantic import BaseModel
from typing import Optional

class EsvRate(BaseModel):
    year: int
    month: int
    value: float

class TaxRule(BaseModel):
    year: int
    month: int
    esv_value: float
    single_tax_g1: float
    single_tax_g2: float
    fixed_military_tax: float
    limit_g1: float
    limit_g2: float
    limit_g3: float
    income_tax_percent: Optional[float] = None
    military_tax_percent: Optional[float] = None

class UserEsvOverride(BaseModel):
    user_id: str
    year: int
    month: int
    value: float

class UserTaxOverride(BaseModel):
    user_id: str
    year: int
    month: int
    income_tax_percent: Optional[float] = None
    military_tax_percent: Optional[float] = None
    fixed_military_tax: Optional[float] = None
