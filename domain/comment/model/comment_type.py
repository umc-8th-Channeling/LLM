from enum import Enum


class CommentType(str, Enum):
    ADVICE_OPINION = 'ADVICE_OPINION'
    NEGATIVE = 'NEGATIVE'
    NEUTRAL = 'NEUTRAL'
    POSITIVE = 'POSITIVE'
