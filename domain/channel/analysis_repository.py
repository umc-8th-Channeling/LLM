from sqlmodel import select

from core.config.database_config import AsyncSessionLocal
from core.database.model.analysis import Analysis
from core.database.repository.crud_repository import CRUDRepository


class AnalysisRepository(CRUDRepository[Analysis]):
    def model_class(self) -> type[Analysis]:
        return Analysis

    async def find_by_video_id(self, video_id: int) -> Analysis | None:
        async with AsyncSessionLocal() as session:
            statement = select(self.model_class()).where(
                self.model_class().video_id == video_id
            )

            result = await session.execute(statement)

            return result.scalar_one_or_none()
