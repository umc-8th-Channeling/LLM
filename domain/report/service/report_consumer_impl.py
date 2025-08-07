
from typing import Any, Dict, Optional, Tuple
import time
import json
import logging

from domain.comment.service.comment_service import CommentService
from domain.channel.repository.channel_repository import ChannelRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.report.model.report import Report
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.service.report_consumer import ReportConsumer
from domain.report.service.report_service import ReportService
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service_impl import RagServiceImpl
from domain.video.service.video_service import VideoService
from external.rag import leave_analyize
from core.enums.source_type import SourceTypeEnum
from external.youtube.youtube_comment_service import YoutubeCommentService
from domain.task.model.task import Status
from domain.trend_keyword.repository.trend_keyword_repository import TrendKeywordRepository
from domain.trend_keyword.model.trend_keyword_type import TrendKeywordType

logger = logging.getLogger(__name__)

class ReportConsumerImpl(ReportConsumer):
    def __init__(self, broker):
        super().__init__(broker)
        self.rag_service = RagServiceImpl()
        self.video_repository = VideoRepository()
        self.report_repository = ReportRepository()
        self.task_repository = TaskRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.idea_repository = IdeaRepository()
        self.channel_repository = ChannelRepository()
        self.youtube_comment_service = YoutubeCommentService()
        self.comment_service = CommentService()
        self.report_service = ReportService()
        self.trend_keyword_repository = TrendKeywordRepository()
 

    async def _get_report_and_video(self, message: Dict[str, Any]) -> Optional[Tuple[Any, Any]]:
        """
        메시지에서 report_id를 추출하고 report와 video 정보를 조회하는 공통 메서드
        
        Args:
            message: 처리할 메시지
            
        Returns:
            성공 시 (report, video) 튜플, 실패 시 None
        """
        logger.info(f"받은 메시지 내용: {message}")

        report_id = message.get("report_id")
        if report_id is None:
            logger.error("report_id가 메시지에 없습니다")
            return None

        report = await self.report_repository.find_by_id(report_id)
        if not report:
            logger.warning(f"report_id={report_id}에 해당하는 보고서가 없습니다.")
            return None

        # Report 정보 로그 출력
        logger.info(f"보고서 정보: {report}")

        # 연관된 Video 정보 로그 출력
        video_id = getattr(report, "video_id", None)
        video = None
        if video_id:
            video = await self.video_repository.find_by_id(video_id)
            if video:
                logger.info(f"연관된 비디오 정보: {video}")
            else:
                logger.warning(f"video_id={video_id}에 해당하는 비디오가 없습니다.")
        else:
            logger.warning("report에 video_id가 없습니다.")
            
        return report, video


    async def handle_overview(self, message: Dict[str, Any]):
        logger.info(f"Handling overview request")

        start_time = time.time()  # 시작 시간 기록

        try:
            # 공통 메서드로 report와 video 정보 조회
            result = await self._get_report_and_video(message)
            if not result:
                return

            report, video = result
            report_id = report.id
            video_id = video.id    

            
            # 여기 부터 rag 시작
            # 유튜브 영상 아이디 조회
            youtube_video_id = getattr(video, "youtube_video_id", None)
            
            #요약 결과 조회
            summary = self.rag_service.summarize_video(youtube_video_id)

            # 요약 결과만 출력
            logger.info("요약 결과:\n%s", summary)     

            # 벡터 db에 저장       
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.VIDEO_SUMMARY,
                source_id=report_id,
                context=summary
            )
            logger.info("요약 결과를 벡터 DB에 저장했습니다.")

            # 요약 정보 업데이트
            await self.report_repository.save({
                "id": report_id,
                "summary": summary
            })
            logger.info("요약 결과를 MYSQL DB에 저장했습니다.")

            #---------------------------------------------------------------------------------------

            # 댓글 정보 조회
            comments_by_youtube = await self.youtube_comment_service.get_comments(youtube_video_id, report_id)
            comments_obj = await self.comment_service.convert_to_comment_objects(comments_by_youtube)
            result = await self.comment_service.gather_classified_comments(comments_obj)
            summarized_comments = await self.comment_service.summarize_comments_by_emotions_with_llm(result)
            await self.report_service.update_report_emotion_counts(report_id, summarized_comments)

            # 수치 정보 조회
            video_service = VideoService()
            concept = await video_service.analyze_consistency(video)
            seo = await video_service.analyze_seo(video)
            revisit = await video_service.analyze_revisit(video)
            logger.info(f"일관성 : {concept}")
            logger.info(f"seo : {seo}")
            logger.info(f"재방문률 : {revisit}")
            logger.info(f"조회수 : {video.view}")
            logger.info(f"좋아요 : {video.like_count}")
            logger.info(f"댓글 : {video.comment_count}")

            # 요약 정보 업데이트
            await self.report_repository.save({
                "id": report_id,
                # 영상 평가
                "like_count": video.like_count,
                "comment" : video.comment_count,
                "view" : video.view,
                "concept" : concept,
                "seo" : seo,
                "revisit" : revisit,
            })
            logger.info("보고서 정보를 MYSQL DB에 저장했습니다.")

            # task 정보 업데이트
            task = await self.task_repository.find_by_id(message["task_id"])
            if task:
                await self.task_repository.save({
                    "id": task.id,
                    "overview_status": Status.COMPLETED
                })
                logger.info(f"Task ID {task.id}의 overview_status를 COMPLETED로 업데이트했습니다.")

        except Exception as e:
            logger.error(f"handle_overview 처리 중 오류 발생: {e}")
        finally:
            end_time = time.time()  # 종료 시간 기록
            elapsed_time = end_time - start_time
            logger.info(f"handle_overview 전체 처리 시간: {elapsed_time:.3f}초")

        

    async def handle_analysis(self, message: Dict[str, Any]):
        """보고서 분석 요청 처리"""
        logger.info(f"Handling analysis request")
        start_time = time.time()  # 시작 시간 기록
        
        try:
            # 공통 메서드로 report와 video 정보 조회
            result = await self._get_report_and_video(message)
            if not result:
                return
            
            report, video = result

            # 시청자 이탈 분석
            leave_result = await leave_analyize.analyze_leave(video)
            logger.info(f"시청자 이탈 분석 결과: {leave_result}")

            # 벡터 DB에 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS,
                source_id=report.id,
                context=leave_result
            )
            logger.info("시청자 이탈 분석 결과를 벡터 DB에 저장했습니다.")

            # report 업데이트
            await self.report_repository.save({
                "id": report.id,
                "leave_analyze": leave_result
            })
            logger.info("시청자 이탈 분석 결과를 MYSQL DB에 저장했습니다.")

            #-------------------------------------------------------------------------------------

            # 알고리즘 최적화 방안 분석
            analyze_opt = self.rag_service.analyze_algorithm_optimization(video_id=video.youtube_video_id)
            logger.info("알고리즘 최적화 분석 결과:\n%s", analyze_opt)

            # 벡터 DB에 저장
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.ALGORITHM_OPTIMIZATION,
                source_id=report.id,
                context=analyze_opt
            )
            logger.info("알고리즘 최적화 분석 결과를 벡터 DB에 저장했습니다.")

            # report 업데이트
            await self.report_repository.save({
                "id": report.id,
                "optimization": analyze_opt
            })
            logger.info("알고리즘 최적화 분석 결과를 MYSQL DB에 저장했습니다.")

            # task 업데이트
            task = await self.task_repository.find_by_id(message["task_id"])
            if task:
                await self.task_repository.save({
                    "id": task.id,
                    "analysis_status": Status.COMPLETED
                })
                logger.info(f"Task ID {task.id}의 analysis_status를 COMPLETED로 업데이트했습니다.")

        except Exception as e:
            logger.error(f"handle_analysis 처리 중 오류 발생: {e}")
        finally:
            end_time = time.time()  # 종료 시간 기록
            elapsed_time = end_time - start_time
            logger.info(f"handle_analysis 전체 처리 시간: {elapsed_time:.3f}초")


    async def handle_idea(self, message: Dict[str, Any]):
        """보고서 아이디어 요청 처리"""
        logger.info(f"Handling idea request")
        try:
            # 공통 메서드로 report와 video 정보 조회
            result = await self._get_report_and_video(message)
            if not result:
                return
            report, video = result
            report_id = report.id
             # 실시간 트렌드 키워드 분석
            realtime_keyword= self.rag_service.analyze_realtime_trends()

            logger.info(f"실시간 트렌드 키워드 분석 결과: {realtime_keyword}")

            # Video에서 channel_id 가져오기
            channel_id = getattr(video, "channel_id", None)
            if not channel_id:
                logger.error("video에 channel_id가 없습니다.")
                return
                
            # Channel 정보 조회
            channel = await self.channel_repository.find_by_id(channel_id)
            if not channel:
                logger.warning(f"channel_id={channel_id}에 해당하는 채널이 없습니다.")
                return
            
            logger.info(f"연관된 채널 정보: {channel}")
            
            # 채널 정보를 사용하여 트렌드 분석
            channel_concept = getattr(channel, "concept", "")
            target_audience = getattr(channel, "target", "")
            
            channel_keyword = self.rag_service.analyze_channel_trends(
                channel_concept=channel_concept,
                target_audience=target_audience
            )
            logger.info(f"채널 컨셉 : {channel_concept}")
            logger.info(f"타겟 시청자 : {target_audience}")
            logger.info(f"채널 맞춤형 키워드 분석 결과: {channel_keyword}")

            # 벡터 db에 저장(채널 맞춤형 키워드만 저장)
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.PERSONALIZED_KEYWORDS,
                source_id=report_id,
                context=json.dumps(channel_keyword, ensure_ascii=False)
            )
            logger.info("채널 맞춤형 키워드를 벡터 DB에 저장했습니다.")
            
            
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
                
                # 일괄 저장
                saved_realtime = await self.trend_keyword_repository.save_bulk(realtime_keywords_to_save)
                logger.info(f"{len(saved_realtime)}개의 실시간 트렌드 키워드를 MySQL에 저장했습니다.")
            
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
                
                # 일괄 저장
                saved_channel = await self.trend_keyword_repository.save_bulk(channel_keywords_to_save)
                logger.info(f"{len(saved_channel)}개의 채널 맞춤형 키워드를 MySQL에 저장했습니다.")
        
        except Exception as e:
            logger.error(f"handle_idea 처리 중 오류 발생: {e}")


        # 메시지에서 video_id 추출 TODO 예외처리
        report = await self.report_repository.find_by_id(message["report_id"])
        video = await self.video_repository.find_by_id(report.video_id)
        channel = await self.channel_repository.find_by_id(video.channel_id)

        # 아이디어 분석 요청
        idea_results = await self.rag_service.analyze_idea(video, channel)

        logger.info(f"아이디어 분석 결과: {idea_results}")

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
        logger.info("아이디어 분석 결과를 MYSQL DB에 저장했습니다.")

        # task 업데이트
        task = await self.task_repository.find_by_id(message["task_id"])
        if task:
            await self.task_repository.save({
                "id": task.id,
                "idea_status": Status.COMPLETED
            })
            logger.info(f"Task ID {task.id}의 idea_status를 COMPLETED로 업데이트했습니다.")
