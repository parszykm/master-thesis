from flask import Flask, request, Response
from prometheus_client import Summary, CollectorRegistry, generate_latest
import os
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


app = Flask(__name__)
registry = CollectorRegistry()


CHAIN_DURATION = Summary(
    'invoice_chain_duration_seconds',
    'Total time from submission to chain completion',
    registry=registry
)

@app.route('/record_duration', methods=['POST'])
def record_duration():
    """
    Receives a duration from a Celery worker and observes it.
    """
    try:
        data = request.get_json()
        duration = data.get('duration')
        if duration is not None:
            
            CHAIN_DURATION.observe(float(duration))
            logging.info(f"Recorded duration: {duration} seconds")
            return "OK", 200
        else:
            logging.warning("Bad Request: Missing 'duration' in payload")
            return "Bad Request: Missing 'duration'\n", 400
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return "Internal Server Error\n", 500

@app.route('/metrics')
def metrics():
    """
    Exposes the Prometheus metrics.
    """
    return Response(generate_latest(registry), mimetype='text/plain')

if __name__ == '__main__':
    
    port = int(os.getenv("METRICS_PORT", "8001"))
    app.run(host='0.0.0.0', port=port)
