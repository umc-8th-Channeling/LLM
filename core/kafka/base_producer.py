import json
import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from faststream.kafka import KafkaBroker
from core.config.kafka_config import KafkaConfig
from core.kafka.message import Message

logger = logging.getLogger(__name__)


class BaseProducer:
    """공통 Kafka Producer 클래스"""

    def __init__(self, broker: KafkaBroker, kafka_config: KafkaConfig):
        self.broker = broker
        self.config = kafka_config

    async def send_message(
        self,
        topic: str,
        message: Message        
    ) -> bool:
        """메시지를 Kafka 토픽에 발행 (재시도 로직 포함)"""
        # 메시지에 공통 메타데이터 추가
        enriched_message = self.add_metadata(message.model_dump())
        
        # 재시도 로직
        for attempt in range(self.config.producer_retries):
            try:
                # 메시지 발행
                await self.broker.publish(
                    message=enriched_message,
                    topic=topic
                )
                
                logger.info(f"✅ 메시지 발행 성공: {topic} (시도 {attempt + 1}/{self.config.producer_retries})")
                return True
                
            except Exception as e:
                # 마지막 시도가 아닌 경우 재시도
                if attempt < self.config.producer_retries - 1:
                    retry_delay = 2 ** attempt  # 지수 백오프: 1초, 2초, 4초...
                    logger.warning(
                        f"⚠️ 메시지 발행 실패: {topic}, "
                        f"시도 {attempt + 1}/{self.config.producer_retries}, "
                        f"오류: {e}, "
                        f"{retry_delay}초 후 재시도..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    # 모든 재시도 실패
                    logger.error(
                        f"❌ 메시지 발행 최종 실패: {topic}, "
                        f"모든 재시도 소진 ({self.config.producer_retries}회), "
                        f"오류: {e}"
                    )
                    return False
        
        return False

    def add_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지에 공통 메타데이터 추가"""
        return {
            **message,
            "timestamp": datetime.utcnow().isoformat()     
        }