from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum

class Status(str, Enum):
    """작업 상태 Enum"""
    PENDING = "pending"  # 대기 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", description="리포트 ID")
    overview_status: Status
    analysis_status: Status
    idea_status: Status



