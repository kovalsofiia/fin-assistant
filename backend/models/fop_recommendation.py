from typing import Optional

from pydantic import BaseModel, Field


class FopRecommendManualFlags(BaseModel):
    """Уточнення, які не виводяться лише з транзакцій."""

    is_b2b_or_foreign: Optional[bool] = Field(
        None,
        description="B2B з юрособами на загальній або іноземні замовники. True блокує 1–2 групи.",
    )
    g4_land_type: str = Field("arable_pasture", pattern="^(arable_pasture|water|closed_soil)$")
