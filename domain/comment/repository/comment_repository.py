from typing import Dict, Any

from core.database.repository.crud_repository import CRUDRepository, T
from domain.comment.model.comment import Comment


class CommentRepository(CRUDRepository[Comment]):
    def model_class(self) -> type[Comment]:
        return Comment

    # 댓글을 저장하는 레포
    #comment를 파라미터로 받음
    async def save(self, data:Comment) -> Comment:
        data_copy = data.dict()

        if data.id is not None:
            # UPDATE - 기존 레코드 부분 업데이트
            return await self._update_partial(data_copy)
        else:
            # INSERT - 새 레코드 생성
            return await self._create_new(data_copy)