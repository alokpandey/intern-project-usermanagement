from kafka import KafkaConsumer
from src.session import get_db
from src.models.DB_models import Audit
import json 
import logging


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

def get_consumer():
    consumer = KafkaConsumer('audit', bootstrap_servers='kafka:9092',         
                        group_id="audit-consumer-group",
                        auto_offset_reset="earliest",
                        enable_auto_commit=True)
    return consumer


def consume_message():
    consumer = get_consumer()
    logger.info("Consumer started")
    for message in consumer:
        try:
            logger.info(f"{message} : consumer message")
            data = json.loads(message.value.decode('utf-8'))
            db = next(get_db())
            new_audit = Audit(
                username=data['username'],
                operation=data['operation'],
                timestamp=data['timestamp']
            )
            db.add(new_audit)
            db.commit()
            db.refresh(new_audit)
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)

if __name__ == "__main__":
    consume_message()
