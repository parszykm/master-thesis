from celery import Celery
import requests
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OCR_URL = os.getenv("OCR_URL", "http://ocr-service:9090/ocr")
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://data-extractor-service:8000/generate")

app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

@app.task
def process_invoice(image_bytes):
    # Step 1: OCR
    ocr_response = requests.post(OCR_URL, files={'image': ('invoice.png', image_bytes)})
    ocr_text = ocr_response.json().get('text')

    # Step 2: Extractor
    extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
    return extractor_response.json()
