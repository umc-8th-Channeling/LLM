from fastapi import APIRouter, HTTPException
from core.kafka.message import Message
from core.database.model.report import Report
from core.kafka.message import Step
from domain.report.repository.report_repository import ReportRepository
from domain.task.repository.task_repository import TaskRepository
from domain.report.service.report_producer import ReportProducer
from faststream.kafka import KafkaBroker
from core.config.kafka_config import KafkaConfig


router = APIRouter(prefix="/reports", tags=["reports"])

report_repository = ReportRepository()
task_repository = TaskRepository()
report_producer = ReportProducer(KafkaBroker, KafkaConfig)

@router.post("")
async def create_report(video_id: int) -> int:
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
    task_data = {"report_id": report.id}
    task = await task_repository.save(data=task_data)
    print(f"Task created with ID: {task.id}")

    # 메시지 생성
    overview_message= Message(
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
    report_producer.send_message("overview-topic", overview_message)
    report_producer.send_message("analysis-topic", analysis_message)
    report_producer.send_message("idea-topic", idea_message)

    # return task.id
    return None