FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir Flask gunicorn prometheus_client

COPY server.py .

RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8001

ENV FLASK_APP=server.py
CMD ["flask", "run"]

