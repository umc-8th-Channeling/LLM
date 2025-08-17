
from fastapi import APIRouter
from pydantic import BaseModel
from core.config.kafka_config import KafkaConfig
from domain.channel.repository.channel_repository import ChannelRepository
from domain.idea.repository.idea_repository import IdeaRepository
from domain.task.model.task import Status
from core.kafka.message import Message
from core.kafka.message import Step
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
from domain.report.service.report_producer import ReportProducer
from core.kafka.kafka_broker import kafka_broker
from domain.video.repository.video_repository import VideoRepository
from external.rag.rag_service import RagService
from external.rag.rag_service_impl import RagServiceImpl
from response.api_response import ApiResponse
from response.code.status.success_status import SuccessStatus

from domain.video.service.video_service import VideoService

import logging

# Request Body Model
class CreateReportRequest(BaseModel):
    googleAccessToken: str

router = APIRouter(prefix="/reports", tags=["reports"])

report_repository = ReportRepository()
task_repository = TaskRepository()
kafka_config = KafkaConfig()
report_producer = ReportProducer(kafka_broker, kafka_config)

rag_service = RagServiceImpl()
logger = logging.getLogger(__name__)
video_repository = VideoRepository()
channel_repository = ChannelRepository()
idea_repository = IdeaRepository()

@router.post("")
async def create_report(video_id: int, request: CreateReportRequest):
    """
    리포트 생성을 시작합니다.
    parameters:
        video_id: int - 리포트에 대한 영상 ID
        request: CreateReportRequest - Google Access Token을 포함한 요청 body
    returns:
        task_id: int
    """
    # Google Access Token 로깅 (디버깅용)
    logger.info(f"Received Google Access Token: {request.googleAccessToken[:20]}...")  # 토큰의 일부만 로깅
    
    # report 생성
    report_data = {"video_id": video_id}
    report = await report_repository.save(data=report_data)
    print(f"Report created with ID: {report.id}")
    
    # task 생성
    task_data = {
        "report_id": report.id,
        "overview_status": Status.PENDING,
        "analysis_status": Status.PENDING,
        "idea_status": Status.PENDING
        }
    task = await task_repository.save(data=task_data)
    print(f"Task created with ID: {task.id}")

    # 메시지 생성
    overview_message= Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.overview,
        google_access_token=request.googleAccessToken
    )

    analysis_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.analysis,
        google_access_token=request.googleAccessToken
    )

    idea_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.idea
    )

    # 메시지 발행
    await report_producer.send_message("overview-topic", overview_message)
    await report_producer.send_message("analysis-topic", analysis_message)
    await report_producer.send_message("idea-topic", idea_message)

    return ApiResponse.on_success(SuccessStatus._OK, {"task_id": task.id})

