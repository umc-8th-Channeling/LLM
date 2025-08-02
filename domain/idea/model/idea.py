from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Idea(SQLModel, table=True):
    """Report 테이블 모델 - Spring Entity를 SQLModel로 변환"""
    __tablename__ = "idea"

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Fk
    video_id:int = Field(description="video id")

    title:str = Field(description="아이디어 제목")
    content:str = Field(description="아이디어 내용")
    hash_tag:str = Field(description="해시태그")

    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)