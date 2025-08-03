from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import async_session

from core.config.database_config import MySQLSessionLocal
from core.database.repository.crud_repository import CRUDRepository, T
from domain.comment.model.comment import Comment


class CommentRepository(CRUDRepository[Comment]):
    def __init__(self):
        self.async_session = async_session

    def model_class(self) -> type[Comment]:
        return Comment

    async def save_bulk(self, comments_entities: List[Comment]) -> List[Comment]:
        """여러 엔티티를 한 번에 저장"""
        async with MySQLSessionLocal() as session:
            session.add_all(comments_entities)
            await session.commit()
        return comments_entities