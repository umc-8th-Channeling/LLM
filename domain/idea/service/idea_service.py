from domain.channel.model.channel import Channel
from domain.idea.repository.idea_repository import IdeaRepository
from domain.video.model.video import Video
from external.rag.rag_service_impl import RagServiceImpl
import json
import logging


logger = logging.getLogger(__name__)

class IdeaService:
    def __init__(self):
        self.idea_repository = IdeaRepository()
        self.rag_service = RagServiceImpl()

    """
    아이디어 생성 요청
    """
    async def create_idea(self, video: Video, channel: Channel):
        try:
            # 아이디어 분석 요청
            idea_results = await self.rag_service.analyze_idea(video, channel)

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