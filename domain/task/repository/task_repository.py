from domain.task.model.task import Task
from core.database.repository.crud_repository import CRUDRepository


class TaskRepository(CRUDRepository[Task]):
    def model_class(self) -> type[Task]:
        """Task 모델 클래스를 반환합니다."""
        return Task