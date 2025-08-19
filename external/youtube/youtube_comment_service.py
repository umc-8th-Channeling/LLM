import logging
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YoutubeCommentService:
    """YouTube 댓글 처리 서비스"""
    
    def __init__(self):
        
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    async def get_comments(self, video_id: str, report_id: int, max_comments: int = 1000) -> list[dict]:
        #특정 video의 모든 댓글을 가져오는 함수 (최대 개수 제한 추가)
        comments = []
        page_count = 0
        max_pages = max_comments // 100  # 최대 페이지 수 계산
        
        try:
            response = self.youtube.commentThreads().list(
                part='snippet,replies', 
                videoId=video_id, 
                maxResults=100
            ).execute()
        except HttpError as e:
            logger.error(f"YouTube API 에러: {e}")
            if e.resp.status == 403 and 'commentsDisabled' in str(e):
                logger.warning(f"비디오 {video_id}의 댓글이 비활성화되어 있습니다.")
                return []  # 빈 리스트 반환
            raise
        except Exception as e:
            logger.error(f"YouTube 댓글 가져오기 실패: {e}")
            return []  # 빈 리스트 반환
        
        while response and page_count < max_pages:
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    "comment_type": None,
                    "content": comment["textDisplay"],
                    "created_at": comment["publishedAt"],
                    "like_count": comment["likeCount"],
                    "report_id": report_id
                })

                
                if item['snippet']['totalReplyCount'] > 0 and 'replies' in item:
                    for reply_item in item['replies']['comments']:
                        reply = reply_item['snippet']
                        comments.append({
                            "comment_type": None,
                            "content": reply["textDisplay"],
                            "created_at": reply["publishedAt"],
                            "like_count": reply["likeCount"],
                            "report_id": report_id
                        })

            
            if 'nextPageToken' in response:
                page_count += 1
                if page_count >= max_pages:
                    logger.info(f"최대 댓글 수 {max_comments}개에 도달. 수집 중단")
                    break
                    
                try:
                    response = self.youtube.commentThreads().list(
                        part='snippet,replies',
                        videoId=video_id,
                        pageToken=response['nextPageToken'],
                        maxResults=100
                    ).execute()
                except HttpError as e:
                    if e.resp.status == 400:
                        logger.warning(f"pageToken 에러 발생, 페이지네이션 중단: {e}")
                        break  # pageToken 에러시 수집한 댓글만 반환
                    else:
                        raise
            else:
                break
                
        return comments

