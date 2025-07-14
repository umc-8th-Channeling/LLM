import json
import logging
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
        """메시지를 Kafka 토픽에 발행"""
        try:
            # 메시지에 공통 메타데이터 추가
            enriched_message = self.add_metadata(message)

            # 메시지 발행
            await self.broker.publish(
                message=enriched_message,
                topic=topic
            )

            logger.info(f"✅ 메시지 발행 성공: {topic}")
            return True

        except Exception as e:
            logger.error(f"❌ 메시지 발행 실패: {topic}, 오류: {e}")
            return False

    def add_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """메시지에 공통 메타데이터 추가"""
        return {
            **message,
            "timestamp": datetime.utcnow().isoformat()     
        }