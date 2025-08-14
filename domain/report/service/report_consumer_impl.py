
import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from core.enums.source_type import SourceTypeEnum
from domain.channel.repository.channel_repository import ChannelRepository
from domain.comment.service.comment_service import CommentService
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.idea.service.idea_service import IdeaService
from domain.report.repository.report_repository import ReportRepository
from domain.report.service.report_consumer import ReportConsumer
from domain.report.service.report_service import ReportService
from domain.task.model.task import Status
from domain.task.repository.task_repository import TaskRepository
from domain.trend_keyword.model.trend_keyword_type import TrendKeywordType
from domain.trend_keyword.repository.trend_keyword_repository import TrendKeywordRepository
from domain.video.repository.video_repository import VideoRepository
from domain.video.service.video_service import VideoService
from external.rag import leave_analyize
from external.rag.rag_service_impl import RagServiceImpl
from external.youtube.youtube_comment_service import YoutubeCommentService

logger = logging.getLogger(__name__)

class ReportConsumerImpl(ReportConsumer):
    def __init__(self, broker):
        super().__init__(broker)
        self.rag_service = RagServiceImpl()
        self.video_repository = VideoRepository()
        self.report_repository = ReportRepository()
        self.task_repository = TaskRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.channel_repository = ChannelRepository()
        self.comment_service = CommentService()
        self.report_service = ReportService()
        self.trend_keyword_repository = TrendKeywordRepository()
        self.idea_service = IdeaService()
        self.youtube_comment_service = YoutubeCommentService()
        self.video_service = VideoService()
 

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
                "summary": summary,
                "title": video.title
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
            token = message.get("google_access_token")
            avg_dic = await self.video_service.get_overview_rating(video, token)
            logger.info("영상 평가 정보:\n%s", avg_dic)

            # 요약 정보 업데이트
            await self.report_repository.save({
                "id": report_id,
                # 영상 평가
                "like_count": video.like_count,
                "like_channel_avg": avg_dic['like_category_avg'],
                "like_topic_avg": avg_dic['like_avg'],
                "comment" : video.comment_count,
                "comment_channel_avg": avg_dic['comment_category_avg'],
                "comment_topic_avg": avg_dic['comment_avg'],
                "view" : video.view,
                "view_channel_avg": avg_dic['view_avg'],
                "view_topic_avg": avg_dic['view_category_avg'],
                "concept" : avg_dic['concept'],
                "seo" : avg_dic['seo'],
                "revisit" : avg_dic['revisit'],
            })
            logger.info("수치 정보를 MYSQL DB에 저장했습니다.")

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
            
            # 구글 액세스 토큰 추출
            token = message.get("google_access_token")

            # analyze_leave 호출 전 video 객체 상태 로깅
            logger.info(f"[DEBUG] analyze_leave 호출 전 - video 객체 타입: {type(video)}")
            logger.info(f"[DEBUG] analyze_leave 호출 전 - video.id: {getattr(video, 'id', 'None')}")
            logger.info(f"[DEBUG] analyze_leave 호출 전 - video.youtube_video_id: {getattr(video, 'youtube_video_id', 'None')}")
            logger.info(f"[DEBUG] analyze_leave 호출 전 - video 전체 속성: {vars(video) if hasattr(video, '__dict__') else 'No __dict__'}")

            # 시청자 이탈 분석 (재시도 로직 포함)
            leave_result = None
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    logger.info(f"[DEBUG] leave_analyize.analyze_leave 함수 호출 시작 (시도 {retry_count + 1}/{max_retries})")
                    leave_result = await leave_analyize.analyze_leave(video, token)
                    logger.info(f"[DEBUG] leave_analyize.analyze_leave 함수 호출 성공")
                    logger.info(f"[DEBUG] leave_result 타입: {type(leave_result)}")
                    logger.info(f"[DEBUG] leave_result 내용: {leave_result}")
                    break  # 성공하면 루프 종료
                    
                except AttributeError as ae:
                    logger.error(f"[ERROR] analyze_leave AttributeError 발생: {ae}")
                    logger.error(f"[ERROR] AttributeError 상세: {ae.__class__.__name__}: {str(ae)}")
                    raise
                    
                except TypeError as te:
                    logger.error(f"[ERROR] analyze_leave TypeError 발생: {te}")
                    logger.error(f"[ERROR] TypeError 상세: {te.__class__.__name__}: {str(te)}")
                    raise
                    
                except KeyError as ke:
                    logger.error(f"[ERROR] analyze_leave KeyError 발생: {ke}")
                    logger.error(f"[ERROR] KeyError 상세: {ke.__class__.__name__}: {str(ke)}")
                    raise
                    
                except Exception as e:
                    error_type = e.__class__.__name__
                    logger.error(f"[ERROR] analyze_leave 오류 발생 (시도 {retry_count + 1}/{max_retries}): {e}")
                    logger.error(f"[ERROR] 오류 타입: {error_type}")
                    logger.error(f"[ERROR] 오류 상세: {str(e)}")
                    
                    # ConnectTimeout이나 네트워크 관련 에러인 경우 재시도
                    if error_type in ['ConnectTimeout', 'ReadTimeout', 'ConnectionError', 'TimeoutError']:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = retry_count * 5  # 5초, 10초, 15초 대기
                            logger.warning(f"[WARNING] 네트워크 타임아웃 발생. {wait_time}초 후 재시도합니다...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"[ERROR] 최대 재시도 횟수 {max_retries}회 초과")
                            import traceback
                            logger.error(f"[ERROR] 최종 스택 트레이스:\n{traceback.format_exc()}")
                            # 타임아웃 시 기본값 설정
                            leave_result = "시청자 이탈 분석 실패 (네트워크 타임아웃)"
                            logger.warning(f"[WARNING] 기본값으로 설정: {leave_result}")
                            break
                    else:
                        # 네트워크 에러가 아닌 경우 즉시 종료
                        import traceback
                        logger.error(f"[ERROR] 스택 트레이스:\n{traceback.format_exc()}")
                        raise
            
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
            analyze_opt = await self.rag_service.analyze_algorithm_optimization(video_id=video.youtube_video_id)
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
            # 트렌드 분석 및 키워드 저장 프로세스
            try:
                await self.report_service.analyze_trends_and_save(video, report_id)
            except Exception as e:
                logger.error(f"트렌드 분석 및 키워드 저장 프로세스 실패: {e!r}")
                raise
                
            # 채널 정보는 아이디어 서비스에서 필요하므로 조회
            channel_id = getattr(video, "channel_id", None)
            if not channel_id:
                logger.error("video에 channel_id가 없습니다.")
                return
                
            channel = await self.channel_repository.find_by_id(channel_id)
            if not channel:
                logger.warning(f"channel_id={channel_id}에 해당하는 채널이 없습니다.")
                return

            # 아이디어 생성 프로세스
            try:
                await self.idea_service.create_idea(video, channel, report_id)
            except Exception as e:
                logger.error(f"아이디어 생성 프로세스 실패: {e!r}")
                raise

            # task 업데이트
            task = await self.task_repository.find_by_id(message["task_id"])
            if task:
                await self.task_repository.save({
                    "id": task.id,
                    "idea_status": Status.COMPLETED
                })
                logger.info(f"Task ID {task.id}의 idea_status를 COMPLETED로 업데이트했습니다.")

        except Exception as e:
            pass
        
