from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Step(Enum):
    """Kafka 메시지의 단계"""
    overview = "overview"
    analysis = "analysis"
    idea= "idea"


class Message(BaseModel):
    """Kafka 메시지의 기본 클래스"""
    task_id: int
    report_id: int
    step: Step
    google_access_token: Optional[str] = None
    skip_vector_save: Optional[bool] = False


