from sqlmodel import select, func

from core.config.database_config import MySQLSessionLocal
from core.database.repository.crud_repository import CRUDRepository
from domain.video.model.video import Video


class VideoRepository(CRUDRepository[Video]):
    def model_class(self) -> type[Video]:
        return Video

    # 채널별 비디오 조회
    async def find_by_channel_id(self, channel_id: int) -> list[Video]:
        """
        """
        async with MySQLSessionLocal() as session:
            statement = select(self.model_class()).where(
                self.model_class().channel_id == channel_id
            )

            result = await session.execute(statement)

            return result.scalars().all()

    # 채널의 조회수 평균 (토픽별 채널별)
    async def get_view_summary_by_channel_id(self, channel_id: int, category: str = ""):
        async with MySQLSessionLocal() as session:

            statement = select(
                func.sum(self.model_class().view).label("sum"),
                func.count().label("cnt")
            ).where(
                self.model_class().channel_id == channel_id
            )

            if category:
                statement.where(
                    self.model_class().video_category == category
                )

            result = await session.execute(statement)

            return result.first()

    # 채널의 좋아요 평균 (토픽별 채널별)
    async def get_like_summary_by_channel_id(self, channel_id: int, category: str = ""):
        async with MySQLSessionLocal() as session:
            statement = select(
                func.sum(self.model_class().like_count).label("sum"),
                func.count().label("cnt")
            ).where(
                self.model_class().channel_id == channel_id
            )

            if category:
                statement.where(
                    self.model_class().video_category == category
                )

            result = await session.execute(statement)

            return result.first()

    # 채널의 댓글 평균 (토픽별 채널별)
    async def get_comment_summary_by_channel_id(self, channel_id: int, category: str = ""):
        async with MySQLSessionLocal() as session:
            statement = select(
                func.sum(self.model_class().comment_count).label("sum"),
                func.count().label("cnt")
            ).where(
                self.model_class().channel_id == channel_id
            )

            if category:
                statement.where(
                    self.model_class().video_category == category
                )

            result = await session.execute(statement)

            return result.first()