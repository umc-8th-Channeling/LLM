from domain.question_template.model.question_template import QuestionTemplate
from core.database.repository.vector_repository import VectorRepository
from typing import Dict, Any, List
from core.config.database_config import PGSessionLocal
class QuestionTemplateRepository(VectorRepository[QuestionTemplate]):
    """질문 템플릿을 위한 벡터 저장소 클래스입니다."""

    def model_class(self) -> type[QuestionTemplate]:
        return QuestionTemplate
    
    async def save_question_template(self, data: Dict[str, Any]) -> QuestionTemplate:
        """
        QuestionTemplate 저장 (텍스트를 임베딩으로 변환 후 저장)
        
        data: Dict[str, Any] - 저장할 데이터
            필수: source_type, question_text
            선택: metadata
        """
        # 임베딩 생성 (await 추가)
        embedding = await self.generate_embedding(data["question_text"])
        
        # 데이터에 임베딩 추가
        data_with_embedding = {**data, "embedding": embedding}
        
        async with PGSessionLocal() as session:
            instance = QuestionTemplate(**data_with_embedding)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance