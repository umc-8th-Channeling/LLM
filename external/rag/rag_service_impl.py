from external.rag.rag_service import RagService
from external.youtube.transcript_service import TranscriptService
from external.youtube.video_detail_service import VideoDetailService
from external.youtube.youtube_comment_service import YoutubeCommentService
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.video.model.video import Video
from domain.channel.model.channel import Channel
from domain.comment.model.comment_type import CommentType
from core.enums.source_type import SourceTypeEnum
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from core.llm.prompt_template_manager import PromptTemplateManager
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class RagServiceImpl(RagService):
    def __init__(self):
        self.transcript_service = TranscriptService()
        self.video_detail_service = VideoDetailService()
        self.youtube_comment_service = YoutubeCommentService()
        self.content_chunk_repository = ContentChunkRepository()
        self.llm = ChatOpenAI(model="gpt-4o-mini")
    
    def summarize_video(self, video_id: str) -> str:
        context = self.transcript_service.get_formatted_transcript(video_id)
        print("정리된 자막 = ", context)
        print()
        
        query = "유튜브 영상 자막을 기반으로 10초 단위 개요를 위의 형식에 따라 작성해주세요."
        return self._execute_llm_chain(context, query, PromptTemplateManager.get_video_summary_prompt())
    
    def classify_comment(self, comment: str) -> Dict[str, Any]:
        query = "유튜브 댓글을 분석하여 감정을 분류하고 백틱(```)이나 설명 없이 순수 JSON으로 출력해주세요."
        result = self._execute_llm_chain(comment, query, PromptTemplateManager.get_comment_reaction_prompt())
        print("LLM 응답 = ", result)

        result_json = json.loads(result)
        return {
            "comment_type": CommentType.from_emotion_code(result_json.get("emotion"))
        }

    def summarize_comments(self, comments: str) -> List[str]:
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

    async def analyze_idea(self, video: Video, channel: Channel) -> List[Dict[str, Any]]:
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
        category_id = "0"  # TODO 카테고리가 없을 수 있는지 확인 (youtube api 내 기본값이 0)
        popular_videos = self.youtube_comment_service.get_category_popular(category_id)
        logging.info(f"카테고리 '{category_id}'의 인기 영상 {len(popular_videos)}개 조회 완료")

        # 3. 텍스트로 변환하여 Vector DB에 저장
        for popular in popular_videos:
            pop_video_text = f"""제목: {popular['video_title']}, 설명: {popular['video_description']},태그: {popular['video_hash_tag']},채널명: {popular['channel_title']}"""
            await self.content_chunk_repository.save_context(
                source_type=SourceTypeEnum.IDEA_RECOMMENDATION,
                source_id=video.id,
                context=pop_video_text)
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

    def _execute_llm_chain(self, context: str, query: str, prompt_template_str: str) -> str:
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