from core.database.repository.crud_repository import CRUDRepository
from domain.trend_keyword.model.trend_keyword import TrendKeyword


class TrendKeywordRepository(CRUDRepository):
    def model_class(self) -> type["TrendKeyword"]:
        return TrendKeyword
    