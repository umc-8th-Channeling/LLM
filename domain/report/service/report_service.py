from typing import DefaultDict, List, Any
import logging
import json
import asyncio
from domain.comment.model.comment import Comment
from domain.report.repository.report_repository import ReportRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.trend_keyword.repository.trend_keyword_repository import TrendKeywordRepository
from domain.trend_keyword.model.trend_keyword_type import TrendKeywordType
from domain.channel.repository.channel_repository import ChannelRepository
from domain.video.model.video import Video
from domain.channel.model.channel import Channel
from core.enums.source_type import SourceTypeEnum
from external.rag.rag_service_impl import RagServiceImpl
from external.rag import leave_analyize

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        self.report_repository = ReportRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.trend_keyword_repository = TrendKeywordRepository()
        self.channel_repository = ChannelRepository()
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

    async def analyze_trends_and_save(self, video: Video, report_id: int) -> bool:
        """
        트렌드 분석 및 키워드 저장
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 1. 실시간 트렌드 분석
            realtime_keyword = self.rag_service.analyze_realtime_trends()
            
            # 2. 채널 정보 조회
            channel_id = getattr(video, "channel_id", None)
            if not channel_id:
                raise ValueError("video에 channel_id가 없습니다.")
                
            channel = await self.channel_repository.find_by_id(channel_id)
            if not channel:
                raise ValueError(f"channel_id={channel_id}에 해당하는 채널이 없습니다.")
            
            # 3. 채널 맞춤형 트렌드 분석
            channel_concept = getattr(channel, "concept", "")
            target_audience = getattr(channel, "target", "")
            
            channel_keyword = self.rag_service.analyze_channel_trends(
                channel_concept=channel_concept,
                target_audience=target_audience
            )
            
            # 4. Vector DB에 채널 맞춤형 키워드 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.PERSONALIZED_KEYWORDS,
                source_id=report_id,
                context=json.dumps(channel_keyword, ensure_ascii=False)
            )
            logger.info("채널 맞춤형 키워드를 Vector DB에 저장했습니다.")
            
            # 5. MySQL에 키워드 저장
            # 실시간 트렌드 키워드 저장
            if realtime_keyword and "trends" in realtime_keyword:
                realtime_keywords_to_save = []
                for keyword_data in realtime_keyword["trends"]:
                    trend_keyword = {
                        "report_id": report_id,
                        "keyword_type": TrendKeywordType.REAL_TIME,
                        "keyword": keyword_data.get("keyword", ""),
                        "score": keyword_data.get("score", 0)
                    }
                    realtime_keywords_to_save.append(trend_keyword)
                
                await self.trend_keyword_repository.save_bulk(realtime_keywords_to_save)
                logger.info("실시간 트렌드 키워드를 MySQL DB에 저장했습니다.")

            # 채널 맞춤형 키워드 저장
            if channel_keyword and "customized_trends" in channel_keyword:
                channel_keywords_to_save = []
                for keyword_data in channel_keyword["customized_trends"]:
                    trend_keyword = {
                        "report_id": report_id,
                        "keyword_type": TrendKeywordType.CHANNEL,
                        "keyword": keyword_data.get("keyword", ""),
                        "score": keyword_data.get("score", 0)
                    }
                    channel_keywords_to_save.append(trend_keyword)
                
                await self.trend_keyword_repository.save_bulk(channel_keywords_to_save)
                logger.info("채널 맞춤형 키워드를 MySQL DB에 저장했습니다.")
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