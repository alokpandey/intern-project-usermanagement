FROM python:3.11-slim

WORKDIR /listener

COPY requirements.txt /listener/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py /listener/models.py
COPY database.py /listener/database.py
COPY listener.py /listener/listener.py
COPY settings.py /listener/settings.py


CMD ["python", "-u", "listener.py"]
