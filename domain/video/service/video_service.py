import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.video.model.video import Video
from domain.video.repository.video_repository import VideoRepository

video_repository = VideoRepository()
content_chunk_repository = ContentChunkRepository()

class VideoService:

    # TODO 비디오 analytics 더미데이터 : 추후 외부 API 연동 시점 결정 후 수정
    video_analytics_dummy = {
        "duration": 300,  # 비디오 길이 (초 단위)
        "share_count": 15,  # 공유 수
        "average_view_duration": 200,  # 평균 시청 시간 (초 단위)
        "subscribers_gained": 10,  # 구독자 증가 수
    }


    """
    유사도 계산
    - 채널 내 다른 영상들과의 유사도를 계산하여 일관성 점수 반환
    """
    async def analyze_consistency(self, video: Video):
        # 채널 내 모든 영상 조회 (영상이 없다면 유사도 100으로 처리)
        videos = await video_repository.find_by_channel_id(video.channel_id)
        other_videos = [v for v in videos if v.id != video.id]

        if (other_videos is None) or (len(other_videos) == 0):
            return 100

        # 1. 대상 비디오의 임베딩
        target_video_text = f"{video.title} {video.description}"
        target_embedding = await content_chunk_repository.generate_embedding(target_video_text)

        # 2. 다른 영상들의 임베딩
        other_videos_texts = [f"{v.title} {v.description}" for v in other_videos]
        other_embeddings = []
        for text in other_videos_texts:
            embedding = await content_chunk_repository.generate_embedding(text)
            other_embeddings.append(embedding)

        # 3. 코사인 유사도 계산
        similarity_scores = cosine_similarity([target_embedding], other_embeddings)

        # 4. 평균 유사도 점수 계산
        average_similarity = np.mean(similarity_scores[0])
        consistency_score = average_similarity * 100
        return round(consistency_score, 0)


    """
    SEO 분석 
    - 조회수 대비 시청지속시간, 좋아요, 공유, 구독자증가율을 기반으로 SEO 점수 계산
    """
    async def analyze_seo(self, video: Video):

        views = video.view
        if views == 0:
            return 0  # TODO 조회수가 0인 경우 처리

        # 1. 조회수 대비 참여율 계산
        likes_per_1000_views = (video.like_count or 0) / views * 1000
        shares_per_1000_views = (self.video_analytics_dummy["share_count"] or 0) / views * 1000 # TODO : API 연동
        subscribers_gained_per_1000_views = (self.video_analytics_dummy["subscribers_gained"] or 0) / views * 1000 # TODO : API 연동

        # 2. 목표 수치 기준 정규화
        TARGETS = {
            "likes_per_1000_views": 30,  # 1000회 조회당 좋아요 30개 목표
            "shares_per_1000_views": 5,  # 1000회 조회당 공유 5개 목표
            "subscribers_per_1000_views": 5,  # 1000회 조회당 구독자 5명 목표
        }

        normalized_scores = {
            "duration": min((self.video_analytics_dummy["average_view_duration"] or 0) / self.video_analytics_dummy["duration"], 1.0), # TODO : API 연동
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

        return round(total_score, 1)

    """
    재방문률 분석 (좋아요 + 공유 + 구독) / (조회수)
    """
    async def analyze_revisit(self, video: Video):
        # 조회수 대비 (좋아요 + 공유 + 구독)
        if video.view == 0:
            return 0  # TODO 조회수가 0인 경우 처리

        # TODO : API 연동
        revisit = ((video.like_count or 0) + (self.video_analytics_dummy["share_count"] or 0) + (self.video_analytics_dummy["subscribers_gained"] or 0)) / video.view
        return round(revisit * 100, 2)