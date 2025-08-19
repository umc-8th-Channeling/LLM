
from abc import abstractmethod
from typing import Dict, Any
from core.kafka.base_consumer import BaseConsumer

"""
뭐를 벡터db에 저장할 지는 아직 명확하지 않습니다.
일단 리포트 만드는 김에 db에 저장하고, 다음 리포트 생성 때 context로 활용해서 결과를 보고 어떤 걸 저장할 지 확실히 정하는 것이 좋을 것 같습니다.
"""
class ReportConsumer(BaseConsumer):
    
    # @abstractmethod
    async def handle_overview(self, message: Dict[str, Any]):
        """보고서 개요 요청 처리"""
        # TODO: 영상 평가 저장
        """
        1. youtube api에서 정보 가져오기
        2. 별도 처리 필요한 지표(SEO, 재방문율) 계산(수식 or llm)
        3. 모든 지표 report에 저장 report_repository.save() 호출
        4. 다음 분석을 위해 벡터 db에 저장
        """
        # TODO: 영상 요약 저장
        """
        1. transcrpt api에서 영상 자막 가져오기
        2. llm을 사용해서 요약 생성
        3. 요약을 report에 저장 report_repository.save() 호출
        4. 다음 분석을 위해 벡터 db에 저장
        """
        # TODO: 댓글 반응 저장
        """
        1. youtube api에서 댓글 정보 가져오기
        2. llm을 사용해서 댓글 요약 생성
        3. 모든 지표 report에 저장 report_repository.save() 호출
        4. 다음 분석을 위해 벡터 db에 저장
        """
        pass
    
    # @abstractmethod
    async def handle_analysis(self, message: Dict[str, Any]):
        """보고서 분석 요청 처리"""
        pass
    
    # @abstractmethod
    async def handle_idea(self, message: Dict[str, Any]):
        """보고서 아이디어 요청 처리"""
        pass