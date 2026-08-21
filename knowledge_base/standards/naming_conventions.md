# Enterprise Naming Conventions & Resource Taxonomy

## 1. Kafka Topics
- **Format**: `<domain>.<subdomain>.<event-type>.<version>`
- **Casing**: All lowercase, dot-separated.
- **Example**: `finance.payments.processed.v1`
- **Environment Prefixing**: Avoid environment prefixes in the topic name itself; handle isolation via cluster separation or logical namespaces.

## 2. Consumer Groups
- **Format**: `<application-id>-<component>-<version>`
- **Example**: `payment-service-fraud-detector-v1`
- **Rule**: Must be unique per logical consumer application to prevent cross-service offset conflicts and partition rebalancing issues.

## 3. Java Classes (Processors & Topologies)
- **Format**: PascalCase with functional suffixes.
- **Topologies**: Must end with `Topology` (e.g., `FraudDetectionTopology`).
- **Processors/Transformers**: Must end with `Processor` or `Transformer` (e.g., `RiskScoreTransformer`).
- **Serdes**: Custom SerDes must end with `Serde` (e.g., `TransactionSerde`).

## 4. Application ID
- **Format**: Reverse domain notation combined with the service slug.
- **Example**: `com.company.finance.paymentservice`
- **Rule**: Must be globally unique across the enterprise Kafka ecosystem to guarantee isolated internal state stores and changelog topics.
