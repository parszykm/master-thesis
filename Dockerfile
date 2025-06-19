# Dockerfile for Flower
# This file should be placed at the root of your project directory.
# Build with a command like: 
# docker buildx build --platform linux/amd64 -f Dockerfile.flower -t parszyk/flower-app:latest . --push

# Use a python base image that is consistent with your other workers
FROM python:3.10-slim

# Set the application's working directory inside the container
WORKDIR /app

# Set the PYTHONPATH environment variable. This is a crucial step.
# It tells Python to look for modules in the /app directory, allowing
# "backend.tasks" to be imported correctly.
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copy all your application code into the image.
# This command assumes your build context is the project root and your code
# lives in subdirectories like 'backend' and 'ocr_worker'.
COPY ./app/backend /app/backend
COPY ./app/ocr-worker /app/ocr_worker

# Install the necessary Python dependencies.
# This example assumes your requirements.txt is in the 'backend' directory.
# You should adjust this path if it's located elsewhere.
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN pip install flower

# Expose the default Flower port
EXPOSE 5555

# Define the command to start Flower.
# - It specifies the Celery app object within your code ('backend.tasks').
# - It connects directly to the Redis broker.
CMD ["celery", "-A", "backend.tasks", "flower", "--broker=redis://redis:6379/0", "--port=5555"]
