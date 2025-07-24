from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Video(SQLModel, table=True):
    id: int
    channel_id: int = Field(description="채널 ID")
    youtube_video_id: str
    video_category: str # VideoCategory enum
    title: Optional[str] = None
    view: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    link: Optional[str] = None
    upload_date: Optional[datetime] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None