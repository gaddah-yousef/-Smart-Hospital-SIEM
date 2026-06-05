FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY . .

EXPOSE 8000 9101
CMD ["sh", "-c", "python -m stream.kafka_consumer worker -l info & uvicorn main:app --host 0.0.0.0 --port 8000"]
