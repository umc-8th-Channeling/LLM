from langchain.chains.combine_documents import create_stuff_documents_chain
from domain.comment.model.comment import Comment
from domain.comment.model.comment_type import CommentType
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI

from core.enums.source_type import SourceTypeEnum
from core.llm.prompt_template_manager import PromptTemplateManager
from typing import List, Dict, Any
import json
from domain.channel.model.channel import Channel
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.video.model.video import Video
from external.youtube.comment_service import CommentService
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스


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

    def classify_comment(self, comment: str) -> dict[str, Any]:
        query= "유튜브 댓글을 분석하여 감정을 분류하고 백틱(```)이나 설명 없이 순수 JSON으로 출력해주세요."
        result = self._execute_llm_chain(comment, query, PromptTemplateManager.get_comment_reaction_prompt())
        print("LLM 응답 = ", result)

        result_json = json.loads(result)
        return {
            "comment_type" : CommentType.from_emotion_code(result_json.get("emotion"))
        }

    def summarize_comments(self, comments: str):
        query = (
            "유튜브 댓글을 분석하여 요약하고 "
            "백틱(```)이나 설명 없이 순수 JSON으로 출력해주세요."
        )

        result = self._execute_llm_chain(
            comments, query, PromptTemplateManager.get_sumarlize_comment_prompt()
        )
        print("LLM 응답 = ", result)

        result_list = json.loads(result)
        contents = [item["content"] for item in result_list if isinstance(item, dict) and "content" in item]
        return contents





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
        # 1. 내 채널, 내 영상
        origin_context = f"""
        - 분석 채널명: {channel.name}
        - 채널 컨셉: {channel.concept}
        - 타겟 시청자: {channel.target}
        - 분석 영상 제목: {video.title}
        - 분석 영상 설명: {video.description}
        """
        logging.info("분석 기반 데이터(Origin) 생성 완료")

        # 2. 인기 동영상 목록 유튜브 호출
        # category_id = video.video_category if video.video_category else "0"
        category_id = "0" # TODO 카테고리가 없을 수 있는지 확인 (youtube api 내 기본값이 0)
        popular_videos = self.comment_service.get_category_popular(category_id)
        logging.info(f"카테고리 '{category_id}'의 인기 영상 {len(popular_videos)}개 조회 완료")

        # 3. 텍스트로 변환하여 Vector DB에 저장
        for popular in popular_videos:
            pop_video_text = f"""제목: {popular['video_title']}, 설명: {popular['video_description']},태그: {popular['video_hash_tag']},채널명: {popular['channel_title']}"""
            await self.content_chunk_repository.save_context(
                SourceTypeEnum.IDEA_RECOMMENDATION, video.id, pop_video_text)
        logging.info("인기 영상 정보 Vector DB 저장 완료")

        # 4. 영상과 의미적으로 가장 유사한 '인기 영상' 청크를 검색
        query_text = f"제목: {video.title}, 설명: {video.description}, 채널명: {channel.name}"
        video_embedding = await self.content_chunk_repository.generate_embedding(query_text)
        meta_data = {"query_embedding": str(video_embedding)}

        similar_chunks = await self.content_chunk_repository.search_similar_test(
            SourceTypeEnum.IDEA_RECOMMENDATION, metadata=meta_data, limit=5
        )
        logging.info(f"유사도 높은 인기 영상 청크 {len(similar_chunks)}개 검색 완료")

        # 5. 검색된 청크(내용)를 텍스트로
        popularity_context = "\n".join([chunk.get("content", "") for chunk in similar_chunks])
        # prompt = PromptTemplateManager.get_idea_prompt()

        # TODO _execute_llm_chain
        chain = PromptTemplateManager.get_idea_prompt | self.llm
        result_str = await chain.ainvoke({
            "context": origin_context,
            "input": popularity_context
        })

        logging.info(f"LLM 아이디어 생성 결과: {result_str.content}")

        # LLM의 응답 문자열을 JSON 파싱
        try:
            clean_json_str = result_str.content.strip().replace("```json", "").replace("```", "")
            return json.loads(clean_json_str)
        except json.JSONDecodeError:
            logging.error("LLM 응답을 JSON으로 파싱하는 데 실패했습니다.")
            return []