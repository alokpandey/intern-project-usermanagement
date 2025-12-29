FROM python:3.11-slim

WORKDIR /tester

COPY requirements.txt /tester/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py /tester/models.py
COPY database.py /tester/database.py
COPY consumer.py /tester/consumer.py
COPY settings.py /tester/settings.py


CMD ["python", "-u", "consumer.py"]
