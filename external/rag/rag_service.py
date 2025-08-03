from domain.comment.model.comment import Comment
from domain.comment.model.comment_type import CommentType
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from core.llm.prompt_template_manager import PromptTemplateManager
from typing import List, Dict, Any
import json


class RagService:
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.llm = ChatOpenAI(model="gpt-4o-mini")  # LLM 모델 설정
    
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