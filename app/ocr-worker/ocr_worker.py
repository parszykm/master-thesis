from celery import Celery
import pytesseract
from PIL import Image
import io
import os

# Connect to the same Redis broker as your other workers
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
app = Celery('ocr_tasks', broker=REDIS_URL, backend=REDIS_URL)

@app.task(name='ocr.perform_ocr')
def perform_ocr(image_bytes: bytes, start_time: float) -> dict:
    """
    This task receives image bytes, performs OCR, and returns the text.
    It runs on a dedicated, high-CPU OCR worker.
    """
    try:
        # Use an in-memory byte stream to open the image from the bytes
        image_stream = io.BytesIO(image_bytes)
        image = Image.open(image_stream)
        
        # Perform the CPU-intensive OCR processing
        text = pytesseract.image_to_string(image)
        if not text:
            return {'error': 'OCR process returned no text', 'start_time': start_time}
        return {'text': text, 'start_time': start_time}
    except Exception as e:
        # Catch potential errors from PIL or Pytesseract
        return {'error': f"OCR error: {str(e)}", 'start_time': start_time}