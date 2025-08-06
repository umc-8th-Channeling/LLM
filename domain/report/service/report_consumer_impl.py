
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

            # Report 정보 로그 출력
            logger.info(f"보고서 정보: {report}")

            # 연관된 Video 정보 로그 출력 (예: report.video)
            video_id = getattr(report, "video_id", None)
            if video_id:
                video = await video_repository.find_by_id(video_id)
                if video:
                    logger.info(f"연관된 비디오 정보: {video}")
                else:
                    logger.warning(f"video_id={video_id}에 해당하는 비디오가 없습니다.")
            else:
                logger.warning("report에 video_id가 없습니다.")
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
            print(f"일관성 : {concept}")
            print(f"seo : {seo}")
            print(f"재방문률 : {revisit}")
            print(f"조회수 : {video.view}")
            print(f"좋아요 : {video.like_count}")
            print(f"댓글 : {video.comment_count}")

            # 요약 정보 업데이트
            # report_repository.save({
            #     "id": report_id,
            #     # 영상 평가
            #     "like_count": video.like_count,
            #     "comment" : video.comment_count,
            #     "view" : video.view,
            #     "concept" : concept,
            #     "seo" : seo,
            #     "revisit" : revisit,
            #     # 영상 요약
            #     "summary": summary,
            #     # 댓글 반응
            # })

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

        # 키워드

        # -------------------------------------------------------------------------------

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
