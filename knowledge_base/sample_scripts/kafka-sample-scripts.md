# Kafka Sample Code & Scripts

This document contains the reference implementation scripts and sample code for the standard Kafka event-driven architecture. These samples act as the baseline code generation templates for new tracts.

## Scenario 1: Single Topic Processing

### Processor
```java
import org.apache.kafka.streams.kstream.KStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class MyKafkaStreamProcessor {
    private static final Logger logger = LoggerFactory.getLogger(MyKafkaStreamProcessor.class);
    private final MyKafkaStreamSupplier supplier;

    public MyKafkaStreamProcessor(MyKafkaStreamSupplier supplier) {
        this.supplier = supplier;
    }

    @customAnnotation(inputTopic = "input-topic", outputTopic = "output-topic", applicationId = "processor-app")
    public KStream<String, String> process(KStream<String, String> input) {
        input.foreach((key, value) -> logger.info("Processor received message [key={}, value={}]", key, value));
        KStream<String, String> filtered = input.filter((key, value) -> value != null && value.length() > 3);
        return supplier.supply(filtered);
    }
}
```

### Supplier & Handler
```java
@Component
public class MyKafkaStreamSupplier {
    public KStream<String, String> supply(KStream<String, String> filteredStream) {
        MyKafkaStreamHandler handler = new MyKafkaStreamHandler();
        return handler.handle(filteredStream);
    }
}

public class MyKafkaStreamHandler {
    private static final Logger logger = LoggerFactory.getLogger(MyKafkaStreamHandler.class);
    public KStream<String, String> handle(KStream<String, String> inputStream) {
        return inputStream.mapValues(value -> {
            logger.info("Handler processing value: {}", value);
            return value.toLowerCase() + "-processed";
        });
    }
}
```

## Scenario 2: Multi-Topic Stateful Processing

### Transformer (Topic 1 - Save State)
```java
public class Handler1Transformer implements ValueTransformerWithKey<String, String, String> {
    private KeyValueStore<String, String> stateStore;

    @Override
    public void init(ProcessorContext context) {
        this.stateStore = (KeyValueStore<String, String>) context.getStateStore(StoreNames.STORE_1);
    }

    @Override
    public String transform(String key, String value) {
        if (key == null || value == null) return null;
        String storedValue = stateStore.get(key);
        if (storedValue == null) {
            stateStore.put(key, value);
            return null; // Wait for second topic
        } else {
            String combined = storedValue + "|" + value;
            stateStore.delete(key);
            return combined.toUpperCase();
        }
    }
    @Override
    public void close() {}
}
```

### Transformer (Topic 2 - Process or Error)
```java
public class Handler2Transformer implements ValueTransformerWithKey<String, String, String> {
    private KeyValueStore<String, String> stateStore1;
    private ProcessorContext context;

    @Override
    public void init(ProcessorContext context) {
        this.context = context;
        this.stateStore1 = (KeyValueStore<String, String>) context.getStateStore(StoreNames.STORE_1);
    }

    @Override
    public String transform(String key, String value) {
        if (key == null || value == null) return null;
        String firstHandlerState = stateStore1.get(key);

        if (firstHandlerState == null) {
            // Forward to error topic if state is missing
            context.forward(key, value, "error-topic-processor");
            return null;
        }

        String combined = firstHandlerState + "|" + value;
        return new StringBuilder(combined).reverse().toString();
    }
    @Override
    public void close() {}
}
```
