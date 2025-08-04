from domain.comment.model.comment import Comment
from domain.comment.model.comment_type import CommentType
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from external.youtube.trend_service import TrendService  # 트렌드 데이터 수집 서비스
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from core.llm.prompt_template_manager import PromptTemplateManager
import json
from datetime import datetime
from typing import List, Dict, Optional, Any


class RagService:
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.trend_service = TrendService()
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
    
    def analyze_realtime_trends(self, limit: int = 6, geo: str = "KR") -> Dict:
        """
        실시간 트렌드를 분석하여 YouTube 콘텐츠에 적합한 형태로 반환
        
        Args:
            limit: 분석할 트렌드 개수 (최대 6개)
            geo: 지역 코드 (기본값: KR)
            
        Returns:
            분석된 트렌드 정보
        """
        # 1. Google Trends에서 실시간 트렌드 가져오기
        raw_trends = self.trend_service.get_realtime_trends(limit=limit*2, geo=geo)  # 여유있게 가져오기
        
        if not raw_trends:
            return {"error": "트렌드 데이터를 가져올 수 없습니다."}
        
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        # 3. Context 구성
        context = {
            "trends_data": raw_trends,
            "current_date": current_date,
            "region": geo
        }
        
        # 4. LLM에게 분석 요청
        query = f"실시간 트렌드 중 YouTube 콘텐츠로 적합한 상위 {limit}개를 선정하고 분석해주세요."
        prompt_template = PromptTemplateManager.get_trend_analysis_prompt()
        
        # 5. LLM 실행 및 결과 파싱
        result_str = self._execute_llm_chain(
            context=json.dumps(context, ensure_ascii=False),
            query=query,
            prompt_template_str=prompt_template
        )
        
        try:
            result = json.loads(result_str)
            return result
        except json.JSONDecodeError:
            return {"error": "결과 파싱 오류", "raw_result": result_str}
    
    def analyze_channel_trends(
        self,
        channel_concept: str,
        target_audience: str

    ) -> Dict:
        """
        채널 맞춤형 트렌드를 생성하고 분석
        
        Args:
            channel_concept: 채널 컨셉
            target_audience: 타겟 시청자
            
        Returns:
            채널 맞춤형 트렌드 분석 결과
        """
        # 1. Context 구성 (채널 정보)
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        context = {
            "channel_concept": channel_concept,
            "target_audience": target_audience,
            "current_date": current_date
        }
        
        # 2. LLM에게 분석 요청
        query = "채널에 최적화된 트렌드 키워드 6개를 생성하고 분석해주세요."
        prompt_template = PromptTemplateManager.get_channel_customized_trend_prompt()
        
        # 3. LLM 실행 및 결과 파싱
        result_str = self._execute_llm_chain(
            context=json.dumps(context, ensure_ascii=False),
            query=query,
            prompt_template_str=prompt_template
        )
        
        try:
            result = json.loads(result_str)
            return result
        except json.JSONDecodeError:
            return {"error": "결과 파싱 오류", "raw_result": result_str}