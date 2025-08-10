import logging
import isodate

import numpy as np

from core.enums.avg_type import AvgType
from domain.content_chunk.repository.content_chunk_repository import ContentChunkRepository
from domain.video.model.video import Video
from domain.video.repository.video_repository import VideoRepository
import external.youtube.analytics_service as analytics_service
from external.youtube.video_detail_service import VideoDetailService


class VideoService:

    def __init__(self):
        self.video_repository = VideoRepository()
        self.content_chunk_repository = ContentChunkRepository()
        self.youtube_video_detail_service = VideoDetailService()


    async def get_overview_rating(self, video: Video, access_token: str):
        video_analytics = await analytics_service.get_youtube_analytics_data(
            access_token =access_token,
            video_id = video.youtube_video_id,
            metrics = 'views,averageViewDuration,likes,shares,subscribersGained'
        )

        video_detail = self.youtube_video_detail_service.get_video_details(video.youtube_video_id)
        google_result = video_analytics['rows'][0]

        analytics_data = {
            "views": google_result[0],  # 조회수
            "average_view_duration": google_result[1],  # 평균시청길이
            "likes": google_result[2],  # 좋아요수
            "shares": google_result[3],  # 공유수
            "subscribers_gained": google_result[4],  # 구독증가율
        }

        concept = await self._analyze_consistency(video) # 유사도
        seo = await self._analyze_seo(video, analytics_data, video_detail) # SEO 분석
        revisit = await self._analyze_revisit(video,analytics_data) # 재방문률
        avg_dic = await self._get_rating_avg(video) # 채널/토픽(카테고리)별 평균

        return {
            "concept" : concept,
            "seo" : seo,
            "revisit" : revisit,
            "view": video.view,
            "view_avg": avg_dic['view_avg'],
            "view_category_avg": avg_dic['view_category_avg'],
            "like": video.like_count,
            "like_avg": avg_dic['like_avg'],
            "like_category_avg": avg_dic['like_category_avg'],
            "comment": video.comment_count,
            "comment_avg": avg_dic['comment_avg'],
            "comment_category_avg": avg_dic['comment_category_avg'],
        }

    """
    유사도 계산
    - 채널 내 다른 영상들과의 유사도를 계산하여 일관성 점수 반환
    """
    async def _analyze_consistency(self, video: Video):
        # 채널 내 모든 영상 조회 (영상이 없다면 유사도 100으로 처리)
        videos = await self.video_repository.find_by_channel_id(video.channel_id)
        other_videos = [v for v in videos if v.id != video.id]

        if (other_videos is None) or (len(other_videos) == 0):
            return 100

        # 1. 대상 비디오의 임베딩
        target_video_text = f"{video.title} {video.description}"
        target_embedding = await self.content_chunk_repository.generate_embedding(target_video_text)

        # 2. 다른 영상들의 임베딩
        other_videos_texts = [f"{v.title} {v.description}" for v in other_videos]
        other_embeddings = []
        for text in other_videos_texts:
            embedding = await self.content_chunk_repository.generate_embedding(text)
            other_embeddings.append(embedding)

        # 3. 코사인 유사도 계산 (NumPy 사용)
        similarity_scores = []
        for other_embedding in other_embeddings:
            # 코사인 유사도 = (A·B) / (||A|| * ||B||)
            dot_product = np.dot(target_embedding, other_embedding)
            norm_target = np.linalg.norm(target_embedding)
            norm_other = np.linalg.norm(other_embedding)
            
            if norm_target == 0 or norm_other == 0:
                similarity = 0
            else:
                similarity = dot_product / (norm_target * norm_other)
            similarity_scores.append(similarity)

        # 4. 평균 유사도 점수 계산
        average_similarity = np.mean(similarity_scores)
        consistency_score = average_similarity * 100
        return round(consistency_score, 0)


    """
    SEO 분석 
    - 조회수 대비 시청지속시간, 좋아요, 공유, 구독자증가율을 기반으로 SEO 점수 계산
    """
    async def _analyze_seo(self, video: Video, analytics_data: dict, video_detail: dict):
        delta = isodate.parse_duration(video_detail.get('duration'))
        total_duration = delta.total_seconds()

        views = analytics_data['views']
        if views == 0:
            return 0  # TODO 조회수가 0인 경우 처리

        # 1. 조회수 대비 참여율 계산
        likes_per_1000_views = (video.like_count or 0) / views * 1000

        shares_per_1000_views = (analytics_data["shares"] or 0) / views * 1000

        subscribers_gained_per_1000_views = (analytics_data["subscribers_gained"] or 0) / views * 1000

        # 2. 목표 수치 기준 정규화
        TARGETS = {
            "likes_per_1000_views": 30,  # 1000회 조회당 좋아요 30개 목표
            "shares_per_1000_views": 5,  # 1000회 조회당 공유 5개 목표
            "subscribers_per_1000_views": 5,  # 1000회 조회당 구독자 5명 목표
        }

        logging.info("6")


        normalized_scores = {
            "duration": min((analytics_data["average_view_duration"] or 0) / total_duration, 1.0),
            "likes_rate": min(likes_per_1000_views / TARGETS["likes_per_1000_views"], 1.0),
            "shares_rate": min(shares_per_1000_views / TARGETS["shares_per_1000_views"], 1.0),
            "subscribers_rate": min(subscribers_gained_per_1000_views / TARGETS["subscribers_per_1000_views"], 1.0),
        }

        logging.info(f"제발 {normalized_scores}")

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
    async def _analyze_revisit(self, video: Video, analytics_data):
        # 조회수 대비 (좋아요 + 공유 + 구독)
        if video.view == 0:
            return 0

        revisit = ((video.like_count or 0) + (analytics_data["shares"] or 0) + (analytics_data["subscribers_gained"] or 0)) / video.view
        return round(revisit * 100, 2)

    """
    채널/토픽(카테고리별) 평균 조회수
    """
    async def _get_rating_avg(self, video: Video):

        # 채널 내 전체 영상 조회
        videos = await self.video_repository.find_by_channel_id(video.channel_id)
        if len(videos) == 1 :
            return {
                "view_avg": 0,
                "view_category_avg": 0,
                "like_avg": 0,
                "like_category_avg": 0,
                "comment_avg": 0,
                "comment_category_avg": 0
            }

        # 조회수 - 평균 대비 비율
        avg = sum(v.view for v in videos if v.view is not None) / len(videos)
        view_avg = await self._avg(video.view, avg)

        # 조회수 - 카테고리별 평균 대비 비율
        avg = sum(v.view for v in videos if v.video_category == video.video_category) / len(videos)
        view_category_avg = await self._avg(video.view, avg)

        # 좋아요수 - 평균 대비 비율
        avg = sum(v.like_count for v in videos if v.like_count is not None) / len(videos)
        like_avg = await self._avg(video.like_count, avg)

        # 좋아요수 - 카테고리별 평균 대비 비율
        avg = sum(v.like_count for v in videos if v.video_category == video.video_category) / len(videos)
        like_category_avg = await self._avg(video.like_count, avg)

        # 댓글수 - 평균 대비 비율
        avg = sum(v.comment_count for v in videos if v.comment_count is not None) / len(videos)
        comment_avg = await self._avg(video.comment_count, avg)

        # 댓글수 - 카테고리별 평균 대비 비율
        avg = sum(v.comment_count for v in videos if v.video_category == video.video_category) / len(videos)
        comment_category_avg = await self._avg(video.comment_count, avg)

        return {
            "view_avg": view_avg,
            "view_category_avg": view_category_avg,
            "like_avg": like_avg,
            "like_category_avg": like_category_avg,
            "comment_avg": comment_avg,
            "comment_category_avg": comment_category_avg
        }


    async def _avg(self, target, avg):
        ratio_avg = target / avg if avg != 0 else 0
        return round(ratio_avg * 100, 2)



