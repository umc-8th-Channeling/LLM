from pydantic import BaseModel

from core.enums.video_category import VideoCategory


class IdeaRequest(BaseModel):
    channel_id: int
    video_type: str
    keyword: str
    detail: str

class PopularRequest(BaseModel):
    category: VideoCategory