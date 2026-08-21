# Industry Standard Architecture Validations

These rules enforce production-ready best practices for Kafka Streams and Spring Boot applications.

## 1. Unit Testing & Topology Validation
- **Rule**: Every Kafka Streams processor must have a corresponding JUnit test that uses `TopologyTestDriver`.
- **Check**: Verify there is a `*Test.java` file in `src/test/java/`. The test file MUST import and instantiate `TopologyTestDriver`, `TestInputTopic`, and `TestOutputTopic`. Tests that only use `contextLoads()` or basic assertions without a topology driver should FAIL.

## 2. Dead Letter Queue (DLQ) Routing
- **Rule**: Exception handling must include logical routing to a DLQ topic instead of dropping messages or relying on generic uncaught exceptions.
- **Check**: Verify that the Java code (Processor or Handler) has explicit `try/catch` blocks. In the `catch` block, exceptions should either throw a domain-specific exception that is handled by a Spring Error Handler, or explicitly branch the stream to a DLQ topic. Generic `throw new RuntimeException()` without DLQ handling should FAIL.

## 3. Dependency Integrity
- **Rule**: `pom.xml` must not mix conflicting Kafka paradigms.
- **Check**: Ensure `spring-kafka` and `kafka-streams` are present. The file MUST NOT contain `spring-cloud-stream-binder-kafka-streams` to avoid architectural mixing.

## 4. State Store Naming
- **Rule**: Any stateful operation (like `reduce`, `aggregate`, `windowedBy`) must define an explicitly named state store using `Materialized.as("store-name")`.
- **Check**: Look for `Materialized.as(...)` in the Processor. The state store name should NOT be generic (e.g., just "store"). It must incorporate the application ID or topic name to avoid collisions in a shared Kafka cluster.

## 5. Main Method Exception Handling
- **Rule**: The Spring Boot `main` method must let Spring handle startup failures, rather than swallowing them in a generic `try-catch`.
- **Check**: Ensure `SpringApplication.run(Application.class, args);` is not wrapped in a generic `try { ... } catch (Exception e) { log.error(...); }` block that prevents the JVM from exiting with a non-zero status on startup failure.

## 6. Proper Logging Practices
- **Rule**: Code must use `SLF4J` logging (e.g., `@Slf4j`) instead of `System.out.println()`.
- **Check**: Verify that `log.info`, `log.debug`, or `log.error` are used exclusively for logging. Any use of `System.out.println` should FAIL.
