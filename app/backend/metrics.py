# from flask import Flask, request, jsonify
# from tasks import process_invoice_pipeline
# from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, start_http_server
# import time

# app = Flask(__name__)

# # Start Prometheus metrics server on separate port if needed (optional)
# # start_http_server(8001)

# # Metrics
# REQUEST_COUNT = Counter('flask_request_count', 'Total HTTP requests', ['method', 'endpoint'])
# TASK_SUBMITTED = Counter('tasks_submitted_total', 'Tasks submitted successfully')
# TASK_FAILED = Counter('tasks_submission_failed_total', 'Tasks failed to submit')
# REQUEST_LATENCY = Histogram('flask_request_latency_seconds', 'Request latency in seconds', ['endpoint'])

# @app.route('/metrics')
# def metrics():
#     return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# @app.route('/process', methods=['POST'])
# def process():
#     REQUEST_COUNT.labels(method='POST', endpoint='/process').inc()
#     start_time = time.time()

#     if 'image' not in request.files:
#         TASK_FAILED.inc()
#         return jsonify({'error': 'No image uploaded'}), 400

#     image = request.files['image']
#     image_bytes = image.read()

#     try:
#         task_chain = process_invoice_pipeline(image_bytes)
#         task = task_chain.apply_async()
#         TASK_SUBMITTED.inc()
#         return jsonify({'task_id': task.id}), 202
#     except Exception as e:
#         TASK_FAILED.inc()
#         return jsonify({'error': str(e)}), 500
#     finally:
#         REQUEST_LATENCY.labels(endpoint='/process').observe(time.time() - start_time)

# @app.route('/status/<task_id>', methods=['GET'])
# def check_status(task_id):
#     from tasks import app as celery_app
#     REQUEST_COUNT.labels(method='GET', endpoint='/status').inc()
#     result = celery_app.AsyncResult(task_id)
#     if result.ready():
#         return jsonify({'status': 'done', 'result': result.result})
#     return jsonify({'status': result.status})
