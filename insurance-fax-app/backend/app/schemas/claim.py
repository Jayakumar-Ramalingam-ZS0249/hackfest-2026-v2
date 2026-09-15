from typing import Optional

from pydantic import BaseModel


class DecisionPayload(BaseModel):
    approved: bool
    corrections: Optional[dict] = None  # { field_name: corrected_value }
    reviewer: str = "unknown_user"
    reason: Optional[str] = None
