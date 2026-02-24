from pydantic import BaseModel, Field
from models.common import CommonType
from core.constants import (
    MIN_CATEGORY_LENGTH,
    MAX_CATEGORY_LENGTH 
    )

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=MIN_CATEGORY_LENGTH, max_length=MAX_CATEGORY_LENGTH) 
    type: CommonType
    user_id: str
    is_fop_only: bool = True
    # Цей клас налаштувань автоматично обрізає пробіли " name " -> "name"
    class Config:
        str_strip_whitespace = True 