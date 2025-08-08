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
        
        # CommentType enum과 DB 필드명 매핑
        field_mapping = {
            "ADVICE_OPINION": "advice_comment",
            "NEGATIVE": "negative_comment", 
            "NEUTRAL": "neutral_comment",
            "POSITIVE": "positive_comment"
        }
        
        for comment_type, count in count_dict.items():
            field_name = field_mapping.get(comment_type.value)
            if field_name:
                update_data[field_name] = count
        await self.save(update_data)
        return True
    

    
    