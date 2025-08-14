from typing import DefaultDict, List, Any
import logging
from domain.comment.model.comment import Comment
from domain.report.repository.report_repository import ReportRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from core.enums.source_type import SourceTypeEnum
from external.rag.rag_service_impl import RagServiceImpl
from domain.video.model.video import Video

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        self.report_repository = ReportRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.rag_service = RagServiceImpl()

    async def create_summary(self, video: Video, report_id: int) -> bool:
        """
        영상 요약을 생성하고 Vector DB와 MySQL에 저장
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 유튜브 영상 아이디 조회
            youtube_video_id = getattr(video, "youtube_video_id", None)
            if not youtube_video_id:
                logger.error("YouTube 영상 ID가 없습니다.")
                return False
            
            # 요약 생성
            summary = self.rag_service.summarize_video(youtube_video_id)
            logger.info("요약 결과:\n%s", summary)
            
            # 벡터 DB에 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.VIDEO_SUMMARY,
                source_id=report_id,
                context=summary
            )
            logger.info("요약 결과를 벡터 DB에 저장했습니다.")
            
            # MySQL에 저장
            await self.report_repository.save({
                "id": report_id,
                "summary": summary,
                "title": video.title
            })
            logger.info("요약 결과를 MYSQL DB에 저장했습니다.")
            
            return True
            
        except Exception as e:
            logger.error(f"요약 생성 중 오류 발생: {e}")
            return False

    async def update_report_emotion_counts(self, report_id: int, comment_dict:DefaultDict[str,List[Comment]]) -> bool:
        """
        성공 시 True, 실패 시 False를 반환합니다.
        """
        count_dict = {comment_type: len(comments) for comment_type, comments in comment_dict.items()}
        logger.info("댓글 개수를 MYSQL DB에 저장합니다.")
        return await self.report_repository.update_count(report_id, count_dict)