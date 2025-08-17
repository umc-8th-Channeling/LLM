import asyncio
import time

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
        start_time = time.time()
        logger.info(f"💡 아이디어 생성 시작 - Report ID: {report_id}")
        
        try:
            summary = await self.wait_for_summary(report_id)
            if not summary:
                logger.warning(f"Report ID {report_id}에 대한 요약본을 찾을 수 없어 아이디어 생성을 건너뜁니다.")

            # 아이디어 분석 요청
            idea_results = await self.rag_service.analyze_idea(video, channel, summary)

            # 아이디어 분석 결과를 Report에 저장
            db_start = time.time()
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
            db_time = time.time() - db_start
            logger.info(f"🗄️ 아이디어 DB 저장 완료 ({db_time:.2f}초) - {len(ideas)}개 아이디어")
            
            total_time = time.time() - start_time
            logger.info(f"💡 아이디어 생성 전체 완료 ({total_time:.2f}초)")
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"💡 아이디어 생성 실패 ({total_time:.2f}초): {e!r}")
            raise e

    async def wait_for_summary(self, report_id: int, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            report = await report_repository.find_by_id(report_id)
            if report.summary:
                return report.summary

            logger.info(f"아이디어 요약본 확인 시도 {attempt + 1}: {report.summary}")
            await asyncio.sleep(1)

        return None