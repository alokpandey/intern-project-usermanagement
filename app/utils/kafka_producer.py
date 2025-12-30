import json
import time
from kafka import KafkaProducer, errors
from app.config.settings import KAFKA_BOOTSTRAP

for i in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
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

def publish_event(payload: dict) -> None:
    try:
        # producer.send("auth-events", message)
        producer.send("auth-events", payload).get(timeout=5)
    except Exception as e:
        print("Kafka publish failed:", e)
