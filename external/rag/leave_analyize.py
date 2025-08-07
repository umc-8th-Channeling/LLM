from typing import List

from dotenv import load_dotenv
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
import external.youtube.analytics_service as analyticsServcie
import external.rag.chunk_service as ChunkService # ← 지연 import로 순환참조 방지
from external.youtube.transcript_service import TranscriptService  # 유튜브 자막 처리 서비스
from domain.video.model.video import Video
from core.enums.source_type import SourceTypeEnum
from external.rag.rag_service_impl import RagServiceImpl
import json
from core.llm.prompt_template_manager import PromptTemplateManager
from domain.channel.repository.channel_repository import ChannelRepository
import os
load_dotenv()

transcript_service = TranscriptService()
content_repository = ContentChunkRepository()
rag_service = RagServiceImpl()
channel_repository = ChannelRepository()
async def analyze_leave(video: Video) -> str:






# 1. 영상, 채널 정보 가져오기

    # 구글 엑세스 토큰
    token = os.getenv("GOOGLE_ACCESS_TOKEN")
    # 영상 가져오기
    youtube_video_id = video.youtube_video_id
    video_id = video.id

    #체널 가져오기    
    channel_id = video.channel_id
    channel = await channel_repository.find_by_id(channel_id)

    # context, analytics_data = await asyncio.gather(
    #     transcript_service.get_structured_transcript(youtube_video_id),
    #     analyticsServcie.get_youtube_analytics_data(token, youtube_video_id)
    # )




# 2. 영상의 스크립트 가져오기
    # 대본 스크립트 가져오기
    context = transcript_service.get_structured_transcript(youtube_video_id)
    
# 3. 스크립트를 사용해서 영상 총 길이 구하기
    # 영상 총 길이 구하기
    video_length = context[-1]["end_time"]

# 4. 영상 분석 결과 가져오기 (analytics)
    # analytics 가져오기
    analytics_data = await analyticsServcie.get_youtube_analytics_data(token,youtube_video_id)

# 5. 분석 결과로 이탈 시점 구하기
    #가장 많이 이탈한 (가장 시청 비율이 급락한 시점 추출)
    worst_ratio =analyticsServcie.find_max_drop_time(analytics_data.get("rows", []))

# 6. 시간 단위 청킹 및  임베딩 저장
    # 시간 단위 청킹 데이터 생성 및 저장 -> 기존에 있으면 생략
    exists = await content_repository.exists_by_chunk_type_and_id("time",str(video_id))
    if exists:
        print("기존에 저장한 적 있는 영상입니다. 대본 기반의 청킹 생성을 띄어 넘습니다..")
    else:
        await ChunkService.create_time_chunks_with_focus(video_id,video_length,context,analytics_data.get("rows", []),worst_ratio)
# 7. 의미 단위 청킹 및  임베딩 저장
    # 의미 단위 청킹 데이터 생성 및 저장 (이탈 지점 청킹 llm 호출)
    await ChunkService.create_meaning_chunks_with_focus(video_id,video_length,context,analytics_data.get("rows", []),worst_ratio)



# 8. 질문 리스트와 유사도 분석해서, 각 질문마다 3개씩의 청킹을 조회
    # # 1) 질문 리스트
    questions = {
        "cause": "이 영상의 시청 이탈 원인을 설명해 주세요.",
        "improvement": "이 영상의 시청 이탈을 줄이기 위한 개선 방안을 제시해 주세요.",
        "editing_flow": "이 영상에 적합한 예상 편집 흐름을 제안해 주세요."
    }

    # 추가 필터링이 있다면..?
    meta = {}
    # 2) 질문별 임베딩 및 유사 청킹 검색
    # 이탈 원인 질문의 상위 3개 청킹 데이터 조회 
    cause_chunk = await content_repository.search_similar_K(questions["cause"],SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS.value.upper(),str(video_id),meta ,3)
    # 이탈 원인 질문의 상위 3개 청킹 데이터 조회 
    improvement_chunk = await content_repository.search_similar_K(questions["improvement"],SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS.value.upper(),str(video_id),meta ,3)
    # 이탈 원인 질문의 상위 3개 청킹 데이터 조회 
    editing_flow_chunk = await content_repository.search_similar_K(questions["editing_flow"],SourceTypeEnum.VIEWER_ESCAPE_ANALYSIS.value.upper(),str(video_id),meta ,3)


    # llm 출력
    worst_sec = int(worst_ratio * video_length)  # 최악 이탈 시점(초)
    focus_range_sec = max(10, min(int(0.04 * video_length), 300))  # 집중 범위: 영상 길이의 4%, 최소 10초, 최대 5분
    start_focus_time = max(0, worst_sec - focus_range_sec // 2)
    end_focus_time = min(video_length, worst_sec + focus_range_sec // 2)
    # 3. context 생성
    context_data = {
        "cause_chunk": json.dumps(cause_chunk, ensure_ascii=False, indent=2),
        "improvement_chunk": json.dumps(improvement_chunk, ensure_ascii=False, indent=2),
        "editing_flow_chunk": json.dumps(editing_flow_chunk, ensure_ascii=False, indent=2),
        "worst_sec": worst_sec,
        "start_focus_time": start_focus_time,
        "end_focus_time": end_focus_time,
        "video_length": video_length,
        "video_title" : video.title,
        "video_description" : video.description,
        "video_category" : video.video_category,
        "channel_concept" : channel.concept,
        "channel_target" : channel.target,
        "channel_hashtag" : channel.channel_hash_tag
    }

# 9. 1,8번에서 조회한 정보를 프롬프트에 넣기   
    prompt_template_str = PromptTemplateManager.get_viewer_escape_analysis_prompt()
    formatted_prompt = prompt_template_str.format(**context_data)  
   
# 10. LLM 직접 호출해서 결과 가져오기
    result = rag_service.execute_llm_direct(formatted_prompt)
    return result
