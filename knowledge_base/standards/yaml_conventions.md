# Infrastructure & Configuration Standards (YAML)

## 1. Spring Kafka Configuration Hierarchy
- Configuration must be hierarchically structured in `application.yml` or `application.yaml`.
- Separate properties logically: `spring.kafka.streams`, `spring.kafka.producer`, `spring.kafka.consumer`.
- Avoid flat key-value properties unless strictly required by a legacy framework integration.

## 2. Environment Variables & Secrets Management
- **No Hardcoding**: Never hardcode credentials, SASL JAAS configs, truststores, or bootstrap servers in YAML files.
- **Injection**: Inject sensitive data dynamically via environment variables (e.g., `${KAFKA_BOOTSTRAP_SERVERS}`).
- **Vault Integration**: Integration with enterprise secret managers (e.g., HashiCorp Vault, AWS Secrets Manager) is mandatory for production credentials.

## 3. Deployment Configuration (Kubernetes)
- **Health Checks**: Liveness & Readiness Probes are mandatory for all Kafka Streams deployments. Bind them to the Kafka Streams state listener (e.g., `RUNNING` or `REBALANCING`).
- **Resource Allocation**: Always define explicit CPU and Memory requests/limits to prevent JVM memory exhaustion and OOM kills.
- **State Store Persistence**: Use StatefulSets with Persistent Volume Claims (PVCs) for RocksDB state stores to ensure fast recovery upon pod restarts.
