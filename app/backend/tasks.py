from celery import Celery, chain
import time
import requests
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://data-extractor-service:8000/parse-invoice")
METRICS_SERVER_URL = os.getenv("METRICS_SERVER_URL", "http://localhost:8001/record_duration")

app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)
app.conf.task_routes = {'ocr.perform_ocr': {'queue': 'ocr_queue'}}

def report_duration(duration: float):
    """
    Sends the calculated duration to the metrics sidecar service.
    """
    try:
        response = requests.post(METRICS_SERVER_URL, json={'duration': duration}, timeout=1)
        response.raise_for_status()
        logging.info(f"Worker PID: {os.getpid()} - Successfully reported duration ({duration:.2f}s) to metrics server.")
    except requests.RequestException as e:
        logging.error(f"Worker PID: {os.getpid()} - Could not report duration to metrics server: {e}")

@app.task
def call_extractor(ocr_result: dict):
    """
    Processes OCR result, reports duration, and calls the data extractor.
    """
    start_time = ocr_result.get('start_time')
    if not start_time:
        raise ValueError("Missing start_time in ocr_result")

    end_time = time.time()
    duration = end_time - start_time
    report_duration(duration)

    if 'error' in ocr_result or not ocr_result.get('text'):
        error_message = ocr_result.get('error', 'OCR returned no text')
        raise ValueError(f"OCR step failed: {error_message}")

    ocr_text = ocr_result.get('text')
    logging.info(f"Worker PID: {os.getpid()} - OCR step successful, proceeding to data extraction.")

    extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
    extractor_response.raise_for_status()
    return extractor_response.json()

def process_invoice_pipeline(image_bytes: bytes, start_time: float):
    """
    Constructs the Celery chain for processing an invoice.
    """
    task_chain = chain(
        app.signature('ocr.perform_ocr', args=[image_bytes, start_time]),
        call_extractor.s()
    )
    return task_chain
