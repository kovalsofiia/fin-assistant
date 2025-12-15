from pydantic import BaseModel
from backend.models.common_data import CommonType

class CategoryCreate(BaseModel):
    name: str
    type: CommonType
    user_id: str