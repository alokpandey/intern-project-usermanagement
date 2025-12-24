import os

#environment variables for database, none mentioned in the dockerfile environment so likely just using defaults
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS"))

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP")

EMAIL_VERIFY_TTL_SECONDS = 30 * 60  # 30 minutes