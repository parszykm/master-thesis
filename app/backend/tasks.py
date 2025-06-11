from celery import Celery
import requests
import os
from time import sleep

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OCR_URL = os.getenv("OCR_URL", "http://ocr-service:9090/ocr")
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://data-extractor-service:8000/generate")

MAX_RETRIES=6
TIMEOUT=10

app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

# @app.task
# def process_invoice(image_bytes):
#     # Step 1: OCR
#     ocr_response = requests.post(OCR_URL, files={'image': ('invoice.png', image_bytes)})
#     ocr_text = ocr_response.json().get('text')

#     # Step 2: Extractor
#     extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
#     return extractor_response.json()

@app.task
def process_invoice(image_bytes):
    for i in range(MAX_RETRIES):
        try:
            # Step 1: OCR
            ocr_response = requests.post(OCR_URL, files={'image': ('invoice.png', image_bytes)})
            ocr_response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            
            try:
                response_json = ocr_response.json()
            except ValueError as e:
                raise ValueError(f"Invalid JSON from OCR service: {ocr_response.text}") from e

            if 'error' in response_json:
                raise ValueError(f"OCR service error: {response_json['error']}")
            ocr_text = response_json.get('text')
            if not ocr_text:
                raise ValueError("No text returned from OCR service")

            # Step 2: Extractor
            extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
            extractor_response.raise_for_status()
            
            try:
                return extractor_response.json()
            except ValueError as e:
                raise ValueError(f"Invalid JSON from extractor service: {extractor_response.text}") from e
        except requests.RequestException as e:
            # print(f"{i} try from {MAX_RETRIES} returned with failure")
            if i + 1 < MAX_RETRIES:
                print(f"Failed to process invoice - retrying {i+1}/{MAX_RETRIES}")
                sleep(TIMEOUT)
                continue
            else:
                print(f"Failed to process invoice: {str(e)}")