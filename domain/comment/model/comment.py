from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from domain.comment.model.comment_type import CommentType


class Comment(SQLModel, table=True):
    """댓글 모델 - SQLModel로 정의"""
    __tablename__ = "comment"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", description="리포트 ID")
    comment_type: CommentType = Field(description="댓글 타입")
    content: str = Field(description="댓글 내용")
    
    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
