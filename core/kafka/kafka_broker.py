from faststream.kafka import KafkaBroker
from core.config.kafka_config import kafka_config



# 전역 Kafka Broker 설정 (기존 인스턴스 사용)
kafka_broker = KafkaBroker(kafka_config.bootstrap_servers)