# Multi-Topic Stateful Pattern
This pattern reads from multiple Kafka topics or uses a state store (e.g., KTable) to perform aggregations or joins before emitting results to a target topic.
It requires setting `state_store_needed = true` and declaring the store in application.yml.
Processor class will implement stateful operations.
