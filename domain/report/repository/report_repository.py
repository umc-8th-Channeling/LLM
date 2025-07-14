from core.database.model.report import Report
from core.database.repository.crud_repository import CRUDRepository

class ReportRepository(CRUDRepository):
    def model_class(self) -> type[Report]:
        """Report 모델 클래스를 반환합니다."""
        return Report
    
    
    
    