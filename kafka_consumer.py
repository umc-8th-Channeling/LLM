import asyncio
import logging
from core.kafka.kafka_broker import kafka_broker
from domain.report.service.report_consumer_impl import ReportConsumerImpl as ReportConsumer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Kafka Consumer 시작"""
    logger.info("= Kafka Consumer 시작...")
  
    report_consumer = ReportConsumer(kafka_broker)
    report_consumer.register_handler("overview-topic", report_consumer.handle_overview)
    report_consumer.register_handler("analysis-topic", report_consumer.handle_analysis)
    report_consumer.register_handler("idea-topic", report_consumer.handle_idea)

    await kafka_broker.start()
    logger.info("= Kafka Broker 시작 완료")

    # Consumer 시작
    topics = ["overview-topic", "analysis-topic", "idea-topic"]
    await report_consumer.start_consuming(topics)
    logger.info(f"= Kafka Consumer 시작: {topics}")
    
    try:
        
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("= Kafka Consumer 중단 요청")
    finally:
        
        await report_consumer.stop_consuming()
        await kafka_broker.close()
        logger.info("= Kafka Consumer 중단 완료")


if __name__ == '__main__':
    asyncio.run(main())