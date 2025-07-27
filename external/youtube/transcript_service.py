from youtube_transcript_api import YouTubeTranscriptApi #// 자막 가져오는 비공식 라이브러리 -> 로컬에서는 잘 작동하는데, 배포에서는 잘 될 지 모르겠음


class TranscriptService:
    """YouTube 자막 처리 서비스"""
    
    def __init__(self):
        """TranscriptService 초기화"""
        pass
    
    def get_formatted_transcript(self, video_id: str, languages=['ko', 'en']) -> str:
        try:
            ytt_api = YouTubeTranscriptApi() #-> 해당 라이브러리는 구현체를 사용해야 함
            transcript_list = ytt_api.list(video_id) # -> 가능한 자막의 언어 리스트
            transcript = transcript_list.find_transcript(languages) # -> 기본으로 ko, en 
            transcription = transcript.fetch() #-> 가져오기

            #// 원래는 자막, 시작 시간, 동작 시간 이렇게 3개로 나눠 오는데, 프롬프트가 이해하기 쉽도록 데이터 전처리
            def format_time(seconds: float) -> str:
                m = int(seconds // 60) 
                s = int(seconds % 60)
                return f"{m}:{s:02d}"

            formatted_lines = []
            for entry in transcription:
                start = entry.start
                end = start + entry.duration
                start_fmt = format_time(start)
                end_fmt = format_time(end)

                # 예: "안녕하세요. 채널링 팀원 여러분. (0:08 - 0:13)"
                line = f"{entry.text} ({start_fmt} - {end_fmt})"
                formatted_lines.append(line)

            return "\n".join(formatted_lines)

        except Exception as e:
            print(f"자막 불러오기 실패: {e}")
            return ""
