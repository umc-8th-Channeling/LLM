import random
from collections import defaultdict
from .model.comment_type import CommentType
class CommentsService:
    def __init__(self, comments_repository):
        self.comments_repository = comments_repository
    def classify_comment_with_llm(self, content: str) -> dict:
        # todo: llm을 이용한 댓글 분류 로직 구현. 임시로 랜덤값으로 구현
        comment_type = random.choice(self.CommentType.all())
        return {"content": content, "comment_type": comment_type}


    # 댓글을 분류하고, 각 유형별로 6개씩 모아서 반환하는 함수
    def gather_classified_comments(self, comments: list[dict]) -> dict:
        grouped = defaultdict(list)
        for comment in comments:
            result = self.classify_comment_with_llm(comment["content"])
            grouped[result["comment_type"]].append(result)

            if all(len(grouped[ct]) >= 6 for ct in self.CommentType.all()):
                break

        return grouped
