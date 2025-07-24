# comments 를 저장하기 위해 모델을 정의
from pydantic import BaseModel
from datetime import datetime
from comment_type import CommentType

class Comment(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    comment_type: CommentType
    content: str
    report_id: int
