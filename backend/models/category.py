from pydantic import BaseModel
from models.common_type import CommonType

class CategoryCreate(BaseModel):
    name: str
    type: CommonType
    user_id: str