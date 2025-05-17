from flask import Flask, request, jsonify
from tasks import process_invoice
import os

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image = request.files['image']
    image_bytes = image.read()

    task = process_invoice.delay(image_bytes)
    return jsonify({'task_id': task.id}), 202

@app.route('/status/<task_id>', methods=['GET'])
def check_status(task_id):
    from tasks import app as celery_app
    result = celery_app.AsyncResult(task_id)
    if result.ready():
        return jsonify({'status': 'done', 'result': result.result})
    return jsonify({'status': result.status})
