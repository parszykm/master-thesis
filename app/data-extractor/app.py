from flask import Flask, request, jsonify
import requests
import os
import sys
import json

app = Flask(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL")

if not OLLAMA_URL:
    print("OLLAMA_URL variable is not set")
    sys.exit(1)

PROMPT_TEMPLATE = '''<|input|>
### Template:
{{
  "invoice_number": "",
  "issue_date": "",
  "seller": "",
  "seller_address": "",
  "seller_tax_id": "",
  "iban": "",
  "client": "",
  "client_address": "",
  "client_tax_id": "",
  "items": [
    {{
      "description": "",
      "quantity": 0,
      "unit": ""
    }}
  ],
  "vat_rate": "",
  "net_total": 0,
  "vat_amount": 0,
  "gross_total": 0
}}

### Text:
{invoice_text}

<|output|>'''

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json()
        invoice_text = data.get("invoice_text")
        if not invoice_text:
            return jsonify({"error": "Missing 'invoice_text' in request"}), 400

        prompt = PROMPT_TEMPLATE.format(invoice_text=invoice_text)

        payload = {
            "model": "sroecker/nuextract-tiny-v1.5",
            "prompt": prompt,
            "stream": False
        }

        ollama_resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        ollama_resp.raise_for_status()
        resp_json = ollama_resp.json()

        response_str = resp_json.get("response")
        if not response_str:
            return jsonify({"error": "'response' field missing"}), 502

        # Convert the JSON string to a Python dictionary
        extracted_data = json.loads(response_str)

        return jsonify(extracted_data)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
