from typing import DefaultDict, List, Any
import logging
import asyncio
from domain.comment.model.comment import Comment
from domain.report.repository.report_repository import ReportRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from core.enums.source_type import SourceTypeEnum
from external.rag.rag_service_impl import RagServiceImpl
from external.rag import leave_analyize
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
            raise

    async def analyze_viewer_retention(self, video: Video, report_id: int, token: str) -> bool:
        """
        시청자 이탈 분석 (재시도 로직 포함)
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            token: Google 액세스 토큰
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            leave_result = None
            max_retries = 3
            retry_count = 0
            
            # 재시도 로직
            while retry_count < max_retries:
                try:
                    leave_result = await leave_analyize.analyze_leave(video, token)
                    break  # 성공하면 루프 종료
                    
                except (AttributeError, TypeError, KeyError):
                    # 즉시 실패해야 하는 에러들
                    raise
                    
                except Exception as e:
                    error_type = e.__class__.__name__
                    
                    # 네트워크 관련 에러인 경우 재시도
                    if error_type in ['ConnectTimeout', 'ReadTimeout', 'ConnectionError', 'TimeoutError']:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = retry_count * 5  # 지수 백오프
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # 최대 재시도 초과시 기본값 설정
                            leave_result = "시청자 이탈 분석 실패 (네트워크 타임아웃)"
                            break
                    else:
                        # 네트워크 에러가 아닌 경우 즉시 종료
                        raise
            
            # Vector DB에 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS,
                source_id=report_id,
                context=leave_result
            )
            
            # MySQL에 저장
            await self.report_repository.save({
                "id": report_id,
                "leave_analyze": leave_result
            })
            
            return True
            
        except Exception as e:
            raise

    async def analyze_optimization(self, video: Video, report_id: int) -> bool:
        """
        알고리즘 최적화 분석
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 알고리즘 최적화 분석
            analyze_opt = await self.rag_service.analyze_algorithm_optimization(video_id=video.youtube_video_id)
            
            # Vector DB에 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.ALGORITHM_OPTIMIZATION,
                source_id=report_id,
                context=analyze_opt
            )
            
            # MySQL에 저장
            await self.report_repository.save({
                "id": report_id,
                "optimization": analyze_opt
            })
            
            return True
            
        except Exception as e:
            raise

    async def update_report_emotion_counts(self, report_id: int, comment_dict:DefaultDict[str,List[Comment]]) -> bool:
        """
        성공 시 True, 실패 시 False를 반환합니다.
        """
        count_dict = {comment_type: len(comments) for comment_type, comments in comment_dict.items()}
        logger.info("댓글 개수를 MYSQL DB에 저장합니다.")
        return await self.report_repository.update_count(report_id, count_dict)