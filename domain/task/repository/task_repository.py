from sqlmodel import select

from core.config.database_config import MySQLSessionLocal
from domain.task.model.task import Task
from core.database.repository.crud_repository import CRUDRepository


class TaskRepository(CRUDRepository[Task]):
    def model_class(self) -> type[Task]:
        """Task 모델 클래스를 반환합니다."""
        return Task

    async def find_by_report_id(self, report_id: int) -> Task:
        async with MySQLSessionLocal() as session:
            statement = select(self.model_class()).where(
                self.model_class().report_id == report_id
            )
            result = await session.execute(statement)
            return result.scalar_one_or_none()
