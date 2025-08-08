from enum import Enum

class AvgType(Enum):
    VIEW_AVG = "view_avg",
    VIEW_CATEGORY_AVG = "view_category_avg",
    LIKE_AVG = "like_avg",
    LIKE_CATEGORY_AVG = "like_category_avg",
    COMMENT_AVG = "comment_avg",
    COMMENT_CATEGORY_AVG = "comment_category_avg",
