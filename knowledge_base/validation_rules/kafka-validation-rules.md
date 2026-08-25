# Kafka Validation Rules

This document defines the automated validation rules for the Kafka event-driven architecture. These rules are used to validate generated blueprints and code for any new tract.

## 1. Code Structure Validation
- **Processor Validation**: 
  - Must be annotated with `@Component` or equivalent framework annotation.
  - Must have `@customAnnotation` specifying `inputTopic`, `outputTopic` (or conditionally based on logic), and `applicationId`.
  - Must delegate the actual processing stream to a `Supplier`.
- **Supplier Validation**:
  - Must instantiate or inject the appropriate `Handler` or `ValueTransformer`.
  - Must register any required `StoreNames` if stateful processing is used.
- **Handler Validation**:
  - Must contain the core business logic (e.g., transformations, aggregations).
  - Should not handle raw Kafka consumer/producer configurations manually.

## 2. Stateful Processing Validation (Multi-Topic)
- **State Store Registration**: If consuming from multiple dependent topics, a `KeyValueStore` MUST be initialized in the `init(ProcessorContext)` method.
- **Topic 1 (State Saver)**:
  - The transformation logic must save the value into the state store using `stateStore.put(key, value)`.
  - It must return `null` to prevent emitting incomplete data downstream.
- **Topic 2 (State Consumer & Processor)**:
  - Must attempt to retrieve the prior state: `stateStore.get(key)`.
  - If state is `null` (missing prior state), the code MUST call `context.forward(key, value, "error-topic")` (or equivalent configuration) and return `null`.
  - If state exists, it must combine the data, apply the business logic, and return the transformed object.
  - State MUST be cleaned up using `stateStore.delete(key)` to prevent unbounded growth.

## 3. Configuration & Resiliency Validation
- **No Hardcoded Configurations**: Topic names, consumer groups, and app IDs must not be hardcoded in standard logic; they must be provided via `@customAnnotation` or YAML properties.
- **Logging Compliance**: Every input stream must have a `.foreach()` or similar logging mechanism at the `INFO` level to log incoming `key` and `value`.
