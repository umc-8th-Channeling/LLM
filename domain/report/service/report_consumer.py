
from abc import abstractmethod
from typing import Dict, Any
from core.kafka.base_consumer import BaseConsumer


class ReportConsumer(BaseConsumer):
    
    @abstractmethod
    async def handle_overview(self, message: Dict[str, Any]):
        """보고서 개요 요청 처리"""
        pass
    
    @abstractmethod
    async def handle_analysis(self, message: Dict[str, Any]):
        """보고서 분석 요청 처리"""
        pass
    
    @abstractmethod
    async def handle_idea(self, message: Dict[str, Any]):
        """보고서 아이디어 요청 처리"""
        pass