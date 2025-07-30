from fastapi import APIRouter
from core.config.kafka_config import KafkaConfig
from domain.video.service.video_service import VideoService
from domain.task.model.task import Status
from core.kafka.message import Message
from core.kafka.message import Step
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
from domain.report.service.report_producer import ReportProducer
from core.kafka.kafka_broker import kafka_broker
from domain.video.repository.video_repository import VideoRepository
from response.api_response import ApiResponse
from response.code.status.success_status import SuccessStatus

router = APIRouter(prefix="/reports", tags=["reports"])

report_repository = ReportRepository()
task_repository = TaskRepository()
kafka_config = KafkaConfig()
report_producer = ReportProducer(kafka_broker, kafka_config)


@router.post("")
async def create_report(video_id: int):
    """
    리포트 생성을 시작합니다.
    parameters:
        video_id: int - 리포트에 대한 영상 ID
    returns:
        task_id: int
    """
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
    overview_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.overview
    )

    analysis_message = Message(
        task_id=task.id,
        report_id=report.id,
        step=Step.analysis
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


@router.get("/test")
async def test(video_id: int):
    video_repository = VideoRepository()
    video = await video_repository.find_by_id(video_id)

    video_service = VideoService()
    print(await video_service.analyze_consistency(video))
    print(await video_service.analyze_seo(video))
    print(await video_service.analyze_revisit(video))

    return "ok"
