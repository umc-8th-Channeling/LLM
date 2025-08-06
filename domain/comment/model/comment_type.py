from enum import Enum


class CommentType(str, Enum):
    ADVICE = 'advice'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'
    POSITIVE = 'positive'

    @staticmethod
    def from_emotion_code(code: int) -> "CommentType":
        mapping = {
            1: CommentType.POSITIVE,
            2: CommentType.NEGATIVE,
            3: CommentType.NEUTRAL,
            4: CommentType.ADVICE
        }
        return mapping.get(code, CommentType.NEUTRAL)  # 기본값 NEUTRAL
