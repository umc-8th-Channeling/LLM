import random
from collections import defaultdict
from typing import List, DefaultDict
import logging
from domain.comment.model.comment import Comment
from domain.comment.model.comment_type import CommentType
from domain.comment.repository.comment_repository import CommentRepository
from domain.report.repository.report_repository import ReportRepository
from domain.video.model.video import Video
from external.rag.rag_service_impl import RagServiceImpl
from external.youtube.youtube_comment_service import YoutubeCommentService

logger = logging.getLogger(__name__)

class CommentService:
    def __init__(self):
        self.rag_service = RagServiceImpl()
        self.comment_repository = CommentRepository()
        self.youtube_comment_service = YoutubeCommentService()
        self.report_repository = ReportRepository()

    async def summarize_comments_by_emotions_with_llm(self, comments_by_emotions: DefaultDict[CommentType, list[Comment]]) -> defaultdict[CommentType, List[Comment]]:
        summarized_comments: defaultdict[CommentType, List[Comment]] = defaultdict(list)

        # 감정별로 요약
        for emotion, comments in comments_by_emotions.items():
            if not comments:
                summarized_comments[emotion].append("")
                continue

            # 해당 감정 그룹의 content만 개행으로 합치기
            contents_str = "\n".join(comment.content for comment in comments)

            # LLM 서비스 호출 -> returns list[str]
            summarized_contents = self.rag_service.summarize_comments(contents_str)


            # 요약 내용을 defaultdict에 추가 & DB 저장
            comments_to_save = []
            for content in summarized_contents:
                summarized_comment_obj = Comment(
                    comment_type=emotion.value,
                    content=content,
                    report_id=comments[0].report_id
                )
                summarized_comments[emotion].append(summarized_comment_obj)
                # 딕셔너리로 변환하여 저장
                comments_to_save.append({
                    "comment_type": emotion.value,
                    "content": content,
                    "report_id": comments[0].report_id
                })
            await self.comment_repository.save_bulk(comments_to_save)
            logger.info("댓글 결과를 MYSQL DB에 저장했습니다.")
        return summarized_comments

    async def classify_comment_with_llm(self, comment: Comment) -> Comment:
        result = self.rag_service.classify_comment(comment.content)
        # comment의 comment_type 업데이트
        comment.comment_type = result["comment_type"]
        # db 저장 후 반환 -> 그냥 반환
        return comment

    # 댓글을 분류
    def sample_comments(self, comments: list[Comment], threshold: int = 100, sample_rate: float = 0.2) -> tuple[list[Comment], bool]:
        """
        댓글이 threshold 이상일 때 sample_rate 비율로 샘플링
        
        Args:
            comments: 전체 댓글 리스트
            threshold: 샘플링 시작 기준 (기본 100개)
            sample_rate: 샘플링 비율 (기본 20%)
            
        Returns:
            (샘플링된 댓글 리스트, 샘플링 여부 플래그)
        """
        total_count = len(comments)
        
        if total_count < threshold:
            # 임계값 미만이면 전체 댓글 반환
            logger.info(f"댓글 수({total_count})가 임계값({threshold}) 미만, 전체 댓글 분석")
            return comments, False
        
        # 샘플링 수 계산 (최소 20개 보장)
        sample_size = max(20, int(total_count * sample_rate))
        sample_size = min(sample_size, total_count)  # 전체 댓글 수를 초과하지 않도록
        
        # 랜덤 샘플링
        sampled_comments = random.sample(comments, sample_size)
        
        logger.info(f"댓글 샘플링: {total_count}개 중 {sample_size}개 선택 ({sample_rate*100:.0f}%)")
        return sampled_comments, True

    async def gather_classified_comments(self, comments: list[Comment])->DefaultDict[CommentType, list[Comment]]:
        grouped = defaultdict(list)
        for comment in comments:
            result = await self.classify_comment_with_llm(comment)
            grouped[result.comment_type].append(result)

        return grouped

    async def analyze_comments(self, video: Video, report_id: int) -> bool:
        """
        영상의 댓글을 분석하고 감정별로 요약하여 저장
        
        Args:
            video: 비디오 객체
            report_id: 리포트 ID
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 유튜브 영상 아이디 조회
            youtube_video_id = getattr(video, "youtube_video_id", None)
            if not youtube_video_id:
                logger.error("YouTube 영상 ID가 없습니다.")
                return False
            
            # 댓글 정보 조회
            comments_by_youtube = await self.youtube_comment_service.get_comments(youtube_video_id, report_id)
            
            # Comment 객체로 변환
            comments_obj = await self.convert_to_comment_objects(comments_by_youtube)
            
            # 감정별로 분류
            result = await self.gather_classified_comments(comments_obj)
            
            # 감정별 요약 생성
            summarized_comments = await self.summarize_comments_by_emotions_with_llm(result)
            
            # 감정별 댓글 개수 업데이트
            count_dict = {comment_type: len(comments) for comment_type, comments in summarized_comments.items()}
            logger.info("댓글 개수를 MYSQL DB에 저장합니다.")
            await self.report_repository.update_count(report_id, count_dict)
            
            logger.info("댓글 분석이 완료되었습니다.")
            return True
            
        except Exception as e:
            raise

    # 유튜브 api 에서 가져온 댓글을 Comment 객체로 변환
    async def convert_to_comment_objects(self, comments: list[dict]) -> list[Comment]:
        comment_objects = []
        for data in comments:
            comment = Comment(
                comment_type=data.get("comment_type", None),
                content=data["content"],
                report_id=data["report_id"],
            )
            comment_objects.append(comment)
        return comment_objects
