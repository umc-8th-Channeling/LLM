from abc import ABC, abstractmethod
from typing import Dict, TypeVar, Generic, Any, Optional, List
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from core.config.database_config import PGSessionLocal
from sqlmodel import SQLModel
from sqlalchemy import text
from core.database.model.content_chunk import ContentChunk
from core.database.model.question_template import QuestionTemplate

load_dotenv()

T = TypeVar("T", bound=SQLModel)
"""
예상 사용 예시:
---데이터 저장할 때---
1. 추후에 context로 제공할 텍스트 정보를 받아옴
(ex. 채널 정보, 이전 추천 아이디어, 영상 요약, 시청 최적화 전략, 이탈 분석)
* 단순히 이전 리포트의 정보만 쓸거면, 리포트 하나 생성 후에 각 요소마다 source_type만 다르게 해서 저장하는 것도 괜찮아 보임!
2. content_chunk_repository.save_context(source_type: idea, source_id: 1,  context: 후쿠오카에서 꼭 가야할 맛집) 호출
3. 알아서 텍스트 청크로 나누고, 임베딩 생성 후 벡터 저장소에 저장

---검색할 때---
1. content_chunk_repository.search_similar(source_type: idea, limit=5) 호출
2. 유사한 청크들을 반환받음
3. 청크들을 context로 추가해서 llm에 전달
* 예시로는 채널에 대한 아이디어를 생성할 때, 이전에 저장된 아이디어들을 참고할 수 있음
* source_type만으로는 필터링하기 힘들 경우, metadata를 활용해서 추가 필터링 가능
"""
class VectorRepository(Generic[T], ABC):
    """벡터 저장소를 위한 추상 클래스입니다."""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-large"

    @abstractmethod
    def model_class(self) -> type[T]:
        """서브클래스에서 구체적인 모델 클래스를 반환해야 함"""
        pass
    
    async def generate_embedding(self, text: str) -> List[float]:
        """OpenAI API를 사용해서 텍스트(청크)의 임베딩 생성"""
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def chunk_text(self, text: str, chunk_size: int = 50, overlap: int = 10) -> List[str]:
        """텍스트를 청크로 분할"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            # 의미 없는 공백은 저장 skip
            if chunk.strip():
                chunks.append(chunk)
            
            start = end - overlap
            
        return chunks

    
    async def save_context(self, source_type: str, source_id: int, context: str, metadata: Dict[str, any] = None):
        """
        컨텍스트를 벡터 저장소에 저장
        parameters:
            source_type: str - 'video_info', 'channel_data', 'report' 등(이걸 뭐로 할 지 잘 모르겠음..)
            source_id: int - 해당 소스의 ID (예: video_id, channel_id, report_id 등)
            context: str - 저장할 텍스트 컨텍스트
            metadata: Dict[str, Any] - 추가 메타데이터 (선택적)
        """
        chunks = self.chunk_text(context)
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embedding(chunk)
            content_chunk = ContentChunk(
                source_type=source_type,
                source_id=source_id,
                content=chunk,
                chunk_index=i,
                embedding=embedding,
                metadata=metadata
            )
            # 벡터 저장소에 청크 저장
            await self.model_class.save(content_chunk)
            # 예시로 print문 사용
            print(f"Saved chunk {i} with embedding: {embedding}")


    async def search_similar(self, source_type: str, metadata: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        source_type에 해당하는 question_template의 임베딩을 기준으로
        같은 source_type을 가진 content_chunks 중 가장 유사한 것들을 검색
        
        parameters:
            source_type: str - 'video_info', 'channel_data', 'report' 등
            metadata: Dict[str, Any] - 추가 필터링을 위한 메타데이터 (선택적)
            limit: int - 검색할 최대 결과 수
        returns:
            List[Dict[str, Any]] - 유사도 순으로 정렬된 청크 목록
        """
        
        
        async with PGSessionLocal() as session:
            # 1. template_key로 question_template의 임베딩 가져오기
            template_query = text("""
                SELECT embedding, template_key
                FROM question_template
                WHERE template_key = :template_key
                LIMIT 1
            """)
            
            template_result = await session.execute(
                template_query, 
                {"template_key": source_type}
            )
            template_row = template_result.fetchone()
            
            if not template_row:
                return []
            
            template_embedding = template_row.embedding
            
            
            # 2. 해당 source_type의 content_chunks 중 가장 유사한 것들 검색
            search_query = text("""
                SELECT 
                    c.id,
                    c.source_type,
                    c.source_id,
                    c.content,
                    c.chunk_index,
                    c.metadata,
                    c.created_at,
                    1 - (c.embedding <=> :template_embedding) as similarity
                FROM content_chunks c
                WHERE c.source_type = :source_type
                ORDER BY c.embedding <=> :template_embedding
                LIMIT :limit
            """)
            
            result = await session.execute(
                search_query,
                {
                    "template_embedding": template_embedding,
                    "source_type": source_type,
                    "limit": limit
                }
            )
            
            chunks = []
            for row in result:
                chunks.append({
                    "id": row.id,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "content": row.content,
                    "chunk_index": row.chunk_index,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                    "similarity": row.similarity
                })
            
            return chunks
    
    
