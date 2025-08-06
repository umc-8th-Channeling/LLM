import random
from collections import defaultdict
from typing import List, DefaultDict
import logging
from domain.comment.model.comment import Comment
from domain.comment.model.comment_type import CommentType
from domain.comment.repository.comment_repository import CommentRepository
from external.rag.rag_service_impl import RagServiceImpl

logger = logging.getLogger(__name__)

class CommentService:
    def __init__(self):
        self.rag_service = RagServiceImpl()
        self.comment_repository = CommentRepository()

    async def summarize_comments_by_emotions_with_llm(self, comments_by_emotions: DefaultDict[CommentType, list[Comment]]) -> defaultdict[CommentType, List[Comment]]:
        summarized_comments: defaultdict[CommentType, List[Comment]] = defaultdict(list)

        # 감정별로 요약
        for emotion, comments in comments_by_emotions.items():
            if not comments:
                summarized_comments[emotion].append("")
                continue

            # 해당 감정 그룹의 content만 개행으로 합치기
            contents_str = "\n".join(comment.content for comment in comments)

            # LLM 서비스 호출 -> returns list[str]
            summarized_contents = self.rag_service.summarize_comments(contents_str)


            # 요약 내용을 defaultdict에 추가 & DB 저장
            comments_to_save = []
            for content in summarized_contents:
                summarized_comment_obj = Comment(
                    comment_type=emotion.value,
                    content=content,
                    report_id=comments[0].report_id
                )
                summarized_comments[emotion].append(summarized_comment_obj)
                # 딕셔너리로 변환하여 저장
                comments_to_save.append({
                    "comment_type": emotion.value,
                    "content": content,
                    "report_id": comments[0].report_id
                })
            await self.comment_repository.save_bulk(comments_to_save)
            logger.info("댓글 결과를 MYSQL DB에 저장했습니다.")
        return summarized_comments

    async def classify_comment_with_llm(self, comment: Comment) -> Comment:
        result = self.rag_service.classify_comment(comment.content)
        # comment의 comment_type 업데이트
        comment.comment_type = result["comment_type"]
        # db 저장 후 반환 -> 그냥 반환
        return comment

    # 댓글을 분류
    async def gather_classified_comments(self, comments: list[Comment])->DefaultDict[CommentType, list[Comment]]:
        grouped = defaultdict(list)
        for comment in comments:
            result = await self.classify_comment_with_llm(comment)
            grouped[result.comment_type].append(result)

        return grouped

    # 유튜브 api 에서 가져온 댓글을 Comment 객체로 변환
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
