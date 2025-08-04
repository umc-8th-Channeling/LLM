from googleapiclient.discovery import build
import os
from typing import Dict

from googleapiclient.discovery import build, logger
from googleapiclient.errors import HttpError


class YoutubeCommentService:
    """YouTube 댓글 처리 서비스"""
    
    def __init__(self):
        
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    async def get_comments(self, video_id: str, report_id: int) -> list[dict]:
        #특정 video의 모든 댓글을 가져오는 함수
        comments = []
        response = self.youtube.commentThreads().list(
            part='snippet,replies', 
            videoId=video_id, 
            maxResults=100
        ).execute()
        
        while response:
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    "comment_type": None,
                    "content": comment["textDisplay"],
                    "created_at": comment["publishedAt"],
                    "like_count": comment["likeCount"],
                    "report_id": report_id
                })

                
                if item['snippet']['totalReplyCount'] > 0:
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
                response = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    pageToken=response['nextPageToken'],
                    maxResults=100
                ).execute()
            else:
                break
                
        return comments

    def get_category_popular(self, category_id: str, region_code: str = 'KR') -> list[dict]:
        """
        카테고리별 인기 순위 조회
        https://www.googleapis.com/youtube/v3/videoCategories?part=snippet&regionCode=KR (한국 기준 카테고리 목록 조회)
        """

        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

        try:
            # 해당 카테고리의 인기 영상 조회
            response = self.youtube.videos().list(
                part='snippet,statistics',
                chart='mostPopular',
                videoCategoryId=category_id,
                regionCode=region_code,
                maxResults=3
            ).execute()

            logger.info("유튜브 원본")
            logger.info(response)

            videos = []
            for item in response['items']:
                video = {
                    "video_title": item['snippet']['title'],
                    "video_description": item['snippet']['description'],
                    "channel_title": item['snippet']['channelTitle'],
                    "video_hash_tag": item['snippet'].get('tags', []),
                }
                videos.append(video)

            return videos

        except HttpError as e:
            if e.resp.status == 403:
                logger.error("YouTube API quota exceeded")
            else:
                logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_category_benchmarks: {e}")
            raise