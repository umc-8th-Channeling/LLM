
from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, DateTime, JSON, text
from pgvector.sqlalchemy import Vector
from sqlmodel import Column, DateTime


class QuestionTemplate(SQLModel, table=True):
    __tablename__ = "question_template"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_type: str = Field(max_length=50, nullable=False)  
    question_text: str = Field(nullable=False)  # 질문 
    embedding: List[float] = Field(sa_column=Column(Vector(1536)))  
    metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # 메타데이터
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, server_default=text("NOW()"))
    )