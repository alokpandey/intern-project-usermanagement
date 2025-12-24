import json
import time
from kafka import KafkaProducer, errors

for i in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
        )
        break
    except errors.NoBrokersAvailable:
        print("Kafka not ready, retrying...")
        time.sleep(2)
else:
    print("Failed to connect to Kafka after 10 retries")
    producer = None

def publish_event(event_type: str, payload: dict) -> None:
    message = {
        "type": event_type,
        "payload": payload,
    }

    try:
        producer.send("auth-events", message)
    except Exception as e:
        print("Kafka publish failed:", e)

# def publish_event(event_type: str, payload: dict) -> None:
#     message = {
#         "type": event_type,
#         "payload": payload,
#     }

#     try:
#         # send() returns a FutureRecordMetadata object
#         future = producer.send("auth-events", message)

#         # add callback to print when message is successfully sent
#         def on_success(record_metadata):
#             print(
#                 f"Published event '{event_type}' to topic '{record_metadata.topic}' "
#                 f"partition {record_metadata.partition} at offset {record_metadata.offset}"
#             )

#         def on_error(excp):
#             print("Failed to publish event:", excp)

#         future.add_callback(on_success)
#         future.add_errback(on_error)

#         # flush to ensure it is sent immediately (for testing)
#         producer.flush()

#     except Exception as e:
#         print("Kafka publish failed:", e)
