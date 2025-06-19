# Use a slim, secure base image
FROM python:3.9-slim

WORKDIR /app

# Install only necessary dependencies
RUN pip install --no-cache-dir Flask gunicorn prometheus_client

# Copy the application code into the container
COPY server.py .

# Define the user to run the application
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8001

ENV FLASK_APP=server.py
CMD ["flask", "run"]

