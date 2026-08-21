# Enterprise Data Integrity & Resiliency Standards

## 1. Processing Guarantees
- **Exactly-Once Semantics (EOS)**: All Kafka Streams applications processing financial, transactional, or state-mutating data MUST enable exactly-once semantics (`processing.guarantee="exactly_once_v2"`).
- **Idempotency**: Producer idempotency must be enabled (`enable.idempotence=true`) by default for all standalone producers to prevent duplicate records on network retries.

## 2. Observability & Tracing
- **Correlation IDs**: All events MUST carry a standard `X-Correlation-ID` header to allow distributed end-to-end tracing across microservices (e.g., using OpenTelemetry, Zipkin, or Jaeger).
- **Metrics**: Expose JMX metrics via Prometheus exporter for Kafka Streams thread states, consumer lag, and processing latency.

## 3. Error Handling & Dead Letter Queues
- **Poison Pills**: Configure `default.deserialization.exception.handler` to a custom DLQ handler to prevent pipeline blockage on bad data.
- **Dead Letter Queues (DLQ)**: Deserialization errors and unrecoverable processing exceptions must be routed to a standardized DLQ topic (e.g., `<original-topic>.dlq`) with the stack trace appended to the headers.
- **Transient Failures**: Implement exponential backoff for transient network or external database exceptions within processors.