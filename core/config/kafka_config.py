import os
from typing import List
from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka 설정 클래스(환경 변수와 기본값 관리)"""

    # 브로커 서버 주소 등록(환경변수에서 문자열로 받음)
    bootstrap_servers: str = "localhost:9092"
    # 보안 프로토콜 설정
    security_protocol: str = "PLAINTEXT"

    # Producer 설정
    # 메시지 전송 확인 레벨 (0=안함, 1=리더만, all=모든 복제본)
    producer_acks: str = "all"  
    # 전송 실패시 재시도 횟수
    producer_retries: int = 3
    # 메시지 압축 방식 (none, gzip, snappy, lz4, zstd)
    producer_compression_type: str = "gzip"

    # Consumer 설정
    consumer_group_id: str = "llm-service-group"
    # 오프셋이 없을 때 읽기 시작 위치 (earliest=처음부터, latest=최신부터)
    consumer_auto_offset_reset: str = "latest"  
    # 오프셋 자동 커밋 여부 (True시 자동으로 읽은 위치 저장)
    consumer_enable_auto_commit: bool = True
    # 자동 커밋 간격 (밀리초, 5초마다 오프셋 커밋)
    consumer_auto_commit_interval_ms: int = 5000
  

    # 토픽 설정
    overview_topic: str = "overview-topic"
    analysis_topic: str = "analysis-topic"
    idea_topic: str = "idea-topic"

    class Config:
        # 환경 변수에서 설정값을 읽어옴
        env_prefix = "KAFKA_"
        env_file = ".env"
        extra = "ignore"


# 전역에서 사용할 설정 인스턴스 (싱글톤 패턴)
kafka_config = KafkaConfig()