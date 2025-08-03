from domain.report.model.report import Report
from core.database.repository.crud_repository import CRUDRepository

class ReportRepository(CRUDRepository[Report]):
    def model_class(self) -> type[Report]:
        """Report 모델 클래스를 반환합니다."""
        return Report

    async def update_count(self, report_id, count_dict):
        report = await self.find_by_id(report_id)
        if not report:
            return False
        for comment_type, count in count_dict.items():
            setattr(report, f"{comment_type.value}_comment", count)
        await self.save(report.dict())
        return True
    

    
    