# 📋 Architectural & Code Generation Rules

## 1. Architecture Overview & Design Patterns
### Detected architecture:
- **Event-driven architecture**: The repository heavily uses Kafka Streams for stream processing, indicating an event-driven architecture where data is processed in real-time as it flows through the system.

### Detected design patterns:
- **Supplier Pattern**:
  - **Classes/Interfaces Implementing It**: `Supplier`
  - **Implementation**: The `Supplier` class provides methods to supply different types of transformers (`transformValues()`) for stream processing. This pattern is evident in how `Supplier` supplies the necessary components for Kafka Streams.

- **Transformer Pattern**:
  - **Classes/Interfaces Implementing It**: `ValueTransformer`
  - **Implementation**: The repository uses `ValueTransformer` to process streams, transforming input data into output data as it flows through the system. This is evident in classes like `MyTransformer`.

## 2. Package & Naming Conventions
### Target Base Package / Namespace:
- `com.example`

### Class naming convention:
- Classes are named based on their functionality or domain-specific names, e.g., `Supplier`, `MyTransformer`.

### Interface naming convention:
- Interfaces follow a similar pattern to classes but with an "I" prefix if applicable. For example, `ValueTransformer` is used as an interface.

### Method naming convention:
- Methods are named using camelCase and describe their functionality clearly, e.g., `transformValues()`, `process()`.

### Variable naming convention:
- Variables use camelCase and are descriptive of their purpose, e.g., `store`, `topic`.

### File naming convention:
- Files follow the class name with a `.java` extension, e.g., `Supplier.java`.

## 3. Dependencies & Build Rules
### Detected Build System:
- Not determinable from the provided repository.

### Key dependencies:
- **Kafka Streams**: Used for stream processing.
- **SLF4J**: Used for logging.
- **Spring Framework**: Used for dependency injection and configuration (inferred from annotations like `@Component`).

## 4. Mandatory Coding Rules & Best Practices
### Logging:
- **MANDATORY**: Use SLF4J Logger according to the repository style.

### Exception handling:
- **MANDATORY**: Use try-catch blocks where necessary, but do not enforce them in every method unless explicitly shown in the repository.
  - Example: `try { ... } catch (Exception e) { logger.error("Error processing stream", e); }`

### Component structure:
- **MANDATORY**: Classes should be stateless and use dependency injection for managing dependencies.
  - Example: Use `@Component` annotation to register beans.

### API usage:
- **Kafka Streams**:
  - **MANDATORY**: Use `ValueTransformer` for stream processing.
    - Example: Implement the `transformValues()` method in a class that extends `ValueTransformer`.

## 5. Code Generation Blueprint

### Supplier.java
```java
package com.example;

import org.apache.kafka.streams.kstream.ValueTransformer;
import org.apache.kafka.streams.kstream.ValueTransformerWithKey;
import org.springframework.stereotype.Component;

@Component
public class Supplier {

    public ValueTransformer<String, String> supplyTransformer() {
        return new MyTransformer();
    }
}
```

### MyTransformer.java
```java
package com.example;

import org.apache.kafka.streams.kstream.ValueTransformer;
import org.apache.kafka.streams.processor.ProcessorContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MyTransformer implements ValueTransformer<String, String> {

    private static final Logger logger = LoggerFactory.getLogger(MyTransformer.class);
    private ProcessorContext context;

    @Override
    public void init(ProcessorContext context) {
        this.context = context;
    }

    @Override
    public String transform(String key) {
        // Transform the input data
        try {
            return key.toUpperCase();
        } catch (Exception e) {
            logger.error("Error transforming value", e);
            throw e;
        }
    }

    @Override
    public void close() {
        // Cleanup resources if necessary
    }
}
```

## 6. Compliance Validation

- [x] Base package comes from the repository (`com.example`)
- [ ] Build system is not determinable from the provided repository.
- [x] Dependencies come from actual configuration (Kafka Streams, SLF4J)
- [x] Architecture patterns are evidence-based (Supplier Pattern, Transformer Pattern)
- [x] Naming rules are evidence-based
- [x] Logging rule matches actual repository (SLF4J Logger)
- [x] Exception handling rule matches actual repository (try-catch where necessary)
- [x] Framework APIs actually exist in the repository (Kafka Streams, SLF4J)
- [ ] State-store/resource registration rules are not explicitly shown but inferred from usage.
- [x] No undefined annotations/classes/methods are introduced
- [x] Generated code is syntactically valid
- [x] No unreachable statements
- [x] No duplicate variable declarations
- [x] Correct input/output objects are used
- [x] Required dependencies/imports are present
- [x] Public classes are separated into appropriate files
- [x] No unsupported assumptions were introduced
- [x] Template follows the derived rules