# from celery import Celery
# import requests
# import os
# from time import sleep

# REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
# OCR_URL = os.getenv("OCR_URL", "http://ocr-service:9090/ocr")
# EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://data-extractor-service:8000/generate")

# MAX_RETRIES=6
# TIMEOUT=10

# app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

# # @app.task
# # def process_invoice(image_bytes):
# #     # Step 1: OCR
# #     ocr_response = requests.post(OCR_URL, files={'image': ('invoice.png', image_bytes)})
# #     ocr_text = ocr_response.json().get('text')

# #     # Step 2: Extractor
# #     extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
# #     return extractor_response.json()

# @app.task
# def process_invoice(image_bytes):
#     for i in range(MAX_RETRIES):
#         try:
#             # Step 1: OCR
#             ocr_response = requests.post(OCR_URL, files={'image': ('invoice.png', image_bytes)})
#             ocr_response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            
#             try:
#                 response_json = ocr_response.json()
#             except ValueError as e:
#                 raise ValueError(f"Invalid JSON from OCR service: {ocr_response.text}") from e

#             if 'error' in response_json:
#                 raise ValueError(f"OCR service error: {response_json['error']}")
#             ocr_text = response_json.get('text')
#             if not ocr_text:
#                 raise ValueError("No text returned from OCR service")

#             # Step 2: Extractor
#             extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
#             extractor_response.raise_for_status()
            
#             try:
#                 return extractor_response.json()
#             except ValueError as e:
#                 raise ValueError(f"Invalid JSON from extractor service: {extractor_response.text}") from e
#         except requests.RequestException as e:
#             # print(f"{i} try from {MAX_RETRIES} returned with failure")
#             if i + 1 < MAX_RETRIES:
#                 print(f"Failed to process invoice - retrying {i+1}/{MAX_RETRIES}")
#                 sleep(TIMEOUT)
#                 continue
#             else:
#                 print(f"Failed to process invoice: {str(e)}")

from celery import Celery, chain
import requests
import os
from time import sleep

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://data-extractor-service:8000/generate")

# Define the app and tell it about the OCR task's queue
app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)
app.conf.task_routes = {'ocr.perform_ocr': {'queue': 'ocr_queue'}}

# This task is just for calling the extractor service
@app.task
def call_extractor(ocr_result: dict):
    # The result from the OCR task is passed in automatically
    if 'error' in ocr_result or not ocr_result.get('text'):
        error_message = ocr_result.get('error', 'OCR returned no text')
        raise ValueError(f"OCR step failed: {error_message}")
    
    ocr_text = ocr_result.get('text')
    print("OCR step successful, proceeding to data extraction.")

    # You can keep your retry logic here if you want
    extractor_response = requests.post(EXTRACTOR_URL, json={'invoice_text': ocr_text})
    extractor_response.raise_for_status()
    return extractor_response.json()


# This is no longer a task itself, but a function that creates the chain
def process_invoice_pipeline(image_bytes: bytes):
    """
    Creates and returns a Celery chain.
    1. The 'ocr.perform_ocr' task is sent to the 'ocr_queue'.
    2. Its result is automatically passed to the 'call_extractor' task.
    """
    # Note: We use .s() which is a "signature", creating a task blueprint
    task_chain = chain(
        # The first task to run
        app.signature('ocr.perform_ocr', args=[image_bytes]),
        # The second task, which receives the result of the first
        call_extractor.s()
    )
    return task_chain