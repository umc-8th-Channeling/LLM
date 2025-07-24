from typing import Optional

from sqlmodel import SQLModel, Field


# youtube analytics (가정)
class Analysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(description="비디오 ID")
    views: Optional[int] = Field(description="조회수")
    average_view_duration: Optional[int] = Field(description="평균 시청 시간 (초)")
    likes: Optional[int] = Field(description="좋아요 수")
    shares: Optional[int] = Field(default=0, description="공유 수")
    subscribers_gained: Optional[int] = Field(description="구독자 증가 수")
