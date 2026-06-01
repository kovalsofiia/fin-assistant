from typing import Optional

from pydantic import BaseModel, Field

from core.constants import CURRENCY_REGEX, MAX_NAME_LENGTH, MIN_NAME_LENGTH


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
    bank_name: Optional[str] = Field(None, max_length=MAX_NAME_LENGTH)
    currency_code: str = Field("UAH", pattern=CURRENCY_REGEX)
    is_business: bool = True
    sort_order: int = Field(0, ge=0, le=9999)

    class Config:
        str_strip_whitespace = True


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
    bank_name: Optional[str] = Field(None, max_length=MAX_NAME_LENGTH)
    currency_code: Optional[str] = Field(None, pattern=CURRENCY_REGEX)
    is_business: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0, le=9999)

    class Config:
        str_strip_whitespace = True
