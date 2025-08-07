from enum import Enum


class CommentType(str, Enum):
    ADVICE = 'ADVICE_OPINION'
    NEGATIVE = 'NEGATIVE'
    NEUTRAL = 'NEUTRAL'
    POSITIVE = 'POSITIVE'

    @staticmethod
    def from_emotion_code(code: int) -> "CommentType":
        mapping = {
            1: CommentType.POSITIVE,
            2: CommentType.NEGATIVE,
            3: CommentType.NEUTRAL,
            4: CommentType.ADVICE
        }
        return mapping.get(code, CommentType.NEUTRAL)  # 기본값 NEUTRAL
