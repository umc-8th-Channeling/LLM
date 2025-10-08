from fastapi import APIRouter
import logging
from external.rag.rag_service_impl import RagServiceImpl
from domain.trend_keyword.repository.trend_keyword_repository import TrendKeywordRepository

from domain.trend_keyword.model.trend_keyword_type import TrendKeywordType


logger = logging.getLogger(__name__)

trend_keyword_repository = TrendKeywordRepository()

rag_service = RagServiceImpl()
router = APIRouter(prefix="/trend-keywords", tags=["trend-keywords"])

@router.post("")
async def create_report():
    realtime_keyword = rag_service.analyze_realtime_trends()
    # 실시간 트렌드 키워드 저장
    if realtime_keyword and "trends" in realtime_keyword:
        realtime_keywords_to_save = []
        for keyword_data in realtime_keyword["trends"]:
            trend_keyword = {
                "channel_id":  None,
                "keyword_type": TrendKeywordType.REAL_TIME,
                "keyword": keyword_data.get("keyword", ""),
                "score": keyword_data.get("score", 0)
            }
            realtime_keywords_to_save.append(trend_keyword)
        
        await trend_keyword_repository.save_bulk(realtime_keywords_to_save)
        logger.info("실시간 트렌드 키워드를 MySQL DB에 저장했습니다.")
    return {"message": "ok"}