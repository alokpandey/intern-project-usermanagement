import json
import time
from kafka import KafkaConsumer, errors
from settings import KAFKA_BOOTSTRAP
import time
from sqlalchemy.exc import OperationalError
from database import engine, SessionLocal, Base
from models import AuditEvent


print("Waiting for Postgres...")

for i in range(20):
    try:
        with engine.connect():
            print("Connected to Postgres")
            break
    except OperationalError:
        print("Postgres not ready yet, retrying...")
        time.sleep(3)
else:
    raise RuntimeError("Postgres never became available")

print("Creating audit tables if not present...")
Base.metadata.create_all(bind=engine)

# print("Starting audit consumer...")
print("Starting audit consumer...", flush=True)


db = SessionLocal()

for i in range(20):
    try:
        consumer = KafkaConsumer(
            "auth-events",
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="audit-consumer-group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        print("Connected to Kafka")
        break
    except errors.NoBrokersAvailable:
        print("Kafka not ready yet, retrying...")
        time.sleep(3)
else:
    raise RuntimeError("Kafka never became available")

for msg in consumer:
    print(
        f"AUDIT EVENT | topic={msg.topic} "
        f"partition={msg.partition} "
        f"offset={msg.offset} "
        f"value={msg.value}"
    )

    event = msg.value

    audit_row = AuditEvent(
        username=event["username"],
        operation=event["operation"],
        timestamp=event["timestamp"],
    )

    try:
        db.add(audit_row)
        db.commit()
        print(
            f"AUDIT STORED | username={event['username']} operation={event['operation']} timestamp={event['timestamp']} offset={msg.offset}"
        )
    except Exception as e:
        db.rollback()
        print("Audit DB insert failed:", e)
