FROM python:3.11

WORKDIR /backend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000