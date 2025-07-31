from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from external.youtube.video_detail_service import VideoDetailService  # 유튜브 비디오 상세 정보 서비스
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from core.llm.prompt_template_manager import PromptTemplateManager
from typing import List, Dict
import json


class RagService:
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.video_detail_service = VideoDetailService()
        self.llm = ChatOpenAI(model="gpt-4o-mini")  # LLM 모델 설정
    
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
    
    def analyze_algorithm_optimization(self, video_id: str) -> str:
        """
        유튜브 알고리즘 최적화 분석
        
        Args:
            video_id: YouTube 영상 ID
            
        Returns:
            알고리즘 최적화 분석 결과
        """
        # 영상 상세 정보 조회
        video_details = self.video_detail_service.get_video_details(video_id)
        
        # 채널 정보 조회
        channel_id = video_details.get('channelId')
        
        channel_stats = {}
        if channel_id:
            channel_stats = self.video_detail_service.get_channel_stats(channel_id)
        
        # 카테고리 벤치마크 조회
        category_benchmarks = {}
        category_id = video_details.get('categoryId')
        if category_id:
            category_benchmarks = self.video_detail_service.get_category_benchmarks(category_id)
        
        # 분석에 필요한 데이터 구조화
        optimization_data = {
            "video": {
                "title": video_details.get('title', ''),
                "description": video_details.get('description', ''),
                "tags": video_details.get('tags', []),
                "publishedAt": video_details.get('publishedAt', ''),
                "duration": video_details.get('duration', ''),
                "viewCount": video_details.get('viewCount', 0),
                "likeCount": video_details.get('likeCount', 0),
                "commentCount": video_details.get('commentCount', 0),
                "thumbnails": video_details.get('thumbnails', {})
            },
            "channel": {
                "name": video_details.get('channelTitle', ''),
                "subscriberCount": channel_stats.get('subscriberCount', 0),
                "totalViewCount": channel_stats.get('viewCount', 0),
                "totalVideoCount": channel_stats.get('videoCount', 0)
            },
            "categoryBenchmarks": {
                "avgViewCount": category_benchmarks.get('avgViewCount', 0),
                "avgLikeCount": category_benchmarks.get('avgLikeCount', 0),
                "avgCommentCount": category_benchmarks.get('avgCommentCount', 0),
                "medianViewCount": category_benchmarks.get('medianViewCount', 0),
                "sampleSize": category_benchmarks.get('sampleSize', 0)
            }
        }
        
        # JSON 형식으로 context 생성
        context = json.dumps(optimization_data, ensure_ascii=False, indent=2)
        
        query = "이 유튜브 영상의 알고리즘 최적화 상태를 분석하고 구체적인 개선 방안을 제시해주세요."
        
        # 프롬프트 템플릿 가져오기
        prompt_template = PromptTemplateManager.get_algorithm_optimization_prompt()
        
        return self._execute_llm_chain(context, query, prompt_template)