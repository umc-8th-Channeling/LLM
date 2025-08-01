from abc import ABC, abstractmethod


class RagService(ABC):

    @abstractmethod
    def summarize_video(self, video_id: str) -> str:
        """유튜브 영상 자막을 기반으로 10초 단위 개요를 작성"""
        pass
    
    @abstractmethod
    def analyze_algorithm_optimization(self, video_id: str) -> str:
        """유튜브 알고리즘 최적화 분석"""
        pass

    
    