import os

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

EMAIL_VERIFY_TTL_SECONDS = int(os.getenv("EMAIL_VERIFY_TTL_SECONDS"))
PASS_VERIFY_TTL_SECONDS = int(os.getenv("PASS_VERIFY_TTL_SECONDS"))

FRONT_END_URL = os.getenv("FRONT_END_URL")

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_FROM = os.getenv("EMAIL_FROM")

RATE_LIMIT_RESET_PASSWORD = 3  # max 3 requests
RATE_LIMIT_PERIOD_SECONDS = 3600  # per hour

RATE_LIMIT_LOGIN_ATTEMPTS = 5  # max 5 login attempts
RATE_LIMIT_LOGIN_PERIOD_SECONDS = 900  # per 15 minutes