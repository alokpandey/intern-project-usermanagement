from kafka import KafkaProducer
import json
import logging


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

def get_producer():
    producer = KafkaProducer(bootstrap_servers='kafka:9092')
    return producer

def send_message(message):
    producer = get_producer()
    topic = 'audit'
    producer.send(topic, json.dumps(message).encode("utf-8"))
    logger.info(f"Message sent to kafka: {message}")
    producer.flush()
    
