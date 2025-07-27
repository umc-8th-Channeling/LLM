from enum import Enum


class SourceTypeEnum(str, Enum):
    """벡터 저장소 및 질문 템플릿의 소스 타입"""
    VIDEO_EVALUATION = "video_evaluation"
    VIDEO_SUMMARY = "video_summary"
    COMMENT_REACTION = "comment_reaction"
    VIEWER_ESCAPE_ANALYSIS = "viewer_escape_analysis"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    PERSONALIZED_KEYWORDS = "personalized_keywords"
    IDEA_RECOMMENDATION = "idea_recommendation"
