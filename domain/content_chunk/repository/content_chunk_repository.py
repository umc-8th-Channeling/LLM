from core.database.model.content_chunk import ContentChunk
from core.database.repository.vector_repository import VectorRepository

class ContentChunkRepository(VectorRepository[ContentChunk]):
    def model_class(self) -> type[ContentChunk]:
        """ContentChunk 모델 클래스를 반환합니다."""
        return ContentChunk

    
    