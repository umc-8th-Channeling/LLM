
from typing import Any, Dict, Optional, Tuple
from typing import Any, Dict
import time
import json
import logging

from domain.comment.service.comment_service import CommentService
from domain.channel.repository.channel_repository import ChannelRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.report.model.report import Report
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.service.report_consumer import ReportConsumer
from external.rag.rag_service_impl import RagServiceImpl
from domain.video.repository.video_repository import VideoRepository
from typing import Any, Dict
import time
import json
import logging

from domain.comment.service.comment_service import CommentService
from domain.channel.repository.channel_repository import ChannelRepository
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.idea.repository.idea_repository import IdeaRepository
from domain.report.service.report_consumer import ReportConsumer
from domain.report.service.report_service import ReportService
>>>>>>> develop
from domain.report.service.report_service import ReportService
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service import RagService

from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service import RagService

from external.rag import leave_analyize
import logging
import time
from core.enums.source_type import SourceTypeEnum
from external.youtube.youtube_comment_service import YoutubeCommentService


video_repository = VideoRepository()
report_repository = ReportRepository()
task_repository = TaskRepository()
idea_repository = IdeaRepository()
channel_repository = ChannelRepository()
content_chunk_repository = ContentChunkRepository()

rag_service = RagService()
youtubecommentservice = YoutubeCommentService()
comment_service = CommentService()
report_service = ReportService()

logger = logging.getLogger(__name__)

class ReportConsumerImpl(ReportConsumer):


    rag_service = RagServiceImpl()
    video_repository = VideoRepository()
    report_repository = ReportRepository()
    task_repository = TaskRepository()
    content_chunk_repository = ContentChunkRepository()
    
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

            report = await report_repository.find_by_id(report_id)
            if not report:
                logger.warning(f"report_id={report_id}에 해당하는 보고서가 없습니다.")
                return

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
            summary = rag_service.summarize_video(youtube_video_id)

            # 요약 결과만 출력
            logger.info("요약 결과:\n%s", summary)     

            # 벡터 db에 저장       
            await content_chunk_repository.save_context(
                source_type=SourceTypeEnum.VIDEO_SUMMARY,
                source_id=report_id,
                context=summary
            )
            logger.info("요약 결과를 벡터 DB에 저장했습니다.")

            # 댓글 정보 조회 
            # 수치 정보 조회
						
            # 요약 정보 업데이트
            ReportRepository.save({
                  "id": report_id,  
                  "summary": summary
                   
            })
            
            # task 정보 업데이트
            
            

        except Exception as e:
            logger.error(f"handle_overview 처리 중 오류 발생: {e}")
        finally:
            end_time = time.time()  # 종료 시간 기록
            elapsed_time = end_time - start_time
            logger.info(f"handle_overview 전체 처리 시간: {elapsed_time:.3f}초")

        

    async def handle_analysis(self, message: Dict[str, Any]):
        """보고서 분석 요청 처리"""
        report_id = message.get("report_id")
        if report_id is None:
            logger.error("report_id가 메시지에 없습니다")
            return

        report = await self.report_repository.find_by_id(report_id)
        if not report:
            logger.warning(f"report_id={report_id}에 해당하는 보고서가 없습니다.")
            return

        # Report 정보 로그 출력
        logger.info(f"보고서 정보: {report}")

        # 연관된 Video 정보 로그 출력 (예: report.video)
        video_id = getattr(report, "video_id", None)
        print("videoID : ", video_id)
        if video_id:
            video = await self.video_repository.find_by_id(video_id)
            if video:
                logger.info(f"연관된 비디오 정보: {video}")
            else:
                logger.warning(f"video_id={video_id}에 해당하는 비디오가 없습니다.")
        else:
            logger.warning("report에 video_id가 없습니다.")

        result = await leave_analyize.analyze_leave(video)

        print("시청자 이탈 분석 : ", result)

        logger.info(f"Handling analysis request")

        
        end_time = time.time()  # 종료 시간 기록
        elapsed_time = end_time - start_time
        logger.info(f"시청자 이탈 분석 전체 처리 시간: {elapsed_time:.3f}초")
        # TODO: 보고서 분석 처리 로직 구현
        try:
            # 공통 메서드로 report와 video 정보 조회
            result = await self._get_report_and_video(message)
            if not result:
                return
            
            report, video = result
            
            # TODO: 시청자 이탈 분석


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
            # await self.report_repository.save(
            #     Report(
            #         id=report.id, 
            #         optimization=analyze_opt
            #     )
            # )
        except Exception as e:
            logger.error(f"handle_analysis 처리 중 오류 발생: {e}")


    async def handle_idea(self, message: Dict[str, Any]):
        """보고서 아이디어 요청 처리"""
        logger.info(f"Handling idea request")

        # 메시지에서 video_id 추출 TODO 예외처리
        report = await report_repository.find_by_id(message["report_id"])
        video = await video_repository.find_by_id(report.video_id)
        channel = await channel_repository.find_by_id(video.channel_id)

        # 아이디어 분석 요청
        idea_results = await rag_service.analyze_idea(video, channel)

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

        await idea_repository.save_bulk(ideas)


