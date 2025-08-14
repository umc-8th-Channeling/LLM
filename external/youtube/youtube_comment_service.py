import logging
import os

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

