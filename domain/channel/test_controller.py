import numpy as np
from fastapi import APIRouter
from sklearn.metrics.pairwise import cosine_similarity

from domain.channel.video_repository import VideoRepository
from domain.report.repository.report_repository import ReportRepository

"""
1. 컨셉 일관성
채널 내 전체 영상 제목, 설명, 태그와의 유사도를 계산
"""

"""
2. SEO 구성 (점수)
- 핵심 키워드 포함 여부 (20점): 영상의 주요 키워드가 제목, 설명, 태그에 모두 포함되어 있는지 확인합니다.
- 제목 길이 (20점): 제목이 너무 길거나 짧지 않고 적절한 길이(예: 20~70자)를 유지하는지 평가합니다.
- 설명 길이 및 링크 (20점): 설명란이 충분히 길고(예: 100자 이상), 관련 링크나 타임스탬프가 포함되어 있는지 확인합니다.
- 태그 개수 (20점): 적절한 개수의 태그(예: 5~15개)를 사용했는지 평가합니다.
- 스크립트(자막) 유무 (20점): 영상에 자막이 존재하면 검색에 유리하므로 추가 점수를 부여합니다.
"""

"""
3. 재방문률 (%)
유튜브 공식 API를 통해 얻을 수 있는 
'구독자 증가/감소 수(subscribersGained, subscribersLost)', '영상당 평균 조회수', '영상별 좋아요/댓글 수' 
등의 데이터를 종합하여 분석
"""



router = APIRouter(prefix="/test", tags=["test"])

class TestController:

    def __init__(self):
        self.pg_vector_repo = None
        self.mysql_video_repo = VideoRepository()
        self.mysql_report_repo = ReportRepository()

    """
    테스트용 라우터
    """
    @router.get("")
    async def get_rating(self):
        message = {
            "member": { "id":1, "channel":{"id":1,}},
            "report": { "id":1, "video_id": 1,},
        }

        report = await self.report_repository.find_by_id(message.get("report").get("id"))

        await self.update_pg_video(message.get("member").get("channel").get("id"))
        await self.analyze_consistency()
        await self.analyze_seo()
        await self.analyze_revisit()

        await self.mysql_report_repo._update_partial(report)



    """
    백터 DB 내 영상 업데이트
    """
    async def update_pg_video(self, channel_id: int):
        # 1. 벡터 DB(PostgreSQL)에서 채널의 기존 영상 벡터 조회
        existing_embeddings = await self.pg_vector_repo.find_embeddings_by_channel_id(channel_id)

        # 1-1. 벡터가 존재하지 않으면, MySQL에서 데이터를 가져와 벡터화 후 저장
        if not existing_embeddings:
            # MySQL에서 비디오 원본 데이터 조회
            videos_from_mysql = await self.mysql_video_repo.find_by_channel_id(channel_id)
            if not videos_from_mysql:
                print("분석할 영상이 없습니다.") # 또는 예외 처리

            # 텍스트 데이터 준비 및 벡터화
            texts = [f"{v.title} {v.description} {v.video_category}" for v in videos_from_mysql]
            new_embeddings = self.model.encode(texts)

            # 생성된 벡터를 PostgreSQL에 저장
            await self.pg_vector_repo.save_embeddings(channel_id, videos_from_mysql, new_embeddings)
        else:
            texts = existing_embeddings

        return texts

    """
    유사도 계산
    """
    async def analyze_consistency(self, channel_id: int, curr_video, report):
        # 1. 벡터 DB에서 채널 모든 영상 조회
        existing_embeddings = await self.update_pg_video(channel_id)

        # 2. 현재 대상 비디오와 기존 비디오들 간의 유사도 수치화
        curr_video_text = f"{curr_video.title} {curr_video.description} {curr_video.video_category}"
        curr_video_embedding = self.model.encode([curr_video_text])

        # 코사인 유사도 계산
        similarities = cosine_similarity(curr_video_embedding, np.array(existing_embeddings))
        consistency_score = np.mean(similarities[0]) * 100 # 백분율로 변환
        print(f"계산된 유사도 점수: {consistency_score:.2f}%")

        # report 테이블에 수치화한 유사도 저장
        report.concept = consistency_score
        return report


    async def analyze_seo(self):
        return report


    async def analyze_revisit(self):
        return report
