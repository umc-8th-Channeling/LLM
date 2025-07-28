import random
from collections import defaultdict

from domain.comment.model.comment import Comment
from domain.comment.repository.comment_repository import CommentRepository
from external.rag.rag_service import RagService


class CommentService:
    def __init__(self):
        self.rag_service = RagService()
        self.comment_repository = CommentRepository()

    async def classify_comment_with_llm(self, comment: Comment) -> Comment:
        result = self.rag_service.classify_comment(comment.content)
        #comment의 comment_type 업데이트
        comment.comment_type = result["comment_type"]
        #db 저장 후 반환
        return await self.comment_repository.save(comment)

    # 댓글을 분류
    async def gather_classified_comments(self, comments: list[Comment]):
        grouped = defaultdict(list)
        for comment in comments:
            result = await self.classify_comment_with_llm(comment)
            grouped[result.comment_type].append(result)

        return grouped

    #유튜브 api 에서 가져온 댓글을 Comment 객체로 변환
    async def convert_to_comment_objects(self, comments: list[dict]) -> list[Comment]:
        comment_objects = []
        for data in comments:
            comment = Comment(
                comment_type=data.get("comment_type", None),
                content=data["content"],
                report_id=data["report_id"],
            )
            comment_objects.append(comment)
        return comment_objects