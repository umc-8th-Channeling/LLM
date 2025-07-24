from googleapiclient.discovery import build
import os



#특정 video의 모든 댓글을 가져오는 함수
class GetCommentsYoutube:
    def __init__(self, video_id: str,report_id: int):
        self.video_id = video_id
        self.report_id = report_id

    def get_comments(self) -> list[dict]:
        api_key = os.getenv('YOUTUBE_API_KEY')
        comments = []
        api_obj = build('youtube', 'v3', developerKey=api_key)
        response = api_obj.commentThreads().list(part='snippet,replies', videoId=self.video_id, maxResults=100).execute()
        while response:
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    "comment_type": None,
                    "content": comment["textDisplay"],
                    "created_at": comment["publishedAt"],
                    "like_count": comment["likeCount"],
                    "report_id": self.report_id
                })

                if item['snippet']['totalReplyCount'] > 0:
                    for reply_item in item['replies']['comments']:
                        reply = reply_item['snippet']
                        comments.append({
                            "comment_type": None,
                            "content": reply["textDisplay"],
                            "created_at": reply["publishedAt"],
                            "like_count": reply["likeCount"],
                            "report_id": self.report_id
                        })

            if 'nextPageToken' in response:
                response = api_obj.commentThreads().list(
                    part='snippet,replies',
                    videoId=self.video_id,
                    pageToken=response['nextPageToken'],
                    maxResults=100
                ).execute()
            else:
                break
        return comments
