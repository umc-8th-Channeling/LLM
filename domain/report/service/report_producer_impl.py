from domain.report.service.report_producer import ReportProducer


class ReportProducerImpl(ReportProducer):
    async def produce(self, topic: str, key: str, value: str) -> None:
        # Kafka에 메시지를 전송하는 로직 구현
        pass