# FROM python:3.10-slim

# RUN apt-get update && \
#     apt-get install -y tesseract-ocr libtesseract-dev && \
#     pip install flask pillow pytesseract && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# WORKDIR /app
# COPY . /app

# EXPOSE 9090
# CMD ["python", "app.py"]


FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["celery", "-A", "ocr_worker", "worker", "--loglevel=info", "--concurrency=1"]

