from pydantic import BaseModel
from typing import Optional


class AssistantQuery(BaseModel):
    message: str
    incident_id: Optional[str] = None  # optional context


class AssistantResponse(BaseModel):
    answer: str
    recommendations: list[str]
    references: list[str]
    severity_assessment: Optional[str] = None
    incident_context: Optional[dict] = None
    source: str  # "rule-based" or "llm"
