from faststream.kafka import KafkaBroker
from core.config.kafka_config import KafkaConfig

# 전역 Kafka Broker 설정
kafka_broker = KafkaBroker(KafkaConfig().bootstrap_servers)