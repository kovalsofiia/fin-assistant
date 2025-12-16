from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type
from core.constants import (
    MIN_NAME_LENGTH,
    MAX_NAME_LENGTH,
    NAME_REGEX
)
class ProfileBase(BaseModel):
    is_fop: bool = True
    
    # ВАЛІДАЦІЯ ІМЕНІ:
    # min_length=1
    # max_length=100
    # pattern: Дозволяє:
    #   - Кирилицю (а-я, А-Я)
    #   - Українські літери (є, і, ї, ґ і великі)
    #   - Латиницю (a-z)
    #   - Апострофи (') та (’)
    #   - Дефіс (-) та пробіли
    full_name: Optional[str] = Field(
        None, 
        min_length=MIN_NAME_LENGTH, 
        max_length=MAX_NAME_LENGTH, 
        pattern=NAME_REGEX
    )
    class Config:
        str_strip_whitespace = True

class ProfileCreate(ProfileBase):
    user_id: str # При створенні ID обов'язковий

class ProfileUpdate(BaseModel):
    # В Update всі поля опціональні, але правила ті самі
    is_fop: Optional[bool] = None
    full_name: Optional[str] = Field(
        None, 
        min_length=MIN_NAME_LENGTH, 
        max_length=MAX_NAME_LENGTH, 
        pattern=NAME_REGEX
    )
    class Config:
        str_strip_whitespace = True