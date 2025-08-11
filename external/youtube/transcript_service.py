import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

# .env 파일 로드
load_dotenv()

class TranscriptService:
    """YouTube 자막 처리 서비스"""

    def __init__(self):
        # Webshare 프록시 설정
        self.proxy_username = os.getenv("PROXY_USERNAME")
        self.proxy_password = os.getenv("PROXY_PASSWORD")
        
        # 프록시 설정된 API 인스턴스 생성
        self.ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=self.proxy_username,
                proxy_password=self.proxy_password,
                filter_ip_locations=["kr", "us"]
            )
        )

    def fetch_transcript(self, video_id: str, languages=['ko', 'en']) -> list:
        """
        공통: YouTubeTranscriptApi를 사용해 자막 리스트 반환
        각 요소: FetchedTranscriptSnippet 객체 (text, start, duration 속성 포함)
        """
        try:
            transcript_list = self.ytt_api.list(video_id) # -> 가능한 자막의 언어 리스트
            transcript = transcript_list.find_transcript(languages) # -> 기본으로 ko, en 
            return transcript.fetch() #-> 가져오기
        except Exception as e:
            print(f"자막 불러오기 실패: {e}")
            return []

    @staticmethod
    def format_time(seconds: float) -> str:
        """초 단위를 '분:초' 문자열로 변환"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    def get_formatted_transcript(self, video_id: str, languages=['ko', 'en']) -> str:
        """
        fetch_transcript로 자막 가져와서 사람이 읽기 좋은 문자열 포맷으로 변환
        예: "안녕하세요. (0:08 - 0:13)"
        """
        transcription = self.fetch_transcript(video_id, languages)
        if not transcription:
            return ""
        
        formatted_lines = []
        for entry in transcription:
            start = entry.start
            end = start + entry.duration
            start_fmt = self.format_time(start)
            end_fmt = self.format_time(end)
            line = f"{entry.text} ({start_fmt} - {end_fmt})"
            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def get_structured_transcript(self, video_id: str, languages=['ko', 'en']) -> list[dict]:
        """
        fetch_transcript로 자막 가져와서
        [{'text': ..., 'start_time': ..., 'end_time': ...}, ...] 형식 리스트로 반환
        """
        transcription = self.fetch_transcript(video_id, languages)
        if not transcription:
            return []

        structured = []
        for entry in transcription:
            structured.append({
                "text": entry.text,
                "start_time": entry.start,
                "end_time": entry.start + entry.duration
            })

        return structured
