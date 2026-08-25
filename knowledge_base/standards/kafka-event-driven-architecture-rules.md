# Kafka Event-Driven Architecture Standards

## Overview
This document outlines the industry standard rules for building event-driven microservices using Apache Kafka, based on the standard processing pipeline. All tracts must follow these rules by default. Modifications to these rules are handled on a per-tract basis in the database.

## Architecture Pattern
1. **Pipeline Structure**: Every service must implement the standard processing pipeline: `Processor → Supplier → Handler → Supplier → Kafka Topic`.
2. **Processor Component**: 
   - Responsible for consuming incoming events.
   - Must leverage a shared enterprise communication library for Kafka integration.
   - Handles serialization/deserialization and communication management.
3. **Externalized Configuration**: Kafka-related configurations (topic names, consumer groups, partitions, concurrency, retries) MUST be externalized in YAML files (e.g., using `@customAnnotation`).
4. **Supplier Component**:
   - Invoked by the Processor.
   - Instantiates and invokes the appropriate Handler implementation.
   - Publishes the resulting event (returned by Handler) to the next Kafka topic.
5. **Handler Component**:
   - Encapsulates ALL business logic.
   - Responsible for mandatory field validations, business rules validations, duplicate detection, data enrichment, and transformation.
   - Handles error scenarios and prepares failure status events, triggering alerts if required.

## Multi-Topic Stateful Processing
For applications consuming from multiple input topics with strict ordering dependency (e.g., Topic 1 must be processed before Topic 2 for a given key):
1. **First Handler (Topic 1)**:
   - Must consume messages from the first input topic.
   - Must store the received message data (keyed by message key) into an internal Kafka Streams local state store (e.g., `KeyValueStore`).
   - Must NOT emit any output messages to downstream Kafka topics.
2. **Second Handler (Topic 2)**:
   - Must consume messages from the second input topic.
   - Must read the prior state stored by the First Handler.
   - **If state exists**: Combine stored data with current message, apply business logic, emit the processed message to the output topic, and MUST delete the state to prevent unbounded storage growth.
   - **If state does NOT exist**: Route the original message unaltered to an `error-topic` for manual investigation or reprocessing. Do NOT produce an output message.
3. **State Management**:
   - Must use durable, fault-tolerant local Kafka Streams state stores.
   - Handlers must maintain processing isolation and avoid emitting intermediate streams.
4. **Reliability & Logging**:
   - All consumed messages MUST be logged at the INFO level (with keys and values).
   - Routing to the error topic MUST be logged with WARNING or ERROR levels indicating the ordering violation.
   - The application must handle restarts and rebalances gracefully without data loss.

