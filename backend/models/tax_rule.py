from typing import Optional
from pydantic import BaseModel, Field


class TaxRuleBase(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    min_wage: Optional[float] = Field(None, ge=0)
    esv_value: Optional[float] = Field(None, ge=0)
    single_tax_g1: Optional[float] = Field(None, ge=0)
    single_tax_g2: Optional[float] = Field(None, ge=0)
    fixed_military_tax: Optional[float] = Field(None, ge=0)
    limit_g1: Optional[float] = Field(None, ge=0)
    limit_g2: Optional[float] = Field(None, ge=0)
    limit_g3: Optional[float] = Field(None, ge=0)
    limit_g1_mzp_units: Optional[int] = Field(None, ge=0)
    limit_g2_mzp_units: Optional[int] = Field(None, ge=0)
    limit_g3_mzp_units: Optional[int] = Field(None, ge=0)
    income_tax_percent: Optional[float] = Field(None, ge=0, le=100)
    income_tax_percent_vat: Optional[float] = Field(None, ge=0, le=100)
    military_tax_percent: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_arable: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_water: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_closed_soil: Optional[float] = Field(None, ge=0, le=100)
    vat_supply_threshold: Optional[float] = Field(None, ge=0)


class TaxRuleUpdate(BaseModel):
    min_wage: Optional[float] = Field(None, ge=0)
    esv_value: Optional[float] = Field(None, ge=0)
    single_tax_g1: Optional[float] = Field(None, ge=0)
    single_tax_g2: Optional[float] = Field(None, ge=0)
    fixed_military_tax: Optional[float] = Field(None, ge=0)
    limit_g1: Optional[float] = Field(None, ge=0)
    limit_g2: Optional[float] = Field(None, ge=0)
    limit_g3: Optional[float] = Field(None, ge=0)
    limit_g1_mzp_units: Optional[int] = Field(None, ge=0)
    limit_g2_mzp_units: Optional[int] = Field(None, ge=0)
    limit_g3_mzp_units: Optional[int] = Field(None, ge=0)
    income_tax_percent: Optional[float] = Field(None, ge=0, le=100)
    income_tax_percent_vat: Optional[float] = Field(None, ge=0, le=100)
    military_tax_percent: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_arable: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_water: Optional[float] = Field(None, ge=0, le=100)
    g4_rate_closed_soil: Optional[float] = Field(None, ge=0, le=100)
    vat_supply_threshold: Optional[float] = Field(None, ge=0)


class TaxRuleResponse(TaxRuleBase):
    id: Optional[str] = None
