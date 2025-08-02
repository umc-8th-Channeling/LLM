import logging

from core.enums.source_type import SourceTypeEnum
from domain.channel.model.channel import Channel
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.video.model.video import Video
from external.youtube.comment_service import CommentService
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from core.llm.prompt_template_manager import PromptTemplateManager
from typing import List
import json


class RagService:
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.llm = ChatOpenAI(model="gpt-4o-mini")  # LLM 모델 설정
        self.content_chunk_repository = ContentChunkRepository()
        self.comment_service = CommentService()
    
    def summarize_video(self, video_id: str) -> str:
        context = self.transcript_service.get_formatted_transcript(video_id)
        print("정리된 자막 = ", context)
        print()
        
        query = "유튜브 영상 자막을 기반으로 10초 단위 개요를 위의 형식에 따라 작성해주세요."
        return self._execute_llm_chain(context, query, PromptTemplateManager.get_video_summary_prompt())
    
    def _execute_llm_chain(self, context: str, query: str, prompt_template_str: str) -> str:
        # TODO: 
        # 벡터 db에서 관련 정보 검색 후 context에 추가하는 로직 필요
        # 사용자 질문은 question_template에서 가져와야 함, 추후 구현
        """
        LLM 체인을 실행하는 공통 메서드
        :param context: LLM에 제공할 정보(youtube api를 통해 가져온 자막 등)
        :param query: 사용자 질문
        :return: LLM의 응답
        """
        documents = [Document(page_content=context)]
        
        # 프롬프트 템플릿 생성
        prompt_template = PromptTemplate(
            input_variables=["input", "context"],
            template=prompt_template_str
        )

        chat_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate(prompt=prompt_template)
        ])

        # 체인 조합 및 실행
        combine_chain = create_stuff_documents_chain(self.llm, chat_prompt)
        result = combine_chain.invoke({"input": query, "context": documents})
        return result

    async def analyze_idea(self, video: Video, channel: Channel):
        # 필요한 데이터
        query = "유튜브 채널에 대한 콘텐츠 아이디어를 생성해주세요."

        data = {
            "channel": {
                "name" : channel.name,
                "target" : channel.name,
                "concept" : channel.concept,
                "hash_tag" : channel.channel_hash_tag,
            },
            "video": {
                "title" : video.title,
                "description" : video.description,
                "category" : video.video_category,
            },
        }

        # 해당 카테고리의 유튜브 인기 영상 가져오기 # TODO 카테고리가 없을 수 있는지 확인 (youtube api 내 기본값이 0)
        # category_id = video.category_id if video.category_id else "0"
        category_id = "0"
        popular_videos = self.comment_service.get_category_popular(category_id)
        logging.info("인기 영상 조회 확인")
        logging.info(len(popular_videos))

        # 인기 영상 벡터 db 임베딩
        for popular in popular_videos:
            context_str = json.dumps(popular, ensure_ascii=False, indent=2)
            await self.content_chunk_repository.save_context(SourceTypeEnum.IDEA_RECOMMENDATION, video.id, context_str)
        logging.info("임베딩 확인")

        # 유사도 기준 5개 줍기
        similar_video = await self.content_chunk_repository.search_similar(SourceTypeEnum.IDEA_RECOMMENDATION, metadata=None, limit=5)
        logging.info("유사도 조회 확인")

        # JSON 형식으로 context 생성
        context_json = {
            "popularity": similar_video,
            "origin": data
        }
        context = json.dumps(context_json, ensure_ascii=False, indent=2)
        logging.info("context 생성 확인")

        # llm 생성
        result = self._execute_llm_chain(context, query, PromptTemplateManager.get_idea_prompt())

        return json.load(result, ensure_ascii=False, indent=2)