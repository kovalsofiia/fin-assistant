from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class UserKvedItem(BaseModel):
    """У запиті: code/kved_code та name/kved_name. У БД: kved_code, kved_name."""

    code: Optional[str] = Field(None, min_length=1, max_length=20)
    kved_code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, max_length=500)
    kved_name: Optional[str] = Field(None, max_length=500)

    class Config:
        str_strip_whitespace = True

    def resolved_kved_code(self) -> str:
        return (self.kved_code or self.code or "").strip()

    def resolved_kved_name(self) -> Optional[str]:
        raw = (self.kved_name or self.name or "").strip()
        return raw[:500] if raw else None

    @model_validator(mode="after")
    def require_kved_identifier(self):
        if self.resolved_kved_code():
            return self
        raise ValueError("Потрібно поле code або kved_code")


class UserKvedsSync(BaseModel):
    kveds: List[UserKvedItem] = Field(default_factory=list)
