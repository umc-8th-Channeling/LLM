import asyncio
import logging
from faststream.kafka import KafkaBroker
from core.config.kafka_config import KafkaConfig
from domain.report.service.report_consumer import ReportConsumer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Kafka Consumer 시작"""
    logger.info("= Kafka Consumer 시작...")
    broker = KafkaBroker(KafkaConfig().bootstrap_servers)
    
    report_consumer = ReportConsumer(broker)
    report_consumer.register_handler("report-requests", report_consumer.handle_overview)
    report_consumer.register_handler("analysis-generation", report_consumer.handle_analysis)
    report_consumer.register_handler("idea-generation", report_consumer.handle_idea)
    
     
    await broker.start()
    logger.info("= Kafka Broker 시작 완료")

    # Consumer 시작
    topics = ["report-requests", "analysis-generation", "idea-generation"]
    await report_consumer.start_consuming(topics)
    logger.info(f"= Kafka Consumer 시작: {topics}")
    
    try:
        
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("= Kafka Consumer 중단 요청")
    finally:
        
        await report_consumer.stop_consuming()
        await broker.close()
        logger.info("= Kafka Consumer 중단 완료")


if __name__ == '__main__':
    asyncio.run(main())