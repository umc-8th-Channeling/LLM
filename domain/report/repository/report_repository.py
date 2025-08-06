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
        update_data = {"id": report_id}
        for comment_type, count in count_dict.items():
            update_data[f"{comment_type.value}_comment"] = count
        await self.save(update_data)
        return True
    

    
    