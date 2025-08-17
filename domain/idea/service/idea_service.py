import asyncio

from domain.channel.model.channel import Channel
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.controller.report_controller import report_repository
from domain.report.repository.report_repository import ReportRepository
from domain.video.model.video import Video
from external.rag.rag_service_impl import RagServiceImpl
import json
import logging


logger = logging.getLogger(__name__)

class IdeaService:
    def __init__(self):
        self.idea_repository = IdeaRepository()
        self.rag_service = RagServiceImpl()
        self.report_repository = ReportRepository()

    """
    아이디어 생성 요청
    """
    async def create_idea(self, video: Video, channel: Channel, report_id: int):
        try:
            logger.info("idea 생성")

            summary = await self.wait_for_summary(report_id)
            if not summary:
                logger.warning(f"Report ID {report_id}에 대한 요약본을 찾을 수 없어 아이디어 생성을 건너뜁니다.")
                summary = ""

            # 아이디어 분석 요청
            idea_results = await self.rag_service.analyze_idea(video, channel, summary)

            # 아이디어 분석 결과를 Report에 저장
            ideas = []
            for idea_result in idea_results:
                idea = {
                    "video_id": video.id,
                    "title": idea_result.get("title"),
                    "content": idea_result.get("description"),
                    "hash_tag": json.dumps(idea_result.get("tags"), ensure_ascii=False),
                    "is_book_marked": 0,
                }
                ideas.append(idea)

            await self.idea_repository.save_bulk(ideas)
        except Exception as e:
            logger.error(f"handle_idea 처리 중 오류 발생: {e!r}")
            raise e

    async def wait_for_summary(self, report_id: int, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            report = await report_repository.find_by_id(report_id)
            if report.summary:
                return report.summary

            logger.info(f"아이디어 요약본 확인 시도 {attempt + 1}: {report.summary}")
            await asyncio.sleep(1)

        return None