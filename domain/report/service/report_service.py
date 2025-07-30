from typing import DefaultDict, List

from domain.comment.model.comment import Comment
from domain.report.repository.report_repository import ReportRepository


class ReportService:
    def __init__(self):
        self.report_repository = ReportRepository()

    async def update_report_count(self, report_id: int, comment_dict:DefaultDict[str,List[Comment]]) -> bool:
        """
        성공 시 True, 실패 시 False를 반환합니다.
        """
        count_dict = {comment_type: len(comments) for comment_type, comments in comment_dict.items()}
        return await self.report_repository.update_count(report_id, count_dict)