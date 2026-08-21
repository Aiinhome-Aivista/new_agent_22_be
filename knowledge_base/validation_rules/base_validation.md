# Base Validation Rules

These rules are strictly enforced during the code validation process.
If any of these conditions are violated, the generated package should be flagged with an error.

## 1. Application ID Validation
- **Rule**: The `application.yml` file must explicitly define the Kafka Streams application ID.
- **Check**: Ensure `spring.kafka.streams.application-id` is present in `application.yml` and matches the `application_id` defined in the generation spec.

## 2. Topic Naming Validation
- **Rule**: All source and target topics must follow the strict lowercase, hyphen-separated format (e.g., `my-topic-name`).
- **Check**: Verify that the topics mentioned in the `application.yml` and Java bindings do not contain spaces, uppercase characters, or special symbols (other than dots, hyphens, and underscores).

## 3. Processor Duplication
- **Rule**: The pipeline should not contain redundant or duplicate Processor classes doing the same logic.
- **Check**: Review the Java class names and logic. Ensure that there are no two `*Processor.java` files implementing identical stream logic.

## 4. Documentation
- **Rule**: The package must contain a `README.md` file.
- **Check**: Look for `README.md` in the root of the file manifest. It should briefly explain the microservice logic.

## 5. Configuration Completeness
- **Rule**: `application.yml` must exist and define at least one bootstrap server.
- **Check**: Ensure `application.yml` is present in the package.
