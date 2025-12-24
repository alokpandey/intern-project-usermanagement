import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "auth-events",
    bootstrap_servers="localhost:9092",  # host can reach Docker
    auto_offset_reset="earliest",
    group_id="test-consumer",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

print("Listening for messages on auth-events...")

for message in consumer:
    print("Received message:", message.value)

with open("kafka_events.txt", "a") as f:
    for message in consumer:
        f.write(json.dumps(message.value) + "\n")

