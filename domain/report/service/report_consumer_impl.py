from typing import Any, Dict
from domain.report.service.report_consumer import ReportConsumer
import logging

logger = logging.getLogger(__name__)

class ReportConsumerImpl(ReportConsumer):
    async def handle_overview(self, message: Dict[str, Any]):
        """보고서 개요 요청 처리"""
        logger.info(f"Handling overview request")
        # TODO: 보고서 개요 처리 로직 구현

    async def handle_analysis(self, message: Dict[str, Any]):
        """보고서 분석 요청 처리"""
        logger.info(f"Handling analysis request")
        # TODO: 보고서 분석 처리 로직 구현


    async def handle_idea(self, message: Dict[str, Any]):
        """보고서 아이디어 요청 처리"""
        logger.info(f"Handling idea request")
        # TODO: 보고서 아이디어 처리 로직 구현
