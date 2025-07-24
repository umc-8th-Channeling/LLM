from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Channel(SQLModel, table=True):
    """Channel 테이블 모델 - Spring Entity를 SQLModel로 변환"""
    __tablename__ = "channel"

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign Key - Video 테이블 참조
    member_id: int = Field(description="멤버 ID")

    youtube_channel_id: str
    youtube_playlist_id: str
    name: str
    view: int
    like_count: int
    subscribe: int
    share: int
    video_count: int
    comment: int
    link: str
    join_date: datetime
    target: str
    concept: str
    image: str
    channel_hash_tag: str  # Enum 타입 : ChannelHashTag
    channel_update_at: datetime

    # BaseEntity 상속 부분 (created_at, updated_at)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

