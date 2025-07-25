from fastapi import APIRouter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from core.database.model.video import Video
from domain.channel.video_repository import VideoRepository

router = APIRouter(prefix="/ratings", tags=["rating"])

"""
테스트 라우터
"""

video_repository = VideoRepository()

@router.get("")
async def get_rating(video_id: int):
    # 영상 analytics 정보 조회
    video = await video_repository.find_by_id(video_id)
    if not video:
        return {"error": f"Analysis data not found for video_id: {video_id}"}

    # 1. SEO 분석
    print(await analyze_seo(video))
    # 2. 재방문률 분석
    print(await analyze_revisit(video))

    return "ok"

# """
# 백터 DB 내 영상 업데이트
# """
# async def update_pg_video(self, channel_id: int):
#     # 1. 벡터 DB(PostgreSQL)에서 채널의 기존 영상 벡터 조회
#     existing_embeddings = await self.pg_vector_repo.find_embeddings_by_channel_id(channel_id)
#
#     # 1-1. 벡터가 존재하지 않으면, MySQL에서 데이터를 가져와 벡터화 후 저장
#     if not existing_embeddings:
#         # MySQL에서 비디오 원본 데이터 조회
#         videos_from_mysql = await self.mysql_video_repo.find_by_channel_id(channel_id)
#         if not videos_from_mysql:
#             print("분석할 영상이 없습니다.") # 또는 예외 처리
#
#         # 텍스트 데이터 준비 및 벡터화
#         texts = [f"{v.title} {v.description} {v.video_category}" for v in videos_from_mysql]
#         new_embeddings = self.model.encode(texts)
#
#         # 생성된 벡터를 PostgreSQL에 저장
#         await self.pg_vector_repo.save_embeddings(channel_id, videos_from_mysql, new_embeddings)
#     else:
#         texts = existing_embeddings
#
#     return texts

"""
유사도 계산
"""
# async def analyze_consistency(self, channel_id: int, curr_video, report):
    # # 1. 벡터 DB에서 채널 모든 영상 조회
    # existing_embeddings = await self.update_pg_video(channel_id)
    #
    # # 2. 현재 대상 비디오와 기존 비디오들 간의 유사도 수치화
    # curr_video_text = f"{curr_video.title} {curr_video.description} {curr_video.video_category}"
    # curr_video_embedding = self.model.encode([curr_video_text])
    #
    # # 코사인 유사도 계산
    # similarities = cosine_similarity(curr_video_embedding, np.array(existing_embeddings))
    # consistency_score = np.mean(similarities[0]) * 100 # 백분율로 변환
    # print(f"계산된 유사도 점수: {consistency_score:.2f}%")
    #
    # # report 테이블에 수치화한 유사도 저장
    # report.concept = consistency_score
    # return report

"""
SEO 분석
"""
async def analyze_seo(video: Video):

    views = video.view
    if views == 0:
        return 0 # TODO 조회수가 0인 경우 처리

    # 1. 조회수 대비 참여율 계산
    likes_per_1000_views = (video.like_count or 0) / views * 1000
    shares_per_1000_views = (video.share_count or 0) / views * 1000
    subscribers_gained_per_1000_views = (video.subscribers_gained or 0) / views * 1000

    # 2. 목표 수치 기준 정규화
    TARGETS = {
        "likes_per_1000_views": 30,  # 1000회 조회당 좋아요 30개 목표
        "shares_per_1000_views": 5,  # 1000회 조회당 공유 5개 목표
        "subscribers_per_1000_views": 10,  # 1000회 조회당 구독자 10명 목표
    }

    normalized_scores = {
        "duration": min((video.average_view_duration or 0) / video.duration, 1.0),
        "likes_rate": min(likes_per_1000_views / TARGETS["likes_per_1000_views"], 1.0),
        "shares_rate": min(shares_per_1000_views / TARGETS["shares_per_1000_views"], 1.0),
        "subscribers_rate": min(subscribers_gained_per_1000_views / TARGETS["subscribers_per_1000_views"], 1.0),
    }

    # 3. 항목별 가중치
    WEIGHTS = {
        "duration": 50,
        "likes_rate": 15,
        "shares_rate": 15,
        "subscribers_rate": 20,
    }

    final_scores = {}
    total_score = 0

    for key, weight in WEIGHTS.items():
        score = normalized_scores.get(key, 0) * weight
        final_scores[f"{key}_score"] = round(score, 0)
        total_score += score

    return {
        "total_seo_score": round(total_score, 1),
        "details": final_scores,
        "source_metrics": video.dict()
    }

"""
재방문률 분석
"""
async def analyze_revisit(video: Video):
    # 조회수 대비 (좋아요 + 공유 + 구독)
    if video.view == 0:
        return 0 # TODO 조회수가 0인 경우 처리

    revisit = ((video.like_count or 0) + (video.share_count or 0) + (video.share_count or 0)) / video.view
    return round(revisit * 100, 2)


