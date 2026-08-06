# Single Topic Pattern
This pattern reads from a single Kafka source topic, processes each record statelessly, and outputs to a single target topic.
Class names follow the `<Domain>Processor` and `<Domain>Handler` naming convention.
Typically used for basic transformation, filtering, or simple message routing without maintaining local state.
