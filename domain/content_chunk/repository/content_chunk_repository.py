from domain.content_chunk.model.content_chunk import ContentChunk
from core.database.repository.vector_repository import VectorRepository
from core.config.database_config import PGSessionLocal
from sqlalchemy import text

class ContentChunkRepository(VectorRepository[ContentChunk]):
    def model_class(self) -> type[ContentChunk]:
        """ContentChunk 모델 클래스를 반환합니다."""
        return ContentChunk

    async def exists_by_chunk_type_and_id(self, chunk_type: str, source_id: str) -> bool:
        async with PGSessionLocal() as session:
            query = text("""
                SELECT 1 FROM content_chunk
                WHERE source_id = :source_id
                AND meta ->> 'chunk_type' = :chunk_type
                LIMIT 1
            """)
            result = await session.execute(query, {"chunk_type": chunk_type, "source_id": source_id})
            row = result.fetchone()
            return row is not None
    