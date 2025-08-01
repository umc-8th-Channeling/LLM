from typing import Any, Dict, Optional, Tuple
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.report.model.report import Report
from domain.report.service.report_consumer import ReportConsumer
from external.rag.rag_service_impl import RagServiceImpl
from domain.video.repository.video_repository import VideoRepository
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
import logging
import time
from core.enums.source_type import SourceTypeEnum

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
        logger.info(f"Handling analysis request")
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
        # TODO: 보고서 아이디어 처리 로직 구현
