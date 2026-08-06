# Error Topic Pattern
When processing encounters a recoverable error (e.g., parsing failure), the message is routed to a dedicated dead-letter queue (DLQ) or error topic.
Configure `error_topic_policy` to define exactly where errors go.
