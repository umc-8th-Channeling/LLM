from abc import ABC, abstractmethod
from typing import Any, Dict, List
from domain.video.model.video import Video
from domain.channel.model.channel import Channel


class RagService(ABC):
    """RAG 서비스 추상 클래스"""
    
    @abstractmethod
    def summarize_video(self, video_id: str) -> str:
        """비디오 요약"""
        pass
    
    @abstractmethod
    def classify_comment(self, comment: str) -> Dict[str, Any]:
        """댓글 감정 분류"""
        pass
    
    @abstractmethod
    def summarize_comments(self, comments: str) -> List[str]:
        """댓글 요약"""
        pass
    
    @abstractmethod
    async def analyze_idea(self, video: Video, channel: Channel) -> List[Dict[str, Any]]:
        """아이디어 분석"""
        pass
    
    @abstractmethod
    def analyze_algorithm_optimization(self, video_id: str) -> str:
        """알고리즘 최적화 분석"""
        pass

    @abstractmethod
    def execute_llm_chain(self, context: str, query: str, prompt_template: str) -> str:
        """LLM 체인 실행"""
        pass

    @abstractmethod
    def execute_llm_direct(self, prompt: str) -> str:
        """LLM 직접 실행"""
        pass