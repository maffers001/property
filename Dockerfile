FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY property_pipeline/ property_pipeline/

ENV DB_PATH=/app/data/property/labels.db
ENV DATA_PATH=/app/data/property

ENTRYPOINT ["python", "-m", "property_pipeline"]
