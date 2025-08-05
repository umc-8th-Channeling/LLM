from sqlmodel import Session, select

from core.config.database_config import MySQLSessionLocal
# from core.config.database_config import AsyncSessionLocal
from domain.channel.model.channel import Channel
from domain.video.model.video import Video
from core.database.repository.crud_repository import CRUDRepository


class VideoRepository(CRUDRepository[Video]):
    def model_class(self) -> type[Video]:
        return Video

    # 채널별 비디오 조회
    async def find_by_channel_id(self, channel_id: int) -> list[Channel]:
        """
        """
        async with MySQLSessionLocal() as session:
            statement = select(self.model_class()).where(
                self.model_class().channel_id == channel_id
            )

            result = await session.execute(statement)

            return result.scalars().all()