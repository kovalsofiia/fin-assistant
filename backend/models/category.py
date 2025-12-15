from pydantic import BaseModel
from models.common import CommonType

class CategoryCreate(BaseModel):
    name: str
    type: CommonType
    user_id: str