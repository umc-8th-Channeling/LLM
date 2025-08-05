from core.database.repository.crud_repository import CRUDRepository
from domain.idea.model.idea import Idea

class IdeaRepository(CRUDRepository[Idea]):
    def model_class(self) -> type[Idea]:
        return Idea
